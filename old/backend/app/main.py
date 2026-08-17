"""FastAPI application factory."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import Settings, get_settings
from app.core.dependencies import build_container, shutdown_container
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware
from app.infrastructure.database.indexes import ensure_indexes
from app.infrastructure.database.migrations import run_migrations

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_output=settings.environment != "development")

    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = await build_container(settings)
        await ensure_indexes(container.mongo)
        applied = await run_migrations(container.mongo)
        logger.info("startup_complete", migrations_applied=applied)
        app.state.container = container
        yield
        await shutdown_container(container)

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        docs_url="/docs" if settings.environment != "production" else None,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    # RateLimitMiddleware needs redis from the container; it resolves lazily
    # through app.state at request time via a thin wrapper.
    app.add_middleware(_LazyRateLimit, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    _register_routers(app, settings)
    return app


class _LazyRateLimit:
    """ASGI wrapper that instantiates RateLimitMiddleware once the container
    (and thus Redis) exists on app.state."""

    def __init__(self, app, settings: Settings):  # type: ignore[no-untyped-def]
        self._app = app
        self._settings = settings
        self._inner = None

    async def __call__(self, scope, receive, send):  # type: ignore[no-untyped-def]
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        if self._inner is None:
            container = scope["app"].state.container
            self._inner = RateLimitMiddleware(self._app, container.redis, self._settings)
        await self._inner(scope, receive, send)


def _register_routers(app: FastAPI, settings: Settings) -> None:
    from app.modules.admin.router import router as admin_router
    from app.modules.auth.router import router as auth_router
    from app.modules.chat.router import router as chat_router
    from app.modules.consultant.router import router as consultant_router
    from app.modules.dashboard.router import router as dashboard_router
    from app.modules.documents.router import router as documents_router
    from app.modules.finance.router import router as finance_router
    from app.modules.legal.router import router as legal_router
    from app.modules.marketing.router import router as marketing_router
    from app.modules.tax.router import router as tax_router

    prefix = settings.api_v1_prefix
    app.include_router(auth_router, prefix=prefix)
    app.include_router(chat_router, prefix=prefix)
    app.include_router(consultant_router, prefix=prefix)
    app.include_router(legal_router, prefix=prefix)
    app.include_router(tax_router, prefix=prefix)
    app.include_router(marketing_router, prefix=prefix)
    app.include_router(documents_router, prefix=prefix)
    app.include_router(finance_router, prefix=prefix)
    app.include_router(dashboard_router, prefix=prefix)
    app.include_router(admin_router, prefix=prefix)


app = create_app()
