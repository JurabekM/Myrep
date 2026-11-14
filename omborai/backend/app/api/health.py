from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Jarayon tirik ekanini tekshiradi (liveness)."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(session: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Ma'lumotlar bazasi bilan aloqa bor-yo'qligini tekshiradi (readiness)."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - har qanday ulanish xatosi "tayyor emas" degani
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return JSONResponse({"status": "ready"})
