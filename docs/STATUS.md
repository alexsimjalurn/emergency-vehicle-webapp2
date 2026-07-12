# STATUS — EVD System

> **Living document** — อ่านไฟล์นี้ก่อนเริ่มงานใหม่ทุกครั้ง และอัปเดตเมื่อสถานะเปลี่ยน
> อัปเดตล่าสุด: 2026-07-12

---

## เฟสปัจจุบัน

**Prototype รัน local** — ยังไม่ deploy production
เป้าหมายเฉพาะหน้า: พาไป **production ให้ทันวัน present** (ดู `PRODUCTION_ROADMAP.md`)

---

## ✅ ทำเสร็จแล้ว (ใช้งานได้)

- Backend FastAPI ครบ: dashboard, detect (image/video/webcam), stream, stats, settings API
- YOLOv8 2 โมเดล (`x` แม่น / `m` เร็ว) สลับได้ตอน runtime + ปรับ confidence จาก UI
- Dashboard 4 กล้อง (วิดีโอจำลอง) — MJPEG ลื่นด้วย threading model (playback แยก inference)
- สัญญาณไฟ STOP/CLEAR ต่อกล้อง + alert log + session counts
- เครื่องมือ detect ครบ 3 แบบ + หน้า results (metric) + about + landing — UI ภาษาลาว
- **โครงสร้างโปรเจกต์จัดใหม่ (2026-07-12):** โค้ดเป็น package `app/`, ลบไฟล์ขยะ, `yolov8m.pt` เอาออกจาก git, README/docs/CLAUDE.md เขียนใหม่
- **✅ D1 เสร็จ (2026-07-12) — GPU + env:** ลง Python 3.12.10, venv ใหม่, torch **2.5.1+cu121** (CUDA ใช้ได้จริง), `DEVICE="cuda"`, default โมเดล `m` (+ fallback cpu อัตโนมัติใน `detector.py`), เพิ่ม `pymongo` ใน requirements · แอปบูตบน GPU ตรวจจับได้ (nvidia-smi: 928MB/4GB, util 80%)

### 📊 Benchmark GPU vs CPU (imgsz 480, north.mp4 · เก็บไว้โชว์ present)

| โมเดล | device | ms/frame | fps | VRAM |
|---|---|---|---|---|
| m | **cuda** | 26.6 | **37.6** | 0.13 GB |
| m | cpu | 214.2 | 4.7 | — |
| x | **cuda** | 54.8 | **18.3** | 0.32 GB |
| x | cpu | 472.3 | 2.1 | — |

→ **GPU เร็วขึ้น ~8×** · VRAM 4GB เหลือเฟือ (single-model inference serialize) · ยืนยันเลือก default `m` ถูกต้อง (fps headroom สำหรับ 4 กล้อง)

- **✅ D2 เสร็จ (2026-07-12) — MongoDB persistence:** เพิ่ม `app/db.py` (connect + insert + restore, fail-safe: Mongo ล่ม → memory-only ไม่ crash) · `state.update()` เขียน event ลง collection `detections` ตอนรถโผล่ใหม่ (นอก lock) · `state.load_from_db()` restore counts(วันนี้)+log ตอน startup · config `MONGO_URI`/`MONGO_DB`/`STATION_TZ_OFFSET_HOURS` (env override ได้)
  - **verify:** รัน→ตรวจจับ→Mongo มี docs ตรง in-memory · **restart→ counts คืนจาก DB** (`restored from DB: counts={ambulance:61}`) ไม่รีเซ็ตแล้ว
  - **แก้ bug encoding:** console Windows (cp1252) encode ภาษาไทย/`→` ไม่ได้ → print crash ทั้ง process · แก้ด้วย reconfigure stdout=utf-8 ใน `app/__init__.py` (ครอบทุก entry ไม่ต้องพึ่ง env)
  - **หมายเหตุ:** DB `evd.detections` มี test docs (ambulance จากคลิปทดสอบวันนี้) · ล้างได้ด้วย `db.detections.delete_many({})` ถ้าอยากเริ่มสะอาดก่อน present

- **🟡 D3 (2026-07-12) — ทำ Part B เสร็จ, Part A รอไฟล์:**
  - **✅ หน้า History (`/history`):** aggregate จาก MongoDB ตาม STATION_TZ — summary cards (total+per class+peak hour), กราฟแนวโน้มรายวัน (stacked ตาม class), การแจกแจงตามชั่วโมง 0-23, แยกตามกล้อง/ทิศ, ตารางล่าสุด · range today/7d/30d · endpoint `GET /api/history?range=` · `db.history()` + helpers · charts เป็น vanilla div (ไม่พึ่ง CDN — ปลอดภัยตอน present ไม่ต้องเน็ต)
    - verify: endpoint คืน totals/daily/hourly/byCamera/peakHour ถูก (peakHour 13 = 06:xx UTC→13:xx ICT), page+assets 200, timezone แม่น
  - **⏳ Part A (Results ใช้เลขจริง): ยังไม่ทำ — ติดที่ไม่มี training artifacts** (results.csv/confusion matrix) ในโปรเจกต์ · `stats.html` ยัง hardcode (97.54% ฯลฯ) · **ต้องขอไฟล์ผลเทรนจาก Colab ของผู้ใช้** แล้วค่อยทำ data-driven + parser

---

## ⚠️ ข้อจำกัด / หนี้ทางเทคนิค (ต้องรู้ก่อนพูดว่า "production-ready")

| หัวข้อ | สถานะปัจจุบัน | กระทบอะไร |
|---|---|---|
| **กล้อง** | ไฟล์ `.mp4` วนลูป | ไม่ใช่กล้องจริง — production ต้องต่อ RTSP/IP |
| ~~**Persistence**~~ | ✅ **แก้แล้ว (D2)** — MongoDB `evd.detections` | restart แล้ว counts/log คืนจาก DB · มีข้อมูลย้อนหลังพร้อมทำหน้า History (D3) |
| **Object tracking** | นับ frame-level (set diff) | รถคันเดิมหลุด frame แล้วกลับมา = นับซ้ำ · เลขไม่แม่นสำหรับรายงานจริง |
| **สัญญาณไฟ** | display อย่างเดียว | ไม่ต่อฮาร์ดแวร์ · ไม่มี logic เลือกทิศเมื่อหลายกล้อง CLEAR พร้อมกัน |
| **หน้า Results** | metric **hardcode ใน HTML** | mAP50/precision/dataset ไม่ได้มาจากผล eval จริง — ถ้ากรรมการถามที่มาต้องมีหลักฐานรองรับ |
| **Auth** | ไม่มี | dashboard เปิดโล่ง — ห้ามเปิด public ก่อนใส่ auth |
| **Inference** | CPU | 4 กล้องพร้อมกันช้า (แย่งกันผ่าน lock) |
| **Deploy** | `python run.py` เท่านั้น | ไม่มี Docker/nginx/service/HTTPS |
| **Tests** | ไม่มี | ไม่มี regression guard |

---

## 🔧 ปัญหาสภาพแวดล้อม dev (เครื่องนี้)

- **`venv/` เสีย** — สร้างจากเครื่อง "GAMING" interpreter path หายไป → ใช้ไม่ได้ ต้อง `python -m venv venv` ใหม่
- **ไม่มี Python บน PATH ของเชลล์ที่ Claude ใช้** → Claude **รัน/verify runtime บนเครื่องนี้ไม่ได้** ต้องให้ผู้ใช้ทดสอบเอง หรือใช้ static check เท่านั้น

---

## 🎯 งานถัดไป (ตามที่ผู้ใช้ระบุ)

1. ให้ Claude ช่วย **review + ออกแบบระบบให้ใช้จริงได้ระดับ production** ให้ทันวัน present
2. ลำดับความสำคัญ/แผนย่อย → ดู `PRODUCTION_ROADMAP.md` (ยังไม่ตัดสินว่าจะทำข้อไหนก่อน — รอยืนยันกับผู้ใช้)

---

## 📌 การตัดสินใจ (เคาะแล้ว 2026-07-12)

- **เครื่อง demo:** มี GPU **RTX 3050 · VRAM 4GB** → เปิด CUDA ได้ แต่ 4GB น้อย → default dashboard = **YOLOv8m** (x ไว้ตรวจภาพเดี่ยว) · ต้องลง **torch CUDA build (cu121)** ไม่ใช่ pip default (CPU-only)
- **กล้อง:** ใช้ **วิดีโอจำลองต่อ** (ไม่มีกล้อง IP/webcam จริง) แต่**มีคลิปจากกล้องเยอะ** → ทำให้เลือก/สลับคลิปได้ ไม่ต้องทำ RTSP
- **DB:** **MongoDB** (เคาะแล้ว — ผู้ใช้ขอ) · บนเครื่องนี้ **ติดตั้ง+รันเป็น service Automatic อยู่แล้ว** (พอร์ต 27017, auto-start เมื่อบูต) → เสี่ยงวัน present ต่ำ · เพิ่มแค่ `pymongo` + connection ใน `config.py` · DB name เสนอ `evd`
- **เวลา:** เหลือ **5 วัน** ถึงวัน present (deadline ~2026-07-17)
- **ไฟจราจร:** (ยังไม่ระบุ) — สันนิษฐาน = simulation บนจอต่อไป ไม่ต่อฮาร์ดแวร์

## 🖥️ สภาพเครื่อง demo (เครื่องนี้ = เครื่อง present จริง — ยืนยันแล้ว)

- **GPU:** RTX 3050 4GB — เปิด CUDA ได้
- **MongoDB:** ✅ service Automatic รันอยู่ (27017)
- **⚠️ Python: ยังไม่ได้ติดตั้งเลย** — venv ที่มาถูก copy จากเครื่องอื่น (`C:\Users\GAMING\...\emergency-vehicle-webapp2`, Python 3.12.5) → **D1 ต้องลง Python 3.12 ก่อนเป็นอันดับแรก** ไม่งั้นรันอะไรไม่ได้

## 🗓️ แผน 5 วัน → ดู `PRODUCTION_ROADMAP.md` (section "แผน 5 วัน")
