"""
config.py — ตั้งค่าทั้งหมดของระบบไว้ที่เดียว
แก้ตรงนี้ที่เดียว ไม่ต้องไปแก้โค้ดส่วนอื่น
"""
from pathlib import Path

# BASE_DIR = โฟลเดอร์ app/ · PROJECT_ROOT = รากโปรเจกต์ (ที่เก็บ models/, videos/, static/, templates/)
BASE_DIR     = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

STATIC_DIR    = PROJECT_ROOT / "static"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# ===== โมเดล =====
# วางไฟล์ที่เทรนเองในโฟลเดอร์ models/
# ถ้าไม่พบไฟล์ใด → ระบบ fallback ไปใช้ pretrained จาก ultralytics อัตโนมัติ
MODEL_PATH_X = PROJECT_ROOT / "models" / "best_x.pt"   # YOLOv8x ที่เทรนเอง
MODEL_PATH_M = PROJECT_ROOT / "models" / "best_m.pt"   # YOLOv8m ที่เทรนเอง
FALLBACK_X   = "yolov8x.pt"   # pretrained fallback สำหรับ x
FALLBACK_M   = "yolov8m.pt"   # pretrained fallback สำหรับ m

# compat alias (ใช้กับโค้ดเก่าที่ยังอ้าง MODEL_PATH)
MODEL_PATH     = MODEL_PATH_X
FALLBACK_MODEL = FALLBACK_X

# ===== กล้อง 4 มุม =====
# วางวิดีโอไว้ในโฟลเดอร์ videos/ แล้วตั้งชื่อให้ตรง
# ถ้ามีคลิปไม่ครบ 4 → ใส่ path เดิมซ้ำได้ หรือปล่อยไฟล์ที่ไม่มีไว้ (จะขึ้น NO SIGNAL)
CAMERA_VIDEOS = {
    "cam1": PROJECT_ROOT / "videos" / "north.mp4",
    "cam2": PROJECT_ROOT / "videos" / "east.mp4",
    "cam3": PROJECT_ROOT / "videos" / "south.mp4",
    "cam4": PROJECT_ROOT / "videos" / "west.mp4",
}

CAMERA_LABELS = {
    "cam1": "CAM-1 · NORTH",
    "cam2": "CAM-2 · EAST",
    "cam3": "CAM-3 · SOUTH",
    "cam4": "CAM-4 · WEST",
}

# ===== พารามิเตอร์การตรวจจับ =====
CONF_THRESHOLD = 0.40    # ความมั่นใจขั้นต่ำ (0-1) ต่ำกว่านี้ไม่นับ
IMG_SIZE       = 480     # 640 = แม่นสุด/ช้า, 480 = สมดุล, 416/320 = เร็วสุด
# "cuda" = ใช้ GPU · "cpu" = ใช้ CPU · detector.py จะ fallback เป็น cpu อัตโนมัติถ้า CUDA ไม่พร้อม
DEVICE         = "cuda"

# ===== ควบคุมความเร็ว =====
# หมายเหตุ: เวอร์ชันนี้แยก thread เล่นวิดีโอ/ตรวจจับแล้ว ภาพจึงลื่นเสมอ
TARGET_FPS = 20          # fps ของการเล่นวิดีโอแต่ละกล้อง

# ===== เกณฑ์ class ที่ถือว่าเป็น "รถฉุกเฉิน" (ใช้ปรับสัญญาณไฟ) =====
EMERGENCY_CLASSES = {"ambulance", "firetruck", "police"}
