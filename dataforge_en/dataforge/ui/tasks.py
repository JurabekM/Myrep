"""Background tasks — keep heavy computation off the GUI thread."""
from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class WorkerSignals(QObject):
    finished = Signal(object)     # result
    failed = Signal(str)          # error text
    progress = Signal(str, int)   # (message, percent)


class Worker(QRunnable):
    """Run a callable on a separate thread.

    If the callable accepts a ``progress`` keyword argument, it receives a
    ``progress(msg, pct)`` function.
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
    def run(self) -> None:  # pragma: no cover - runs on a worker thread
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
    """Run a task on the global thread pool."""
    worker = Worker(fn, *args, with_progress=with_progress, **kwargs)
    if on_done:
        worker.signals.finished.connect(on_done)
    if on_error:
        worker.signals.failed.connect(on_error)
    if on_progress:
        worker.signals.progress.connect(on_progress)
    QThreadPool.globalInstance().start(worker)
    return worker
