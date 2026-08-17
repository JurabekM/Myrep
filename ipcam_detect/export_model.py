"""YOLOv8n / YOLO11n modelini ONNX yoki OpenVINO formatiga eksport qilish.

Bu skript **bir marta** ishga tushiriladi (ultralytics + torch kerak).
Ishlash paytida (main.py) na torch, na ultralytics kerak bo'lmaydi —
shuning uchun runtime RAM sarfi ~5-8 barobar kam bo'ladi.

Namunalar::

    python export_model.py --model yolov8n.pt --format onnx --imgsz 640
    python export_model.py --model yolo11n.pt --format openvino --imgsz 416
    python export_model.py --model yolov8n.pt --format onnx --half   # FP16
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="YOLO -> ONNX/OpenVINO eksport")
    p.add_argument("--model", default="yolov8n.pt",
                   help="Ultralytics model nomi yoki .pt yo'li (yolov8n.pt, yolo11n.pt)")
    p.add_argument("--format", choices=("onnx", "openvino"), default="onnx")
    p.add_argument("--imgsz", type=int, default=640, help="Kirish o'lchami (640 / 416 / 320)")
    p.add_argument("--opset", type=int, default=12, help="ONNX opset versiyasi")
    p.add_argument("--half", action="store_true", help="FP16 (faqat GPU/NPU uchun foydali)")
    p.add_argument("--int8", action="store_true", help="INT8 kvantlash (OpenVINO, eng tejamkor)")
    p.add_argument("--simplify", action="store_true", default=True,
                   help="onnx-simplifier bilan grafni soddalashtirish")
    p.add_argument("--out-dir", default="models", help="Natija papkasi")
    p.add_argument("--name", default=None,
                   help="Natija fayl nomi (default: <model>_<imgsz>.onnx)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError:
        print(
            "XATO: ultralytics o'rnatilmagan.\n"
            "  pip install ultralytics onnx onnxsim\n"
            "(Bu faqat eksport uchun kerak, runtime uchun emas.)",
            file=sys.stderr,
        )
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Model yuklanmoqda: {args.model}")
    model = YOLO(args.model)

    kwargs = dict(format=args.format, imgsz=args.imgsz, half=args.half, dynamic=False)
    if args.format == "onnx":
        kwargs.update(opset=args.opset, simplify=args.simplify)
    else:
        kwargs.update(int8=args.int8)

    print(f"Eksport: format={args.format} imgsz={args.imgsz} ...")
    exported = Path(model.export(**kwargs))

    # Natijani models/ papkasiga ko'chirish. Nomga imgsz qo'shiladi — aks
    # holda 416 eksporti mavjud 640 modelni jimgina ustidan yozib yuboradi.
    name = args.name or f"{exported.stem}_{args.imgsz}{exported.suffix}"
    target = out_dir / name
    if exported.resolve() != target.resolve():
        if exported.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(exported, target)
        else:
            shutil.copy2(exported, target)

    if args.format == "openvino":
        xml = next(target.glob("*.xml"), None) if target.is_dir() else None
        final = xml or target
    else:
        final = target

    print(f"\nTayyor: {final}")
    print("Ishga tushirish:")
    print(f'  python main.py --url "rtsp://..." --model "{final}" '
          f"--backend {args.format} --imgsz {args.imgsz}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
