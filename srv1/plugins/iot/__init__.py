"""`iot` plagini: MQTT (Mosquitto), serial portlar, Modbus va telemetriyani saqlash.

Uch manbadan kelgan sonli qiymatlar bitta telemetriya omboriga tushadi; manba
nomi `mqtt:<mavzu>`, `serial:<port>`, `modbus:<qurilma>` yoki `manual:<nom>`.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from srv1_sdk.context import PluginContext
from srv1_sdk.hookspec import hookimpl
from srv1_sdk.panel import PanelSpec

from .models import NAME_PATTERN, TOPIC_MAX, ModbusDevice
from .panel import build_panel
from .service import MESSAGES_KEPT, IotError, IotService

_services: dict[str, IotService] = {}
_SOURCE = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_./:#+-]{0,127}$")
_KEY = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_.-]{0,31}$")


def _service(ctx: PluginContext) -> IotService:
    if ctx.name not in _services:
        _services[ctx.name] = IotService(ctx)
    return _services[ctx.name]


class RecordIn(BaseModel):
    """Qo'lda yozuv. Manba har doim `manual:` bilan boshlanadi."""

    source: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")]
    values: dict[Annotated[str, _KEY], float] = Field(
        default_factory=dict[str, float], max_length=32
    )
    key: Annotated[str, _KEY] | None = None
    value: float | None = None
    ts: float | None = Field(default=None, ge=0)


class PublishIn(BaseModel):
    topic: str = Field(min_length=1, max_length=TOPIC_MAX)
    payload: str = Field(default="", max_length=64 * 1024)
    qos: int = Field(default=0, ge=0, le=1)
    retain: bool = False


class TopicIn(BaseModel):
    topic: str = Field(min_length=1, max_length=TOPIC_MAX)


class SerialOpenIn(BaseModel):
    port: str = Field(min_length=1, max_length=64)
    baudrate: int = Field(default=9600, ge=300, le=921600)


class SerialPortIn(BaseModel):
    port: str = Field(min_length=1, max_length=64)


class SerialWriteIn(SerialPortIn):
    text: str = Field(max_length=4096)
    newline: bool = True


class DeviceIn(BaseModel):
    name: str = Field(pattern=NAME_PATTERN)


class ModbusWriteIn(DeviceIn):
    key: Annotated[str, _KEY]
    value: float


async def _run[T](operation: Awaitable[T]) -> T:
    try:
        return await operation
    except IotError as exc:
        raise HTTPException(exc.status, detail=exc.detail) from exc


def _call[**P, T](operation: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return operation(*args, **kwargs)
    except IotError as exc:
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


def _telemetry_routes(router: APIRouter, service: IotService) -> None:
    @router.get("/status")
    async def status() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await service.status()

    @router.get("/telemetry/latest")
    async def latest(  # pyright: ignore[reportUnusedFunction]
        source: Annotated[str, Query(max_length=128)] = "",
    ) -> list[dict[str, Any]]:
        return await _run(service.latest(source))

    @router.get("/telemetry/series")
    async def series(  # pyright: ignore[reportUnusedFunction]
        source: Annotated[str, _SOURCE],
        key: Annotated[str, _KEY],
        minutes: Annotated[float, Query(gt=0, le=60 * 24 * 366)] = 60,
        limit: Annotated[int, Query(ge=1, le=5000)] = 500,
    ) -> list[dict[str, Any]]:
        return await _run(service.series(source, key, minutes, limit))

    @router.post("/telemetry/record", status_code=201)
    async def record(body: RecordIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        values = dict(body.values)
        if body.key is not None and body.value is not None:
            values[body.key] = body.value
        if not values:
            raise HTTPException(422, detail="values yoki key + value kerak")
        source = f"manual:{body.source}"
        service.record(source, values, body.ts)
        return {"source": source, "recorded": len(values)}

    @router.post("/telemetry/purge")
    async def purge() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.purge())


def _mqtt_routes(router: APIRouter, service: IotService) -> None:
    @router.get("/mqtt/log")
    async def mqtt_log(  # pyright: ignore[reportUnusedFunction]
        tail: Annotated[int, Query(ge=1, le=MESSAGES_KEPT)] = 100,
    ) -> list[str]:
        return service.message_lines(tail)

    @router.get("/mqtt/messages")
    async def mqtt_messages(  # pyright: ignore[reportUnusedFunction]
        tail: Annotated[int, Query(ge=1, le=MESSAGES_KEPT)] = 100,
    ) -> list[dict[str, Any]]:
        return list(service.messages)[-tail:]

    @router.get("/mqtt/subscriptions")
    async def subscriptions() -> list[dict[str, str]]:  # pyright: ignore[reportUnusedFunction]
        return service.subscriptions()

    @router.post("/mqtt/publish")
    async def publish(body: PublishIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return _call(service.publish, body.topic, body.payload, body.qos, body.retain)

    @router.post("/mqtt/subscribe")
    async def subscribe(body: TopicIn) -> list[dict[str, str]]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.subscribe(body.topic))

    @router.post("/mqtt/unsubscribe")
    async def unsubscribe(body: TopicIn) -> list[dict[str, str]]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.unsubscribe(body.topic))


def _serial_routes(router: APIRouter, service: IotService) -> None:
    @router.get("/serial/ports")
    async def ports() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return await service.serial_ports()

    @router.post("/serial/open")
    async def open_port(body: SerialOpenIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.open_serial(body.port, body.baudrate))

    @router.post("/serial/close")
    async def close_port(body: SerialPortIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.close_serial(body.port))

    @router.post("/serial/write")
    async def write_port(body: SerialWriteIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.write_serial(body.port, body.text, body.newline))

    @router.get("/serial/lines")
    async def lines(  # pyright: ignore[reportUnusedFunction]
        port: Annotated[str, Query(min_length=1, max_length=64)],
        tail: Annotated[int, Query(ge=1, le=300)] = 100,
    ) -> list[str]:
        return _call(service.serial_lines, port, tail)


def _modbus_routes(router: APIRouter, service: IotService) -> None:
    @router.get("/modbus")
    async def devices() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return [service.pollers[name].describe() for name in sorted(service.pollers)]

    @router.post("/modbus", status_code=201)
    async def add_device(device: ModbusDevice) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.add_modbus(device))

    @router.post("/modbus/remove")
    async def remove_device(body: DeviceIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.remove_modbus(body.name))

    @router.post("/modbus/poll")
    async def poll_device(body: DeviceIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.poll_modbus(body.name))

    @router.post("/modbus/write")
    async def write_device(body: ModbusWriteIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.write_modbus(body.name, body.key, body.value))


@hookimpl
def srv1_router(ctx: PluginContext) -> APIRouter:
    router = APIRouter()
    service = _service(ctx)
    _telemetry_routes(router, service)
    _mqtt_routes(router, service)
    _serial_routes(router, service)
    _modbus_routes(router, service)
    return router
