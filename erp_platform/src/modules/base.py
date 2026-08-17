# -*- coding: utf-8 -*-
"""
Barcha biznes servislar uchun umumiy asos.

Servislar DI konteyner orqali yaratiladi va kerakli yadro
komponentlarini shu yerdan oladi (yengil Dependency Injection).
"""
from __future__ import annotations

from src.core.container import ServiceContainer
from src.core.logger import get_logger


class BaseService:
    """
    Biznes servislarning ota klassi.

    Meros oluvchilar ``self.db``, ``self.config``, ``self.audit``,
    ``self.bus``, ``self.cache`` va ``self.container`` ga ega bo'ladi.
    """

    def __init__(self, container: ServiceContainer) -> None:
        self.container = container
        self.db = container.get("db")
        self.config = container.get("config")
        self.audit = container.get("audit")
        self.bus = container.get("bus")
        self.cache = container.get("cache")
        self.log = get_logger(type(self).__name__)

    def service(self, name: str):
        """Boshqa servisni oladi (mavjud bo'lmasa None — yumshoq bog'lanish)."""
        return self.container.get(name) if self.container.has(name) else None
