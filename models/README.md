# models/

วางไฟล์ YOLO weights ที่นี่ (ไฟล์ `.pt` ถูก gitignore — ไม่ commit เข้า repo)

| ไฟล์ | คำอธิบาย |
|---|---|
| `best_x.pt` | YOLOv8x ที่เทรนเอง (แม่นกว่า / ช้ากว่า) |
| `best_m.pt` | YOLOv8m ที่เทรนเอง (เร็วกว่า / เบากว่า) |

ถ้าไม่พบไฟล์ที่เทรนเอง ระบบจะ fallback ไปใช้ pretrained (`yolov8x.pt` / `yolov8m.pt`)
จาก ultralytics โดยดาวน์โหลดอัตโนมัติ — ดู `app/config.py`
