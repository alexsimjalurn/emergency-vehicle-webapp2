"""
detector.py — โหลดโมเดล YOLOv8 และตรวจจับยานพาหนะฉุกเฉิน
รองรับ 2 โมเดล: yolov8x (แม่นกว่า) และ yolov8m (เร็วกว่า)
โหลดครั้งเดียวตอน startup ไม่โหลดซ้ำทุก request
"""
import time
import threading
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from . import config

CLASS_COLORS = {
    "ambulance": (53, 107, 255),
    "firetruck": (53, 53, 224),
    "police":    (255, 158, 75),
}
DEFAULT_COLOR = (122, 196, 0)

MODEL_INFO = {
    "x": {"name": "YOLOv8x", "params": "68.2M parameters"},
    "m": {"name": "YOLOv8m", "params": "25.9M parameters"},
}


class Detector:
    def __init__(self):
        self._models: dict[str, YOLO] = {}
        self._lock = threading.Lock()   # single lock — GPU calls must be serialized
        self.last_infer_ms = 0.0
        self.using_custom = False

        # resolve device once — fall back to cpu if cuda ไม่พร้อม (กันพังเมื่อย้ายเครื่องที่ไม่มี GPU)
        self.device = config.DEVICE
        if self.device == "cuda" and not torch.cuda.is_available():
            print("[Detector] CUDA ไม่พร้อม → fallback ไปใช้ cpu")
            self.device = "cpu"
        print(f"[Detector] device = {self.device}")

        # โหลด YOLOv8x
        if Path(config.MODEL_PATH_X).exists():
            self._models["x"] = YOLO(str(config.MODEL_PATH_X))
            self.using_custom = True
            print(f"[Detector] โหลด YOLOv8x custom: {config.MODEL_PATH_X}")
        else:
            self._models["x"] = YOLO(config.FALLBACK_X)
            print(f"[Detector] ไม่พบ best_x.pt → ใช้ pretrained {config.FALLBACK_X}")

        # โหลด YOLOv8m
        if Path(config.MODEL_PATH_M).exists():
            self._models["m"] = YOLO(str(config.MODEL_PATH_M))
            if not self.using_custom:
                self.using_custom = True
            print(f"[Detector] โหลด YOLOv8m custom: {config.MODEL_PATH_M}")
        else:
            self._models["m"] = YOLO(config.FALLBACK_M)
            print(f"[Detector] ไม่พบ best_m.pt → ใช้ pretrained {config.FALLBACK_M}")

        # alias ใช้กับ CameraWorker เดิม (ใช้โมเดล x เป็น default)
        self.model = self._models["x"]
        self.names = self.model.names

    # ------------------------------------------------------------------
    def get_model(self, key: str) -> YOLO:
        return self._models.get(key, self._models["x"])

    def get_model_info(self, key: str) -> dict:
        return MODEL_INFO.get(key, MODEL_INFO["x"])

    def color_for(self, name: str):
        return CLASS_COLORS.get(name.lower(), DEFAULT_COLOR)

    # ------------------------------------------------------------------
    def infer(self, frame, model_key: str = "x", conf: float | None = None) -> list[dict]:
        """ตรวจจับวัตถุใน 1 เฟรม — คืน list ของ detection dict"""
        if conf is None:
            conf = config.CONF_THRESHOLD
        model = self.get_model(model_key)

        t0 = time.time()
        with self._lock:
            results = model.predict(
                frame,
                imgsz=config.IMG_SIZE,
                conf=conf,
                device=self.device,
                verbose=False,
            )
        self.last_infer_ms = (time.time() - t0) * 1000

        dets = []
        r = results[0]
        names = model.names
        if r.boxes is not None:
            for box in r.boxes:
                cls_id   = int(box.cls[0])
                conf_val = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                dets.append({
                    "name": names.get(cls_id, str(cls_id)),
                    "conf": conf_val,
                    "box":  (x1, y1, x2, y2),
                })
        return dets

    def draw(self, frame, dets: list[dict]):
        """วาดกรอบ + label ลงบนเฟรม — คืนเฟรมที่วาดแล้ว"""
        out = frame.copy()
        for d in dets:
            x1, y1, x2, y2 = d["box"]
            color = self.color_for(d["name"])
            label = f'{d["name"].upper()} {int(d["conf"] * 100)}%'
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(out, (x1, y1 - th - 8), (x1 + tw + 8, y1), color, -1)
            cv2.putText(out, label, (x1 + 4, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        return out


def placeholder_frame(text="NO SIGNAL", w=640, h=360):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = (20, 16, 10)
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
    cv2.putText(img, text, ((w - tw) // 2, (h + th) // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (80, 100, 140), 2, cv2.LINE_AA)
    return img
