"""FastAPI ilovasi (ADR-0011): auth, RBAC, sinxronlash, ochiq tekshirish sahifasi, kuzatuv."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from zanjir_server import __version__
from zanjir_server.api import auth, org, public, sync
from zanjir_server.api.deps import AppContext
from zanjir_server.config import Settings, get_settings
from zanjir_server.db.session import Database
from zanjir_server.middleware import (
    AccessLogMiddleware,
    BodyLimitMiddleware,
    RateLimiter,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from zanjir_server.observability import ErrorReporter, Metrics, NullErrorReporter, configure_logging
from zanjir_server.otp import DisabledOtpSender
from zanjir_server.security.login_guard import LoginGuard
from zanjir_server.security.passwords import Passwords
from zanjir_server.security.tokens import AccessTokens

# Barcha marshrutlar (prefikssiz ulanadi) — RBAC matritsasi testi shu ro'yxatni to'liq tekshiradi.
ROUTERS = (auth.router, auth.me_router, org.router, sync.router, public.router)


def create_app(
    settings: Settings | None = None,
    *,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    reporter: ErrorReporter | None = None,
    rate_limiter: RateLimiter | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    metrics = Metrics()
    db = Database(settings.database_url.get_secret_value())

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await db.dispose()

    app = FastAPI(
        title="ZANJIR", version=__version__, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
    )
    app.state.ctx = AppContext(
        settings=settings,
        db=db,
        passwords=Passwords(settings.argon2),
        tokens=AccessTokens(settings.jwt_secret.get_secret_value(), settings.access_ttl_seconds, clock),
        otp=DisabledOtpSender(),
        metrics=metrics,
        clock=clock,
        login_guard=LoginGuard(
            settings.login_failures_max,
            settings.login_failures_window_seconds,
            lambda: clock().timestamp(),
        ),
    )
    for r in ROUTERS:
        app.include_router(r)
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "web" / "static"), name="static")

    # Tartib: tashqi qatlam oxirida qo'shiladi (log → rate limit → hajm → CORS → ilova).
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["authorization", "content-type"],
        )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_middleware(
        RateLimitMiddleware,
        limiter=rate_limiter or RateLimiter(),
        auth_limit=settings.rate_limit_auth_per_minute,
        default_limit=settings.rate_limit_default_per_minute,
    )
    app.add_middleware(AccessLogMiddleware, metrics=metrics, reporter=reporter or NullErrorReporter())
    return app


def app() -> FastAPI:
    """`uvicorn --factory zanjir_server.main:app` — sozlamalar muhitdan."""
    return create_app()
