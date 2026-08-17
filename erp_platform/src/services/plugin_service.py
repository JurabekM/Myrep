# -*- coding: utf-8 -*-
"""
Plugin tizimi.

``plugins/`` papkasidagi har bir ``.py`` fayl plugin hisoblanadi.
Plugin fayli ``register(api)`` funksiyasini e'lon qilishi kerak::

    PLUGIN_NAME = "Mening plaginim"
    PLUGIN_VERSION = "1.0"
    PLUGIN_DESCRIPTION = "Nima qilishi haqida"

    def register(api):
        api.bus.subscribe("sale.confirmed", handler)
        api.add_menu_item("Mening sahifam", "/plugins/my-page")

Plugin xatosi tizimni to'xtatmaydi — xato holati ro'yxatda ko'rinadi.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from src.modules.base import BaseService


class PluginAPI:
    """
    Pluginlarga taqdim etiladigan xavfsiz interfeys.

    * ``api.services`` — servis konteyneri (db, sales, inventory, ...)
    * ``api.bus``      — hodisalar shinasi (subscribe/emit)
    * ``api.config``   — konfiguratsiya (faqat o'qish tavsiya etiladi)
    * ``api.log``      — plugin loggeri
    * ``api.add_menu_item(title, url)`` — web menyuga band qo'shish
    """

    def __init__(self, container, log) -> None:
        self.services = container
        self.bus = container.get("bus")
        self.config = container.get("config")
        self.log = log
        self.menu_items: list[dict] = []

    def add_menu_item(self, title: str, url: str) -> None:
        """Web interfeys yon panelida ko'rinadigan menyu bandi qo'shadi."""
        self.menu_items.append({"title": str(title), "url": str(url)})


class PluginService(BaseService):
    """Pluginlarni yuklash va boshqarish."""

    def __init__(self, container) -> None:
        super().__init__(container)
        self.plugins_dir = Path(container.get("base_dir")) / "plugins"
        self.api = PluginAPI(container, self.log)
        self.loaded: list[dict] = []

    def load_all(self) -> list[dict]:
        """
        ``plugins/`` dagi barcha pluginlarni yuklaydi.

        Har bir plugin holati (yuklandi/xato) ro'yxatda qaytadi.
        """
        self.loaded = []
        if not self.plugins_dir.exists():
            return self.loaded

        for path in sorted(self.plugins_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            info = {"file": path.name, "name": path.stem, "version": "",
                    "description": "", "status": "loaded", "error": ""}
            try:
                spec = importlib.util.spec_from_file_location(
                    f"uzerp_plugin_{path.stem}", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                info["name"] = getattr(module, "PLUGIN_NAME", path.stem)
                info["version"] = str(getattr(module, "PLUGIN_VERSION", "1.0"))
                info["description"] = str(
                    getattr(module, "PLUGIN_DESCRIPTION", ""))

                register = getattr(module, "register", None)
                if callable(register):
                    register(self.api)
                else:
                    info["status"] = "skipped"
                    info["error"] = "register(api) funksiyasi topilmadi"
            except Exception as exc:  # noqa: BLE001 - plugin izolyatsiyasi
                info["status"] = "error"
                info["error"] = str(exc)
                self.log.exception("Plugin yuklashda xato: %s", path.name)
            self.loaded.append(info)

        active = sum(1 for p in self.loaded if p["status"] == "loaded")
        if self.loaded:
            self.log.info("Pluginlar: %d ta yuklandi, %d ta xato.",
                          active, len(self.loaded) - active)
        return self.loaded

    def menu_items(self) -> list[dict]:
        """Pluginlar qo'shgan menyu bandlari (web UI uchun)."""
        return list(self.api.menu_items)
