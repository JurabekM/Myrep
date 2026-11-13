"""Plagin modulini yuklash va hook'larini chaqirish (ikkala rejim uchun umumiy)."""

import importlib.util
import inspect
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pluggy

from srv1_sdk.asgi import AsgiApp, AsgiResponse, call_asgi, json_error
from srv1_sdk.context import PluginContext
from srv1_sdk.hookspec import PROJECT, PluginSpec
from srv1_sdk.manifest import PluginManifest
from srv1_sdk.panel import PanelSpec, parse_panel
from srv1_sdk.types import EventHandler, Job, PermissionDenied

MODULE_PREFIX = "srv1_plugins."


class PluginLoadError(RuntimeError):
    """Plagin kodi import bo'lmadi yoki hook noto'g'ri qiymat qaytardi."""


def _import_plugin(plugin_dir: Path, name: str) -> ModuleType:
    init_file = plugin_dir / "__init__.py"
    module_name = MODULE_PREFIX + name
    spec = importlib.util.spec_from_file_location(
        module_name, init_file, submodule_search_locations=[str(plugin_dir)]
    )
    if spec is None or spec.loader is None or not init_file.is_file():
        raise PluginLoadError(f"__init__.py topilmadi: {plugin_dir}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except MemoryError:
        raise
    except Exception as exc:
        _forget_modules(module_name)
        raise PluginLoadError(f"import xatosi: {type(exc).__name__}: {exc}") from exc
    return module


def _forget_modules(module_name: str) -> None:
    for loaded in [m for m in sys.modules if m == module_name or m.startswith(module_name + ".")]:
        del sys.modules[loaded]


def _typed_sequence[T](raw: Any, item_type: type[T], hook: str) -> tuple[T, ...]:  # noqa: ANN401
    if raw is None:
        return ()
    items = tuple(cast(Sequence[Any], raw))
    for item in items:
        if not isinstance(item, item_type):
            raise PluginLoadError(f"{hook} {item_type.__name__} ro'yxatini qaytarishi kerak")
    return cast(tuple[T, ...], items)


class LoadedPlugin:
    """Import qilingan plagin: hook natijalari va hayot sikli."""

    def __init__(self, plugin_dir: Path, manifest: PluginManifest, ctx: PluginContext) -> None:
        self._dir = plugin_dir
        self.manifest = manifest
        self.ctx = ctx
        self._hooks: pluggy.PluginManager | None = None
        self._router: Any = None
        self._app: AsgiApp | None = None
        self.subscriptions: tuple[EventHandler, ...] = ()
        self.jobs: tuple[Job, ...] = ()
        self.panel: PanelSpec | None = None

    def load(self) -> None:
        module = _import_plugin(self._dir, self.manifest.name)
        hooks = pluggy.PluginManager(PROJECT)
        hooks.add_hookspecs(PluginSpec)
        hooks.register(module)
        self._hooks = hooks
        try:
            self._collect(hooks)
        except PluginLoadError:
            self.unload()
            raise
        except Exception as exc:
            self.unload()
            raise PluginLoadError(f"hook xatosi: {type(exc).__name__}: {exc}") from exc

    def _collect(self, hooks: pluggy.PluginManager) -> None:
        ctx = self.ctx
        self._router = hooks.hook.srv1_router(ctx=ctx)
        self.subscriptions = _typed_sequence(
            hooks.hook.srv1_subscriptions(ctx=ctx), EventHandler, "srv1_subscriptions"
        )
        self.jobs = _typed_sequence(hooks.hook.srv1_jobs(ctx=ctx), Job, "srv1_jobs")
        if len({job.id for job in self.jobs}) != len(self.jobs):
            raise PluginLoadError("srv1_jobs: vazifa id'lari takrorlanmasin")
        self.panel = parse_panel(hooks.hook.srv1_panel(ctx=ctx))

    async def start(self) -> None:
        await self._call_lifecycle("srv1_start")

    async def stop(self) -> None:
        await self._call_lifecycle("srv1_stop")

    async def _call_lifecycle(self, hook: str) -> None:
        if self._hooks is None:
            return
        result = getattr(self._hooks.hook, hook)(ctx=self.ctx)
        if inspect.isawaitable(result):
            await result

    def unload(self) -> None:
        """Modulni `sys.modules` dan olib tashlaydi (xotiradagi kod darhol yo'qolmaydi)."""
        self._hooks = None
        self._app = None
        _forget_modules(MODULE_PREFIX + self.manifest.name)

    @property
    def has_router(self) -> bool:
        return self._router is not None

    def _asgi_app(self) -> AsgiApp:
        if self._app is None:
            from fastapi import FastAPI  # faqat router bergan plagin uchun yuklanadi
            from fastapi.responses import JSONResponse

            app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
            app.include_router(self._router)

            async def denied(_request: object, exc: Exception) -> JSONResponse:
                return JSONResponse({"detail": str(exc)}, status_code=403)

            app.add_exception_handler(PermissionDenied, denied)
            self._app = cast(AsgiApp, app)
        return self._app

    async def handle_request(
        self,
        *,
        method: str,
        path: str,
        query: bytes,
        headers: Sequence[tuple[str, str]],
        body: bytes,
    ) -> AsgiResponse:
        if self._router is None:
            return json_error(404, "plaginda API yo'q")
        return await call_asgi(
            self._asgi_app(), method=method, path=path, query=query, headers=headers, body=body
        )
