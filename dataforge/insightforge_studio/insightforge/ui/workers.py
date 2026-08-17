from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class Signals(QObject):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(str, int)


class Worker(QRunnable):
    def __init__(self, fn: Callable[..., Any], *args: Any,
                 progress_enabled: bool = False, **kwargs: Any) -> None:
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = Signals()
        self.progress_enabled = progress_enabled

    @Slot()
    def run(self) -> None:
        try:
            if self.progress_enabled:
                self.kwargs["progress"] = self.signals.progress.emit
            result = self.fn(*self.args, **self.kwargs)
        except Exception:
            self.signals.failed.emit(traceback.format_exc(limit=5))
        else:
            self.signals.done.emit(result)


def submit(fn: Callable[..., Any], *args: Any, on_done=None, on_error=None,
           on_progress=None, progress_enabled: bool = False, **kwargs: Any) -> Worker:
    worker = Worker(fn, *args, progress_enabled=progress_enabled, **kwargs)
    if on_done:
        worker.signals.done.connect(on_done)
    if on_error:
        worker.signals.failed.connect(on_error)
    if on_progress:
        worker.signals.progress.connect(on_progress)
    QThreadPool.globalInstance().start(worker)
    return worker

