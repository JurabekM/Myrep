"""`GET /api/v1/system` — CPU, RAM, disk va yadro jarayoni holati."""

import asyncio

from fastapi import APIRouter

from srv1_core.system import SystemSnapshot, take_snapshot

router = APIRouter(tags=["system"])


@router.get("/system")
async def system() -> SystemSnapshot:
    return await asyncio.to_thread(take_snapshot)
