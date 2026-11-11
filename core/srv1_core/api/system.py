"""Tizim holati: `/system`, jarayonlar bo'yicha xotira va oxirgi log yozuvlari."""

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Query

from srv1_core.log_setup import LOG_BUFFER_SIZE
from srv1_core.state import Core
from srv1_core.system import ProcessReport, SystemSnapshot, process_report, take_snapshot

router = APIRouter(tags=["system"])


@router.get("/system")
async def system() -> SystemSnapshot:
    return await asyncio.to_thread(take_snapshot)


@router.get("/system/processes")
async def processes(core: Core) -> ProcessReport:
    """Yadro va alohida jarayondagi plaginlar xotirasi (shell o'zini o'zi qo'shadi)."""
    return await asyncio.to_thread(process_report, core.plugins.process_ids())


@router.get("/logs")
async def logs(
    core: Core, tail: Annotated[int, Query(ge=1, le=LOG_BUFFER_SIZE)] = 200
) -> list[dict[str, Any]]:
    """Oxirgi log yozuvlari (INFO va yuqori). Jonli oqim: `log` mavzusi."""
    return core.logs.tail(tail)
