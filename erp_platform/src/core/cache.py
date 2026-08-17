# -*- coding: utf-8 -*-
"""
Yengil kesh qatlami (TTL + LRU siyosati).

Dashboard, analitika va hisobotlardagi og'ir so'rovlarni tezlashtirish uchun.
Tashqi server (Redis va h.k.) TALAB QILINMAYDI — hammasi xotirada.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable

_MISSING = object()


class TTLCache:
    """Thread-safe TTL kesh. Hajm oshsa eng eski yozuvlar chiqarib yuboriladi."""

    def __init__(self, maxsize: int = 1024, ttl: float = 300.0) -> None:
        self._maxsize = maxsize
        self._ttl = ttl
        self._data: OrderedDict[Any, tuple[float, Any]] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: Any, default: Any = None) -> Any:
        """Kalit bo'yicha qiymatni qaytaradi (muddati o'tgan bo'lsa — default)."""
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return default
            expires_at, value = item
            if time.monotonic() >= expires_at:
                del self._data[key]
                return default
            self._data.move_to_end(key)
            return value

    def set(self, key: Any, value: Any, ttl: float | None = None) -> None:
        """Qiymatni keshga yozadi (ttl berilmasa — standart TTL)."""
        with self._lock:
            self._data[key] = (time.monotonic() + (ttl or self._ttl), value)
            self._data.move_to_end(key)
            while len(self._data) > self._maxsize:
                self._data.popitem(last=False)

    def get_or_set(self, key: Any, factory: Callable[[], Any], ttl: float | None = None) -> Any:
        """Keshda bo'lsa qaytaradi, bo'lmasa factory() natijasini saqlab qaytaradi."""
        value = self.get(key, _MISSING)
        if value is not _MISSING:
            return value
        value = factory()
        self.set(key, value, ttl)
        return value

    def delete(self, key: Any) -> None:
        """Kalitni keshdan o'chiradi (bo'lmasa jim o'tadi)."""
        with self._lock:
            self._data.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """Berilgan prefiks bilan boshlanuvchi barcha kalitlarni o'chiradi."""
        with self._lock:
            for key in [k for k in self._data if isinstance(k, str) and k.startswith(prefix)]:
                del self._data[key]

    def clear(self) -> None:
        """Butun keshni tozalaydi."""
        with self._lock:
            self._data.clear()


def cached(cache: TTLCache, ttl: float | None = None, prefix: str = ""):
    """
    Funksiya natijasini keshlovchi dekorator.

    Kalit funksiya nomi va argumentlardan tuziladi; faqat hash bo'ladigan
    argumentlar bilan ishlatilsin.
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (prefix or fn.__qualname__, args, tuple(sorted(kwargs.items())))
            return cache.get_or_set(key, lambda: fn(*args, **kwargs), ttl)

        return wrapper

    return decorator
