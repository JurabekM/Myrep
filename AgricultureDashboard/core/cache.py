"""Thread-safe in-process TTL cache with a decorator API."""
from __future__ import annotations

import functools
import threading
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_registry: list["TTLCache"] = []
_registry_lock = threading.Lock()


class TTLCache:
    """Small dictionary cache where each entry expires after ``ttl`` seconds."""

    def __init__(self, ttl: float = 300.0, max_items: int = 512) -> None:
        self.ttl = ttl
        self.max_items = max_items
        self._data: dict[Any, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        with _registry_lock:
            _registry.append(self)

    def get(self, key: Any) -> Any | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            expires, value = entry
            if time.monotonic() > expires:
                del self._data[key]
                return None
            return value

    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            if len(self._data) >= self.max_items:
                # Drop the oldest half to stay bounded.
                for stale in sorted(self._data, key=lambda k: self._data[k][0])[
                    : self.max_items // 2
                ]:
                    del self._data[stale]
            self._data[key] = (time.monotonic() + self.ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


def cached(ttl: float = 300.0) -> Callable[[F], F]:
    """Decorator caching a function's result per-arguments for ``ttl`` seconds."""

    def decorator(func: F) -> F:
        store = TTLCache(ttl=ttl)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (args, tuple(sorted(kwargs.items())))
            hit = store.get(key)
            if hit is not None:
                return hit
            value = func(*args, **kwargs)
            if value is not None:
                store.set(key, value)
            return value

        wrapper.cache = store  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


def clear_all_caches() -> int:
    """Flush every registered cache (used after imports / restores)."""
    with _registry_lock:
        for cache in _registry:
            cache.clear()
        return len(_registry)
