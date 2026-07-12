# 🚨 Emergency Vehicle Detection — Web App

เว็บแอป Dashboard จำลองสี่แยก 4 กล้อง ตรวจจับรถฉุกเฉิน (ambulance / firetruck / police)
ด้วย YOLOv8 แบบ real-time + นับจำนวนคันด้วย object tracking + แสดงสถานะสัญญาณไฟจราจร

Stack: **FastAPI · Ultralytics YOLOv8 (+ByteTrack) · PyTorch/CUDA · OpenCV · MongoDB · Jinja2**

## ✨ ฟีเจอร์

- **Dashboard 4 กล้อง real-time** — MJPEG stream + box ตรวจจับ + track ID (playback แยก inference thread ภาพลื่น)
- **GPU inference** (CUDA) — เร็วขึ้น ~8× เทียบ CPU · สลับ YOLOv8m (เร็ว) / YOLOv8x (แม่น) ได้ตอน runtime
- **Object tracking (ByteTrack)** — นับ "คัน" ต่อ track_id ไม่ใช่ต่อเฟรม (ไม่นับซ้ำ) · tracker แยกต่อกล้อง
- **สัญญาณไฟอัตโนมัติ** — CLEAR เมื่อกล้องเจอรถฉุกเฉิน
- **MongoDB persistence** — เก็บทุก detection · restart ไม่หาย · หน้า History สรุปย้อนหลัง (รายวัน/ชั่วโมง/กล้อง)
- **หน้า Results** — metric จริงจากผลเทรน (parse `results.csv`) + รูปหลักฐาน (confusion matrix / prediction)
- **เครื่องมือ detect** — image / video / webcam

---

## 📁 โครงสร้างโปรเจกต์

```
emergency-vehicle-webapp/
├── app/                  # โค้ดหลัก (Python package)
│   ├── main.py           # FastAPI app + routes
│   ├── config.py         # ⚙️ ตั้งค่าทั้งหมดที่นี่ (device, tracking, mongo, ...)
│   ├── detector.py       # โหลด YOLO + ตรวจจับ + วาดกรอบ
│   ├── camera.py         # worker ต่อกล้อง (playback + inference + ByteTrack)
│   ├── state.py          # สถานะระบบ (thread-safe) + นับตาม track_id
│   ├── db.py             # MongoDB persistence + aggregation (History)
│   └── model_report.json # metric จริง (สร้างจาก scripts/build_model_report.py)
├── static/ · templates/  # frontend (CSS/JS · Jinja2)
├── models/               # YOLO weights (.pt — gitignored)
├── videos/               # คลิป 4 กล้อง (.mp4 — gitignored)
├── run/                  # ผลเทรนจริง (results.csv, curves, confusion matrix)
├── scripts/              # build_model_report.py · reset_data.py
├── notebooks/            # Colab notebooks (เทรนโมเดล)
├── docs/                 # STATUS · ARCHITECTURE · PRODUCTION_ROADMAP · DEMO
├── run.py                # launcher
└── requirements.txt
```

---

## 🚀 วิธีรัน

### 1. สร้าง virtual env
```bash
python -m venv venv
venv\Scripts\activate        # Windows  (macOS/Linux: source venv/bin/activate)
```

### 2. ติดตั้ง PyTorch (⚠️ ต้องก่อน requirements — เลือก GPU หรือ CPU)
```bash
# GPU (CUDA 12.1) — แนะนำถ้ามีการ์ด NVIDIA
pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121

# CPU อย่างเดียว
pip install torch==2.5.1 torchvision==0.20.1
```
> ⚠️ **ห้ามข้ามขั้นนี้** — ถ้าลง `requirements.txt` ก่อน pip จะดึง torch CPU-only มาทับ GPU ใช้ไม่ได้

### 3. ติดตั้ง package ที่เหลือ
```bash
pip install -r requirements.txt
```
ตรวจว่า GPU ใช้ได้: `python -c "import torch; print(torch.cuda.is_available())"` → ควรได้ `True`

**ต้องมี MongoDB รันอยู่** (default `mongodb://localhost:27017`) — ระบบยังรันได้ถ้า Mongo ล่ม (memory-only)

### 4. วางไฟล์
- **โมเดล:** ใส่ `best_x.pt` / `best_m.pt` ในโฟลเดอร์ `models/`
  (ยังไม่มี? ระบบจะดาวน์โหลด pretrained `yolov8x.pt` / `yolov8m.pt` มาใช้อัตโนมัติ)
- **วิดีโอ:** ใส่ `north.mp4 / east.mp4 / south.mp4 / west.mp4` ในโฟลเดอร์ `videos/`
  (ดู `models/README.md` และ `videos/README.md`)

### 5. เปิดเซิร์ฟเวอร์
```bash
python run.py --reload
# หรือ: uvicorn app.main:app --reload
```

### 6. เปิดเบราว์เซอร์ → http://localhost:8000

---

## 🗺️ Endpoints

| Path | คำอธิบาย |
|---|---|
| `GET /` | Landing page |
| `GET /dashboard` | Dashboard 4 กล้อง |
| `GET /detect` | เครื่องมือตรวจจับ (image / video / webcam) |
| `GET /stream/{cam_id}` | MJPEG stream ของแต่ละกล้อง |
| `GET /stats` | สถานะระบบ (JSON) |
| `POST /predict/image` | ตรวจจับภาพที่อัปโหลด |
| `POST /predict/video` | ตรวจจับทุกเฟรมในวิดีโอ → คืน stats |

---

## ⚙️ ปรับแต่ง (แก้ใน `app/config.py`)

| ตัวแปร | ค่าเริ่มต้น | ความหมาย |
|---|---|---|
| `CONF_THRESHOLD` | 0.40 | ความมั่นใจขั้นต่ำ |
| `IMG_SIZE` | 480 | ลดเป็น 416/320 = เร็วขึ้น |
| `DEVICE` | `"cpu"` | เปลี่ยนเป็น `"cuda"` ถ้าการ์ดจอไหว |
| `TARGET_FPS` | 20 | จำกัด fps แต่ละสตรีม |
| `EMERGENCY_CLASSES` | ambulance/firetruck/police | class ที่ถือเป็นรถฉุกเฉิน |

---

## 💡 เคล็ดลับ Performance

YOLOv8x หนัก — รัน 4 กล้องพร้อมกันบน CPU จะช้า ถ้าอืดให้ลอง:
1. ลด `IMG_SIZE` เป็น 416 หรือ 320
2. สลับไปใช้โมเดล `m` (YOLOv8m) บน dashboard
3. ตั้ง `DEVICE = "cuda"` ถ้ามี GPU
4. Export โมเดลเป็น ONNX สำหรับ production

---

## 🐳 รันด้วย Docker (ทางเลือก)

```bash
docker compose up --build                                           # CPU
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build   # GPU
```
→ http://localhost:8000 · รายละเอียด: [`docs/DOCKER.md`](docs/DOCKER.md)

---

## 📚 เอกสาร

| ไฟล์ | เนื้อหา |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | กฎประจำโปรเจกต์ (สำหรับ AI dev assistant) |
| [`docs/STATUS.md`](docs/STATUS.md) | สถานะปัจจุบัน + ข้อจำกัด (อ่านก่อนเริ่มงาน) |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | สถาปัตยกรรม · threading model · endpoints |
| [`docs/PRODUCTION_ROADMAP.md`](docs/PRODUCTION_ROADMAP.md) | แผนพาไป production ให้ทันวัน present |
| [`docs/DEMO.md`](docs/DEMO.md) | 🎤 Demo runbook — checklist + ลำดับนำเสนอ + Q&A + แผนสำรอง |
| [`docs/DOCKER.md`](docs/DOCKER.md) | 🐳 รันด้วย Docker Compose (CPU / GPU) |
