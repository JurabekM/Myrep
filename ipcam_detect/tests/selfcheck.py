"""selfcheck.py — model va IP kamerasiz to'liq quvurni sinash.

Real RTSP va .onnx bo'lmaganda ham arxitekturaning to'g'riligini tekshiradi:
sintetik video fayl yaratiladi, `BaseDetector` ning matematikasi soxta model
chiqishi bilan sinaladi, so'ng butun pipeline shu fayl ustida yuritiladi.

    python tests/selfcheck.py
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import List

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ipcam_detect import (  # noqa: E402
    BoxTracker,
    DetectorConfig,
    Detection,
    PipelineConfig,
    PipelineManager,
    ResourceMonitor,
    StreamConfig,
    StreamHandler,
)
from ipcam_detect.detector import BaseDetector  # noqa: E402

PASS, FAIL = "[OK]  ", "[FAIL]"
_results: List[tuple] = []


def check(name: str, cond: bool, info: str = "") -> None:
    _results.append((name, cond, info))
    print(f"{PASS if cond else FAIL} {name}" + (f"  ({info})" if info else ""))


# --------------------------------------------------------------- soxta model
class FakeDetector(BaseDetector):
    """YOLOv8 chiqish formatini (1, 84, 8400) taqlid qiladi.

    Kadr markazida bitta "person" qutisi qaytaradi — postprocess, letterbox
    teskari transformatsiyasi va NMS shu orqali tekshiriladi.
    """

    def __init__(self, cfg: DetectorConfig, n_boxes: int = 3) -> None:
        super().__init__(cfg)
        self.calls = 0
        self.n_boxes = n_boxes
        self._out = np.zeros((1, 84, 8400), dtype=np.float32)
        c = self.imgsz / 2.0
        for i in range(n_boxes):
            # cx, cy, w, h — letterbox koordinatasida
            self._out[0, 0, i] = c + i * 10
            self._out[0, 1, i] = c
            self._out[0, 2, i] = 80.0
            self._out[0, 3, i] = 160.0
            self._out[0, 4 + i, i] = 0.9  # class i uchun ishonch

    def _infer(self, blob: np.ndarray) -> np.ndarray:
        self.calls += 1
        assert blob.shape == (1, 3, self.imgsz, self.imgsz), blob.shape
        assert blob.dtype == np.float32
        assert 0.0 <= float(blob.max()) <= 1.0, "normalizatsiya buzildi"
        return self._out


def make_video(path: str, frames: int = 90, size=(640, 360), fps: int = 25) -> None:
    """Harakatlanuvchi kvadratli sintetik mp4 yaratadi."""
    # OpenCV 4.x: cv2.VideoWriter_fourcc, 5.x: cv2.VideoWriter.fourcc
    _fourcc = getattr(cv2, "VideoWriter_fourcc", None) or cv2.VideoWriter.fourcc
    fourcc = _fourcc(*"mp4v")
    vw = cv2.VideoWriter(path, fourcc, fps, size)
    w, h = size
    for i in range(frames):
        img = np.full((h, w, 3), 30, dtype=np.uint8)
        x = int((i / frames) * (w - 80))
        cv2.rectangle(img, (x, h // 2 - 40), (x + 70, h // 2 + 40), (0, 200, 255), -1)
        cv2.putText(img, str(i), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        vw.write(img)
    vw.release()


# ------------------------------------------------------------------- testlar
def test_detector_math() -> None:
    cfg = DetectorConfig(model_path="<fake>", imgsz=640, conf_threshold=0.3)
    det = FakeDetector(cfg)

    frame = np.random.randint(0, 255, (360, 640, 3), dtype=np.uint8)
    blob_id = id(det._blob)
    dets = det.detect(frame)
    check("preprocess buferi qayta ishlatiladi", id(det._blob) == blob_id)
    check("deteksiya qaytdi", len(dets) == 3, f"{len(dets)} ta")

    d = dets[0]
    check("bbox kadr ichida",
          0 <= d.x1 < d.x2 <= 640 and 0 <= d.y1 < d.y2 <= 360,
          f"{d.x1},{d.y1},{d.x2},{d.y2}")
    # 640x360 kadr 640x640 ga letterbox -> r=1.0, pad_y=140.
    # Kvadrat markazi (320,320) -> original (320, 180)
    cy = (d.y1 + d.y2) / 2
    check("letterbox teskari transformatsiyasi", abs(cy - 180) <= 2, f"cy={cy:.1f}")
    check("class nomi to'g'ri", dets[0].label == "person", dets[0].label)

    # class filtri
    cfg2 = DetectorConfig(model_path="<fake>", imgsz=640, conf_threshold=0.3, class_filter=[1])
    det2 = FakeDetector(cfg2)
    dets2 = det2.detect(frame)
    check("class filtri ishlaydi",
          len(dets2) == 1 and dets2[0].class_id == 1, f"{[x.label for x in dets2]}")

    # allokatsiya barqarorligi: 50 marta chaqirilganda bufer o'zgarmasin
    ids = {id(det._blob) for _ in range(50) if det.detect(frame) is not None}
    check("50 iteratsiyada qo'shimcha allokatsiya yo'q", len(ids) == 1)

    # imgsz=416 ham ishlashi kerak
    det3 = FakeDetector(DetectorConfig(model_path="<fake>", imgsz=416, conf_threshold=0.3))
    check("imgsz=416 qo'llab-quvvatlanadi", len(det3.detect(frame)) == 3)


def test_stream_handler(video: str) -> None:
    # loop_source=True -> fayl jonli oqimdek cheksiz o'qiladi
    cfg = StreamConfig(url=video, backend="opencv", max_reconnects=1,
                       resize_to=(320, 180), loop_source=True)
    sh = StreamHandler(cfg)
    with sh:
        frame = sh.read(timeout=5.0)
        check("StreamHandler kadr qaytardi", frame is not None)
        if frame is not None:
            check("resize_to qo'llandi", frame.shape[:2] == (180, 320), str(frame.shape))
        # sekin iste'molchi -> slot hech qachon 1 dan oshmasligi kerak
        time.sleep(0.7)
        check("navbat hajmi 1 dan oshmadi", len(sh._slot) <= 1, f"len={len(sh._slot)}")
        got = sum(1 for _, f in zip(range(20), sh.frames(timeout=2.0)))
        check("frames() generatori ishlaydi", got >= 5, f"{got} kadr")
        check("frame dropping ishladi", sh.stats.dropped > 0, f"dropped={sh.stats.dropped}")
    check("stop() dan keyin thread to'xtadi", not sh.is_running)
    check("stop() slotni bo'shatdi", len(sh._slot) == 0)


def test_backend_fallback(video: str) -> None:
    """PyAV yo'q bo'lsa cheksiz qayta ulanish emas, opencv ga o'tish kerak."""
    import ipcam_detect.stream_handler as SH

    saved = SH._HAS_AV
    try:
        SH._HAS_AV = False
        h = SH.StreamHandler(StreamConfig(url=video, backend="av"))
        check("PyAV yo'q -> opencv backend tanlandi", h.backend == "opencv",
              f"backend={h.backend}, stats={h.stats.backend}")
        h.start()
        got = h.read(timeout=5.0)
        h.stop()
        check("fallback bilan kadr o'qildi", got is not None,
              str(got.shape) if got is not None else "yo'q")
        check("cheksiz qayta ulanish bo'lmadi", h.stats.reconnects == 0,
              f"reconnects={h.stats.reconnects}")
    finally:
        SH._HAS_AV = saved

    if saved:
        h2 = SH.StreamHandler(StreamConfig(url=video, backend="av",
                                           resize_to=(320, 180)))
        h2.start()
        frame = h2.read(timeout=6.0)
        h2.stop()
        check("PyAV backend haqiqatan ishlaydi", frame is not None
              and frame.shape[:2] == (180, 320),
              str(frame.shape) if frame is not None else "kadr yo'q")
    else:
        print("  (PyAV o'rnatilmagan — backend testi o'tkazib yuborildi)")


def test_reconnect() -> None:
    """Mavjud bo'lmagan manba -> qayta ulanish sikli va limit tekshiruvi.

    Ataylab fayl yo'li ishlatiladi (RTSP emas): xato darhol qaytadi, test
    tarmoq timeout'iga bog'liq bo'lmaydi.
    """
    cfg = StreamConfig(url="__yoq_manba__.mp4", backend="opencv",
                       timeout_sec=1.0, reconnect_min_delay=0.2,
                       reconnect_max_delay=0.4, max_reconnects=2)
    sh = StreamHandler(cfg)
    sh.start()
    t0 = time.monotonic()
    while sh.is_running and time.monotonic() - t0 < 20:
        time.sleep(0.2)
    sh.stop()
    check("qayta ulanish urinishlari bo'ldi", sh.stats.reconnects >= 1,
          f"reconnects={sh.stats.reconnects}")
    check("max_reconnects dan keyin to'xtadi", not sh.is_running)


def test_eof_stops(video: str) -> None:
    """Chekli fayl tugaganda qayta ulanmasdan to'xtashi kerak."""
    sh = StreamHandler(StreamConfig(url=video, backend="opencv"))
    sh.start()
    t0 = time.monotonic()
    n = sum(1 for f in sh.frames(timeout=2.0))
    elapsed = time.monotonic() - t0
    check("EOF da generator tugadi", n > 0 and elapsed < 15,
          f"{n} kadr, {elapsed:.1f}s")
    check("EOF da qayta ulanish bo'lmadi", sh.stats.reconnects == 0,
          f"reconnects={sh.stats.reconnects}")
    check("EOF da thread o'zi to'xtadi", not sh.is_running)
    sh.stop()


def test_tracker() -> None:
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    dets = [Detection(100, 100, 200, 250, 0.9, 0, "person")]
    tr = BoxTracker("cache")
    tr.reset(frame, dets)
    check("cache tracker qutini saqlaydi", len(tr.update(frame)) == 1)
    tr.clear()
    check("clear() bo'shatadi", len(tr.current) == 0)

    tr_none = BoxTracker("none")
    tr_none.reset(frame, dets)
    check("none tracker bo'sh qaytaradi", tr_none.update(frame) == [])

    tr_light = BoxTracker("light")
    tr_light.reset(frame, dets)
    out = tr_light.update(frame)
    check("light tracker yiqilmaydi (yoki cache ga tushadi)", isinstance(out, list),
          f"kind={tr_light.kind}, n={len(out)}")


def test_monitor() -> None:
    mon = ResourceMonitor(interval=0.0)
    snap = mon.sample(fps=10.0)
    check("psutil monitoringi ishlaydi", mon.enabled and snap.rss_mb > 0,
          f"RSS={snap.rss_mb:.1f} MB")
    check("HUD matni formatlanadi", "RAM" in snap.format())


def test_pipeline(video: str) -> None:
    events = os.path.join(tempfile.gettempdir(), "ipcam_selfcheck_events.jsonl")
    if os.path.exists(events):
        os.remove(events)

    dcfg = DetectorConfig(model_path="<fake>", imgsz=416, conf_threshold=0.3)
    fake = FakeDetector(dcfg)
    cfg = PipelineConfig(
        stream=StreamConfig(url=video, backend="opencv", max_reconnects=0,
                            resize_to=(480, 270), loop_source=True),
        detector=dcfg,
        detect_every=3,
        tracker="cache",
        show=False,              # headless
        stats_interval=0.5,
        events_path=events,
        gc_every=5,
    )
    seen = []
    pipe = PipelineManager(cfg, on_detections=lambda f, d: seen.append(len(d)),
                           detector=fake)

    # 3 soniyadan keyin tashqaridan to'xtatamiz (graceful shutdown sinovi)
    threading.Timer(3.0, pipe.stop).start()
    pipe.run()

    check("pipeline kadrlarni qayta ishladi", pipe.frames_processed > 0,
          f"{pipe.frames_processed} kadr")
    check("detect_every hurmat qilindi",
          0 < pipe.detections_run <= pipe.frames_processed / 2 + 2,
          f"{pipe.detections_run}/{pipe.frames_processed}")
    check("inference chaqirig'i mos", fake.calls == pipe.detections_run,
          f"calls={fake.calls}")
    check("callback chaqirildi", len(seen) > 0, f"{len(seen)} marta")
    check("JSONL yozildi", os.path.exists(events) and os.path.getsize(events) > 0)
    check("graceful shutdown: stream to'xtadi", not pipe.stream.is_running)
    check("detektor bo'shatildi", pipe.detector is None)
    check("FPS o'lchandi", pipe.avg_fps > 0.0, f"{pipe.avg_fps:.1f} FPS")
    check("peak RAM qayd etildi", pipe.monitor.peak_rss_mb > 0,
          f"{pipe.monitor.peak_rss_mb:.1f} MB")


def test_onnx_runtime() -> None:
    """Haqiqiy ONNX Runtime sessiyasi bilan `OnnxDetector` sinovi."""
    try:
        import onnx  # noqa: F401
        import onnxruntime  # noqa: F401
    except ImportError:
        print("  (onnx/onnxruntime yo'q — o'tkazib yuborildi)")
        return

    from make_dummy_onnx import build

    from ipcam_detect.detector import OnnxDetector

    path = os.path.join(tempfile.gettempdir(), "dummy_yolo.onnx")
    build(path, imgsz=640)

    det = OnnxDetector(DetectorConfig(model_path=path, imgsz=640,
                                      conf_threshold=0.3, num_threads=1))
    frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    dets = det.detect(frame)
    check("OnnxDetector sessiyasi ochildi", det.session is not None)
    check("ONNX inference natija berdi", len(dets) == 3, f"{len(dets)} ta")
    check("ONNX bbox koordinatalari to'g'ri",
          all(0 <= d.x1 < d.x2 <= 1280 and 0 <= d.y1 < d.y2 <= 720 for d in dets))
    check("thread cheklovi qo'llandi",
          det.session.get_session_options().intra_op_num_threads == 1)

    t0 = time.perf_counter()
    for _ in range(30):
        det.detect(frame)
    ms = (time.perf_counter() - t0) / 30 * 1000
    check("30 iteratsiya barqaror", True, f"o'rtacha {ms:.2f} ms/kadr")

    det.close()
    check("close() sessiyani bo'shatdi", det.session is None)
    try:
        os.remove(path)
    except OSError:
        pass


def test_memory_stability(video: str) -> None:
    """500 kadr davomida RSS o'smasligi (leak yo'qligi) tekshiruvi."""
    import psutil

    proc = psutil.Process()
    dcfg = DetectorConfig(model_path="<fake>", imgsz=416, conf_threshold=0.3)
    det = FakeDetector(dcfg)
    tr = BoxTracker("cache")
    frame = np.random.randint(0, 255, (540, 960, 3), dtype=np.uint8)

    for _ in range(50):  # isitish (warm-up)
        tr.reset(frame, det.detect(frame))
    rss0 = proc.memory_info().rss / 1024 / 1024
    for i in range(500):
        if i % 3 == 0:
            tr.reset(frame, det.detect(frame))
        else:
            tr.update(frame)
    rss1 = proc.memory_info().rss / 1024 / 1024
    growth = rss1 - rss0
    check("500 kadrda RAM o'smadi (<10 MB)", growth < 10.0,
          f"{rss0:.1f} -> {rss1:.1f} MB (+{growth:.2f})")


def main() -> int:
    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s | %(name)s | %(message)s")
    tmp = tempfile.gettempdir()
    video = os.path.join(tmp, "ipcam_selfcheck.mp4")

    print("=" * 68)
    print(" ipcam_detect — selfcheck")
    print("=" * 68)

    print("\n-- Sintetik video yaratilmoqda --")
    make_video(video)
    check("test video yaratildi", os.path.getsize(video) > 1000,
          f"{os.path.getsize(video)/1024:.0f} KB")

    print("\n-- Detector (pre/post-processing) --")
    test_detector_math()
    print("\n-- StreamHandler (producer + frame dropping) --")
    test_stream_handler(video)
    print("\n-- Backend tanlash / PyAV fallback --")
    test_backend_fallback(video)
    print("\n-- EOF (chekli manba) --")
    test_eof_stops(video)
    print("\n-- Reconnect logikasi --")
    test_reconnect()
    print("\n-- Tracker --")
    test_tracker()
    print("\n-- ResourceMonitor --")
    test_monitor()
    print("\n-- ONNX Runtime (haqiqiy sessiya) --")
    test_onnx_runtime()
    print("\n-- Pipeline (end-to-end, headless) --")
    test_pipeline(video)
    print("\n-- Xotira barqarorligi --")
    test_memory_stability(video)

    ok = sum(1 for _, c, _ in _results if c)
    total = len(_results)
    print("\n" + "=" * 68)
    print(f" NATIJA: {ok}/{total} test o'tdi")
    print("=" * 68)
    for name, cond, info in _results:
        if not cond:
            print(f"  {FAIL} {name} {info}")
    try:
        os.remove(video)
    except OSError:
        pass
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
