"""
main.py — เซิร์ฟเวอร์ FastAPI

Endpoints:
  GET  /                    → Landing page
  GET  /dashboard           → 4-camera dashboard
  GET  /detect              → Detection tool (image / video / webcam)
  GET  /stream/{cam_id}     → MJPEG stream ของแต่ละกล้อง
  GET  /stats               → สถานะระบบ JSON
  GET  /api/settings        → การตั้งค่าปัจจุบัน (model, conf)
  POST /api/settings        → อัปเดต model / conf สำหรับ dashboard
  POST /predict/image       → ตรวจจับภาพที่อัปโหลด
  POST /predict/video       → ตรวจจับทุก frame ในวิดีโอ → คืน stats
  POST /predict/webcam_frame → ตรวจจับ 1 frame จาก webcam (base64)
"""
import base64
import os
import tempfile
import time

import cv2
import numpy as np
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
from detector import Detector
from camera import CameraWorker
from state import state

app = FastAPI(title="Emergency Vehicle Detection")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# โหลดโมเดลครั้งเดียวตอน startup
detector = Detector()
workers  = {cam: CameraWorker(cam, detector) for cam in config.CAMERA_VIDEOS}
for w in workers.values():
    w.start()


# ===== Pages =====

@app.get("/")
def landing(request: Request):
    return templates.TemplateResponse(request, "landing.html", {"active": "home"})


@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "cameras": config.CAMERA_LABELS,
        "using_custom": detector.using_custom,
        "active": "dashboard",
    })


@app.get("/detect")
def detect_page(request: Request, tab: str = "image"):
    valid_tabs = {"image", "video", "webcam"}
    safe_tab = tab if tab in valid_tabs else "image"
    return templates.TemplateResponse(request, "detect.html", {
        "active": safe_tab,
        "active_tab": safe_tab,
    })


@app.get("/results")
def results_page(request: Request):
    return templates.TemplateResponse(request, "stats.html", {"active": "results"})


@app.get("/about")
def about_page(request: Request):
    return templates.TemplateResponse(request, "about.html", {"active": "about"})


# ===== Dashboard streams / stats =====

@app.get("/stream/{cam_id}")
def stream(cam_id: str):
    worker = workers.get(cam_id)
    delay  = 1.0 / max(config.TARGET_FPS, 1)

    def gen():
        while True:
            jpg = worker.get_jpeg() if worker else None
            if jpg:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
            time.sleep(delay)

    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/stats")
def stats():
    snap = state.snapshot()
    snap["model_info"] = detector.get_model_info(snap["current_model"])
    return JSONResponse(snap)


# ===== Settings API (for dashboard model/conf selector) =====

@app.get("/api/settings")
def get_settings():
    return JSONResponse({
        "model": state.current_model,
        "conf":  round(state.current_conf, 2),
    })


@app.post("/api/settings")
async def post_settings(request: Request):
    body = await request.json()
    if "model" in body:
        state.set_model(str(body["model"]))
    if "conf" in body:
        state.set_conf(float(body["conf"]))
    return JSONResponse({"ok": True, "model": state.current_model, "conf": state.current_conf})


# ===== Detection endpoints =====

@app.post("/predict/image")
async def predict_image(
    file:       UploadFile = File(...),
    model_name: str        = Form("x"),
    conf:       float      = Form(0.25),
):
    data  = await file.read()
    arr   = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse({"error": "ไม่สามารถอ่านไฟล์ภาพได้"}, status_code=400)

    dets     = detector.infer(frame, model_key=model_name, conf=conf)
    annotated = detector.draw(frame, dets)

    _, buf   = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
    img_b64  = base64.b64encode(buf.tobytes()).decode()
    info     = detector.get_model_info(model_name)

    return JSONResponse({
        "image":        img_b64,
        "detections":   [
            {"name": d["name"], "conf": round(d["conf"], 3), "box": list(d["box"])}
            for d in dets
        ],
        "infer_ms":     round(detector.last_infer_ms, 1),
        "model_name":   info["name"],
        "model_params": info["params"],
    })


@app.post("/predict/video")
async def predict_video(
    file:       UploadFile = File(...),
    model_name: str        = Form("x"),
    conf:       float      = Form(0.25),
):
    data   = await file.read()
    suffix = os.path.splitext(file.filename or ".mp4")[1] or ".mp4"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    summary: dict[str, int] = {}
    sample_b64 = None

    try:
        cap         = cv2.VideoCapture(tmp_path)
        frame_count = 0
        t_start     = time.time()

        while True:
            ok, frame = cap.read()
            if not ok:
                break
            dets = detector.infer(frame, model_key=model_name, conf=conf)
            frame_count += 1

            for d in dets:
                name = d["name"].lower()
                summary[name] = summary.get(name, 0) + 1

            # เก็บตัวอย่าง frame แรกที่มี detection
            if dets and sample_b64 is None:
                annotated  = detector.draw(frame, dets)
                _, buf     = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
                sample_b64 = base64.b64encode(buf.tobytes()).decode()

        cap.release()
        total_ms = (time.time() - t_start) * 1000
        info     = detector.get_model_info(model_name)

        return JSONResponse({
            "frame_count":       frame_count,
            "total_ms":          round(total_ms, 1),
            "avg_ms_per_frame":  round(total_ms / max(frame_count, 1), 1),
            "detections_summary": summary,
            "sample_frame":      sample_b64,
            "model_name":        info["name"],
            "model_params":      info["params"],
        })
    finally:
        os.unlink(tmp_path)


@app.post("/predict/webcam_frame")
async def predict_webcam_frame(request: Request):
    body      = await request.json()
    img_b64   = body.get("image", "")
    model_name = body.get("model_name", "m")
    conf      = float(body.get("conf", 0.25))

    # base64 → numpy
    raw  = base64.b64decode(img_b64.split(",")[-1])
    arr  = np.frombuffer(raw, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse({"error": "ถอดรหัสภาพไม่ได้"}, status_code=400)

    dets = detector.infer(frame, model_key=model_name, conf=conf)
    info = detector.get_model_info(model_name)

    return JSONResponse({
        "detections": [
            {"name": d["name"], "conf": round(d["conf"], 3), "box": list(d["box"])}
            for d in dets
        ],
        "infer_ms":     round(detector.last_infer_ms, 1),
        "model_name":   info["name"],
        "model_params": info["params"],
    })
