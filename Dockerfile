# Emergency Vehicle Detection — app image
# torch cu121 (ใช้ GPU ได้ถ้า container เข้าถึง GPU · รันบน CPU ได้ด้วย — detector fallback อัตโนมัติ)
FROM python:3.12-slim-bookworm

# system libs ที่ OpenCV ต้องการ
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ⚠️ ลง torch (cu121) ก่อน requirements — ไม่งั้น pip ดึง CPU-only มาทับ
RUN pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 \
        --index-url https://download.pytorch.org/whl/cu121

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# โค้ด + assets (models/ videos/ = mount เป็น volume ตอน runtime · run/ = หลักฐานผลเทรน copy เข้าไป)
COPY app/       ./app/
COPY static/    ./static/
COPY templates/ ./templates/
COPY run/       ./run/
COPY run.py     .

EXPOSE 8000

# MONGO_URI ตั้งผ่าน compose (mongodb://mongo:27017)
CMD ["python", "run.py"]
