"""`monitor` plagini: CPU, RAM va disk tarixi, chegaradan oshganda ogohlantirish.

Har `interval_s` soniyada tizim holatini o'lchab, o'z SQLite bazasiga yozadi,
qoidalarni tekshiradi va holat o'zgarsa `plugin.monitor.alert` hodisasini
chiqaradi. Boshqa plagin yiqilsa ham ogohlantirish yoziladi.

Yangi plagin yozishda andoza sifatida ham qulay: API router, davriy vazifa,
hodisa nashri va obunasi, o'z papkasiga yozish, audit va panel shu yerda bor.
`plugin.toml` da `mode = "subprocess"` qilinsa, shu kod alohida jarayonda ishlaydi.
"""

from collections.abc import Awaitable, Mapping
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from srv1_sdk.context import PluginContext
from srv1_sdk.hookspec import hookimpl
from srv1_sdk.panel import PanelSpec
from srv1_sdk.types import EventHandler, Job

from .models import MonitorError
from .panel import build_panel
from .service import MonitorService

PURGE_INTERVAL_S = 3600.0
_services: dict[str, MonitorService] = {}


def _service(ctx: PluginContext) -> MonitorService:
    if ctx.name not in _services:
        _services[ctx.name] = MonitorService(ctx)
    return _services[ctx.name]


class ThresholdsIn(BaseModel):
    """Faqat berilgan maydonlar o'zgaradi. `0` — qoidani o'chiradi."""

    model_config = ConfigDict(extra="forbid")

    memory_percent: float | None = Field(default=None, ge=0, le=100)
    cpu_percent: float | None = Field(default=None, ge=0, le=100)
    cpu_minutes: float | None = Field(default=None, ge=0, le=120)
    disk_free_gb: float | None = Field(default=None, ge=0, le=100_000)


async def _run[T](operation: Awaitable[T]) -> T:
    try:
        return await operation
    except MonitorError as exc:
        raise HTTPException(exc.status, detail=exc.detail) from exc


@hookimpl
def srv1_start(ctx: PluginContext) -> Awaitable[None]:
    return _service(ctx).start()


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

    async def sample() -> None:
        await service.sample()

    return [
        Job(id="sample", func=sample, interval_s=service.store.config.interval_s),
        Job(id="purge", func=service.purge, interval_s=PURGE_INTERVAL_S),
    ]


@hookimpl
def srv1_subscriptions(ctx: PluginContext) -> list[EventHandler]:
    service = _service(ctx)

    async def on_state(topic: str, data: Mapping[str, Any]) -> None:
        await service.on_plugin_state(data)

    return [EventHandler("plugins.state", on_state)]


@hookimpl
def srv1_router(ctx: PluginContext) -> APIRouter:
    router = APIRouter()
    service = _service(ctx)

    @router.get("/status")
    async def status() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.status())

    @router.post("/sample")
    async def sample_now() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        await _run(service.sample())
        return await _run(service.status())

    @router.get("/history")
    async def history(  # pyright: ignore[reportUnusedFunction]
        minutes: Annotated[float, Query(gt=0, le=366 * 24 * 60)] = 60,
        limit: Annotated[int, Query(ge=1, le=5000)] = 240,
    ) -> list[dict[str, Any]]:
        return await _run(service.series(minutes, limit))

    @router.delete("/history")
    async def clear_history() -> dict[str, int]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.clear_history())

    @router.get("/disks")
    async def disks() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return service.disks()

    @router.get("/rules")
    async def rules() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return service.rules()

    @router.get("/thresholds")
    async def thresholds() -> dict[str, float]:  # pyright: ignore[reportUnusedFunction]
        return service.store.config.thresholds.model_dump()

    @router.post("/thresholds")
    async def set_thresholds(body: ThresholdsIn) -> dict[str, float]:  # pyright: ignore[reportUnusedFunction]
        changes = body.model_dump(exclude_none=True)
        return (await service.set_thresholds(changes)).model_dump()

    @router.get("/alerts")
    async def alerts(  # pyright: ignore[reportUnusedFunction]
        limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    ) -> list[dict[str, Any]]:
        return await _run(service.alerts(limit))

    return router
