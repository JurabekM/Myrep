"""PipelineManager — Consumer: kadrni oladi, deteksiya qiladi, natijani beradi.

Umumiy oqim::

    [IP kamera] --RTSP--> StreamHandler (thread)  --deque(maxlen=1)-->
        PipelineManager (asosiy thread) --> ObjectDetector (har N-kadrda)
                                        --> BoxTracker (oraliq kadrlarda)
                                        --> Visualizer (ixtiyoriy)
                                        --> JSONL events (ixtiyoriy)

Nima uchun inference **asosiy thread**da? ONNX Runtime allaqachon o'z ichida
thread-pool ishlatadi. Uni yana Python thread ichiga o'rash GIL almashinuvi
va qo'shimcha navbat (ya'ni yana bufer, yana RAM) demakdir. Producer-consumer
ajratish faqat **I/O-bound** qism (tarmoq/dekod) uchun kerak.
"""

from __future__ import annotations

import gc
import json
import logging
import signal
import threading
import time
from collections import deque
from typing import Callable, Deque, List, Optional, Sequence, TextIO

import numpy as np

from .config import PipelineConfig
from .detector import BaseDetector, Detection, build_detector
from .resource_monitor import ResourceMonitor
from .stream_handler import StreamHandler
from .tracker import BoxTracker

logger = logging.getLogger(__name__)

#: Faqat deteksiya bajarilgan kadrlarda chaqiriladi (alarm/DB logikasi uchun)
DetectionCallback = Callable[[np.ndarray, List[Detection]], None]
#: HAR BIR qayta ishlangan kadrda chaqiriladi (GUI preview uchun).
#: Uchinchi argument: shu kadrda inference bo'ldimi (False = tracker/cache).
FrameCallback = Callable[[np.ndarray, List[Detection], bool], None]


class PipelineManager:
    """Butun quvurni boshqaradi va graceful shutdown ni ta'minlaydi."""

    def __init__(
        self,
        cfg: PipelineConfig,
        on_detections: Optional[DetectionCallback] = None,
        detector: Optional[BaseDetector] = None,
        on_frame: Optional[FrameCallback] = None,
    ) -> None:
        self.cfg = cfg
        self.on_detections = on_detections
        # GUI preview uchun: kadr `deque` slotida qayta ishlatiladi, shuning
        # uchun callback uni SAQLAB QOLMASLIGI yoki o'zi nusxalashi kerak.
        self.on_frame = on_frame

        self.stream = StreamHandler(cfg.stream)
        # Tayyor detektor berilsa (test/mock yoki bir nechta kamera bitta
        # sessiyani bo'lishsa) qayta yuklanmaydi.
        self.detector: Optional[BaseDetector] = detector
        self.tracker = BoxTracker(cfg.tracker)
        self.monitor = ResourceMonitor(cfg.stats_interval)
        self.visualizer = None  # headless rejimda umuman yaratilmaydi

        self._stop = threading.Event()
        self._events_fh: Optional[TextIO] = None
        # FPS ni silliq hisoblash uchun sirg'aluvchi oyna (ortiqcha ro'yxat yo'q)
        self._frame_times: Deque[float] = deque(maxlen=30)
        self._infer_times: Deque[float] = deque(maxlen=30)

        self.frames_processed = 0
        self.detections_run = 0
        #: Sessiya yakunidagi o'rtacha FPS (shutdown'da hisoblanadi)
        self.avg_fps: float = 0.0
        self._prev_handlers: dict = {}

    # ------------------------------------------------------------- lifecycle
    def _install_signal_handlers(self) -> None:
        """Ctrl+C / SIGTERM ni ushlab, xavfsiz to'xtash."""
        def _handler(signum, _frame):
            logger.info("Signal %s qabul qilindi — to'xtatilmoqda...", signum)
            self._stop.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                self._prev_handlers[sig] = signal.signal(sig, _handler)
            except (ValueError, OSError):
                # asosiy thread emas (masalan web-server ichida) — o'tkazib yuboramiz
                pass

    def _restore_signal_handlers(self) -> None:
        for sig, handler in self._prev_handlers.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass
        self._prev_handlers.clear()

    def stop(self) -> None:
        """Tashqaridan to'xtatish (boshqa thread'dan ham xavfsiz)."""
        self._stop.set()

    # ------------------------------------------------------------------ run
    def run(self) -> None:
        """Asosiy sikl. Bloklaydi, `stop()` yoki Ctrl+C gacha ishlaydi."""
        cfg = self.cfg
        self._install_signal_handlers()
        start_ts = time.monotonic()

        try:
            if self.detector is None:
                logger.info("Model yuklanmoqda: %s", cfg.detector.model_path)
                self.detector = build_detector(cfg.detector)

            if cfg.show:
                from .visualizer import Visualizer  # faqat GUI rejimida import

                self.visualizer = Visualizer(cfg.window_name, show=True)

            if cfg.events_path:
                self._events_fh = open(cfg.events_path, "a", encoding="utf-8")

            self.stream.start()
            logger.info(
                "Pipeline ishga tushdi | detect_every=%d | tracker=%s | show=%s",
                cfg.detect_every, cfg.tracker, cfg.show,
            )
            self._loop()

        except KeyboardInterrupt:  # signal handler ishlamagan holat uchun zaxira
            logger.info("Ctrl+C — to'xtatilmoqda...")
        except Exception:
            logger.exception("Pipeline kutilmagan xato bilan tugadi")
            raise
        finally:
            self._shutdown(start_ts)

    def _loop(self) -> None:
        cfg = self.cfg
        detect_every = max(1, cfg.detect_every)
        min_period = 1.0 / cfg.target_fps if cfg.target_fps > 0 else 0.0
        idx = 0
        last_emit = 0.0
        stale_since = time.monotonic()

        while not self._stop.is_set():
            # --- FPS cheklovi: KADR O'QISHDAN OLDIN kutamiz ---
            # Kadrni olib, keyin "erta keldi" deb tashlab yuborish band-kutish
            # (busy-spin) bo'lardi: CPU behuda yonadi va o'quvchi thread bilan
            # raqobatlashib, aslida target FPS ga yetib bo'lmaydi. Uxlab
            # turgandan keyin olingan kadr yangiroq ham bo'ladi (past latency).
            if min_period:
                wait = last_emit + min_period - time.monotonic()
                if wait > 0 and self._stop.wait(wait):
                    break

            frame = self.stream.read(timeout=1.0)
            if frame is None:
                # Producer butunlay to'xtagan bo'lsa (fayl tugadi yoki
                # reconnect limiti) — kutishning ma'nosi yo'q.
                if not self.stream.is_running:
                    logger.info("Oqim manbasi tugadi — pipeline to'xtatilmoqda")
                    break
                # Kadr yo'q: oqim uzilgan bo'lishi mumkin (StreamHandler o'zi
                # qayta ulanadi). Faqat log yozamiz va davom etamiz.
                if time.monotonic() - stale_since > 10.0:
                    logger.warning("10 s dan beri kadr yo'q (%s)", self.stream.stats.as_dict())
                    stale_since = time.monotonic()
                continue
            now = time.monotonic()
            stale_since = now
            last_emit = now

            idx += 1
            run_detection = (idx % detect_every) == 1 or detect_every == 1

            if run_detection:
                t0 = time.perf_counter()
                detections = self.detector.detect(frame)  # type: ignore[union-attr]
                self._infer_times.append((time.perf_counter() - t0) * 1000.0)
                self.detections_run += 1
                detections = self.tracker.reset(frame, detections)
                self._emit(frame, detections)
                if self.cfg.gc_every and self.detections_run % self.cfg.gc_every == 0:
                    # Aylanma havolalar (tracker/session) uchun davriy tozalash.
                    # Har kadrda chaqirish CPU ni yeydi — shuning uchun kamdan-kam.
                    gc.collect()
            else:
                detections = self.tracker.update(frame)

            self.frames_processed += 1
            self._frame_times.append(now)

            if self.on_frame is not None:
                try:
                    self.on_frame(frame, detections, run_detection)
                except Exception:
                    logger.exception("on_frame callback xatosi")

            if self.visualizer is not None:
                hud = self._hud()
                self.visualizer.draw(frame, detections, hud, stale=not run_detection)
                if not self.visualizer.render(frame):
                    logger.info("Oynadan chiqish so'raldi")
                    break

            self.monitor.maybe_log(self.fps, self.avg_infer_ms)

    # --------------------------------------------------------------- output
    def _emit(self, frame: np.ndarray, detections: Sequence[Detection]) -> None:
        """Deteksiya natijalarini callback va/yoki JSONL ga uzatadi."""
        if self._events_fh is not None and detections:
            record = {
                "ts": time.time(),
                "frame": self.frames_processed,
                "objects": [d.as_dict() for d in detections],
            }
            self._events_fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._events_fh.flush()

        if self.on_detections is not None and detections:
            try:
                self.on_detections(frame, list(detections))
            except Exception:
                logger.exception("on_detections callback xatosi")

    def _hud(self) -> str:
        snap = self.monitor.sample(self.fps, self.avg_infer_ms)
        return (
            f"FPS {self.fps:.1f} | infer {self.avg_infer_ms:.1f}ms | "
            f"CPU {snap.cpu_percent:.0f}% | RAM {snap.rss_mb:.0f}MB | "
            f"drop {self.stream.stats.dropped}"
        )

    # ---------------------------------------------------------------- props
    @property
    def fps(self) -> float:
        """Sirg'aluvchi oyna bo'yicha real FPS."""
        if len(self._frame_times) < 2:
            return 0.0
        span = self._frame_times[-1] - self._frame_times[0]
        return (len(self._frame_times) - 1) / span if span > 0 else 0.0

    @property
    def avg_infer_ms(self) -> float:
        return sum(self._infer_times) / len(self._infer_times) if self._infer_times else 0.0

    # ------------------------------------------------------------- shutdown
    def _shutdown(self, start_ts: float) -> None:
        """Barcha resurslarni tartib bilan bo'shatadi (xato bo'lsa ham)."""
        logger.info("Resurslar bo'shatilmoqda...")
        elapsed = time.monotonic() - start_ts
        self.avg_fps = self.frames_processed / elapsed if elapsed else 0.0
        for name, closer in (
            ("stream", self.stream.stop),
            ("tracker", self.tracker.clear),
            ("detector", getattr(self.detector, "close", lambda: None)),
            ("visualizer", getattr(self.visualizer, "close", lambda: None)),
        ):
            try:
                closer()
            except Exception:
                logger.exception("%s yopishda xato", name)

        if self._events_fh is not None:
            try:
                self._events_fh.close()
            finally:
                self._events_fh = None

        # Katta obyektlarga havolalarni uzib, xotirani darhol qaytarish
        self.detector = None
        self._frame_times.clear()
        self._infer_times.clear()
        gc.collect()

        self._restore_signal_handlers()

        logger.info(
            "Yakun: %d kadr / %d deteksiya / %.1f s (o'rtacha %.1f FPS) | "
            "o'qildi=%d tashlandi=%d reconnect=%d | peak RAM %.1f MB",
            self.frames_processed, self.detections_run, elapsed,
            self.avg_fps,
            self.stream.stats.read, self.stream.stats.dropped,
            self.stream.stats.reconnects, self.monitor.peak_rss_mb,
        )

    def __enter__(self) -> "PipelineManager":
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
