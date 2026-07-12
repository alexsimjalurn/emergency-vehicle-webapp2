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
        self._seen_tracks = set()   # (cam_id, track_id) ที่นับไปแล้ว — กันนับซ้ำเมื่อ tracking
        self.infer_ms = 0.0

        # signal preemption — คิวทิศที่มีรถฉุกเฉิน (เรียงตามลำดับมาถึง) + เวลาที่เห็นรถล่าสุด (สำหรับ hold)
        self._green_queue   = []
        self._emerg_last_ts = {cam: 0.0 for cam in config.CAMERA_VIDEOS}
        self.active_green   = None   # ทิศที่ได้ไฟเขียวตอนนี้ (cam_id) — โชว์บน dashboard

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
        cam_label  = config.CAMERA_LABELS.get(cam_id, cam_id)
        emerg_dets = [d for d in dets if d["name"].lower() in config.EMERGENCY_CLASSES]
        emerg_now  = {d["name"].lower() for d in emerg_dets}
        tracked    = any("id" in d for d in emerg_dets)   # กล้องนี้เปิด tracking ไหม
        to_persist = []                                   # (name, conf, track_id) — เขียน DB นอก lock

        with self._lock:
            if tracked:
                # นับ 1 ครั้งต่อ 1 คัน (track_id ใหม่) — ไม่นับซ้ำจาก flicker/หลายเฟรม
                for d in emerg_dets:
                    tid = d.get("id")
                    if tid is None:
                        continue
                    key = (cam_id, tid)
                    if key in self._seen_tracks:
                        continue
                    self._seen_tracks.add(key)
                    name = d["name"].lower()
                    self.counts[name] = self.counts.get(name, 0) + 1
                    self._append_log(name, cam_label, d["conf"])
                    to_persist.append((name, d["conf"], tid))
            else:
                # fallback เดิม: นับตอน class เปลี่ยนจาก "ไม่มี" → "มี" ต่อกล้อง
                for name in (emerg_now - self._active.get(cam_id, set())):
                    self.counts[name] = self.counts.get(name, 0) + 1
                    conf = max((d["conf"] for d in emerg_dets if d["name"].lower() == name), default=0)
                    self._append_log(name, cam_label, conf)
                    to_persist.append((name, conf, None))
                self._active[cam_id] = emerg_now

            self._update_signals(cam_id, bool(emerg_now))

        # persist นอก lock — DB I/O ไม่ควรถือ lock (กันบล็อก thread กล้องอื่น) · no-op ถ้า Mongo ไม่พร้อม
        for name, conf, tid in to_persist:
            db.insert_detection(name, cam_id, cam_label, conf, track_id=tid)

    def _append_log(self, name, cam_label, conf):
        self.log.appendleft({
            "name": name,
            "cam":  cam_label,
            "conf": int(conf * 100),
            "t":    time.strftime("%H:%M:%S"),
        })

    # ---- signal control (เรียกใต้ _lock เสมอ) ----------------------------
    def _update_signals(self, cam_id, present):
        """อัปเดตไฟจราจร · โหมด preemption = เขียวทีละทิศตามคิว, โหมดเดิม = CLEAR/STOP อิสระ"""
        if not config.SIGNAL_PREEMPTION:
            self.signals[cam_id] = "CLEAR" if present else "STOP"
            return

        now = time.time()
        if present:
            self._emerg_last_ts[cam_id] = now
        # ถือสถานะ "มีรถ" ต่ออีก GREEN_HOLD_SECONDS หลังรถหลุดเฟรม (กันกระพริบ + ให้รถผ่านแยก)
        effective = present or (now - self._emerg_last_ts[cam_id] < config.GREEN_HOLD_SECONDS)

        if effective and cam_id not in self._green_queue:
            self._green_queue.append(cam_id)          # เข้าคิวตามลำดับมาถึง
        elif not effective and cam_id in self._green_queue:
            self._green_queue.remove(cam_id)

        active = self._green_queue[0] if self._green_queue else None
        self.active_green = active
        for cam in self.signals:
            if cam == active:
                self.signals[cam] = "GREEN"           # ได้ไฟเขียว (หัวคิว)
            elif cam in self._green_queue:
                self.signals[cam] = "WAIT"            # มีรถแต่รอคิว (เหลือง)
            else:
                self.signals[cam] = "STOP"            # ไม่มีรถ (แดง)

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
                "active_green":  self.active_green,
                "active_green_label": config.CAMERA_LABELS.get(self.active_green) if self.active_green else None,
            }


state = SystemState()
