"""FastAPI ilovasini yig'ish va hayot sikli."""

import asyncio
import sys
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from srv1_core import __version__
from srv1_core.api import build_router
from srv1_core.audit import AuditLogger
from srv1_core.auth import TokenAuth, load_or_create_token, restrict_to_owner
from srv1_core.db import Database
from srv1_core.events import EventBus
from srv1_core.log_setup import configure_logging, get_logger, shutdown_logging
from srv1_core.paths import DataPaths
from srv1_core.settings import Settings, ensure_config_file, load_settings
from srv1_core.state import CoreState
from srv1_core.system import prime_cpu, take_snapshot

STATS_TOPIC = "system.stats"


def build_settings(paths: DataPaths) -> Settings:
    """Papkalarni yaratadi, kerak bo'lsa standart `config.toml` yozadi, sozlamalarni o'qiydi."""
    paths.ensure()
    ensure_config_file(paths.config_file)
    return load_settings(paths.config_file)


def _require_proactor() -> None:
    if sys.platform != "win32":
        return
    loop = asyncio.get_running_loop()
    if not isinstance(loop, asyncio.ProactorEventLoop):
        raise RuntimeError(
            f"Proactor event loop kerak (subprocess uchun), hozir: {type(loop).__name__}"
        )


async def _setup_auth(paths: DataPaths, audit: AuditLogger) -> TokenAuth:
    log = get_logger("srv1.auth")
    token, created = load_or_create_token(paths.token_file)
    if created:
        restricted = await restrict_to_owner(paths.token_file)
        await audit.record(
            "auth.token_created",
            str(paths.token_file),
            ok=restricted,
            detail={"acl_restricted": restricted},
        )
        if not restricted:
            log.warning("token_acl_not_restricted", path=str(paths.token_file))
    return TokenAuth(token)


async def _stats_loop(bus: EventBus, interval_s: float) -> None:
    """Obunachi bo'lsagina tizim holatini o'lchab, `system.stats` ga nashr qiladi."""
    log = get_logger("srv1.stats")
    while True:
        await asyncio.sleep(interval_s)
        if not bus.has_subscribers(STATS_TOPIC):
            continue
        try:
            snapshot = await asyncio.to_thread(take_snapshot)
        except Exception:
            log.exception("stats_snapshot_failed")
            continue
        bus.publish(STATS_TOPIC, snapshot.model_dump())


def create_app(
    paths: DataPaths, settings: Settings | None = None, *, console_log: bool = False
) -> FastAPI:
    cfg = settings if settings is not None else build_settings(paths)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        paths.ensure()
        configure_logging(paths.logs_dir, cfg.logging, console=console_log)
        log = get_logger("srv1.core")
        _require_proactor()
        db = Database(paths.db_file)
        await db.start()
        bus = EventBus(cfg.events.queue_size)
        audit = AuditLogger(db, bus)
        auth = await _setup_auth(paths, audit)
        prime_cpu()
        app.state.core = CoreState(
            paths=paths,
            settings=cfg,
            db=db,
            bus=bus,
            auth=auth,
            audit=audit,
            started_at=time.monotonic(),
        )
        stats = asyncio.create_task(_stats_loop(bus, cfg.events.stats_interval_s))
        log.info("core_started", version=__version__, data_dir=str(paths.root))
        try:
            yield
        finally:
            stats.cancel()
            with suppress(asyncio.CancelledError):
                await stats
            bus.close()
            await db.stop()
            log.info("core_stopped")
            shutdown_logging()

    app = FastAPI(
        title="SRV_1 yadrosi",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    # DNS rebinding'ga qarshi: faqat kutilgan Host sarlavhalari.
    allowed_hosts = sorted({"127.0.0.1", "localhost", "[::1]", cfg.server.host})
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    app.include_router(build_router())
    return app
