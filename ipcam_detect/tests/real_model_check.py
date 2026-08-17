"""real_model_check.py — HAQIQIY yolov8n.onnx bilan sinov va benchmark.

`selfcheck.py` arxitekturani soxta model bilan tekshiradi; bu skript esa
haqiqiy og'irliklar bilan **deteksiya sifatini** va **resurs sarfini**
o'lchaydi.

Talab:
  1. `python export_model.py --model yolov8n.pt --format onnx --imgsz 640`
  2. `tests/assets/bus.jpg`, `tests/assets/zidane.jpg` (ma'lum tarkibli rasmlar)

    python tests/real_model_check.py [--model models/yolov8n.onnx]
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ipcam_detect import (  # noqa: E402
    DetectorConfig,
    PipelineConfig,
    PipelineManager,
    StreamConfig,
)
from ipcam_detect.detector import OnnxDetector  # noqa: E402
from ipcam_detect.visualizer import Visualizer  # noqa: E402

ASSETS = ROOT / "tests" / "assets"
_results: List[tuple] = []


def check(name: str, cond: bool, info: str = "") -> None:
    _results.append((name, cond, info))
    print(f"{'[OK]  ' if cond else '[FAIL]'} {name}" + (f"  ({info})" if info else ""))


def counts(dets) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for d in dets:
        out[d.label] = out.get(d.label, 0) + 1
    return out


# ---------------------------------------------------------------- 1. sifat
def test_quality(model: str, out_dir: Path) -> None:
    """Ma'lum tarkibli rasmlarda to'g'ri sinflar topilishini tekshiradi."""
    det = OnnxDetector(DetectorConfig(model_path=model, imgsz=640,
                                      conf_threshold=0.35, num_threads=2))
    vis = Visualizer(show=False)

    bus = cv2.imread(str(ASSETS / "bus.jpg"))
    zid = cv2.imread(str(ASSETS / "zidane.jpg"))
    check("test rasmlari o'qildi", bus is not None and zid is not None)

    d1 = det.detect(bus)
    c1 = counts(d1)
    print(f"       bus.jpg    -> {c1}")
    check("bus.jpg: avtobus topildi", c1.get("bus", 0) >= 1, str(c1))
    check("bus.jpg: 3+ odam topildi", c1.get("person", 0) >= 3,
          f"{c1.get('person', 0)} ta")
    check("bus.jpg: ishonch yuqori",
          all(d.score >= 0.35 for d in d1) and max(d.score for d in d1) > 0.8,
          f"max={max(d.score for d in d1):.2f}")

    d2 = det.detect(zid)
    c2 = counts(d2)
    print(f"       zidane.jpg -> {c2}")
    check("zidane.jpg: 2 odam topildi", c2.get("person", 0) == 2, str(c2))

    # Bounding box'lar rasm ichida va mantiqiy o'lchamda
    h, w = bus.shape[:2]
    ok_geom = all(0 <= d.x1 < d.x2 <= w and 0 <= d.y1 < d.y2 <= h and
                  (d.x2 - d.x1) * (d.y2 - d.y1) > 100 for d in d1)
    check("bbox geometriyasi to'g'ri", ok_geom, f"kadr {w}x{h}")

    # Avtobus qutisi kadrning katta qismini egallashi kerak (~sanity)
    bus_box = next(d for d in d1 if d.label == "bus")
    area = (bus_box.x2 - bus_box.x1) * (bus_box.y2 - bus_box.y1) / (w * h)
    check("avtobus qutisi mantiqiy kattalikda", 0.3 < area < 0.95,
          f"kadr maydonining {area * 100:.0f}%")

    # Vizual dalil
    out_dir.mkdir(parents=True, exist_ok=True)
    for img, dets, name in ((bus, d1, "bus"), (zid, d2, "zidane")):
        canvas = img.copy()
        vis.draw(canvas, dets, hud=f"yolov8n.onnx | {counts(dets)}")
        cv2.imwrite(str(out_dir / f"detected_{name}.jpg"), canvas)
    print(f"       natija rasmlari: {out_dir}")

    # class filtri haqiqiy model bilan
    det_p = OnnxDetector(DetectorConfig(model_path=model, imgsz=640,
                                        conf_threshold=0.35, class_filter=[0]))
    only_person = det_p.detect(bus)
    check("class filtri (--classes 0) ishlaydi",
          only_person and all(d.label == "person" for d in only_person),
          f"{len(only_person)} ta odam")
    det_p.close()

    det.close()


# ------------------------------------------------------------ 2. benchmark
def bench(model: str, imgsz: int, threads: int, n: int = 40) -> float:
    """O'rtacha inference vaqti (ms/kadr)."""
    det = OnnxDetector(DetectorConfig(model_path=model, imgsz=imgsz,
                                      conf_threshold=0.35, num_threads=threads))
    frame = cv2.imread(str(ASSETS / "bus.jpg"))
    for _ in range(5):
        det.detect(frame)  # warm-up
    t0 = time.perf_counter()
    for _ in range(n):
        det.detect(frame)
    ms = (time.perf_counter() - t0) / n * 1000
    det.close()
    return ms


def test_benchmark(model640: str, model416: str) -> None:
    """640 va 416 modellarini taqqoslaydi.

    ONNX modeli qat'iy kirish o'lchami bilan eksport qilinadi, shuning uchun
    416 uchun ALOHIDA eksport kerak — bitta faylda `--imgsz` ni o'zgartirish
    yetarli emas (detektor buni sezib, model o'lchamiga moslashadi).
    """
    print("       (yolov8n, bus.jpg 810x1080, CPU)")
    rows = []
    for path, imgsz, threads in (
        (model640, 640, 2), (model640, 640, 1),
        (model416, 416, 2), (model416, 416, 1),
    ):
        if not os.path.exists(path):
            print(f"       {os.path.basename(path)} yo'q — o'tkazib yuborildi")
            continue
        ms = bench(path, imgsz, threads)
        rows.append((imgsz, threads, ms))
        print(f"       imgsz={imgsz} threads={threads}: {ms:6.1f} ms/kadr "
              f"({1000 / ms:5.1f} FPS)")

    ms640 = next((m for i, t, m in rows if i == 640 and t == 2), None)
    ms416 = next((m for i, t, m in rows if i == 416 and t == 2), None)
    check("inference real vaqtda ishlaydi (<200 ms)", bool(ms640) and ms640 < 200,
          f"{ms640:.1f} ms")
    if ms416:
        check("imgsz=416 sezilarli tezroq", ms416 < ms640 * 0.75,
              f"{ms416:.1f} vs {ms640:.1f} ms ({ms640 / ms416:.2f}x)")


def test_imgsz_mismatch(model640: str) -> None:
    """640 model + `--imgsz 416` -> yiqilmasdan moslashishi kerak."""
    det = OnnxDetector(DetectorConfig(model_path=model640, imgsz=416,
                                      conf_threshold=0.35))
    check("noto'g'ri imgsz avtomatik tuzatildi", det.imgsz == 640, f"imgsz={det.imgsz}")
    dets = det.detect(cv2.imread(str(ASSETS / "bus.jpg")))
    check("moslashtirilgandan keyin deteksiya ishlaydi", len(dets) >= 4,
          f"{counts(dets)}")
    det.close()


# ------------------------------------------------------------- 3. pipeline
def make_video(path: str, seconds: int = 12, fps: int = 25) -> None:
    """bus.jpg ustida pan qilib, kamera oqimini taqlid qiluvchi video."""
    src = cv2.imread(str(ASSETS / "bus.jpg"))
    src = cv2.resize(src, (1280, 720))
    _fourcc = getattr(cv2, "VideoWriter_fourcc", None) or cv2.VideoWriter.fourcc
    vw = cv2.VideoWriter(path, _fourcc(*"mp4v"), fps, (960, 540))
    total = seconds * fps
    for i in range(total):
        # sekin gorizontal pan — har kadr boshqacha bo'lsin
        x = int(abs(np.sin(i / total * np.pi)) * (1280 - 960))
        vw.write(src[90:630, x:x + 960])
    vw.release()


def test_pipeline_real(model: str, video: str, out_dir: Path) -> None:
    events = str(out_dir / "real_events.jsonl")
    if os.path.exists(events):
        os.remove(events)

    cfg = PipelineConfig(
        stream=StreamConfig(url=video, backend="opencv", loop_source=True),
        detector=DetectorConfig(model_path=model, imgsz=640,
                                conf_threshold=0.35, num_threads=2),
        detect_every=3,
        tracker="cache",
        show=False,                # headless
        target_fps=15.0,           # tipik IP kamera yuklamasi
        stats_interval=2.0,
        events_path=events,
    )
    seen: List[int] = []
    with_bus: List[bool] = []

    def collect(frame, dets) -> None:
        seen.append(len(dets))
        # yolov8n bus/truck/car sinflarini kesilgan kadrda ba'zan
        # almashtirib yuboradi — "yirik transport" deb hisoblaymiz
        with_bus.append(any(d.label in ("bus", "truck", "car") for d in dets))

    pipe = PipelineManager(cfg, on_detections=collect)
    threading.Timer(15.0, pipe.stop).start()
    pipe.run()

    check("pipeline haqiqiy model bilan ishladi", pipe.frames_processed > 100,
          f"{pipe.frames_processed} kadr / {pipe.detections_run} deteksiya")
    # target_fps — yuqori chegara. Manba 25 fps bo'lgani uchun natija 40 ms
    # panjarasiga kvantlanadi (66 ms -> 80 ms -> ~12.5 FPS). Shuning uchun
    # "oshib ketmadi" va "bir kvantdan ko'p pastga tushmadi" tekshiriladi.
    check("target_fps oshib ketmadi", pipe.avg_fps <= 15.5, f"{pipe.avg_fps:.1f} FPS")
    check("target_fps ga yaqin (1 kvant ichida)", pipe.avg_fps >= 11.5,
          f"{pipe.avg_fps:.1f} / 15.0 FPS")
    # Pan qilinganda kadr chetidagi odamlar chiqib ketadi, shuning uchun
    # obyektlar soni o'zgaruvchan; avtobus esa doim kadr ichida.
    check("har deteksiya kadrida obyekt topildi", seen and min(seen) >= 2,
          f"min={min(seen) if seen else 0} max={max(seen) if seen else 0} obyekt")
    check("yirik transport barqaror aniqlandi",
          with_bus and sum(with_bus) / len(with_bus) >= 0.95,
          f"{sum(with_bus)}/{len(with_bus)} kadr")
    check("JSONL yozildi", os.path.getsize(events) > 0,
          f"{os.path.getsize(events) / 1024:.0f} KB")
    check("RAM chegarada (<250 MB)", pipe.monitor.peak_rss_mb < 250,
          f"peak {pipe.monitor.peak_rss_mb:.0f} MB")
    check("kadr tashlash ishladi", pipe.stream.stats.dropped > 0,
          f"o'qildi={pipe.stream.stats.read} tashlandi={pipe.stream.stats.dropped}")


def main() -> int:
    import logging

    p = argparse.ArgumentParser()
    p.add_argument("--model", default=str(ROOT / "models" / "yolov8n_640.onnx"))
    p.add_argument("--model416", default=str(ROOT / "models" / "yolov8n_416.onnx"))
    p.add_argument("--out", default=str(ROOT / "out"))
    args = p.parse_args()
    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s | %(name)s | %(message)s")

    if not os.path.exists(args.model):
        print(f"Model topilmadi: {args.model}\n"
              "Avval: python export_model.py --model yolov8n.pt --format onnx")
        return 2

    out_dir = Path(args.out)
    print("=" * 70)
    print(" HAQIQIY yolov8n.onnx sinovi")
    print(f" Model: {args.model} ({os.path.getsize(args.model)/1024/1024:.1f} MB)")
    print("=" * 70)

    print("\n-- 1. Deteksiya sifati --")
    test_quality(args.model, out_dir)

    print("\n-- 2. imgsz mosligi --")
    test_imgsz_mismatch(args.model)

    print("\n-- 3. Benchmark --")
    test_benchmark(args.model, args.model416)

    print("\n-- 4. End-to-end pipeline (15 s, headless) --")
    video = os.path.join(tempfile.gettempdir(), "ipcam_real.mp4")
    make_video(video)
    test_pipeline_real(args.model, video, out_dir)
    try:
        os.remove(video)
    except OSError:
        pass

    ok = sum(1 for _, c, _ in _results if c)
    print("\n" + "=" * 70)
    print(f" NATIJA: {ok}/{len(_results)} test o'tdi")
    print("=" * 70)
    for name, cond, info in _results:
        if not cond:
            print(f"  [FAIL] {name} {info}")
    return 0 if ok == len(_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
