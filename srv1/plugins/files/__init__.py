"""`files` plagini: papka kuzatuvi, indeks, nom bo'yicha qidiruv, asosiy amallar va savat.

Kuzatiladigan papkalar `plugin.toml` dagi `permissions.paths` da; plaginning
o'z `library` papkasi (0-ildiz) har doim bor. Yo'llar API'da `(root, path)`
juftligi bilan beriladi: `root` — ildiz raqami, `path` — ildizga nisbatan.
"""

from collections.abc import Awaitable
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from srv1_sdk.context import PluginContext
from srv1_sdk.hookspec import hookimpl
from srv1_sdk.panel import PanelSpec
from srv1_sdk.types import Job

from .panel import build_panel
from .service import FileOpError, FilesService

RESCAN_INTERVAL_S = 6 * 3600.0
RelPath = Annotated[str, Field(max_length=1024)]

_services: dict[str, FilesService] = {}


def _service(ctx: PluginContext) -> FilesService:
    if ctx.name not in _services:
        _services[ctx.name] = FilesService(ctx)
    return _services[ctx.name]


class PathIn(BaseModel):
    root: int = Field(ge=0)
    path: RelPath


class RenameIn(PathIn):
    new_name: str = Field(min_length=1, max_length=255)


class TransferIn(PathIn):
    dest_root: int = Field(ge=0)
    dest_path: RelPath = ""


class TrashIn(BaseModel):
    id: int


async def _run[T](operation: Awaitable[T]) -> T:
    """`FileOpError` ni tegishli HTTP kodiga aylantiradi."""
    try:
        return await operation
    except FileOpError as exc:
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
def srv1_jobs(ctx: PluginContext) -> list[Job]:
    async def rescan() -> None:
        await _service(ctx).rescan()

    return [Job(id="rescan", func=rescan, interval_s=RESCAN_INTERVAL_S)]


@hookimpl
def srv1_panel(ctx: PluginContext) -> PanelSpec:
    return build_panel()


@hookimpl
def srv1_router(ctx: PluginContext) -> APIRouter:
    router = APIRouter()
    service = _service(ctx)

    @router.get("/status")
    async def status() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.status())

    @router.get("/roots")
    async def roots() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.list_roots())

    @router.get("/list")
    async def list_dir(root: int = 0, path: str = "") -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.list_dir(root, path))

    @router.get("/search")
    async def search(  # pyright: ignore[reportUnusedFunction]
        q: Annotated[str, Query(max_length=200)] = "",
        ext: Annotated[str, Query(max_length=20)] = "",
        root: int | None = None,
        min_size: Annotated[int | None, Query(ge=0)] = None,
        max_size: Annotated[int | None, Query(ge=0)] = None,
        limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    ) -> list[dict[str, Any]]:
        return await _run(
            service.search(q, ext=ext, root=root, min_size=min_size, max_size=max_size, limit=limit)
        )

    @router.post("/rescan")
    async def rescan() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.rescan())

    @router.post("/mkdir", status_code=201)
    async def mkdir(body: PathIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.mkdir(body.root, body.path))

    @router.post("/rename")
    async def rename(body: RenameIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.rename(body.root, body.path, body.new_name))

    @router.post("/move")
    async def move(body: TransferIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(
            service.transfer(body.root, body.path, body.dest_root, body.dest_path, copy=False)
        )

    @router.post("/copy", status_code=201)
    async def copy(body: TransferIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(
            service.transfer(body.root, body.path, body.dest_root, body.dest_path, copy=True)
        )

    @router.post("/delete")
    async def delete(body: PathIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        """Savatga ko'chiradi (tiklash mumkin)."""
        return await _run(service.trash(body.root, body.path))

    @router.post("/unlink")
    async def unlink(body: PathIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        """Simvolik havola yoki junction'ning o'zini olib tashlaydi (nishon qoladi)."""
        return await _run(service.unlink(body.root, body.path))

    @router.get("/trash")
    async def trash() -> list[dict[str, Any]]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.list_trash())

    @router.post("/trash/restore")
    async def restore(body: TrashIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.restore(body.id))

    @router.post("/trash/purge")
    async def purge(body: TrashIn) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.purge(body.id))

    @router.delete("/trash")
    async def empty_trash() -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        return await _run(service.purge(None))

    return router
