# Docker — EVD Stack

รันทั้งระบบ (app + MongoDB) ด้วย Docker Compose · ไม่ต้องลง Python/torch/mongo บนเครื่องเอง

---

## องค์ประกอบ

| ไฟล์ | หน้าที่ |
|---|---|
| `Dockerfile` | image ของ app (Python 3.12 + torch cu121 + deps) |
| `docker-compose.yml` | app + mongo (CPU · ใช้ได้ทุกเครื่อง) |
| `docker-compose.gpu.yml` | override เปิด GPU (opt-in) |
| `.dockerignore` | กันไฟล์ใหญ่/ไม่จำเป็นเข้า image |

**models/ และ videos/** ไม่ถูก copy เข้า image (ใหญ่ + gitignored) → **mount เป็น volume** จาก host
→ ต้องมีไฟล์ weights ใน `models/` และคลิปใน `videos/` บนเครื่อง host ก่อนรัน

---

## รัน (CPU — ใช้ได้ทุกเครื่อง)

```bash
docker compose up --build
```
เปิด http://localhost:8000 · หยุด: `docker compose down` (ข้อมูล Mongo อยู่ใน volume `mongo_data` ไม่หาย)

## รัน (GPU — เร็วกว่ามาก)

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

**ต้องมี:**
- **Linux:** NVIDIA driver + [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- **Windows:** Docker Desktop (WSL2 backend) + NVIDIA driver — GPU support เปิดอัตโนมัติถ้า driver พร้อม

ตรวจว่า container เห็น GPU:
```bash
docker compose exec app python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```
> ถ้าได้ `False` → รันบน CPU อยู่ (ระบบยังทำงาน แค่ช้ากว่า — `detector` fallback อัตโนมัติ)

---

## หมายเหตุ

- **MongoDB** ในสแตกนี้แยกจาก MongoDB local ของเครื่อง (คนละ instance/ข้อมูล) — app ต่อผ่าน service `mongo`
- **ครั้งแรก build ช้า** (~ดาวน์โหลด torch cu121 ~2.5GB) · ครั้งถัดไปใช้ cache เร็ว
- **สำหรับวัน present:** แนะนำรัน **native (`python run.py`)** ที่ verify แล้วเสถียรกว่า · Docker ไว้เป็น deliverable/deploy artifact (ดู `docs/DEMO.md`)
- เปลี่ยน config ผ่าน env ได้ใน `docker-compose.yml` → `environment:` (เช่น `MONGO_DB`)
