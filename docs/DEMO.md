# Demo Runbook — วัน Present

คู่มือเตรียม + ซ้อม + นำเสนอ EVD System · อ่านก่อนวัน present และเปิดไว้ตอนขึ้นจริง

---

## ✅ Pre-flight checklist (ทำก่อนขึ้น present 30 นาที)

- [ ] **MongoDB รันอยู่** — เป็น service Automatic แล้ว แต่เช็คให้ชัวร์:
      `Get-Service MongoDB` → ต้อง `Running`
- [ ] **GPU ใช้ได้** — `venv\Scripts\python -c "import torch; print(torch.cuda.is_available())"` → `True`
- [ ] **เปิดเซิร์ฟเวอร์ทดสอบ** — `python run.py` → เปิด http://localhost:8000 ทุกหน้าขึ้นครบ
- [ ] **ล้างข้อมูลเก่า (เริ่มสะอาด)** — `venv\Scripts\python scripts\reset_data.py --yes`
- [ ] **เตรียมคลิปที่เจอครบ 3 ประเภท** ถ้ามี (ตอนนี้คลิป default เจอแต่ ambulance) — ดู "ข้อควรระวัง" ด้านล่าง
- [ ] **ปิดโปรแกรมที่กิน GPU/webcam อื่น** (เกม, Zoom) กันแย่ง VRAM
- [ ] **เตรียมออฟไลน์ได้** — ระบบไม่ต้องใช้เน็ต (charts เป็น local, ไม่มี CDN) แต่เช็คว่าโมเดล/lap ลงครบแล้ว

---

## 🚀 เปิดระบบ

```powershell
cd D:\FYP_2026\emergency-vehicle-webapp
python run.py
```
เปิด browser: **http://localhost:8000**

> ถ้า `python` ไม่เจอ ใช้ full path: `venv\Scripts\python run.py`

---

## 🎬 ลำดับการนำเสนอ (แนะนำ)

1. **Landing (`/`)** — เกริ่นโครงการ: ตรวจจับรถฉุกเฉิน → ให้สิทธิ์ไฟเขียว ลดเวลารถฉุกเฉินติดไฟแดง

2. **Dashboard (`/dashboard`)** — หัวใจของ demo
   - ชี้ 4 กล้อง (จำลองสี่แยก) → box ตรวจจับ real-time พร้อม **track ID (`#1`)**
   - ชี้สัญญาณไฟ: กล้องที่เจอรถ → **CLEAR (เขียว)** อัตโนมัติ
   - ชี้ Session stats: นับ **"คัน"** (ไม่ใช่เฟรม) + alert log
   - สลับ **YOLOv8m ↔ YOLOv8x** ที่ sidebar → ชี้ footer ว่า infer time ต่างกัน (m เร็ว / x แม่น)

3. **ສະຖິຕິຍ້ອນຫຼັງ (`/history`)** — โชว์ว่า "ระบบจำได้"
   - กราฟรายวัน / ตามชั่วโมง / ตามกล้อง — ดึงจาก MongoDB จริง
   - กดสลับ today / 7d / 30d

4. **ຜົນການທົດສອບ (`/results`)** — ความน่าเชื่อถือของโมเดล
   - ตัวเลข **จริงจากการเทรน** (mAP50 97.97%, mAP50-95 81.39%) + ตารางเทียบ m vs x
   - เลื่อนลงดู **confusion matrix + prediction จริง** บน validation set

5. **ກວດຈັບ (`/detect`)** — เครื่องมือเสริม: อัปโหลดรูป/วิดีโอ หรือเปิด webcam ตรวจสด

---

## 💬 Talking points (จุดขาย + ตอบกรรมการ)

| ประเด็น | พูดได้ว่า |
|---|---|
| **ความแม่นยำ** | YOLOv8x เทรนเอง 100 epochs · mAP50 **97.97%** · ตัวเลขมาจาก `results.csv` จริง (โชว์ได้) |
| **ทำไม 2 โมเดล** | m เร็ว (dashboard 4 กล้อง) · x แม่นกว่า (ตรวจภาพเดี่ยว) — เลือกตาม trade-off |
| **GPU** | บน RTX 3050 เร็วขึ้น **~8×** เทียบ CPU (m: 4.7→37.6 fps) |
| **นับแม่น** | ใช้ ByteTrack นับ "คัน" ต่อ track_id ไม่ใช่ต่อเฟรม → ไม่นับซ้ำ |
| **เก็บข้อมูล** | ทุก detection ลง MongoDB → มีสถิติย้อนหลัง + restart ไม่หาย |
| **สถาปัตยกรรม** | แยก playback/inference thread ต่อกล้อง → ภาพลื่นแม้ inference หนัก |

---

## ❓ คำถามกรรมการที่น่าจะเจอ + คำตอบ

- **"ตัวเลข accuracy มาจากไหน?"** → จากไฟล์ `run/yolov8x_clean100/results.csv` (ผลเทรนจริง) · หน้า Results แสดง confusion matrix + prediction จริงประกอบ
- **"กล้องจริงหรือวิดีโอ?"** → เฟสนี้ใช้วิดีโอจำลองสี่แยก · ออกแบบให้เปลี่ยนเป็น RTSP กล้องจริงได้ (แก้แค่ `config.CAMERA_VIDEOS`)
- **"ต่อไฟจราจรจริงไหม?"** → ตอนนี้เป็น simulation บนจอ · ขั้นถัดไปต่อ controller/relay จริง
- **"ถ้ามีรถฉุกเฉินหลายทิศพร้อมกัน?"** → ปัจจุบันแต่ละทิศตัดสินอิสระ · roadmap มี signal preemption logic เลือกลำดับความสำคัญ

---

## 🛟 แผนสำรอง (ถ้ามีปัญหาหน้างาน)

- **GPU มีปัญหา / VRAM เต็ม** → แก้ `app/config.py` `DEVICE="cpu"` (ระบบ fallback อัตโนมัติอยู่แล้วถ้า cuda ไม่พร้อม) · หรือใช้โมเดล `m`
- **ภาพกระตุก** → ลด `IMG_SIZE` เป็น 416 หรือลด `TARGET_FPS`
- **Tracking มีปัญหา** → `config.USE_TRACKING=False` กลับไปนับแบบเดิม (ระบบยังเดิน)
- **MongoDB ล่ม** → ระบบยังรันได้ (memory-only, แค่ไม่ persist) — ไม่ crash
- **เน็ตไม่มี** → ไม่กระทบ (ทุกอย่าง local)
- **รันไม่ขึ้นเลย** → มี branch `main` เป็นตัวสำรองที่รู้ว่าเสถียร

---

## ⚠️ ข้อควรระวัง (สำคัญ)

- **คลิป default เจอแต่ ambulance** — ถ้าอยากโชว์ firetruck/police ให้เตรียมคลิปที่มีรถ 2 ประเภทนั้น วางใน `videos/` (ดู `videos/README.md`)
  - โมเดลรองรับครบ 3 ประเภท (ambulance / firetruck / police) — bug `police_car` แก้แล้ว รถตำรวจนับได้ปกติ
- **ก่อน present ล้างข้อมูลทดสอบ** ด้วย `scripts\reset_data.py` แล้วรันสัก 2-3 นาทีให้มีข้อมูลสวย ๆ ในหน้า History
- **อย่าปิด terminal** ที่รัน `python run.py` ระหว่าง present (จะดับ server)
