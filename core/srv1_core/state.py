"""Yadroning ish vaqtidagi holati va FastAPI bog'liqliklari."""

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, FastAPI, HTTPException, status
from starlette.requests import HTTPConnection

from srv1_core.audit import AuditLogger
from srv1_core.auth import TokenAuth
from srv1_core.db import Database
from srv1_core.events import EventBus
from srv1_core.paths import DataPaths
from srv1_core.plugins.registry import PluginRegistry
from srv1_core.settings import Settings


@dataclass(frozen=True, slots=True)
class CoreState:
    paths: DataPaths
    settings: Settings
    db: Database
    bus: EventBus
    auth: TokenAuth
    audit: AuditLogger
    plugins: PluginRegistry
    started_at: float  # time.monotonic()


def get_core_from_app(app: FastAPI) -> CoreState:
    return cast(CoreState, app.state.core)


def get_core(conn: HTTPConnection) -> CoreState:
    return cast(CoreState, conn.app.state.core)


Core = Annotated[CoreState, Depends(get_core)]


def require_token(conn: HTTPConnection, core: Core) -> None:
    if not core.auth.verify_header(conn.headers.get("authorization")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token yo'q yoki noto'g'ri",
            headers={"WWW-Authenticate": "Bearer"},
        )
