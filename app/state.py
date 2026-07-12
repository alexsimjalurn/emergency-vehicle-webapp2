"""
state.py — เก็บสถานะรวมของระบบ (thread-safe)
"""
import time
import threading
from collections import deque

from . import config
from .db import db


class SystemState:
    def __init__(self):
        self._lock = threading.Lock()
        self.signals  = {cam: "STOP" for cam in config.CAMERA_VIDEOS}
        self.counts   = {}
        self.log      = deque(maxlen=15)
        self._active  = {cam: set() for cam in config.CAMERA_VIDEOS}
        self.infer_ms = 0.0

        # การตั้งค่าที่ปรับได้ผ่าน UI
        # default = "m" (YOLOv8m) — ปลอดภัยกับ VRAM 4GB เมื่อรัน 4 กล้อง · "x" ไว้ตรวจภาพเดี่ยว
        self.current_model = "m"               # "x" = YOLOv8x, "m" = YOLOv8m
        self.current_conf  = config.CONF_THRESHOLD

    # ------------------------------------------------------------------
    def set_model(self, key: str):
        with self._lock:
            self.current_model = key if key in ("x", "m") else "x"

    def set_conf(self, conf: float):
        with self._lock:
            self.current_conf = max(0.0, min(1.0, conf))

    # ------------------------------------------------------------------
    def update(self, cam_id, dets):
        emerg_now = {
            d["name"].lower() for d in dets
            if d["name"].lower() in config.EMERGENCY_CLASSES
        }
        to_persist = []                              # (name, conf) ของรถที่โผล่ใหม่ — เขียน DB นอก lock
        with self._lock:
            prev        = self._active.get(cam_id, set())
            new_arrivals = emerg_now - prev
            for name in new_arrivals:
                self.counts[name] = self.counts.get(name, 0) + 1
                conf = max(
                    (d["conf"] for d in dets if d["name"].lower() == name),
                    default=0,
                )
                self.log.appendleft({
                    "name": name,
                    "cam":  config.CAMERA_LABELS.get(cam_id, cam_id),
                    "conf": int(conf * 100),
                    "t":    time.strftime("%H:%M:%S"),
                })
                to_persist.append((name, conf))
            self._active[cam_id] = emerg_now
            self.signals[cam_id] = "CLEAR" if emerg_now else "STOP"

        # persist นอก lock — DB I/O ไม่ควรถือ lock (กันบล็อก thread กล้องอื่น) · no-op ถ้า Mongo ไม่พร้อม
        cam_label = config.CAMERA_LABELS.get(cam_id, cam_id)
        for name, conf in to_persist:
            db.insert_detection(name, cam_id, cam_label, conf)

    def set_infer_ms(self, ms):
        with self._lock:
            self.infer_ms = ms

    def load_from_db(self):
        """restore counts (วันนี้) + log ล่าสุด จาก MongoDB ตอน startup — restart แล้วเลขไม่รีเซ็ต"""
        counts = db.today_counts()
        log    = db.recent_log(self.log.maxlen)
        with self._lock:
            if counts:
                self.counts = counts
            if log:
                self.log = deque(log, maxlen=self.log.maxlen)
        if counts or log:
            print(f"[State] restored from DB: counts={counts}, log={len(log)} entries")

    def snapshot(self):
        with self._lock:
            return {
                "signals":       dict(self.signals),
                "counts":        dict(self.counts),
                "log":           list(self.log),
                "infer_ms":      round(self.infer_ms, 1),
                "current_model": self.current_model,
                "current_conf":  round(self.current_conf, 2),
            }


state = SystemState()
