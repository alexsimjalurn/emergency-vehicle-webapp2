# Architecture — EVD System

เอกสารอ้างอิงสถาปัตยกรรมระบบ (ปัจจุบัน = prototype รัน local)

---

## 1. ภาพรวม

```
┌─────────────────────────────────────────────────────────────────┐
│                          Browser (Lao UI)                        │
│   Landing · Dashboard · Detect(image/video/webcam) · Results     │
└───────────────┬──────────────────────────┬──────────────────────┘
                │ HTTP / MJPEG              │ fetch (JSON)
                ▼                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FastAPI (app/main.py)                      │
│  Pages (Jinja2)   Streams (/stream)   Predict API   Settings API │
└───────┬───────────────────┬───────────────────┬─────────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
   ┌─────────┐        ┌───────────┐       ┌──────────┐
   │ Detector│◄───────│CameraWorker│──────►│  State   │
   │ (YOLOv8)│        │ (×4, threads)│      │(in-memory)│
   └─────────┘        └───────────┘       └──────────┘
        │                   │
        ▼                   ▼
   models/*.pt         videos/*.mp4   (จำลองกล้อง — ยังไม่ใช่ RTSP)
```

---

## 2. โมดูล (app/)

| ไฟล์ | หน้าที่ | จุดสำคัญ |
|---|---|---|
| `main.py` | FastAPI app · routes ทั้งหมด · สร้าง Detector + CameraWorker ตอน startup | โหลดโมเดล **ตอน import** (top-level) → import = โหลด YOLO จริง |
| `config.py` | ค่าคอนฟิกทั้งหมด (paths, conf, device, fps, classes) | `PROJECT_ROOT`/`BASE_DIR` จาก `__file__` — ไม่พึ่ง cwd |
| `detector.py` | โหลด 2 โมเดล (`x`,`m`) · `infer()` คืน list ของ box · `draw()` วาดกรอบ | `_lock` serialize ทุก inference (กัน GPU/model แข่งกัน) · fallback pretrained ถ้าไม่มี custom weights |
| `camera.py` | `CameraWorker` ต่อกล้อง — 2 thread | playback loop (เร็ว: อ่าน+วาด+encode) / inference loop (หนัก: YOLO) แยกกัน ภาพจึงลื่น |
| `state.py` | `SystemState` singleton — signals/counts/log/settings | ทุก mutation ล็อก `_lock` · counts เพิ่มเมื่อรถฉุกเฉินโผล่ใหม่ (set diff) |

---

## 3. Threading model (หัวใจที่ทำให้ภาพลื่น)

แต่ละกล้องมี **2 thread** (daemon):

1. **playback loop** — อ่านเฟรมจากวิดีโอ → วาด box ล่าสุด (`self.boxes`) → encode JPEG → เก็บใน `latest_jpeg`
   - วิ่งที่ `TARGET_FPS` (default 20) — เบา จึงลื่นตลอด ไม่รอ inference
   - วิดีโอจบ → `seek` กลับต้น (วนลูป)
2. **inference loop** — หยิบเฟรมดิบล่าสุด (`current_raw`) → YOLO infer → อัปเดต `self.boxes` + `state`
   - วิ่งตามความเร็วเครื่อง (บน CPU ช้ากว่า playback มาก) — box จึงอัปเดตช้ากว่าภาพ แต่ภาพไม่กระตุก

`/stream/{cam_id}` แค่ดึง `latest_jpeg` ส่งเป็น MJPEG — ไม่ทำ inference ใน request

> **ข้อจำกัด:** 4 กล้อง × inference บน CPU = แย่งกันผ่าน `detector._lock` (serialize) → box หน่วงมากเมื่อรันครบ 4 ตัว ดู PRODUCTION_ROADMAP (GPU/batching)

---

## 4. Data flow — การนับ & สัญญาณไฟ

```
inference loop เจอ dets
   → state.update(cam_id, dets)
        emerg_now = {class ∈ EMERGENCY_CLASSES ที่เจอในเฟรมนี้}
        new = emerg_now − prev[cam]        # โผล่ใหม่เท่านั้น
        counts[class] += 1 (ต่อ new)       # ← in-memory, reset เมื่อ restart
        log.appendleft({name, cam, conf, t})   # เก็บ 15 รายการล่าสุด
        signals[cam] = "CLEAR" if emerg_now else "STOP"
```

- **counts**: frame-level, ไม่มี object tracking → รถคันเดิมที่หลุด frame แล้วกลับมา = นับใหม่
- **signals**: display เท่านั้น · ไม่มี logic เลือกทิศเมื่อหลายกล้อง CLEAR พร้อมกัน · ไม่ต่อฮาร์ดแวร์

---

## 5. Endpoints

| Method | Path | คืน | หมายเหตุ |
|---|---|---|---|
| GET | `/` | landing.html | หน้าแรก |
| GET | `/dashboard` | index.html | 4 กล้อง + ไฟ + log + counts |
| GET | `/detect?tab=` | detect.html | image / video / webcam |
| GET | `/results` | stats.html | ⚠️ metric hardcode |
| GET | `/about` | about.html | ข้อมูลระบบ |
| GET | `/stream/{cam_id}` | MJPEG | live feed ต่อกล้อง |
| GET | `/stats` | JSON | dashboard poll ทุก 1s |
| GET/POST | `/api/settings` | JSON | สลับ model/conf ตอน runtime |
| POST | `/predict/image` | JSON+base64 | ตรวจภาพอัปโหลด |
| POST | `/predict/video` | JSON | ตรวจทุกเฟรม → สรุป |
| POST | `/predict/webcam_frame` | JSON | ตรวจ 1 เฟรมจาก browser |

(shape เต็มดูใน `CLAUDE.md` → Response Shape)

---

## 6. Frontend

- **Server-rendered** (Jinja2) + vanilla JS — ไม่มี bundler/framework
- `base.html` = layout กลาง (sidebar, clock, model/conf control, footer) → ทุกหน้า extend
- `base.js` = ของใช้ร่วม (clock, sidebar toggle, `getModel()`/`getConf()`, sync `/api/settings`)
- `app.js` = dashboard (poll `/stats` ทุก 1s → อัปเดตไฟ/log/counts)
- `detect.js` = 3 แท็บ (image upload / video upload / webcam realtime loop)
- แก้ JS/CSS แล้ว **ต้อง bump `?v=N`** ใน template กัน cache

---

## 7. Configuration (app/config.py)

| ค่า | default | ผล |
|---|---|---|
| `CONF_THRESHOLD` | 0.40 | ความมั่นใจขั้นต่ำ |
| `IMG_SIZE` | 480 | ↓ = เร็วขึ้น/แม่นลง |
| `DEVICE` | `"cpu"` | `"cuda"` ถ้ามี GPU |
| `TARGET_FPS` | 20 | fps playback ต่อกล้อง |
| `EMERGENCY_CLASSES` | ambulance/firetruck/police | class ที่ trigger ไฟ |
| `CAMERA_VIDEOS` | north/east/south/west.mp4 | map กล้อง→ไฟล์ |
