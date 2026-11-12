"""Yadro API marshrutlari."""

from fastapi import APIRouter, Depends

from srv1_core.api import health, plugins, system, ws
from srv1_core.state import require_token

API_PREFIX = "/api/v1"


def build_router() -> APIRouter:
    router = APIRouter()
    router.include_router(health.router, prefix=API_PREFIX)
    router.include_router(system.router, prefix=API_PREFIX, dependencies=[Depends(require_token)])
    router.include_router(plugins.router, prefix=API_PREFIX, dependencies=[Depends(require_token)])
    router.include_router(ws.router)
    return router
