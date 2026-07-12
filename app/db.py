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

# ลำดับ class คงที่ (ให้ตาราง/กราฟเรียงเหมือนกันทุกที่)
CLASS_ORDER = ["ambulance", "firetruck", "police"]


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
    def insert_detection(self, cls, cam_id, cam_label, conf, ts=None, track_id=None):
        """บันทึก 1 event — เรียกตอนรถฉุกเฉินโผล่ใหม่/track ใหม่ (ดู state.update)"""
        if not self.enabled:
            return
        try:
            doc = {
                "class":     cls,
                "cam":       cam_id,
                "cam_label": cam_label,
                "conf":      float(conf),
                "ts":        ts or datetime.now(timezone.utc),
            }
            if track_id is not None:
                doc["track_id"] = int(track_id)
            self.detections.insert_one(doc)
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

    # ================= History / Analytics (aggregate ตามเวลาสถานี) =================

    def history(self, range_key="7d"):
        """สรุปสถิติย้อนหลังสำหรับหน้า History — group ตาม STATION_TZ"""
        if not self.enabled:
            return self._empty_history(range_key)
        try:
            tz = self._tz_str()
            days = {"today": 1, "7d": 7, "30d": 30}.get(range_key, 7)
            start = self._range_start_utc(days)
            match = {"$match": {"ts": {"$gte": start}}}

            hourly = self._hourly(match, tz)
            peak = max(hourly, key=lambda h: h["count"])
            return {
                "range":     range_key,
                "totals":    self._totals(match),
                "daily":     self._daily(match, tz, days),
                "hourly":    hourly,
                "byCamera":  self._by_camera(match),
                "peakHour":  peak["hour"] if peak["count"] else None,
                "recent":    self.recent_log(12),
            }
        except Exception as e:
            print(f"[DB] history error: {e}")
            return self._empty_history(range_key)

    def _totals(self, match):
        rows = self.detections.aggregate([match, {"$group": {"_id": "$class", "n": {"$sum": 1}}}])
        out = {c: 0 for c in CLASS_ORDER}
        for r in rows:
            out[r["_id"]] = r["n"]
        out["all"] = sum(out[c] for c in CLASS_ORDER)
        return out

    def _daily(self, match, tz, days):
        rows = self.detections.aggregate([
            match,
            {"$group": {
                "_id": {
                    "date": {"$dateToString": {"date": "$ts", "format": "%Y-%m-%d", "timezone": tz}},
                    "class": "$class",
                },
                "n": {"$sum": 1},
            }},
        ])
        by_date = {}
        for r in rows:
            d = r["_id"]["date"]
            by_date.setdefault(d, {c: 0 for c in CLASS_ORDER})
            by_date[d][r["_id"]["class"]] = r["n"]
        # เติมวันที่ครบช่วง (วันไม่มีข้อมูล = 0) เพื่อกราฟต่อเนื่อง
        today_local = datetime.now(STATION_TZ).date()
        out = []
        for i in range(days - 1, -1, -1):
            day = today_local - timedelta(days=i)
            key = day.strftime("%Y-%m-%d")
            counts = by_date.get(key, {c: 0 for c in CLASS_ORDER})
            out.append({"date": key, **counts, "total": sum(counts.values())})
        return out

    def _hourly(self, match, tz):
        rows = self.detections.aggregate([
            match,
            {"$group": {"_id": {"$hour": {"date": "$ts", "timezone": tz}}, "n": {"$sum": 1}}},
        ])
        counts = {r["_id"]: r["n"] for r in rows}
        return [{"hour": h, "count": counts.get(h, 0)} for h in range(24)]

    def _by_camera(self, match):
        rows = self.detections.aggregate([match, {"$group": {"_id": "$cam", "n": {"$sum": 1}}}])
        counts = {r["_id"]: r["n"] for r in rows}
        # เรียงตาม cam1..cam4 ตาม config เสมอ (คงลำดับทิศ N/E/S/W)
        return [
            {"cam": cam, "label": config.CAMERA_LABELS.get(cam, cam), "count": counts.get(cam, 0)}
            for cam in config.CAMERA_LABELS
        ]

    def _empty_history(self, range_key):
        days = {"today": 1, "7d": 7, "30d": 30}.get(range_key, 7)
        today_local = datetime.now(STATION_TZ).date()
        daily = [
            {"date": (today_local - timedelta(days=i)).strftime("%Y-%m-%d"),
             **{c: 0 for c in CLASS_ORDER}, "total": 0}
            for i in range(days - 1, -1, -1)
        ]
        return {
            "range": range_key,
            "totals": {**{c: 0 for c in CLASS_ORDER}, "all": 0},
            "daily": daily,
            "hourly": [{"hour": h, "count": 0} for h in range(24)],
            "byCamera": [{"cam": cam, "label": config.CAMERA_LABELS.get(cam, cam), "count": 0}
                         for cam in config.CAMERA_LABELS],
            "peakHour": None,
            "recent": [],
        }

    def _tz_str(self):
        off = config.STATION_TZ_OFFSET_HOURS
        sign = "+" if off >= 0 else "-"
        return f"{sign}{abs(off):02d}:00"

    def _range_start_utc(self, days):
        now_local = datetime.now(STATION_TZ)
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
        return start_local.astimezone(timezone.utc)


# singleton — เชื่อมครั้งเดียวตอน import
db = Database()
