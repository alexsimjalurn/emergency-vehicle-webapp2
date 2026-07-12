"""Emergency Vehicle Detection — FastAPI application package."""
import sys

__version__ = "1.0.0"

# บังคับ stdout/stderr เป็น utf-8 — console Windows default (cp1252) encode ภาษาไทย/สัญลักษณ์ไม่ได้
# ทำให้ print() ที่มีภาษาลาว/ไทย crash ทั้ง process · แก้ที่นี่ครอบทุก entry point (run.py, uvicorn, -c)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass
