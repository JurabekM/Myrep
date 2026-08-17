"""StreamHandler — IP kameradan kadr o'qiydigan alohida thread (Producer).

Asosiy g'oya (Producer-Consumer):
  * O'qish/dekodlash **alohida thread**da ketadi va hech qachon inference ni
    kutmaydi. Aks holda RTSP dekoderning ichki buferi to'lib, kadrlar
    kechikadi (latency o'sadi) va RAM shishadi.
  * Kadrlar `deque(maxlen=1)` da saqlanadi — ya'ni **faqat eng oxirgi kadr**.
    Eski kadr avtomatik tashlanadi (frame dropping), navbat cheksiz o'smaydi.
  * Backpressure: agar iste'molchi hali oldingi kadrni olmagan bo'lsa, yangi
    kadrni BGR ga o'girish (eng qimmat operatsiya — swscale) umuman
    bajarilmaydi. Dekod davom etadi (oqim buzilmasligi uchun), lekin CPU
    behuda sarflanmaydi.

Ikkita backend:
  * ``av``     — PyAV (FFmpeg to'g'ridan-to'g'ri binding). Yengilroq, HW
                 dekod (``hwaccel``) va aniq timeout beradi. Tavsiya etiladi.
  * ``opencv`` — ``cv2.VideoCapture`` + ``CAP_FFMPEG``, RTSP transport = tcp.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from typing import Iterator, Optional, Tuple

import numpy as np

from .config import StreamConfig

logger = logging.getLogger(__name__)

try:  # PyAV ixtiyoriy — bo'lmasa opencv backend ishlaydi
    import av  # type: ignore

    _HAS_AV = True
except Exception:  # pragma: no cover - muhitga bog'liq
    av = None  # type: ignore
    _HAS_AV = False

#: OpenCV FFmpeg opsiyalari global env orqali beriladi -> lock bilan himoya
_FFMPEG_ENV = "OPENCV_FFMPEG_CAPTURE_OPTIONS"
_FFMPEG_ENV_LOCK = threading.Lock()

#: Jonli (cheksiz) oqim sxemalari — bularda EOF = tarmoq uzilishi
_LIVE_SCHEMES = ("rtsp://", "rtmp://", "udp://", "srt://", "rtp://")


class StreamEOF(Exception):
    """Chekli manba (video fayl) tugadi — bu xato emas."""


class StreamStats:
    """Oqim bo'yicha yengil statistika (lock talab qilmaydi — atomik int)."""

    __slots__ = ("read", "dropped", "reconnects", "last_ts", "connected", "backend")

    def __init__(self) -> None:
        self.read: int = 0
        self.dropped: int = 0
        self.reconnects: int = 0
        self.last_ts: float = 0.0
        self.connected: bool = False
        self.backend: str = ""

    def as_dict(self) -> dict:
        return {
            "read": self.read,
            "dropped": self.dropped,
            "reconnects": self.reconnects,
            "connected": self.connected,
            "backend": self.backend,
            "age_sec": round(time.monotonic() - self.last_ts, 2) if self.last_ts else None,
        }


class StreamHandler:
    """Kadrlarni fonda o'qiydigan thread-safe producer.

    Foydalanish::

        with StreamHandler(cfg) as stream:
            for frame in stream.frames():
                ...  # frame: np.ndarray (H, W, 3) BGR

    Qaytarilgan kadr **nusxa emas** — iste'molchi uni faqat o'qishi kerak.
    Agar o'zgartirish (chizish) kerak bo'lsa, o'zi `copy()` qiladi yoki
    o'zgarishlarni alohida overlay qatlamida bajaradi.
    """

    def __init__(self, cfg: StreamConfig, drop_on_backpressure: bool = True) -> None:
        self.cfg = cfg
        self.drop_on_backpressure = drop_on_backpressure
        self.stats = StreamStats()

        # Backend'ni DARHOL tanlaymiz. PyAV yo'qligi — tuzatib bo'lmaydigan
        # holat: uni qayta ulanish sikliga qo'yib yuborish cheksiz va foydasiz
        # urinishlarga olib keladi. Shuning uchun bir marta ogohlantirib,
        # OpenCV backend'iga o'tamiz.
        self.backend: str = cfg.backend
        if self.backend == "av" and not _HAS_AV:
            logger.warning(
                "PyAV o'rnatilmagan (o'rnatish: pip install av) — 'opencv' "
                "backend'iga o'tildi. RTSP uchun PyAV tavsiya etiladi: aniq "
                "timeout, past kechikish va apparat dekod imkoniyati beradi."
            )
            self.backend = "opencv"
        self.stats.backend = self.backend
        self._hwaccel_failed = False

        # maxlen=1 -> eski kadr avtomatik o'chadi, RAM o'smaydi
        self._slot: deque[np.ndarray] = deque(maxlen=1)
        self._new_frame = threading.Event()   # yangi kadr bor
        self._pending = threading.Event()     # slotda o'qilmagan kadr bor
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._frame_shape: Optional[Tuple[int, int]] = None
        self._first_connect = True

    # ------------------------------------------------------------------ API
    def start(self) -> "StreamHandler":
        """Fon thread'ini ishga tushiradi (idempotent)."""
        if self._thread and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="StreamHandler", daemon=True
        )
        self._thread.start()
        return self

    def stop(self, join_timeout: float = 5.0) -> None:
        """Thread'ni xavfsiz to'xtatadi va slotni bo'shatadi."""
        self._stop.set()
        self._new_frame.set()  # kutayotganlarni uyg'otish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=join_timeout)
        self._slot.clear()
        self.stats.connected = False

    def read(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """Eng oxirgi kadrni qaytaradi yoki timeout bo'lsa ``None``.

        Kadr olingach `_pending` tozalanadi — shu payt producer yangi kadrni
        konvertatsiya qilishga ruxsat oladi.
        """
        if not self._new_frame.wait(timeout):
            return None
        self._new_frame.clear()
        try:
            frame = self._slot[-1]
        except IndexError:
            return None
        self._pending.clear()
        return frame

    def frames(self, timeout: float = 1.0) -> Iterator[np.ndarray]:
        """Kadrlar generatori — `stop()` chaqirilguncha ishlaydi."""
        while not self._stop.is_set():
            frame = self.read(timeout)
            if frame is not None:
                yield frame
            elif not self.is_running:
                break  # producer o'lgan (EOF/limit) — cheksiz kutmaymiz

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @property
    def is_live(self) -> bool:
        """Manba jonli oqimmi (RTSP/RTMP/webcam) yoki chekli faylmi?

        Jonli oqimda EOF = uzilish -> qayta ulanamiz.
        Faylda EOF = tabiiy tugash -> `loop_source` bo'lmasa to'xtaymiz.
        """
        url = self.cfg.url
        if not isinstance(url, str):
            return True  # webcam indeksi
        return url.lower().startswith(_LIVE_SCHEMES)

    @property
    def frame_shape(self) -> Optional[Tuple[int, int]]:
        """(height, width) — birinchi kadr kelgandan keyin ma'lum bo'ladi."""
        return self._frame_shape

    def __enter__(self) -> "StreamHandler":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    # -------------------------------------------------------------- internal
    def _publish(self, frame: np.ndarray) -> None:
        """Kadrni slotga qo'yadi (eskisini tashlaydi)."""
        self._slot.append(frame)  # maxlen=1 -> eski ref darhol bo'shaydi
        self._pending.set()
        self._new_frame.set()
        self.stats.read += 1
        self.stats.last_ts = time.monotonic()
        if self._frame_shape is None:
            self._frame_shape = (frame.shape[0], frame.shape[1])

    def _source_period(self, fps: Optional[float]) -> float:
        """Chekli manba uchun kadrlar orasidagi kutish vaqti (0 = kutmaslik)."""
        if self.is_live or not self.cfg.pace_source or not fps:
            return 0.0
        return 1.0 / fps if 1.0 < fps < 240.0 else 0.0

    def _pace(self, next_ts: float, period: float) -> float:
        """Manba FPS'iga moslab uxlaydi, keyingi deadline'ni qaytaradi."""
        if period <= 0:
            return 0.0
        now = time.monotonic()
        if next_ts <= 0:
            return now + period
        if next_ts > now:
            self._stop.wait(next_ts - now)
        # Orqada qolib ketgan bo'lsak deadline'ni tiklaymiz (drift oldini olish)
        return max(next_ts + period, time.monotonic())

    def _should_convert(self) -> bool:
        """Backpressure tekshiruvi: slot band bo'lsa konvertatsiya qilmaymiz."""
        if not self.drop_on_backpressure:
            return True
        if self._pending.is_set():
            self.stats.dropped += 1
            return False
        return True

    def _run(self) -> None:
        """Qayta ulanish sikli bilan asosiy o'qish loop'i."""
        delay = self.cfg.reconnect_min_delay
        attempts = 0
        while not self._stop.is_set():
            try:
                self.stats.connected = False
                if self.backend == "av":
                    self._loop_av()
                else:
                    self._loop_opencv()
                if self._stop.is_set():
                    break                      # to'xtatish so'raldi — xato emas
                logger.warning("Oqim yakunlandi, qayta ulanishga urinish...")
            except StreamEOF:
                # Chekli manba (video fayl) tugadi
                if not self.cfg.loop_source:
                    logger.info("Manba tugadi (EOF) — to'xtatilmoqda")
                    break
                logger.debug("Fayl tugadi — boshidan qayta o'qiladi")
                delay = self.cfg.reconnect_min_delay  # backoff ni tiklaymiz
                continue
            except Exception as exc:  # tarmoq/dekod xatolari
                logger.warning("Oqim xatosi: %s: %s", type(exc).__name__, exc)
            finally:
                self.stats.connected = False

            if self._stop.is_set():
                break

            attempts += 1
            self.stats.reconnects += 1
            if self.cfg.max_reconnects and attempts > self.cfg.max_reconnects:
                logger.error("Qayta ulanish limiti tugadi (%d)", self.cfg.max_reconnects)
                break

            logger.info("Qayta ulanish %.1f s dan keyin (urinish #%d)", delay, attempts)
            self._stop.wait(delay)
            # eksponensial backoff — kamerani va tarmoqni bosmaslik uchun
            delay = min(delay * 2.0, self.cfg.reconnect_max_delay)

        logger.info("StreamHandler thread to'xtadi.")

    # ---- PyAV backend
    def _loop_av(self) -> None:
        if not _HAS_AV:
            raise RuntimeError("PyAV o'rnatilmagan: pip install av")

        cfg = self.cfg
        options = {
            "rtsp_transport": cfg.rtsp_transport,   # TCP = paket yo'qotmaydi
            "stimeout": str(int(cfg.timeout_sec * 1_000_000)),  # mikrosoniya
            "max_delay": "500000",
            "fflags": "nobuffer",                   # ichki buferni o'chirish
            "flags": "low_delay",
            "reorder_queue_size": "0",              # RTP reorder bufer = 0
        }
        timeouts = (cfg.timeout_sec, cfg.timeout_sec)
        use_hw = cfg.hwaccel and not self._hwaccel_failed
        try:
            container = (
                av.open(cfg.url, options=options, timeout=timeouts,
                        hwaccel=cfg.hwaccel)
                if use_hw else
                av.open(cfg.url, options=options, timeout=timeouts)
            )
        except Exception as exc:
            if not use_hw:
                raise
            # Drayver/FFmpeg build apparat dekodni qo'llamasa — bu ham
            # takrorlanadigan xato emas: bir marta ogohlantirib CPU ga o'tamiz.
            logger.warning(
                "Apparat dekod '%s' ishlamadi (%s) — CPU dekodga o'tildi",
                cfg.hwaccel, exc)
            self._hwaccel_failed = True
            container = av.open(cfg.url, options=options, timeout=timeouts)

        try:
            vstream = container.streams.video[0]
            # Dekod thread'lari: 1 = eng kam CPU, "AUTO" = eng tez
            vstream.thread_count = max(0, cfg.decoder_threads)
            vstream.thread_type = "AUTO" if cfg.decoder_threads != 1 else "NONE"
            # Kechikkan kadrlarni tashlab yuborish
            vstream.codec_context.skip_frame = "DEFAULT"
            self.stats.connected = True
            logger.log(
                logging.INFO if (self._first_connect or self.is_live) else logging.DEBUG,
                "Ulandi (PyAV): %sx%s %s",
                vstream.codec_context.width,
                vstream.codec_context.height,
                vstream.codec_context.name,
            )
            self._first_connect = False

            w, h = (cfg.resize_to or (0, 0))
            idx = 0
            period = self._source_period(
                float(vstream.average_rate) if vstream.average_rate else None
            )
            next_ts = 0.0
            for frame in container.decode(vstream):
                if self._stop.is_set():
                    break
                next_ts = self._pace(next_ts, period)
                idx += 1
                if cfg.read_every > 1 and idx % cfg.read_every:
                    self.stats.dropped += 1
                    continue
                if not self._should_convert():
                    continue
                # reformat() — swscale orqali BIR bosqichda scale + BGR.
                # cv2.resize dan keyin cvtColor qilishdan tejamkorroq.
                if w and h:
                    arr = frame.reformat(width=w, height=h, format="bgr24").to_ndarray()
                else:
                    arr = frame.to_ndarray(format="bgr24")
                self._publish(arr)
            # decode() generatori tugadi -> manba oxiriga yetdi
            if not self._stop.is_set() and not self.is_live:
                raise StreamEOF
        finally:
            try:
                container.close()
            except Exception:
                pass

    # ---- OpenCV backend
    def _loop_opencv(self) -> None:
        import cv2  # lokal import — headless muhitda kerak bo'lmasa yuklanmaydi

        cfg = self.cfg
        # FFmpeg opsiyalari faqat GLOBAL env orqali uzatiladi (VideoCapture API
        # cheklovi). Shuning uchun uni faqat `VideoCapture` yaratilayotgan
        # payt o'rnatamiz, lock bilan himoyalaymiz va darhol tiklaymiz —
        # aks holda boshqa oqim (yoki webcam/fayl) noto'g'ri sozlama oladi.
        opts = (
            f"rtsp_transport;{cfg.rtsp_transport}"
            f"|stimeout;{int(cfg.timeout_sec * 1_000_000)}"
            "|fflags;nobuffer|flags;low_delay"
        )
        is_rtsp = isinstance(cfg.url, str) and cfg.url.lower().startswith("rtsp")
        with _FFMPEG_ENV_LOCK:
            prev = os.environ.get(_FFMPEG_ENV)
            if is_rtsp:
                os.environ[_FFMPEG_ENV] = opts
            try:
                cap = cv2.VideoCapture(cfg.url, cv2.CAP_FFMPEG)
            finally:
                if is_rtsp:
                    if prev is None:
                        os.environ.pop(_FFMPEG_ENV, None)
                    else:
                        os.environ[_FFMPEG_ENV] = prev
        try:
            if not cap.isOpened():
                raise ConnectionError(f"Oqim ochilmadi: {cfg.url}")
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # ichki bufer = 1 kadr
            self.stats.connected = True
            # Fayl loop qilinayotganda har aylanishda INFO yozmaymiz
            logger.log(
                logging.INFO if (self._first_connect or self.is_live) else logging.DEBUG,
                "Ulandi (OpenCV): %dx%d",
                int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )
            self._first_connect = False

            idx = 0
            fail = 0
            period = self._source_period(cap.get(cv2.CAP_PROP_FPS))
            next_ts = 0.0
            while not self._stop.is_set():
                next_ts = self._pace(next_ts, period)
                # grab() dekodlaydi lekin konvertatsiya qilmaydi — arzon
                if not cap.grab():
                    # Fayl uchun grab() muvaffaqiyatsizligi = EOF (xato emas)
                    if not self.is_live:
                        raise StreamEOF
                    fail += 1
                    if fail > 30:
                        raise ConnectionError("grab() ketma-ket muvaffaqiyatsiz")
                    time.sleep(0.01)
                    continue
                fail = 0
                idx += 1
                if cfg.read_every > 1 and idx % cfg.read_every:
                    self.stats.dropped += 1
                    continue
                if not self._should_convert():
                    continue
                ok, frame = cap.retrieve()  # faqat kerak bo'lganda retrieve()
                if not ok or frame is None:
                    continue
                if cfg.resize_to:
                    # INTER_AREA kichraytirishda sifatli, INTER_LINEAR tezroq
                    frame = cv2.resize(
                        frame, cfg.resize_to, interpolation=cv2.INTER_LINEAR
                    )
                self._publish(frame)
        finally:
            cap.release()
