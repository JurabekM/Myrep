"""Tarmoq kuzatuvi API'si: `/api/v1/plugins/monitor/api/net/...`."""

from collections.abc import Awaitable
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..models import MonitorError
from .models import BPF_PATTERN
from .service import NetService

Switch = Literal["on", "off"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartIn(_In):
    name: str = Field(min_length=1, max_length=200)


class ExcludeIn(_In):
    # Bitta yoki vergul bilan ajratilgan bir nechta IPv4/IPv6 manzil.
    ips: str = Field(min_length=1, max_length=4000)


class UnexcludeIn(_In):
    ip: str = Field(min_length=1, max_length=64)


class SettingsIn(_In):
    """Faqat berilgan maydonlar o'zgaradi."""

    store_payload: Switch | None = None
    geo: Switch | None = None
    bpf_filter: str | None = Field(default=None, max_length=200, pattern=BPF_PATTERN)
    # Vergul bilan ajratilgan portlar; `-` — ro'yxatni bo'shatadi.
    suspicious_ports: str | None = Field(default=None, max_length=600, pattern=r"^[0-9,\s-]*$")
    scan_ports: int | None = Field(default=None, ge=3, le=1000)
    scan_window_s: float | None = Field(default=None, ge=1, le=600)
    max_packets: int | None = Field(default=None, ge=100, le=200_000)

    def changes(self) -> dict[str, Any]:
        result = self.model_dump(exclude_none=True)
        for key in ("store_payload", "geo"):
            if key in result:
                result[key] = result[key] == "on"
        if "bpf_filter" in result:
            result["bpf_filter"] = result["bpf_filter"].strip()
        if "suspicious_ports" in result:
            ports = result["suspicious_ports"].replace("-", "").replace(",", " ").split()
            result["suspicious_ports"] = [int(port) for port in ports]
        return result


async def _run[T](operation: Awaitable[T]) -> T:
    try:
        return await operation
    except MonitorError as exc:
        raise HTTPException(exc.status, detail=exc.detail) from exc
    except ValidationError as exc:
        raise HTTPException(422, detail=exc.errors(include_url=False)) from exc


def build_net_router(service: NetService) -> APIRouter:
    router = APIRouter()

    @router.get("/status")
    async def status() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.status())

    @router.get("/summary")
    async def summary() -> list[dict[str, str]]:  # pyright: ignore[reportUnusedFunction]
        return service.summary()

    @router.get("/interfaces")
    async def interfaces() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return service.interfaces()

    @router.post("/start")
    async def start(body: StartIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.start(body.name))

    @router.post("/stop")
    async def stop() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.stop())

    @router.post("/pause")
    async def pause() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.pause())

    @router.post("/resume")
    async def resume() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.resume())

    @router.get("/packets")
    async def packets(  # pyright: ignore[reportUnusedFunction]
        limit: Annotated[int, Query(ge=1, le=2000)] = 200,
        ip: Annotated[str, Query(max_length=64)] = "",
        proto: Annotated[str, Query(max_length=16, pattern=r"^[A-Za-z0-9]*$")] = "",
    ) -> list[dict[str, Any]]:
        return await _run(service.packets(limit, ip, proto))

    @router.get("/alerts")
    async def alerts(  # pyright: ignore[reportUnusedFunction]
        limit: Annotated[int, Query(ge=1, le=2000)] = 200,
    ) -> list[dict[str, Any]]:
        return await _run(service.alerts(limit))

    @router.get("/hosts")
    async def hosts() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return service.hosts()

    @router.delete("/data")
    async def clear() -> dict[str, int]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.clear())

    @router.get("/excluded")
    async def excluded() -> list[dict[str, str]]:  # pyright: ignore[reportUnusedFunction]
        return service.excluded()

    @router.post("/exclude")
    async def exclude(body: ExcludeIn) -> list[dict[str, str]]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.exclude(body.ips.replace(";", ",").split(",")))

    @router.post("/unexclude")
    async def unexclude(body: UnexcludeIn) -> list[dict[str, str]]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.unexclude(body.ip))

    @router.get("/settings")
    async def settings() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return service.settings()

    @router.post("/settings")
    async def set_settings(body: SettingsIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.update_settings(body.changes()))

    return router
