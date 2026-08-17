"""ResourceMonitor — psutil orqali CPU/RAM sarfini o'lchash.

Muhim nuqta: `psutil.Process.cpu_percent()` **birinchi chaqiriqda 0.0**
qaytaradi (o'lchov oralig'i hali yo'q). Shuning uchun konstruktorda bir marta
"primer" chaqiriq qilinadi.

O'lchov o'zi ham resurs yeydi, shuning uchun `interval` sekundda bir marta
(default 5 s) hisoblanadi va oradagi chaqiriqlar keshdan qaytadi.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import psutil  # type: ignore

    _HAS_PSUTIL = True
except Exception:  # pragma: no cover
    psutil = None  # type: ignore
    _HAS_PSUTIL = False


@dataclass(slots=True)
class ResourceSnapshot:
    """Bir lahzadagi resurs holati."""

    cpu_percent: float = 0.0        # jarayon CPU (100% = bitta yadro to'liq)
    cpu_percent_norm: float = 0.0   # yadrolar soniga normallashtirilgan
    rss_mb: float = 0.0             # jismoniy xotira (Resident Set Size)
    vms_mb: float = 0.0             # virtual xotira
    threads: int = 0
    system_cpu: float = 0.0
    system_mem_percent: float = 0.0
    fps: float = 0.0
    infer_ms: float = 0.0

    def format(self) -> str:
        return (
            f"CPU {self.cpu_percent:5.1f}% ({self.cpu_percent_norm:4.1f}% umumiy) | "
            f"RAM {self.rss_mb:6.1f} MB | threads {self.threads:2d} | "
            f"FPS {self.fps:5.1f} | infer {self.infer_ms:5.1f} ms"
        )


class ResourceMonitor:
    """Jarayonning CPU/RAM sarfini davriy o'lchaydi va log qiladi."""

    def __init__(self, interval: float = 5.0, log_to: Optional[logging.Logger] = None) -> None:
        self.interval = interval
        self.log = log_to or logger
        self._proc = psutil.Process(os.getpid()) if _HAS_PSUTIL else None
        self._ncpu = (psutil.cpu_count(logical=True) or 1) if _HAS_PSUTIL else 1
        self._last_ts = 0.0
        self._snapshot = ResourceSnapshot()
        self._lock = threading.Lock()
        self._peak_rss = 0.0
        if self._proc is not None:
            self._proc.cpu_percent(None)  # primer chaqiriq (natija 0.0)
        else:
            logger.warning("psutil o'rnatilmagan — resurs monitoringi o'chirilgan")

    # ------------------------------------------------------------------ API
    def sample(self, fps: float = 0.0, infer_ms: float = 0.0) -> ResourceSnapshot:
        """Kerak bo'lsa yangi o'lchov oladi, aks holda keshdagisini qaytaradi."""
        snap = self._snapshot
        snap.fps = fps
        snap.infer_ms = infer_ms
        if self._proc is None:
            return snap

        now = time.monotonic()
        if now - self._last_ts < self.interval:
            return snap

        with self._lock:
            self._last_ts = now
            try:
                with self._proc.oneshot():  # bitta syscall paketi — arzonroq
                    cpu = self._proc.cpu_percent(None)
                    mem = self._proc.memory_info()
                    snap.threads = self._proc.num_threads()
                snap.cpu_percent = cpu
                snap.cpu_percent_norm = cpu / self._ncpu
                snap.rss_mb = mem.rss / (1024 * 1024)
                snap.vms_mb = mem.vms / (1024 * 1024)
                snap.system_cpu = psutil.cpu_percent(None)
                snap.system_mem_percent = psutil.virtual_memory().percent
                self._peak_rss = max(self._peak_rss, snap.rss_mb)
            except Exception as exc:  # jarayon tugagan bo'lishi mumkin
                logger.debug("Resurs o'lchashda xato: %s", exc)
        return snap

    def maybe_log(self, fps: float = 0.0, infer_ms: float = 0.0) -> Optional[ResourceSnapshot]:
        """Interval yetgan bo'lsa log yozadi va snapshotni qaytaradi."""
        if self._proc is None or self.interval <= 0:
            return None
        prev = self._last_ts
        snap = self.sample(fps, infer_ms)
        if self._last_ts != prev:  # yangi o'lchov bo'ldi
            self.log.info("[RES] %s", snap.format())
            return snap
        return None

    @property
    def peak_rss_mb(self) -> float:
        """Sessiya davomidagi eng yuqori RAM sarfi."""
        return self._peak_rss

    @property
    def enabled(self) -> bool:
        return self._proc is not None
