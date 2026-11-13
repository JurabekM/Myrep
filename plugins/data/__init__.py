"""`data` plagini: CSV/Parquet/Excel import, DuckDB so'rovlari, hisobot va eksport.

Og'ir plagin: alohida jarayonda, RAM limiti bilan, standart holatda o'chiq.
Import qilingan har to'plam SQL'da o'z nomi bilan jadval bo'lib ko'rinadi
(`SELECT * FROM sotuvlar`). So'rovlar faqat o'qiydi va faqat shu to'plamlar ustida.
"""

from collections.abc import Awaitable
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from srv1_sdk.context import PluginContext
from srv1_sdk.hookspec import hookimpl
from srv1_sdk.panel import PanelSpec

from .models import NAME_PATTERN, Encoding
from .panel import build_panel
from .service import DataError, DataService

_services: dict[str, DataService] = {}
SQL_MAX_CHARS = 20_000
Name = Annotated[str, Field(pattern=NAME_PATTERN)]


def _service(ctx: PluginContext) -> DataService:
    if ctx.name not in _services:
        _services[ctx.name] = DataService(ctx)
    return _services[ctx.name]


class ImportIn(BaseModel):
    path: str = Field(min_length=1, max_length=1024)
    name: str = Field(default="", pattern=r"^([a-z][a-z0-9_]{0,47})?$")
    encoding: Encoding = "auto"
    separator: str = Field(default="", max_length=1)
    sheet: str = Field(default="", max_length=64)


class NameIn(BaseModel):
    name: Name


class QueryIn(BaseModel):
    sql: str = Field(min_length=1, max_length=SQL_MAX_CHARS)
    limit: int = Field(default=200, ge=1, le=5000)
    offset: int = Field(default=0, ge=0, le=10_000_000)


class SaveIn(BaseModel):
    sql: str = Field(min_length=1, max_length=SQL_MAX_CHARS)
    name: Name


async def _run[T](operation: Awaitable[T]) -> T:
    try:
        return await operation
    except DataError as exc:
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

    @router.get("/datasets")
    async def datasets() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return service.list_datasets()

    @router.get("/inbox")
    async def inbox() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return await service.list_inbox()

    @router.post("/import", status_code=202)
    async def import_file(body: ImportIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(
            service.start_import(body.path, body.name, body.encoding, body.separator, body.sheet)
        )

    @router.post("/remove")
    async def remove(body: NameIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.remove(body.name))

    @router.get("/schema")
    async def schema(name: Annotated[str, Query(pattern=NAME_PATTERN)]) -> list[dict[str, str]]:  # pyright: ignore[reportUnusedFunction]
        try:
            return service.schema(name)
        except DataError as exc:
            raise HTTPException(exc.status, detail=exc.detail) from exc

    @router.get("/preview")
    async def preview(  # pyright: ignore[reportUnusedFunction]
        name: Annotated[str, Query(pattern=NAME_PATTERN)],
        limit: Annotated[int, Query(ge=1, le=1000)] = 50,
    ) -> dict[str, Any]:
        return await _run(service.preview(name, limit))

    @router.get("/profile")
    async def profile(name: Annotated[str, Query(pattern=NAME_PATTERN)]) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.profile(name))

    @router.post("/query")
    async def query(body: QueryIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.query(body.sql, body.limit, body.offset))

    @router.post("/export", status_code=201)
    async def export(body: SaveIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.export(body.sql, body.name))

    @router.post("/save", status_code=201)
    async def save(body: SaveIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.save_as(body.sql, body.name))

    return router
