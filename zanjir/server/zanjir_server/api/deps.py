"""Umumiy bog'liqliklar: ilova konteksti, joriy foydalanuvchi, rol talabi, xato formati."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, NoReturn

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select

from zanjir_server.config import Settings
from zanjir_server.db.models import AppUser
from zanjir_server.db.session import Database
from zanjir_server.observability import Metrics
from zanjir_server.otp import OtpSender
from zanjir_server.security.passwords import Passwords
from zanjir_server.security.roles import Role
from zanjir_server.security.tokens import AccessTokens, TokenError


@dataclass
class AppContext:
    settings: Settings
    db: Database
    passwords: Passwords
    tokens: AccessTokens
    otp: OtpSender
    metrics: Metrics
    clock: Callable[[], datetime]

    def now(self) -> datetime:
        return self.clock().astimezone(UTC)


def fail(status: int, code: str, **extra: object) -> NoReturn:
    """Xato javobi: `{"detail": {"code": "...", ...}}` — `code` barqaror inglizcha kalit."""
    raise HTTPException(status, {"code": code, **extra})


def get_ctx(request: Request) -> AppContext:
    ctx: AppContext = request.app.state.ctx
    return ctx


Ctx = Annotated[AppContext, Depends(get_ctx)]


@dataclass(frozen=True)
class Principal:
    user_id: str
    org_id: str
    role: Role
    full_name: str
    safety_group: str | None = None


async def current_principal(request: Request, ctx: Ctx) -> Principal:
    """Bearer access token → foydalanuvchi. Rol bazadan olinadi (o'zgarishi darhol amal qiladi)."""
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        fail(401, "not_authenticated")
    try:
        claims = ctx.tokens.decode(token)
    except TokenError:
        fail(401, "invalid_token")
    async with ctx.db.org_session(claims.org_id) as s:
        user = (
            await s.execute(select(AppUser).where(AppUser.id == claims.user_id, AppUser.org_id == claims.org_id))
        ).scalar_one_or_none()
    if user is None or user.deleted:
        fail(401, "invalid_token")
    return Principal(
        user_id=user.id,
        org_id=user.org_id,
        role=Role(user.role),
        full_name=user.full_name,
        safety_group=user.safety_group,
    )


def require(min_role: Role) -> Callable[..., Awaitable[Principal]]:
    async def dep(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
        if not principal.role.at_least(min_role):
            fail(403, "forbidden_role")
        return principal

    dep.min_role = min_role  # type: ignore[attr-defined]  # RBAC matritsasi testi uchun
    return dep


Viewer = Annotated[Principal, Depends(require(Role.VIEWER))]
Engineer = Annotated[Principal, Depends(require(Role.ENGINEER))]
Lead = Annotated[Principal, Depends(require(Role.LEAD))]
Admin = Annotated[Principal, Depends(require(Role.ADMIN))]
