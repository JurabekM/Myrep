"""Application start-up: paths, logging, migrations, seeding, maintenance."""

from __future__ import annotations

from app.config import APP_NAME, APP_VERSION, PATHS
from app.database.engine import session_scope
from app.database.migrations import run_migrations
from app.database.seed import initialise
from app.services import document_service, product_service, quotation_service, task_service
from app.utils.logging_setup import get_logger, setup_logging

log = get_logger(__name__)


def bootstrap(with_demo: bool = True) -> dict:
    """Prepare everything the UI needs before the main window is shown."""
    PATHS.ensure()
    setup_logging()
    log.info("Starting %s %s", APP_NAME, APP_VERSION)

    version = run_migrations()
    log.info("Database schema version: %s", version)

    state = initialise(with_demo=with_demo)
    maintenance = run_maintenance()
    log.info("Startup maintenance: %s", maintenance)
    return {"schema_version": version, **state, "maintenance": maintenance}


def run_maintenance() -> dict:
    """Refresh derived statuses and materialise the pending follow-up tasks."""
    result: dict[str, int] = {}
    try:
        with session_scope() as session:
            result["expired_prices"] = product_service.refresh_expired_prices(session)
            result["expired_quotations"] = quotation_service.refresh_expired_quotations(session)
            result["certificates"] = document_service.refresh_certificate_statuses(session)
            counters = task_service.run_follow_up_rules(session)
            result.update(counters)
    except Exception as exc:  # pragma: no cover - never block start-up
        log.exception("Maintenance failed: %s", type(exc).__name__)
        result["error"] = 1
    return result
