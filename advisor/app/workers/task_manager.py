"""Fon vazifalari menejeri — Celery/RabbitMQ o'rniga sof Python.

``ThreadPoolExecutor`` orqali bloklovchi vazifalar (AI chaqiruvi, hujjat
ajratish, scraping) UI thread'idan tashqarida bajariladi. Natija/xato/oqim
callback'lar orqali qaytariladi; PyQt tomonida bu callback'lar signalга
ulanadi (UI thread'iga xavfsiz o'tkazish uchun).
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from app.core.logging_setup import get_logger

logger = get_logger(__name__)


class TaskManager:
    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="advisor-worker"
        )

    def submit(
        self,
        func: Callable[..., Any],
        *args: Any,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        **kwargs: Any,
    ) -> Future:
        """Vazifani fon oqimida ishga tushiradi.

        ``on_success``/``on_error`` fon thread'ida chaqiriladi — UI'ni to'g'ridan
        to'g'ri o'zgartirmang, Qt signal orqali o'tkazing.
        """

        def _run() -> Any:
            return func(*args, **kwargs)

        future = self._executor.submit(_run)

        def _done(fut: Future) -> None:
            try:
                result = fut.result()
            except Exception as exc:  # noqa: BLE001 — callback'ga uzatamiz
                logger.warning("Fon vazifasi xatosi: %s", exc)
                if on_error is not None:
                    on_error(exc)
                return
            if on_success is not None:
                on_success(result)

        future.add_done_callback(_done)
        return future

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
