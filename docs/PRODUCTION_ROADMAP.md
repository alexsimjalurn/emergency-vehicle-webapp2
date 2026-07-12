# Production Roadmap — EVD System

แผนพา EVD จาก prototype → ใช้งานจริงได้ระดับ production ให้ทันวัน present

> **หลักคิด:** โปรเจกต์นี้ต้อง **demo ขึ้นได้เสมอ** — ทำทีละชั้น, แต่ละชั้นจบแล้วระบบยังรันได้
> อย่ารื้อใหญ่จนวัน present รันไม่ขึ้น · เลือกทำเฉพาะสิ่งที่เพิ่ม "ความน่าเชื่อถือตอน present" มากที่สุดก่อน

---

## แผน 5 วัน (constraint: RTX 3050 4GB · วิดีโอจำลอง · MongoDB · deadline ~2026-07-17)

| วัน | งาน | ผลลัพธ์ที่จับต้องได้ | ความเสี่ยง |
|---|---|---|---|
| **D1** | **Python + GPU + env ให้นิ่ง** — ① ลง Python 3.12 (เครื่องยังไม่มี) ② venv ใหม่ ③ torch CUDA (cu121) ④ `DEVICE="cuda"`, default `m` ⑤ วัด fps/VRAM 4 กล้อง | ระบบเดิมรันบน GPU ลื่นขึ้นชัด + ตัวเลข before/after | ต่ำ (ไม่แตะ logic) |
| **D2** | **MongoDB persistence** — เพิ่ม `pymongo` + connection ใน `config.py` · บันทึก detection event (class, cam, conf, time) ลง collection ทุกครั้งที่ `state.update` เจอรถใหม่ · counts/log ตอน startup โหลดจาก DB | log/counts ไม่หายเมื่อ restart + มีข้อมูลย้อนหลัง | ต่ำ-กลาง |
| **D3** | **หน้า Results ใช้เลขจริง + หน้า History** — results อ่านจากผล training จริง · หน้าสถิติย้อนหลัง aggregate จาก MongoDB (ต่อวัน/ชม./ทิศ/ประเภท) | ตอบกรรมการได้ว่าเลขมาจากไหน + โชว์ analytics | กลาง |
| **D4** | **Object tracking (นับให้แม่น)** — ใส่ ByteTrack (ultralytics `model.track`) นับ "คัน" ไม่ใช่ "เฟรม" | counts น่าเชื่อถือ ไม่นับซ้ำ | กลาง-สูง (ทำหลัง D1-3 เสถียร) |
| **D5** | **Polish + ซ้อม demo** — เลือกคลิปที่ตรวจเจอชัวร์, เขียน demo script, fix bug, (option) auth + Docker, freeze main | present ขึ้นได้ 100% มีของสำรอง | — |

> **buffer:** ถ้า D4 (tracking) ไม่ทัน/พัง → ตัดออกได้ ระบบยังเดิน · ถ้า D1-3 เสร็จเร็ว → ขยับ auth/Docker ขึ้นมา
> **ทำเป็น feature branch ทีละวัน** merge เข้า main เฉพาะที่รันผ่าน — main คือตัวสำรองวัน present

---

## จัดลำดับตาม "คุ้มค่าต่อวัน present"

### 🟢 Tier 1 — ทำก่อน (ผลชัด, เสี่ยงต่ำ, ทำให้ present น่าเชื่อถือ)

1. **หน้า Results ให้มาจากผลจริง**
   - ตอนนี้ metric hardcode ใน `stats.html` → ย้ายไปอ่านจากไฟล์ผล YOLO (`runs/.../results.csv`, `args.yaml`) หรืออย่างน้อยเก็บเป็น `docs/model_report.json` ที่ generate จากการเทรนจริง
   - **เหตุผล:** กรรมการมักถาม "ตัวเลขนี้มาจากไหน" — ต้องตอบได้

2. **Environment ที่ reproduce ได้**
   - `python -m venv` ใหม่ (ตัวเก่าเสีย) · pin เวอร์ชันใน `requirements.txt` (ระบุ torch/ultralytics ที่ทดสอบแล้ว) · เขียนขั้นตอนรันใน README ให้เป๊ะ
   - **เหตุผล:** วัน present เครื่องต้องรันขึ้นชัวร์

3. **Persistence ขั้นต่ำ (log + counts)**
   - เก็บ detection log/counts ลงไฟล์ (SQLite ก็พอ — ไม่ต้อง MongoDB/Postgres) → restart แล้วไม่หาย + มีสถิติย้อนหลังให้โชว์
   - **เหตุผล:** "ระบบจำได้" ดูเป็น product มากกว่า demo ชั่วคราว

4. **Auth ขั้นต่ำ**
   - shared password + session/JWT ก่อนเข้า dashboard (ตามแนวเดียวกับโปรเจกต์อื่นในเครื่องนี้)
   - **เหตุผล:** ถ้า deploy ให้เข้าถึงผ่านเน็ต ต้องไม่เปิดโล่ง

### 🟡 Tier 2 — ถ้าเวลาพอ (ยกระดับจาก demo → ใช้จริง)

5. **กล้องจริง (RTSP/IP)**
   - abstract `CameraWorker` ให้รับ source เป็น RTSP URL ได้ (ตอนนี้ผูกกับไฟล์ mp4) · ทดสอบกับกล้อง IP/webcam จริง 1 ตัวก่อน
   - จัดการ reconnect เมื่อ stream หลุด (กล้องจริงหลุดบ่อย)

6. **Object tracking (นับให้แม่น)**
   - ใส่ tracker (ByteTrack/BoT-SORT ที่ ultralytics รองรับ) → นับ "คัน" ไม่ใช่ "เฟรม" → เลขน่าเชื่อถือ
   - แก้ปัญหานับซ้ำเมื่อรถหลุด frame

7. **Performance / GPU**
   - ถ้ามี GPU: `DEVICE="cuda"` · พิจารณา batch inference 4 กล้องพร้อมกัน · หรือ frame-skip ปรับได้
   - ถ้าไม่มี GPU: ใช้โมเดล `m`/`n`, ลด `IMG_SIZE`, export ONNX/TensorRT

8. **Deploy เป็นบริการ**
   - Docker Compose + Uvicorn/Gunicorn workers + nginx reverse proxy + `restart: unless-stopped`
   - HTTPS ถ้าเข้าผ่านโดเมน (webcam tab ต้องใช้ HTTPS ถึงจะขอ getUserMedia ได้นอก localhost)

### 🔵 Tier 3 — ต่อยอด (ทำให้เป็นระบบจริง, อาจเกินขอบเขต FYP)

9. **Signal preemption logic จริง** — เลือกทิศให้ไฟเขียวเมื่อหลายกล้องเจอพร้อมกัน (priority + timing) · จำลอง controller ไฟจราจร
10. **Hardware integration** — ต่อสัญญาณจริง (Arduino/relay/PLC) หรือชุดไฟจำลอง
11. **Analytics dashboard** — สถิติต่อวัน/ชม./ทิศ, peak time, response time
12. **Alerting** — แจ้งเตือน (LINE/webhook) เมื่อเจอรถฉุกเฉิน

---

## หลักการทำ production (กันพลาดวัน present)

- **แต่ละขั้นต้องรันได้:** ทำ feature branch, merge เข้า main เฉพาะที่ demo ผ่าน · main = ตัวสำรองที่รู้ว่าขึ้นได้เสมอ
- **มี fallback path:** กล้องจริงหลุด → กลับไปวิดีโอจำลองได้ · GPU ไม่มี → CPU + โมเดลเล็กได้ · DB ล่ม → ยัง live ได้
- **เตรียม demo script:** ลำดับที่จะโชว์วัน present + คลิป/ภาพตัวอย่างที่รู้ว่าตรวจเจอชัวร์ (อย่าเสี่ยงกับ input สด 100%)
- **Config เดียว:** ทุกค่าที่ต่างระหว่าง demo/prod (device, camera source, DB path) ผ่าน `config.py`/`.env` — สลับ environment ได้ไม่ต้องแก้โค้ด
- **วัดก่อนเชื่อ:** ทุกคำว่า "เร็วขึ้น/แม่นขึ้น" ต้องมีตัวเลข (fps, ms/frame, mAP) เทียบ before/after

---

## ⏭️ ขั้นถัดไป (รอผู้ใช้ยืนยันก่อนลงมือ)

ก่อนเริ่ม Tier ใด ต้องเคาะคำถามใน `STATUS.md` → "การตัดสินใจที่ยังค้าง":
เครื่อง demo/มี GPU ไหม · กล้องจริงหรือจำลอง · ต้องมี DB ไหม · ไฟจราจร sim หรือ hardware · เหลือเวลากี่วันถึงวัน present

จากคำตอบ → เลือก Tier 1 ที่ทำแน่ ๆ แล้วค่อยไล่ Tier 2 ตามเวลาที่เหลือ
