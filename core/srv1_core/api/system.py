"""Tizim holati: `/system`, jarayonlar xotirasi, oxirgi log yozuvlari, serverni to'xtatish."""

import asyncio
import os
import time
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel

from srv1_core import __version__
from srv1_core.lifecycle import ManagedBy, get_exit_hook, managed_by
from srv1_core.log_setup import LOG_BUFFER_SIZE
from srv1_core.state import Core
from srv1_core.system import ProcessReport, SystemSnapshot, process_report, take_snapshot

router = APIRouter(tags=["system"])
# Javob klientga yetib borishi uchun to'xtatish shuncha kechiktiriladi.
SHUTDOWN_DELAY_S = 0.3


class ServerInfo(BaseModel):
    version: str
    pid: int
    uptime_s: float
    managed_by: ManagedBy
    # Xizmat ostida `False`: NSSM yadroni qayta ko'taradi, shuning uchun xizmatni to'xtatish kerak.
    can_shutdown: bool


class ShutdownReply(BaseModel):
    status: Literal["stopping"]


@router.get("/system")
async def system() -> SystemSnapshot:
    return await asyncio.to_thread(take_snapshot)


@router.get("/system/processes")
async def processes(core: Core) -> ProcessReport:
    """Yadro va alohida jarayondagi plaginlar xotirasi (shell o'zini o'zi qo'shadi)."""
    return await asyncio.to_thread(process_report, core.plugins.process_ids())


@router.get("/system/server")
async def server(request: Request, core: Core) -> ServerInfo:
    owner = await asyncio.to_thread(managed_by)
    return ServerInfo(
        version=__version__,
        pid=os.getpid(),
        uptime_s=round(time.monotonic() - core.started_at, 3),
        managed_by=owner,
        can_shutdown=owner == "standalone" and get_exit_hook(request.app) is not None,
    )


@router.post("/system/shutdown", status_code=status.HTTP_202_ACCEPTED)
async def shutdown(request: Request, core: Core) -> ShutdownReply:
    """Yadroni tartibli to'xtatadi (plaginlar va ularning jarayonlari bilan). Auditga yoziladi."""
    owner = await asyncio.to_thread(managed_by)
    hook = get_exit_hook(request.app)
    if owner == "service" or hook is None:
        reason = "service" if owner == "service" else "no_exit_hook"
        await core.audit.record("core.shutdown", "api", ok=False, detail={"reason": reason})
        detail = (
            "yadro Windows xizmati sifatida ishlayapti: xizmatni to'xtating"
            if owner == "service"
            else "bu rejimda yadroni API orqali to'xtatib bo'lmaydi"
        )
        raise HTTPException(status.HTTP_409_CONFLICT, detail=detail)
    await core.audit.record("core.shutdown", "api", detail={"pid": os.getpid()})
    asyncio.get_running_loop().call_later(SHUTDOWN_DELAY_S, hook)
    return ShutdownReply(status="stopping")


@router.get("/logs")
async def logs(
    core: Core, tail: Annotated[int, Query(ge=1, le=LOG_BUFFER_SIZE)] = 200
) -> list[dict[str, Any]]:
    """Oxirgi log yozuvlari (INFO va yuqori). Jonli oqim: `log` mavzusi."""
    return core.logs.tail(tail)
