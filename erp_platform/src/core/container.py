# -*- coding: utf-8 -*-
"""
Yengil Dependency Injection konteyneri (Service Locator uslubida).

Servislar factory funksiya sifatida ro'yxatdan o'tkaziladi va birinchi
so'ralganda yaratiladi (lazy singleton)::

    container.register("sales", lambda c: SalesService(c.get("db")))
    sales = container.get("sales")
"""
from __future__ import annotations

import threading
from typing import Any, Callable


class ServiceContainer:
    """Thread-safe, lazy-singleton servis konteyneri."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[["ServiceContainer"], Any]] = {}
        self._instances: dict[str, Any] = {}
        self._lock = threading.RLock()

    def register(self, name: str, factory: Callable[["ServiceContainer"], Any]) -> None:
        """Servis factory'sini ro'yxatdan o'tkazadi (instansiya keyin yaratiladi)."""
        with self._lock:
            self._factories[name] = factory
            self._instances.pop(name, None)

    def register_instance(self, name: str, instance: Any) -> None:
        """Tayyor obyektni servis sifatida ro'yxatdan o'tkazadi."""
        with self._lock:
            self._instances[name] = instance
            self._factories.pop(name, None)

    def get(self, name: str) -> Any:
        """Servisni qaytaradi; kerak bo'lsa factory orqali yaratadi."""
        with self._lock:
            if name in self._instances:
                return self._instances[name]
            if name not in self._factories:
                raise KeyError(f"Servis topilmadi: {name!r}")
            instance = self._factories[name](self)
            self._instances[name] = instance
            return instance

    def has(self, name: str) -> bool:
        """Servis ro'yxatdan o'tganligini tekshiradi."""
        with self._lock:
            return name in self._instances or name in self._factories

    def names(self) -> list[str]:
        """Ro'yxatdan o'tgan barcha servis nomlari."""
        with self._lock:
            return sorted(set(self._factories) | set(self._instances))
