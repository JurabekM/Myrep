"""`GET /api/v1/health` — tokensiz, faqat tiriklik belgisi."""

import time
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from srv1_core import __version__
from srv1_core.state import Core

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: Literal["ok"]
    version: str
    uptime_s: float


@router.get("/health")
async def health(core: Core) -> Health:
    uptime = round(time.monotonic() - core.started_at, 3)
    return Health(status="ok", version=__version__, uptime_s=uptime)
