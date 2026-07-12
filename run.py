"""
run.py — จุดเริ่มรันเซิร์ฟเวอร์แบบสะดวก

    python run.py           # รันปกติ
    python run.py --reload  # โหมด dev (auto-reload)

เทียบเท่ากับ: uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
import sys

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload="--reload" in sys.argv,
    )
