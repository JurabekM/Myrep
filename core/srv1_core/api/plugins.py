"""Plaginlar API'si: ro'yxat, yoqish/o'chirish, panel va plaginning o'z API'siga dispetcher."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request, Response, status

from srv1_core.plugins.registry import PluginInfo, PluginNotFoundError, PluginUnavailableError
from srv1_core.state import Core
from srv1_sdk.manifest import NAME_PATTERN
from srv1_sdk.panel import PanelSpec

router = APIRouter(prefix="/plugins", tags=["plugins"])

MAX_REQUEST_BODY_BYTES = 1024 * 1024
_FORWARDED_REQUEST_HEADERS = ("content-type", "accept")
_PAYLOAD_TOO_LARGE = 413
_ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

PluginName = Annotated[str, Path(pattern=NAME_PATTERN)]


def _not_found(exc: PluginNotFoundError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc.args[0]))


def _conflict(exc: PluginUnavailableError) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("")
async def list_plugins(core: Core) -> list[PluginInfo]:
    return core.plugins.list()


@router.get("/{name}")
async def get_plugin(name: PluginName, core: Core) -> PluginInfo:
    try:
        return core.plugins.get(name)
    except PluginNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/{name}/enable")
async def enable_plugin(name: PluginName, core: Core) -> PluginInfo:
    try:
        return await core.plugins.enable(name)
    except PluginNotFoundError as exc:
        raise _not_found(exc) from exc
    except PluginUnavailableError as exc:
        raise _conflict(exc) from exc


@router.post("/{name}/disable")
async def disable_plugin(name: PluginName, core: Core) -> PluginInfo:
    try:
        return await core.plugins.disable(name)
    except PluginNotFoundError as exc:
        raise _not_found(exc) from exc
    except PluginUnavailableError as exc:
        raise _conflict(exc) from exc


@router.get("/{name}/panel")
async def plugin_panel(name: PluginName, core: Core) -> PanelSpec:
    try:
        return core.plugins.panel(name)
    except PluginNotFoundError as exc:
        raise _not_found(exc) from exc
    except PluginUnavailableError as exc:
        raise _conflict(exc) from exc


async def _read_body(request: Request) -> bytes:
    declared = request.headers.get("content-length", "0")
    if declared.isdigit() and int(declared) > MAX_REQUEST_BODY_BYTES:
        raise HTTPException(_PAYLOAD_TOO_LARGE, detail="so'rov tanasi katta")
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_REQUEST_BODY_BYTES:
            raise HTTPException(_PAYLOAD_TOO_LARGE, detail="so'rov tanasi katta")
    return bytes(body)


@router.api_route("/{name}/api/{path:path}", methods=_ALL_METHODS, include_in_schema=False)
async def plugin_api(name: PluginName, path: str, request: Request, core: Core) -> Response:
    """Plaginning o'z API'si. Plaginga token uzatilmaydi; o'chiq plagin — 409."""
    body = await _read_body(request)
    headers = [
        (key, request.headers[key]) for key in _FORWARDED_REQUEST_HEADERS if key in request.headers
    ]
    try:
        reply = await core.plugins.request(
            name,
            method=request.method,
            path="/" + path,
            query=request.url.query.encode("latin-1", "replace"),
            headers=headers,
            body=body,
        )
    except PluginNotFoundError as exc:
        raise _not_found(exc) from exc
    except PluginUnavailableError as exc:
        raise _conflict(exc) from exc
    return Response(content=reply.body, status_code=reply.status, media_type=reply.content_type)
