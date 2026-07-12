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
from .detector import placeholder_frame
from .state import state


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
        """ตรวจจับด้วย YOLOv8x เบื้องหลัง (วิ่งตามความเร็วเครื่อง ไม่บล็อกภาพ)"""
        while self.running:
            frame = self.current_raw
            if frame is None:
                time.sleep(0.01)
                continue

            dets = self.detector.infer(
                frame,
                model_key=state.current_model,
                conf=state.current_conf,
            )
            self.boxes = dets
            state.update(self.cam_id, dets)
            state.set_infer_ms(self.detector.last_infer_ms)
            time.sleep(0.005)                            # คืน CPU เล็กน้อย

    def get_jpeg(self):
        with self._lock:
            return self.latest_jpeg
