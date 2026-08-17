"""Plugin system: drop a .py file into ``plugins/`` and it appears in the UI.

Contract — each plugin module defines:

    PLUGIN = {"name": "...", "icon": "...", "route": "/plugin/..."}

    def register() -> None:
        # registers its own @ui.page(PLUGIN["route"]) here
"""
from __future__ import annotations

import importlib.util
import logging
from dataclasses import dataclass

from config import settings

log = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    name: str
    icon: str
    route: str
    module_name: str


_plugins: list[PluginInfo] = []
_loaded = False


def load_plugins() -> list[PluginInfo]:
    """Import every plugin module once and collect nav metadata."""
    global _loaded
    if _loaded:
        return _plugins
    _loaded = True
    settings.ensure_directories()
    for path in sorted(settings.PLUGINS_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = f"agro_plugin_{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            meta = getattr(module, "PLUGIN", None)
            register = getattr(module, "register", None)
            if not isinstance(meta, dict) or not callable(register):
                log.warning("Plugin %s kontraktga mos emas — o'tkazib yuborildi.", path.name)
                continue
            register()
            _plugins.append(PluginInfo(
                name=str(meta.get("name", path.stem)),
                icon=str(meta.get("icon", "extension")),
                route=str(meta.get("route", f"/plugin/{path.stem}")),
                module_name=module_name,
            ))
            log.info("Plugin yuklandi: %s (%s)", meta.get("name"), path.name)
        except Exception:  # noqa: BLE001 - one broken plugin must not kill the app
            log.exception("Plugin yuklashda xato: %s", path.name)
    return _plugins


def get_plugins() -> list[PluginInfo]:
    """Loaded plugin registry (for the navigation drawer)."""
    return _plugins
