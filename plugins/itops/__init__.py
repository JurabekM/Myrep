"""`itops` plagini: jarayonlar, Windows xizmatlari, tarmoq skaneri va zaxira nusxa.

Xavfli amallar (jarayonni to'xtatish, xizmatni boshqarish, skanerlash, zaxirani
o'chirish) audit jurnaliga yoziladi. Tizim jarayonlari va SRV_1 ning o'z
jarayonlari to'xtatilmaydi.
"""

from collections.abc import Awaitable
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from srv1_sdk.context import PluginContext
from srv1_sdk.hookspec import hookimpl
from srv1_sdk.panel import PanelSpec
from srv1_sdk.types import Job

from .models import ItopsError
from .panel import build_panel
from .processes import Sort
from .service import ItopsService

_services: dict[str, ItopsService] = {}
ServiceState = Literal["", "running", "stopped", "paused", "start_pending", "stop_pending"]


def _service(ctx: PluginContext) -> ItopsService:
    if ctx.name not in _services:
        _services[ctx.name] = ItopsService(ctx)
    return _services[ctx.name]


class KillIn(BaseModel):
    pid: int = Field(ge=1, le=2**31 - 1)
    # Ro'yxatdagi `started` qiymati: PID boshqa jarayonga o'tib qolmaganini tekshirish uchun.
    started: float | None = Field(default=None, ge=0)


class ServiceIn(BaseModel):
    name: str = Field(pattern=r"^[A-Za-z0-9_.$ -]{1,256}$")


class ScanIn(BaseModel):
    network: str = Field(default="", max_length=18)
    ports: list[Annotated[int, Field(ge=1, le=65535)]] = Field(
        default_factory=list[int], max_length=32
    )


class BackupNameIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)


async def _run[T](operation: Awaitable[T]) -> T:
    try:
        return await operation
    except ItopsError as exc:
        raise HTTPException(exc.status, detail=exc.detail) from exc


@hookimpl
def srv1_start(ctx: PluginContext) -> None:
    _service(ctx)


@hookimpl
def srv1_stop(ctx: PluginContext) -> Awaitable[None] | None:
    service = _services.pop(ctx.name, None)
    return None if service is None else service.stop()


@hookimpl
def srv1_panel(ctx: PluginContext) -> PanelSpec:
    return build_panel()


@hookimpl
def srv1_jobs(ctx: PluginContext) -> list[Job]:
    service = _service(ctx)
    cron = service.store.config.backup_cron.strip()
    return [Job(id="backup", func=service.run_backup, cron=cron)] if cron else []


def _system_routes(router: APIRouter, service: ItopsService) -> None:
    @router.get("/status")
    async def status() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.status())

    @router.get("/processes")
    async def processes(  # pyright: ignore[reportUnusedFunction]
        search: Annotated[str, Query(max_length=64)] = "",
        sort: Sort = "memory",
        limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    ) -> list[dict[str, Any]]:
        return await service.processes(search, sort, limit)

    @router.post("/processes/kill")
    async def kill(body: KillIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.kill(body.pid, body.started))

    @router.get("/services")
    async def services(  # pyright: ignore[reportUnusedFunction]
        search: Annotated[str, Query(max_length=64)] = "",
        state: ServiceState = "",
    ) -> list[dict[str, Any]]:
        return await service.services(search, state)

    @router.post("/services/start")
    async def start_service(body: ServiceIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.control(body.name, "start"))

    @router.post("/services/stop")
    async def stop_service(body: ServiceIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.control(body.name, "stop"))

    @router.post("/services/restart")
    async def restart_service(body: ServiceIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.control(body.name, "restart"))


def _scan_routes(router: APIRouter, service: ItopsService) -> None:
    @router.get("/networks")
    async def networks() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return service.networks()

    @router.post("/scan", status_code=202)
    async def scan(body: ScanIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.start_scan(body.network.strip(), body.ports))

    @router.get("/scan")
    async def scan_status() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return service.scan_status()

    @router.get("/scan/hosts")
    async def scan_hosts() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return service.scan_hosts()

    @router.post("/scan/cancel")
    async def scan_cancel() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.cancel_scan())


def _backup_routes(router: APIRouter, service: ItopsService) -> None:
    @router.get("/backups")
    async def backups() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.backups())

    @router.post("/backups/run", status_code=202)
    async def backup_run() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.start_backup())

    @router.get("/backups/status")
    async def backup_status() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return service.backup_status()

    @router.post("/backups/remove")
    async def backup_remove(body: BackupNameIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.remove_backup(body.name))


@hookimpl
def srv1_router(ctx: PluginContext) -> APIRouter:
    router = APIRouter()
    service = _service(ctx)
    _system_routes(router, service)
    _scan_routes(router, service)
    _backup_routes(router, service)
    return router
