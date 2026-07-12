"""
db.py — MongoDB persistence สำหรับ detection events

หลักการ: ต้อง **ไม่ทำให้ app ตาย** ถ้า Mongo ล่ม/ไม่พร้อม
  - connect ตอน import — fail fast (ping timeout 2s) แต่ไม่ throw
  - ถ้าเชื่อมไม่ได้ → enabled=False → ทุก method กลายเป็น no-op (log ชัด) app รันต่อแบบ memory-only

collection `detections` (1 document = รถฉุกเฉิน 1 คันที่ "โผล่ใหม่"):
  { class, cam, cam_label, conf(0-1), ts(UTC datetime) }
"""
from datetime import datetime, timezone, timedelta

from pymongo import MongoClient, DESCENDING

from . import config

# timezone ของสถานี — ใช้แปลง UTC → local ตอนแสดงผล/หาขอบเขต "วันนี้"
STATION_TZ = timezone(timedelta(hours=config.STATION_TZ_OFFSET_HOURS))


class Database:
    def __init__(self):
        self.enabled = False
        self._client = None
        self.detections = None
        self._connect()

    def _connect(self):
        try:
            # serverSelectionTimeoutMS ต่ำ → รู้เร็วว่า Mongo ไม่พร้อม ไม่ค้างตอน startup
            self._client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=2000)
            self._client.admin.command("ping")   # บังคับให้ลองต่อจริง (ไม่ lazy)
            db = self._client[config.MONGO_DB]
            self.detections = db["detections"]
            self.detections.create_index([("ts", DESCENDING)])
            self.detections.create_index([("class", 1), ("ts", DESCENDING)])
            self.enabled = True
            print(f"[DB] connected: {config.MONGO_URI} -> db '{config.MONGO_DB}'")
        except Exception as e:
            self.enabled = False
            print(f"[DB] MongoDB ไม่พร้อม ({e}) -> memory-only (ไม่ persist)")

    # ------------------------------------------------------------------
    def insert_detection(self, cls, cam_id, cam_label, conf, ts=None):
        """บันทึก 1 event — เรียกตอนรถฉุกเฉินโผล่ใหม่ (ดู state.update)"""
        if not self.enabled:
            return
        try:
            self.detections.insert_one({
                "class":     cls,
                "cam":       cam_id,
                "cam_label": cam_label,
                "conf":      float(conf),
                "ts":        ts or datetime.now(timezone.utc),
            })
        except Exception as e:
            print(f"[DB] insert error: {e}")

    # ------------------------------------------------------------------
    def today_counts(self):
        """dict {class: count} เฉพาะวันนี้ (ตาม STATION_TZ) — ใช้ restore counts ตอน startup"""
        if not self.enabled:
            return {}
        try:
            pipeline = [
                {"$match": {"ts": {"$gte": self._today_start_utc()}}},
                {"$group": {"_id": "$class", "n": {"$sum": 1}}},
            ]
            return {d["_id"]: d["n"] for d in self.detections.aggregate(pipeline)}
        except Exception as e:
            print(f"[DB] today_counts error: {e}")
            return {}

    def recent_log(self, limit=15):
        """log ล่าสุด (shape เดียวกับ state.log) — ใช้ restore ตอน startup"""
        if not self.enabled:
            return []
        try:
            docs = self.detections.find().sort("ts", DESCENDING).limit(limit)
            return [self._to_log_item(d) for d in docs]
        except Exception as e:
            print(f"[DB] recent_log error: {e}")
            return []

    # ------------------------------------------------------------------
    def _to_log_item(self, d):
        ts = d["ts"]
        if ts.tzinfo is None:                       # Mongo คืน naive UTC
            ts = ts.replace(tzinfo=timezone.utc)
        return {
            "name": d["class"],
            "cam":  d.get("cam_label", d.get("cam", "")),
            "conf": int(round(d.get("conf", 0) * 100)),
            "t":    ts.astimezone(STATION_TZ).strftime("%H:%M:%S"),
        }

    def _today_start_utc(self):
        now_local = datetime.now(STATION_TZ)
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_local.astimezone(timezone.utc)


# singleton — เชื่อมครั้งเดียวตอน import
db = Database()
