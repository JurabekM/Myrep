"""Fon vazifalari — og'ir hisob-kitoblar GUI'ni muzlatmasligi uchun."""
from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class WorkerSignals(QObject):
    finished = Signal(object)     # natija
    failed = Signal(str)          # xato matni
    progress = Signal(str, int)   # (xabar, foiz)


class Worker(QRunnable):
    """Funksiyani alohida oqimda ishga tushiradi.

    Agar chaqiriluvchi ``progress`` nomli kalit argumentni qabul qilsa,
    unga ``progress(msg, pct)`` funksiyasi uzatiladi.
    """

    def __init__(self, fn: Callable[..., Any], *args: Any,
                 with_progress: bool = False, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self._with_progress = with_progress
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:  # pragma: no cover - oqimda ishlaydi
        try:
            if self._with_progress:
                self.kwargs["progress"] = lambda m, p=0: self.signals.progress.emit(m, int(p))
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:
            detail = traceback.format_exc(limit=3)
            self.signals.failed.emit(f"{exc}\n\n{detail}")
        else:
            self.signals.finished.emit(result)


def run_async(fn: Callable[..., Any], *args: Any,
              on_done: Callable[[Any], None] | None = None,
              on_error: Callable[[str], None] | None = None,
              on_progress: Callable[[str, int], None] | None = None,
              with_progress: bool = False, **kwargs: Any) -> Worker:
    """Vazifani global oqim hovuzida ishga tushiradi."""
    worker = Worker(fn, *args, with_progress=with_progress, **kwargs)
    if on_done:
        worker.signals.finished.connect(on_done)
    if on_error:
        worker.signals.failed.connect(on_error)
    if on_progress:
        worker.signals.progress.connect(on_progress)
    QThreadPool.globalInstance().start(worker)
    return worker
