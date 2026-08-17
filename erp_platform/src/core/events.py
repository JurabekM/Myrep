# -*- coding: utf-8 -*-
"""
Hodisalar shinasi (Event Bus) — Observer pattern.

Modullar bir-biriga bog'lanmasdan hodisalar orqali muloqot qiladi::

    bus.subscribe("sale.created", handler)
    bus.emit("sale.created", doc_id=42, total=Decimal("100000"))

Handler xatosi boshqa handlerlarga va asosiy oqimga ta'sir qilmaydi
(xato faqat logga yoziladi).
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Callable

from src.core.logger import get_logger

Handler = Callable[..., None]


class EventBus:
    """Thread-safe hodisalar shinasi (publish/subscribe)."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._lock = threading.RLock()
        self._log = get_logger("events")

    def subscribe(self, event: str, handler: Handler) -> None:
        """Hodisaga obunachi qo'shadi."""
        with self._lock:
            if handler not in self._handlers[event]:
                self._handlers[event].append(handler)

    def unsubscribe(self, event: str, handler: Handler) -> None:
        """Obunani bekor qiladi (mavjud bo'lmasa jim o'tadi)."""
        with self._lock:
            if handler in self._handlers.get(event, []):
                self._handlers[event].remove(handler)

    def emit(self, event: str, **payload: Any) -> None:
        """
        Hodisani e'lon qiladi. Har bir obunachi izolyatsiyalangan holda
        chaqiriladi — bittasining xatosi qolganlarini to'xtatmaydi.
        """
        with self._lock:
            handlers = list(self._handlers.get(event, []))
        for handler in handlers:
            try:
                handler(**payload)
            except Exception:  # noqa: BLE001 - izolyatsiya ataylab keng
                self._log.exception("Event handler xatosi: %s -> %r", event, handler)
