"""Safe optional-dependency loader.

Heavy or platform-fragile libraries (GeoPandas, Rasterio, TensorFlow, ...)
are imported through :func:`try_import` so a missing wheel never breaks the
platform — every feature has a pure-Python fallback path.
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
from types import ModuleType

log = logging.getLogger(__name__)
_cache: dict[str, ModuleType | None] = {}


def try_import(module_name: str) -> ModuleType | None:
    """Import a module, returning ``None`` (and caching) when unavailable."""
    if module_name in _cache:
        return _cache[module_name]
    try:
        if importlib.util.find_spec(module_name) is None:
            _cache[module_name] = None
            return None
        module = importlib.import_module(module_name)
        _cache[module_name] = module
        return module
    except Exception as exc:  # pragma: no cover - import-time env issues
        log.warning("Optional module '%s' failed to import: %s", module_name, exc)
        _cache[module_name] = None
        return None


def available(module_name: str) -> bool:
    """Return True when the optional module can be imported."""
    return try_import(module_name) is not None


def optional_status() -> dict[str, bool]:
    """Availability map of every registered optional package."""
    from config import settings

    return {pip: available(mod) for pip, mod in settings.OPTIONAL_PACKAGES.items()}
