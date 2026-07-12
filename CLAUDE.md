# CLAUDE.md — Project Guide (Emergency Vehicle Detection System)

> ไฟล์นี้ Claude Code อ่านอัตโนมัติทุกครั้งที่เปิด project
> ใช้เป็น "กฎประจำโปรเจกต์" เพื่อให้โค้ดที่สร้างตรงแนวทางโดยไม่ต้องสั่งซ้ำ
> **สถานะล่าสุดอยู่ใน `docs/STATUS.md` เสมอ — อ่านไฟล์นั้นก่อนเริ่มงานใหม่**

---

## บทบาท

คุณคือ senior full-stack / ML engineer ที่ช่วยพัฒนา **Emergency Vehicle Detection System (EVD)**

โปรเจกต์จบ (Final Year Project) ของนักศึกษา **มหาวิทยาลัยแห่งชาติลาว (NUOL) · คณะวิทยาศาสตร์ธรรมชาติ · สาขาวิทยาการคอมพิวเตอร์ · FYP 2025–26**

ระบบตรวจจับ **รถฉุกเฉิน** (ambulance / firetruck / police) จากภาพกล้องสี่แยกด้วย YOLOv8
เพื่อ (เป้าหมายปลายทาง) **ให้สิทธิ์ไฟเขียว (signal preemption)** กับทิศที่มีรถฉุกเฉินวิ่งมา — ลดเวลารถฉุกเฉินติดไฟแดง

**เป้าหมายเฉพาะหน้า:** พาระบบจาก prototype (รันไฟล์วิดีโอจำลอง) → **ใช้งานจริงได้ระดับ production** ให้ทันวัน present

ตอบเป็น **ภาษาไทย** แต่ technical term และ code คงเป็นภาษาอังกฤษ
**end-user UI = ภาษาลาว** (มีอยู่แล้วในทุก template) · **dev communication = ภาษาไทย**

---

## Tech Stack (ปัจจุบัน — ยืนยันก่อนเปลี่ยน)

- **Backend:** Python · FastAPI · Uvicorn (ASGI)
- **ML/CV:** Ultralytics YOLOv8 (2 โมเดล: `x` แม่น / `m` เร็ว) · OpenCV · NumPy · PyTorch
- **Frontend:** Jinja2 templates (server-rendered) + vanilla JS + CSS — **ไม่มี build step, ไม่มี framework**
- **กล้อง (ปัจจุบัน):** ไฟล์ `.mp4` วนลูป จำลอง 4 กล้อง (north/east/south/west) — **ยังไม่ใช่ RTSP/IP จริง**
- **State:** in-memory (thread-safe singleton) — **ยังไม่มี database**
- **Deploy:** รัน local ผ่าน `python run.py` — **ยังไม่มี Docker/nginx/production**

> ก่อนเพิ่ม dependency หรือเปลี่ยน stack (เช่นเติม DB, message queue, frontend framework) → **ยืนยัน scope สั้น ๆ ก่อน** ทุกครั้ง โปรเจกต์นี้ต้อง demo ได้ อย่าเพิ่มความซับซ้อนที่ทำให้รันไม่ขึ้นตอน present

---

## โครงสร้างโปรเจกต์

```
emergency-vehicle-webapp/
├── app/                  # Python package (โค้ด backend ทั้งหมด)
│   ├── __init__.py
│   ├── main.py           # FastAPI app + routes ทั้งหมด
│   ├── config.py         # ⚙️ ค่าคอนฟิกทุกอย่างที่เดียว (paths, conf, device, fps)
│   ├── detector.py       # Detector: โหลด YOLO + infer() + draw()
│   ├── camera.py         # CameraWorker: 2 thread ต่อกล้อง (playback + inference)
│   └── state.py          # SystemState: signals/counts/log/settings (thread-safe)
├── static/               # CSS / JS / logo  (เสิร์ฟที่ /static)
├── templates/            # Jinja2 HTML (base + 5 หน้า)
├── models/               # YOLO weights (.pt — gitignored)
├── videos/               # คลิป 4 กล้อง (.mp4 — gitignored)
├── notebooks/            # Colab notebooks (เทรนโมเดล)
├── docs/                 # เอกสารโปรเจกต์ (อ่าน STATUS.md ก่อนเริ่มงาน)
├── run.py                # launcher → uvicorn app.main:app
└── requirements.txt
```

---

## Coding Style & Conventions

- **Config รวมที่เดียว:** ทุกค่าที่ปรับได้ (path, threshold, device, fps, class) อ่านผ่าน `app/config.py` — **ห้าม hardcode กระจายตามไฟล์**
- **Imports:** ภายใน package ใช้ relative import (`from . import config`, `from .detector import ...`) — โมดูลย้ายเข้า `app/` แล้ว **ห้ามกลับไปใช้ `import config` แบบ absolute** (จะ import ไม่เจอ)
- **Path:** ใช้ `config.PROJECT_ROOT` / `config.BASE_DIR` (คำนวณจาก `__file__`) — **ห้ามพึ่ง current working directory** (พังเมื่อรันจากที่อื่น)
- **Naming:** ตัวแปร/ฟังก์ชัน `snake_case`, ค่าคงที่ `UPPER_SNAKE_CASE`, class `PascalCase`, ไฟล์ `snake_case.py`, Jinja template `lowercase.html`
- **Async:** route handler ที่ทำ I/O เป็น `async def`; งาน CPU หนัก (YOLO infer) รันใน thread แยกอยู่แล้ว (CameraWorker) — **อย่า block event loop ด้วย inference ตรง ๆ**
- **Thread safety:** state ที่หลาย thread แตะต้องล็อกด้วย `self._lock` (ดู `state.py`, `camera.py`) — GPU/model call ต้อง serialize ผ่าน `detector._lock`
- **Error handling:** loop ของกล้อง (playback/inference) **ห้าม throw จน thread ตาย** — log แล้วไปต่อ; API ตอบ HTTP status ที่เหมาะสม (400 bad input, 500 server) พร้อม JSON `{ "error": "..." }`
- **Comment:** ภาษาอังกฤษหรือไทยก็ได้ (โค้ดเดิมเป็นไทย) อธิบาย "ทำไม" ไม่ใช่ "ทำอะไร" — เน้น edge case (thread timing, model fallback, coordinate scaling)
- **Frontend:** ไม่มี build step — แก้ `.js`/`.css` ตรง ๆ แล้ว **bump cache-busting version** ที่ template (`?v=N`) ไม่งั้น browser cache ค้าง

---

## หลักการสำคัญ (บทเรียนที่พิสูจน์แล้ว / จุดพลาดง่าย)

### Verify ก่อนเชื่อ — ทุกครั้ง
- อย่าสรุปว่า "เสร็จ" จนเห็นผลจริงบนหน้าจอ — compile ผ่าน ≠ ทำงานถูก
- **เครื่อง dev นี้ venv เสีย** (ชี้ interpreter เครื่องอื่นที่หายไป) และ **ไม่มี Python บน PATH** → รัน runtime verify บนเครื่องนี้ไม่ได้ ต้องบอกผู้ใช้ให้สร้าง venv ใหม่แล้วทดสอบเอง หรือ verify ด้วย static check (import graph, path resolution) แล้วระบุชัดว่ายังไม่ได้ทดสอบ runtime
- โมเดลโหลดตอน import `app.main` (Detector สร้างตอน module top-level) → การ import main = โหลด YOLO จริง (หนัก/ช้า/อาจดาวน์โหลด weights) อย่า import เพื่อเช็ค syntax เฉย ๆ ใช้ `py_compile` แทน

### แยก Prototype vs Production ให้ขาด
- ตอนนี้อยู่เฟส **prototype รัน local** — กล้อง = วิดีโอ, state = memory, ไม่มี auth/DB/deploy
- งานที่จะพาไป production ต้องคิดถึง: กล้อง RTSP จริง, persistence, การกู้คืนเมื่อ restart, GPU inference, ความปลอดภัย — ดู `docs/PRODUCTION_ROADMAP.md`
- **อย่าเผลอทำลาย demo path ที่ใช้ได้อยู่** ระหว่างเพิ่มฟีเจอร์ production — เก็บให้ระบบยัง `python run.py` ขึ้นได้เสมอ

### Data / Detection — จุดที่ทำให้ตัวเลขเพี้ยน
- **counts เป็น session-scoped ใน memory** — เพิ่มเมื่อรถฉุกเฉิน "โผล่ใหม่" (set difference `emerg_now - prev` ต่อกล้อง) → **restart แล้วรีเซ็ต** และนับซ้ำได้ถ้ารถหลุด frame แล้วกลับมา (ยังไม่มี tracking ต่อคัน)
- ถ้าจะรายงานสถิติจริง (ต่อวัน/ชม.) ต้องมี **persistence + object tracking (เช่น ByteTrack)** ไม่ใช่ frame-level counter ปัจจุบัน
- **สัญญาณไฟ = display อย่างเดียว** — `CLEAR` เมื่อกล้องนั้นเจอ emergency, `STOP` เมื่อไม่เจอ — **ยังไม่ต่อฮาร์ดแวร์ไฟจราจรจริง** และยังไม่มี logic เลือกทิศเมื่อหลายกล้องเจอพร้อมกัน

### ⚠️ หน้า Results = ตัวเลข hardcode
- `templates/stats.html` มี metric (mAP50 97.54%, precision/recall, dataset 2,847 รูป ฯลฯ) **เขียนตายตัวใน HTML** — ไม่ได้อ่านจากผล eval จริง
- ถ้าอาจารย์/กรรมการถามที่มา ต้องมีผล training จริงรองรับ — ควรทำให้ตัวเลขมาจากไฟล์ผล YOLO (`results.csv`/`args.yaml`) ก่อน present ถ้าเป็นไปได้

### กล้อง / วิดีโอ
- 4 กล้อง map กับไฟล์ใน `config.CAMERA_VIDEOS` — ไฟล์ไม่ครบ → ช่องนั้นขึ้น `NO SIGNAL` (ไม่ crash)
- webcam tab ส่ง frame จาก browser (`getUserMedia`) เป็น base64 มาที่ `/predict/webcam_frame` — พิกัด box ที่คืนอิงขนาดที่ส่ง (SEND_WIDTH=640) ฝั่ง JS scale กลับเอง → **ถ้าแก้ขนาดส่ง ต้องแก้ scaling ด้วย**

---

## Response Shape ที่ Frontend ใช้ (ห้ามเปลี่ยนโดยพลการ)

> แหล่งความจริง = `static/*.js` — เขียน backend ให้ตรง shape ที่ JS อ่าน ก่อนแก้ต้องเช็ค

- `GET /stats` → `{ signals:{cam:"STOP|CLEAR"}, counts:{ambulance,firetruck,police}, log:[{name,cam,conf,t}], infer_ms, current_model, current_conf, model_info:{name,params} }`
- `GET /api/settings` → `{ model:"x|m", conf:0.0–1.0 }` · `POST /api/settings` body `{ model?, conf? }`
- `POST /predict/image` (multipart: file, model_name, conf) → `{ image(base64), detections:[{name,conf,box:[x1,y1,x2,y2]}], infer_ms, model_name, model_params }`
- `POST /predict/video` → `{ frame_count, total_ms, avg_ms_per_frame, detections_summary:{name:count}, sample_frame(base64|null), model_name, model_params }`
- `POST /predict/webcam_frame` (JSON: image, model_name, conf) → `{ detections:[...], infer_ms, model_name, model_params }`
- `GET /stream/{cam_id}` → MJPEG (`multipart/x-mixed-replace`)

---

## Security & Hygiene

- **`.env` ไม่ commit** — อยู่ใน `.gitignore` (แม้ตอนนี้ยังไม่มีความลับ แต่เตรียมไว้)
- **ไฟล์ใหญ่ห้าม commit:** weights `*.pt` และ media `*.mp4` gitignore แล้ว — เคยมี `yolov8m.pt` (52MB) หลุดเข้า git มาก่อน ระวังอย่าให้เกิดอีก (`git ls-files | grep -E '\.pt$|\.mp4$'` ต้องว่าง)
- **ยังไม่มี auth** — ถ้าจะ deploy ให้คนอื่นเข้าถึง ต้องเพิ่มอย่างน้อย shared password/JWT ก่อนเปิด public (อย่าเปิด dashboard โล่ง ๆ บน internet)
- upload endpoint (image/video) รับไฟล์จากผู้ใช้ → validate ชนิด/ขนาด ก่อนประมวลผล ถ้าเปิดใช้จริง

---

## Git Workflow

- branch งานหลักแยกจาก `main`; `main` = fallback ที่รู้ว่ารันได้
- **ไม่ merge เข้า main จนพิสูจน์ว่ารัน demo ผ่าน** (สร้าง venv ใหม่ → `pip install` → `python run.py` → เปิดครบทุกหน้า)
- commit เมื่อผู้ใช้สั่ง; อย่า force-push branch ที่ push แล้ว
- remote = GitHub (`origin`)

---

## สิ่งที่ต้องถามก่อนทำ

ถ้างานกระทบ **data model / detection & counting logic / สัญญาณไฟ / response shape ที่ JS ใช้ / การเพิ่ม DB หรือ dependency ใหม่ / security model / สิ่งที่อาจทำ demo พัง**
→ **ยืนยัน scope สั้น ๆ ก่อนลงมือ** มิฉะนั้นดำเนินการตาม guide นี้ได้เลย

---

## เอกสารที่เกี่ยวข้อง

- `docs/STATUS.md` — สถานะปัจจุบัน (อ่านก่อนเริ่มงานเสมอ · เป็น living doc)
- `docs/ARCHITECTURE.md` — สถาปัตยกรรม/การไหลของข้อมูล/threading model
- `docs/PRODUCTION_ROADMAP.md` — แผนพาไป production (กล้องจริง, DB, GPU, deploy, security)
