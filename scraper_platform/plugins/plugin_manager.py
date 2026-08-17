# -*- coding: utf-8 -*-
"""
plugins/plugin_manager.py
=========================
Plugin (kengaytma) tizimi. `plugins/` papkasiga tashlangan har qanday
Python fayli avtomatik yuklanadi. Bu maxsus parserlar yoki qayta ishlash
mantiqini qo'shish imkonini beradi.

Plugin interfeysi (BasePlugin):
    - name: plugin nomi
    - matches(url, html) -> bool : ushbu plugin sahifaga mos keladimi
    - parse(url, html) -> list[dict] : ma'lumot ajratib olish

Namuna plugin uchun: plugins/example_plugin.py ga qarang.
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Any

from config.settings import PLUGINS_DIR
from logs.logger import get_logger

log = get_logger(__name__)


class BasePlugin:
    """Barcha pluginlar meros oladigan asosiy klass."""

    name: str = "base"

    def matches(self, url: str, html: str) -> bool:
        """Ushbu plugin berilgan sahifaga mos kelishini aniqlaydi."""
        raise NotImplementedError

    def parse(self, url: str, html: str) -> list[dict[str, Any]]:
        """Sahifadan ma'lumot ajratib oladi."""
        raise NotImplementedError


class PluginManager:
    """Pluginlarni yuklash va boshqarish."""

    def __init__(self) -> None:
        self._plugins: list[BasePlugin] = []
        self.reload()

    # -----------------------------------------------------------------
    def reload(self) -> None:
        """plugins/ papkasidagi barcha pluginlarni qayta yuklaydi."""
        self._plugins.clear()
        for file in PLUGINS_DIR.glob("*.py"):
            if file.name.startswith("_") or file.name == "plugin_manager.py":
                continue
            self._load_file(file)
        log.info("{} ta plugin yuklandi", len(self._plugins))

    def _load_file(self, file: Path) -> None:
        """Bitta plugin faylini yuklaydi va BasePlugin voris klasslarini topadi."""
        try:
            spec = importlib.util.spec_from_file_location(file.stem, file)
            if spec is None or spec.loader is None:
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BasePlugin) and obj is not BasePlugin:
                    instance = obj()
                    self._plugins.append(instance)
                    log.info("Plugin yuklandi: {} ({})", instance.name, file.name)
        except Exception as exc:  # noqa: BLE001 - noto'g'ri plugin butun tizimni buzmasin
            log.error("Plugin yuklashda xatolik {}: {}", file.name, exc)

    # -----------------------------------------------------------------
    def apply(self, url: str, html: str) -> list[dict[str, Any]]:
        """
        Mos keluvchi barcha pluginlarni qo'llaydi va natijalarni yig'adi.

        Returns:
            Barcha pluginlardan olingan yozuvlar ro'yxati.
        """
        results: list[dict[str, Any]] = []
        for plugin in self._plugins:
            try:
                if plugin.matches(url, html):
                    parsed = plugin.parse(url, html)
                    if parsed:
                        results.extend(parsed)
                        log.debug("Plugin '{}' {} ta yozuv qaytardi", plugin.name, len(parsed))
            except Exception as exc:  # noqa: BLE001
                log.error("Plugin '{}' xatoligi: {}", plugin.name, exc)
        return results

    @property
    def plugins(self) -> list[BasePlugin]:
        """Yuklangan pluginlar ro'yxati."""
        return list(self._plugins)


# Global singleton
PLUGIN_MANAGER = PluginManager()
