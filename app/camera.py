"""
camera.py — ตัวจัดการกล้องแต่ละตัว (แก้ปัญหาภาพหน่วง)

แนวคิดสำคัญ: แยกการทำงานเป็น 2 thread ต่อกล้อง
  1) playback thread  → อ่านวิดีโอ + วาดกรอบล่าสุด + เข้ารหัส JPEG (เบา วิ่งลื่นตลอด)
  2) inference thread → หยิบเฟรมล่าสุดไปตรวจจับด้วย YOLOv8x (หนัก วิ่งเบื้องหลัง)

วิดีโอจึงเล่นลื่นเสมอ ไม่ต้องรอ inference
"""
import time
import threading

import cv2

from . import config
from .detector import Detector, placeholder_frame
from .state import state


def _make_tracker():
    """สร้าง ByteTrack tracker 1 ตัวต่อกล้อง — โหลด config จาก ultralytics (ตรงเวอร์ชันที่ติดตั้ง)
    fallback เป็นค่า default hardcode ถ้าโหลดไฟล์ไม่ได้"""
    from ultralytics.trackers import BYTETracker
    try:
        from ultralytics.utils import IterableSimpleNamespace, YAML, ROOT
        cfg = IterableSimpleNamespace(**YAML.load(ROOT / "cfg" / "trackers" / "bytetrack.yaml"))
    except Exception:
        from types import SimpleNamespace
        cfg = SimpleNamespace(
            tracker_type="bytetrack", track_high_thresh=0.25, track_low_thresh=0.1,
            new_track_thresh=0.25, track_buffer=30, match_thresh=0.8, fuse_score=True,
        )
    return BYTETracker(cfg)


class CameraWorker:
    def __init__(self, cam_id, detector):
        self.cam_id = cam_id
        self.detector = detector
        self.video_path = config.CAMERA_VIDEOS.get(cam_id)

        self.boxes = []            # กรอบ detection ล่าสุด (playback เอาไปวาด)
        self.current_raw = None    # เฟรมดิบล่าสุด (inference เอาไปตรวจ)
        self.latest_jpeg = None    # ภาพ JPEG ล่าสุดที่พร้อมส่งให้เบราว์เซอร์
        self._lock = threading.Lock()
        self.running = True

        # tracker ของกล้องนี้เอง (ห้ามแชร์ข้ามกล้อง — state ปนกัน) · None = ปิด tracking
        self.tracker = _make_tracker() if config.USE_TRACKING else None

    def start(self):
        # ไม่มีไฟล์วิดีโอ → ทำภาพ NO SIGNAL ค้างไว้ ไม่ต้องเปิด thread
        if not self.video_path or not self.video_path.exists():
            ph = placeholder_frame(f"NO SIGNAL · {self.cam_id}")
            ok, buf = cv2.imencode(".jpg", ph)
            if ok:
                with self._lock:
                    self.latest_jpeg = buf.tobytes()
            return

        threading.Thread(target=self._playback_loop, daemon=True).start()
        threading.Thread(target=self._inference_loop, daemon=True).start()

    def _playback_loop(self):
        """อ่านวิดีโอ → วาดกรอบล่าสุด → เข้ารหัส (วิ่งเร็ว ทำให้ภาพลื่น)"""
        cap = cv2.VideoCapture(str(self.video_path))
        delay = 1.0 / max(config.TARGET_FPS, 1)
        while self.running:
            ok, frame = cap.read()
            if not ok:                                   # วิดีโอจบ → วนกลับต้น
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            self.current_raw = frame                     # ส่งต่อให้ inference thread
            annotated = self.detector.draw(frame, self.boxes)

            ok2, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok2:
                with self._lock:
                    self.latest_jpeg = buf.tobytes()
            time.sleep(delay)

    def _inference_loop(self):
        """ตรวจจับด้วย YOLO เบื้องหลัง (วิ่งตามความเร็วเครื่อง ไม่บล็อกภาพ)"""
        while self.running:
            frame = self.current_raw
            if frame is None:
                time.sleep(0.01)
                continue

            if self.tracker is not None:
                dets = self._infer_tracked(frame)
            else:
                dets = self.detector.infer(
                    frame, model_key=state.current_model, conf=state.current_conf,
                )
            self.boxes = dets
            state.update(self.cam_id, dets)
            state.set_infer_ms(self.detector.last_infer_ms)
            time.sleep(0.005)                            # คืน CPU เล็กน้อย

    def _infer_tracked(self, frame):
        """detect + ByteTrack → dets ที่มี track_id (นับ 'คัน' ไม่ใช่ 'เฟรม')
        track array 8 คอลัมน์: [x1,y1,x2,y2, track_id, conf, cls, det_idx]"""
        try:
            r = self.detector.infer_raw(frame, model_key=state.current_model, conf=state.current_conf)
            names = r.names
            tracks = self.tracker.update(r.boxes.cpu().numpy(), frame)
            dets = []
            for t in tracks:
                x1, y1, x2, y2 = (int(v) for v in t[:4])
                dets.append({
                    "name": Detector.norm_name(names.get(int(t[6]), str(int(t[6])))),
                    "conf": float(t[5]),
                    "box":  (x1, y1, x2, y2),
                    "id":   int(t[4]),
                })
            return dets
        except Exception as e:                           # tracker พังห้ามทำ thread ตาย → fallback ตรวจธรรมดา
            print(f"[Camera {self.cam_id}] tracking error: {e} → fallback infer")
            return self.detector.infer(frame, model_key=state.current_model, conf=state.current_conf)

    def get_jpeg(self):
        with self._lock:
            return self.latest_jpeg
