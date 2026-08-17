"""Application bootstrap: logging, database, seeding and the Qt application."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from app.config import APP_NAME, APP_VERSION, ORG_NAME, load_config
from app.database.engine import get_engine, init_engine
from app.database.migrations import run_migrations
from app.database.seed import seed_all
from app.services import auth_service, integration_service
from app.ui.styles import theme
from app.utils.logging_setup import install_excepthook, setup_logging

logger = logging.getLogger("leadpilot")


def init_backend(seed_demo: bool = True) -> None:
    """Prepare logging, the database schema and the demo dataset."""
    config = load_config()
    global logger
    logger = setup_logging(config.logs_dir, config.log_level)
    install_excepthook(logger)
    logger.info("%s v%s starting", APP_NAME, APP_VERSION)

    init_engine(config.database_url)
    applied = run_migrations(get_engine())
    if applied:
        logger.info("Applied migrations: %s", ", ".join(applied))

    from app.database.engine import session_scope

    with session_scope() as session:
        auth_service.ensure_roles(session)

    if seed_demo:
        try:
            if seed_all():
                logger.info("Demo dataset created")
        except Exception:
            logger.exception("Demo seeding failed — continuing with an empty database")

    try:
        integration_service.ensure_default_configs()
    except Exception:
        logger.exception("Integration defaults could not be created")


def create_application(argv: list[str] | None = None) -> QApplication:
    """Create and theme the Qt application."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    application = QApplication(argv or [])
    application.setApplicationName(APP_NAME)
    application.setApplicationVersion(APP_VERSION)
    application.setOrganizationName(ORG_NAME)
    application.setStyle("Fusion")
    application.setFont(QFont(theme.pick_font(), 10))
    application.setStyleSheet(theme.build_stylesheet())
    try:
        application.setWindowIcon(theme.icon("fa6s.rocket", theme.ACCENT))
    except Exception:  # pragma: no cover - icon is cosmetic
        application.setWindowIcon(QIcon())
    return application
