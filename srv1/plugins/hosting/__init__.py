"""`hosting` plagini: statik sayt, Python va Node loyihalari Caddy ortida.

Har loyiha `<ma'lumotlar>/projects/<nom>/` papkasida va `http://<nom>.localhost:8080/`
manzilida; xohlasa cloudflared tunneli orqali vaqtincha internetga ochiladi.
Jarayonlar `shell`siz, Job Object ichida (RAM limiti bilan) ishga
tushadi; so'rov kelmasa uxlatiladi va keyingi so'rovda o'zi uyg'onadi.
"""

from collections.abc import Awaitable
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from srv1_sdk.context import PluginContext
from srv1_sdk.hookspec import hookimpl
from srv1_sdk.panel import PanelSpec

from .models import NAME_PATTERN, ProjectConfig
from .panel import build_panel
from .service import LOG_LINES, HostingError, HostingService

_services: dict[str, HostingService] = {}


def _service(ctx: PluginContext) -> HostingService:
    if ctx.name not in _services:
        _services[ctx.name] = HostingService(ctx)
    return _services[ctx.name]


class NameIn(BaseModel):
    name: str = Field(pattern=NAME_PATTERN)


class ProjectIn(ProjectConfig):
    """Yangi loyiha. `command` satr yoki ro'yxat bo'lishi mumkin."""

    start: bool = True


async def _run[T](operation: Awaitable[T]) -> T:
    try:
        return await operation
    except HostingError as exc:
        raise HTTPException(exc.status, detail=exc.detail) from exc


@hookimpl
def srv1_start(ctx: PluginContext) -> Awaitable[None]:
    service = _service(ctx)
    service.prepare()
    return service.start()


@hookimpl
def srv1_stop(ctx: PluginContext) -> Awaitable[None] | None:
    service = _services.pop(ctx.name, None)
    return None if service is None else service.stop()


@hookimpl
def srv1_panel(ctx: PluginContext) -> PanelSpec:
    return build_panel()


@hookimpl
def srv1_router(ctx: PluginContext) -> APIRouter:
    router = APIRouter()
    service = _service(ctx)

    @router.get("/status")
    async def status() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await service.status()

    @router.get("/projects")
    async def projects() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return await service.list_projects()

    @router.post("/projects", status_code=201)
    async def create(body: ProjectIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        config = ProjectConfig.model_validate(body.model_dump(exclude={"start", "port"}))
        return await _run(service.create(config, start=body.start))

    @router.post("/start")
    async def start(body: NameIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.start_project(body.name))

    @router.post("/stop")
    async def stop(body: NameIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.stop_project(body.name))

    @router.post("/restart")
    async def restart(body: NameIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.restart_project(body.name))

    @router.post("/remove")
    async def remove(body: NameIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.remove(body.name))

    @router.post("/tunnel/open")
    async def tunnel_open(body: NameIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.open_tunnel(body.name))

    @router.post("/tunnel/close")
    async def tunnel_close(body: NameIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.close_tunnel(body.name))

    @router.get("/log")
    async def log(  # pyright: ignore[reportUnusedFunction]
        name: Annotated[str, Query(pattern=NAME_PATTERN)],
        tail: Annotated[int, Query(ge=1, le=LOG_LINES)] = 200,
    ) -> list[str]:
        try:
            return service.log_tail(name, tail)
        except HostingError as exc:
            raise HTTPException(exc.status, detail=exc.detail) from exc

    return router
