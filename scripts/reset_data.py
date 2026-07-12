r"""
reset_data.py — ล้างข้อมูล detection ทั้งหมดใน MongoDB (เริ่มสะอาดก่อน present)

รัน:  venv\Scripts\python scripts\reset_data.py
      venv\Scripts\python scripts\reset_data.py --yes    (ไม่ถามยืนยัน)
"""
import sys

from app.db import db


def main():
    if not db.enabled:
        print("MongoDB ไม่พร้อม — ไม่มีอะไรให้ล้าง")
        return
    n = db.detections.count_documents({})
    if n == 0:
        print("collection ว่างอยู่แล้ว (0 docs)")
        return
    if "--yes" not in sys.argv:
        ans = input(f"จะลบ detection ทั้งหมด {n} รายการ? พิมพ์ 'yes' เพื่อยืนยัน: ")
        if ans.strip().lower() != "yes":
            print("ยกเลิก")
            return
    db.detections.delete_many({})
    print(f"ล้างแล้ว {n} รายการ — เริ่มสะอาด")


if __name__ == "__main__":
    main()
