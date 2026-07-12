r"""
build_model_report.py — สร้าง app/model_report.json จากผลเทรนจริงใน run/

อ่าน results.csv + args.yaml ของแต่ละโมเดล → เลือก epoch ที่ fitness สูงสุด
(= best.pt ที่ ultralytics เซฟ: fitness = 0.1*mAP50 + 0.9*mAP50-95) → เขียนเป็น JSON
ให้หน้า Results อ่าน (เลิก hardcode)

รัน:  venv\Scripts\python scripts\build_model_report.py
"""
import csv
import json
from pathlib import Path

import yaml

ROOT    = Path(__file__).resolve().parent.parent
RUN_DIR = ROOT / "run"
OUT     = ROOT / "app" / "model_report.json"

NAMES  = {"x": "YOLOv8x", "m": "YOLOv8m"}
PARAMS = {"x": "68.2M", "m": "25.9M"}


def fitness(r):
    return 0.1 * r["mAP50"] + 0.9 * r["mAP50_95"]


def parse_results(csv_path):
    rows = []
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "epoch":     int(float(r["epoch"])),
                "precision": float(r["metrics/precision(B)"]),
                "recall":    float(r["metrics/recall(B)"]),
                "mAP50":     float(r["metrics/mAP50(B)"]),
                "mAP50_95":  float(r["metrics/mAP50-95(B)"]),
            })
    return max(rows, key=fitness), len(rows)   # best fitness row = deployed best.pt


def model_key(dirname):
    if "yolov8x" in dirname:
        return "x"
    if "yolov8m" in dirname:
        return "m"
    return dirname


def main():
    models, training, x_dir = [], None, None
    for d in sorted(RUN_DIR.iterdir()):
        if not (d / "results.csv").exists():
            continue
        key = model_key(d.name)
        best, epochs = parse_results(d / "results.csv")
        models.append({
            "key": key, "name": NAMES.get(key, key), "params": PARAMS.get(key, "?"),
            "precision": round(best["precision"], 4),
            "recall":    round(best["recall"], 4),
            "mAP50":     round(best["mAP50"], 4),
            "mAP50_95":  round(best["mAP50_95"], 4),
            "best_epoch": best["epoch"], "epochs": epochs,
        })
        if key == "x":
            x_dir = d.name
        if training is None:
            a = yaml.safe_load((d / "args.yaml").read_text())
            dev = str(a.get("device", ""))
            training = {
                "epochs": a.get("epochs"), "batch": a.get("batch"), "imgsz": a.get("imgsz"),
                "optimizer": a.get("optimizer"), "lr0": a.get("lr0"),
                "patience": a.get("patience"), "momentum": a.get("momentum"),
                "weight_decay": a.get("weight_decay"),
                "device": "GPU (CUDA)" if dev not in ("", "cpu") else "CPU",
            }

    models.sort(key=lambda m: 0 if m["key"] == "x" else 1)   # x เป็นตัวหลัก
    ev_dir = x_dir or (models[0].get("key") and sorted(p.name for p in RUN_DIR.iterdir())[0])
    report = {
        "primary": "x",
        "classes": ["ambulance", "firetruck", "police"],
        "models": models,
        "training": training,
        # รูปหลักฐาน — เสิร์ฟผ่าน mount /report (= โฟลเดอร์ run/)
        "evidence": {
            "results":     f"/report/{ev_dir}/results.png",
            "confusion":   f"/report/{ev_dir}/confusion_matrix_normalized.png",
            "pr_curve":    f"/report/{ev_dir}/BoxPR_curve.png",
            "predictions": f"/report/{ev_dir}/val_batch0_pred.jpg",
        },
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"wrote {OUT}")
    for m in models:
        print(f"  {m['name']}: mAP50={m['mAP50']} mAP50-95={m['mAP50_95']} "
              f"P={m['precision']} R={m['recall']} (best epoch {m['best_epoch']}/{m['epochs']})")


if __name__ == "__main__":
    main()
