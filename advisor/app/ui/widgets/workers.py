"""Qt worker'lar — fon oqimidagi ish natijasini UI thread'iga signal orqali uzatadi.

PyQt'da UI faqat asosiy thread'da o'zgartiriladi. Bu yerdagi ``QObject``lar
``QThreadPool`` orqali ishlaydi va natijani signal bilan qaytaradi — shunda
callback'lar UI thread'ida (signal-slot) xavfsiz bajariladi.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal


class _StreamSignals(QObject):
    token = pyqtSignal(str)
    provider = pyqtSignal(str)
    finished = pyqtSignal(object)  # natija obyekti
    error = pyqtSignal(str)


class StreamChatRunnable(QRunnable):
    """Chat oqimini fon oqimida bajaradi; har token signal orqali UI'ga uzatiladi."""

    def __init__(self, chat_call: Callable[..., Any]):
        super().__init__()
        self.signals = _StreamSignals()
        self._chat_call = chat_call

    def run(self) -> None:
        try:
            result = self._chat_call(
                on_token=self.signals.token.emit,
                on_provider=self.signals.provider.emit,
            )
            self.signals.finished.emit(result)
        except Exception as exc:  # noqa: BLE001 — signal orqali UI'ga
            self.signals.error.emit(str(exc))


class _TaskSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)


class CallableRunnable(QRunnable):
    """Ixtiyoriy bloklovchi funksiyani fon oqimida bajaradi (AI generatsiya, hisob)."""

    def __init__(self, func: Callable[..., Any], *args: Any, **kwargs: Any):
        super().__init__()
        self.signals = _TaskSignals()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._func(*self._args, **self._kwargs)
            self.signals.finished.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(str(exc))
