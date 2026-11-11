"""`electronics` plagini: serial monitor, plata aniqlash va proshivka yozish.

ESP platalari `esptool`, AVR (Arduino) platalari `avrdude` bilan yoziladi — ikkalasi
ham alohida jarayonda, `shell`siz. Har yozish urinishi audit jurnaliga tushadi.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from srv1_sdk.context import PluginContext
from srv1_sdk.hookspec import hookimpl
from srv1_sdk.panel import PanelSpec

from .models import BOARDS
from .panel import build_panel
from .service import LOG_LINES, ElectronicsError, ElectronicsService, FlashRequest

_services: dict[str, ElectronicsService] = {}
_PORT = Field(min_length=1, max_length=64)


def _service(ctx: PluginContext) -> ElectronicsService:
    if ctx.name not in _services:
        _services[ctx.name] = ElectronicsService(ctx)
    return _services[ctx.name]


class PortIn(BaseModel):
    port: str = _PORT


class MonitorOpenIn(PortIn):
    baudrate: int | None = Field(default=None, ge=300, le=2_000_000)


class MonitorWriteIn(PortIn):
    text: str = Field(max_length=4096)
    newline: bool = True


class FlashIn(PortIn):
    board: str = Field(pattern=r"^[a-z0-9_]{1,32}$")
    file: str = Field(min_length=1, max_length=512)
    # Faqat ESP: yozish manzili (bo'sh — plataning standart manzili).
    offset: str = Field(default="", pattern=r"^(0x[0-9a-fA-F]{1,8})?$")
    baudrate: int | None = Field(default=None, ge=9600, le=2_000_000)
    # Faqat ESP: yozishdan oldin eski proshivkani o'qib saqlash; butun xotirani o'chirish.
    backup: bool = False
    erase: bool = False


async def _run[T](operation: Awaitable[T]) -> T:
    try:
        return await operation
    except ElectronicsError as exc:
        raise HTTPException(exc.status, detail=exc.detail) from exc


def _call[**P, T](operation: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return operation(*args, **kwargs)
    except ElectronicsError as exc:
        raise HTTPException(exc.status, detail=exc.detail) from exc


@hookimpl
def srv1_start(ctx: PluginContext) -> None:
    _service(ctx).prepare()


@hookimpl
def srv1_stop(ctx: PluginContext) -> Awaitable[None] | None:
    service = _services.pop(ctx.name, None)
    return None if service is None else service.stop()


@hookimpl
def srv1_panel(ctx: PluginContext) -> PanelSpec:
    return build_panel()


def _port_routes(router: APIRouter, service: ElectronicsService) -> None:
    @router.get("/status")
    async def status() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return service.status()

    @router.get("/ports")
    async def ports() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return await service.ports()

    @router.get("/boards")
    async def boards() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return [
            {"key": b.key, "title": b.title, "tool": b.tool, "file": b.suffix, "offset": b.offset}
            for b in BOARDS.values()
        ]

    @router.get("/firmware")
    async def firmware() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return await asyncio.to_thread(service.firmware_files)


def _monitor_routes(router: APIRouter, service: ElectronicsService) -> None:
    @router.post("/monitor/open")
    async def open_monitor(body: MonitorOpenIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.open_monitor(body.port, body.baudrate))

    @router.post("/monitor/close")
    async def close_monitor(body: PortIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.close_monitor(body.port))

    @router.post("/monitor/write")
    async def write_monitor(body: MonitorWriteIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.write_monitor(body.port, body.text, body.newline))

    @router.get("/monitor/lines")
    async def lines(  # pyright: ignore[reportUnusedFunction]
        port: Annotated[str, Query(min_length=1, max_length=64)],
        tail: Annotated[int, Query(ge=1, le=300)] = 100,
    ) -> list[str]:
        return _call(service.monitor_lines, port, tail)


def _flash_routes(router: APIRouter, service: ElectronicsService) -> None:
    @router.post("/flash", status_code=202)
    async def flash(body: FlashIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.flash(FlashRequest(**body.model_dump())))

    @router.get("/flash")
    async def flash_status() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return service.job_status()

    @router.get("/flash/log")
    async def flash_log(  # pyright: ignore[reportUnusedFunction]
        tail: Annotated[int, Query(ge=1, le=LOG_LINES)] = 200,
    ) -> list[str]:
        return service.log_lines(tail)

    @router.get("/flash/history")
    async def flash_history() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return service.job_history()

    @router.post("/flash/cancel")
    async def flash_cancel() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.cancel())


@hookimpl
def srv1_router(ctx: PluginContext) -> APIRouter:
    router = APIRouter()
    service = _service(ctx)
    _port_routes(router, service)
    _monitor_routes(router, service)
    _flash_routes(router, service)
    return router
