"""API chaqiruvlarini fon oqimida bajarish: UI qotib qolmasligi uchun.

Natija asosiy (UI) oqimida, signal orqali qaytadi. Testlarda SyncRunner ishlatiladi.
"""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(object)


class _Job(QRunnable):
    def __init__(self, fn: Callable[[], Any], signals: _Signals) -> None:
        super().__init__()
        self._fn = fn
        self._signals = signals
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # noqa: BLE001 - xatoni UI'ga uzatamiz
            self._signals.failed.emit(exc)
        else:
            self._signals.done.emit(result)


class BackgroundRunner:
    def __init__(self, parent: QObject, pool: QThreadPool | None = None) -> None:
        self._parent = parent
        self._pool = pool or QThreadPool.globalInstance()

    def run(
        self,
        fn: Callable[[], Any],
        on_done: Callable[[Any], None],
        on_failed: Callable[[Exception], None] | None = None,
    ) -> None:
        signals = _Signals(self._parent)
        signals.done.connect(on_done)
        if on_failed is not None:
            signals.failed.connect(on_failed)
        signals.done.connect(lambda _r: signals.deleteLater())
        signals.failed.connect(lambda _e: signals.deleteLater())
        self._pool.start(_Job(fn, signals))


class SyncRunner:
    """Testlar uchun: hammasi shu oqimda, darhol bajariladi."""

    def run(
        self,
        fn: Callable[[], Any],
        on_done: Callable[[Any], None],
        on_failed: Callable[[Exception], None] | None = None,
    ) -> None:
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001
            if on_failed is not None:
                on_failed(exc)
            return
        on_done(result)
