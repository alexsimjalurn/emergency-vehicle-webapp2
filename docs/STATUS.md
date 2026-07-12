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

- **✅ D3 เสร็จ (2026-07-12) — Analytics + Results เลขจริง:**
  - **หน้า History (`/history`):** aggregate จาก MongoDB ตาม STATION_TZ — summary cards, กราฟรายวัน (stacked ตาม class), แจกแจงตามชั่วโมง 0-23, แยกตามกล้อง/ทิศ, ตารางล่าสุด · range today/7d/30d · `GET /api/history?range=` · charts vanilla div (ไม่พึ่ง CDN)
  - **✅ Part A — Results ใช้เลขจริงแล้ว:** ผู้ใช้ส่ง `run/` (ผลเทรนจริง 2 โมเดล) → `scripts/build_model_report.py` parse results.csv (เลือก best-fitness epoch = best.pt) + args.yaml → `app/model_report.json` · `stats.html` render จาก report (เลิก hardcode) · mount `/report` เสิร์ฟรูปหลักฐาน (confusion matrix / curves / **val predictions จริง**)
    - **ตัวเลขจริง:** YOLOv8x mAP50 **97.97%** · mAP50-95 **81.39%** · P 95.63% · R 96.12% (best epoch 93) · YOLOv8m mAP50 97.75% · mAP50-95 78.0% → โชว์ตารางเทียบ m vs x
    - **⚠️ เก่า hardcode ผิด:** mAP50-95 เขียนไว้ 72.31% แต่จริง 81.39% · mAP50 เขียน 97.54% จริง 97.97% · per-class table เดิม (96.4/97.2/...) เป็นเลขแต่ง → เอาออก แทนด้วย confusion matrix จริง
    - verify: /results 200, เลขจริงขึ้น, รูป /report เสิร์ฟ 200, ไม่มีเลขแต่งเหลือ · **run/ (44 ไฟล์, ~18MB) commit เป็นหลักฐาน** (weights .pt gitignore กันไว้)
    - **หมายเหตุ:** ผมยังไม่ได้เห็นหน้า Results ด้วยตา (verify แค่ HTML+รูป serve) — ผู้ใช้ควรเปิดดู layout จริง

- **✅ D4 เสร็จ (2026-07-12) — Object Tracking (ByteTrack):**
  - **tracker แยกต่อกล้อง** (`_make_tracker()` ใน camera.py) แชร์ model เดิม — ห้ามใช้ `model.track(persist)` ตรง ๆ เพราะ state ปนข้ามกล้อง · `detector.infer_raw()` คืน Results ดิบ → `tracker.update()` → track array 8 คอลัมน์ `[x1,y1,x2,y2,track_id,conf,cls,det_idx]`
  - **นับ 'คัน' ไม่ใช่ 'เฟรม':** `state` นับ 1 ครั้งต่อ `(cam_id, track_id)` ใหม่ (`_seen_tracks`) → เลิกนับซ้ำจาก flicker · เก็บ `track_id` ลง DB ด้วย · **verify: 35 วิ 4 กล้อง นับ 12 คัน** (เดิม per-frame = 1242 docs!) · box วาด `#id` แล้ว
  - **fallback ปลอดภัย:** `config.USE_TRACKING=False` → กลับไปนับ set-diff เดิม · tracker error → fallback infer (thread ไม่ตาย)
  - **🔴 แก้ bug ที่ซ่อนอยู่:** โมเดล output class = **`police_car`** แต่แอปใช้ `"police"` → รถตำรวจไม่เคยถูกนับ/trigger ไฟเลย · แก้ด้วย `config.CLASS_ALIASES = {"police_car":"police"}` normalize ใน `detector.norm_name` (ใช้ทั้ง infer + tracking) · เพิ่ม `lap>=0.5.12` ใน requirements (ไม่งั้น auto-download ตอน runtime)

---

## ⚠️ ข้อจำกัด / หนี้ทางเทคนิค (ต้องรู้ก่อนพูดว่า "production-ready")

| หัวข้อ | สถานะปัจจุบัน | กระทบอะไร |
|---|---|---|
| **กล้อง** | ไฟล์ `.mp4` วนลูป | ไม่ใช่กล้องจริง — production ต้องต่อ RTSP/IP |
| ~~**Persistence**~~ | ✅ **แก้แล้ว (D2)** — MongoDB `evd.detections` | restart แล้ว counts/log คืนจาก DB · มีข้อมูลย้อนหลังพร้อมทำหน้า History (D3) |
| ~~**Object tracking**~~ | ✅ **แก้แล้ว (D4)** — ByteTrack ต่อกล้อง | นับต่อ track_id (คัน) ไม่ใช่เฟรม · เก็บ track_id ลง DB |
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
