"""YOLOv8 chiqish formatidagi kichik SOXTA .onnx model yaratadi.

Maqsad — `OnnxDetector` ni haqiqiy ONNX Runtime sessiyasi bilan sinash
(ulanish, kirish nomi, dtype, chiqish shakli). Bu real detektor EMAS.

    python tests/make_dummy_onnx.py --out models/dummy_yolo.onnx --imgsz 640
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def build(out_path: str, imgsz: int = 640, n_boxes: int = 8) -> str:
    import onnx
    from onnx import TensorProto, helper, numpy_helper

    nc = 80
    # (1, 4+nc, N) — YOLOv8/YOLO11 ning standart chiqish shakli
    base = np.zeros((1, 4 + nc, n_boxes), dtype=np.float32)
    c = imgsz / 2.0
    for i in range(3):  # 3 ta "obyekt": person, bicycle, car
        base[0, 0, i] = c + i * 60      # cx
        base[0, 1, i] = c               # cy
        base[0, 2, i] = 80.0            # w
        base[0, 3, i] = 160.0           # h
        base[0, 4 + i, i] = 0.9         # class i ishonchi

    const = numpy_helper.from_array(base, name="base")
    zero = numpy_helper.from_array(np.array(0.0, dtype=np.float32), name="zero")

    inp = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, imgsz, imgsz])
    out = helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 4 + nc, n_boxes])

    nodes = [
        # Kirishga bog'liqlik: mean(input) * 0 -> 0, keyin const ga qo'shiladi.
        helper.make_node("ReduceMean", ["images"], ["m"], keepdims=0),
        helper.make_node("Mul", ["m", "zero"], ["m0"]),
        helper.make_node("Add", ["base", "m0"], ["output0"]),
    ]
    graph = helper.make_graph(nodes, "dummy_yolo", [inp], [out], [const, zero])
    model = helper.make_model(
        graph, opset_imports=[helper.make_opsetid("", 18)], producer_name="ipcam_detect"
    )
    model.ir_version = 10  # onnxruntime bilan moslik uchun
    onnx.checker.check_model(model)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    onnx.save(model, out_path)
    return out_path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="models/dummy_yolo.onnx")
    p.add_argument("--imgsz", type=int, default=640)
    args = p.parse_args()
    path = build(args.out, args.imgsz)
    print(f"Yaratildi: {path} ({Path(path).stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
