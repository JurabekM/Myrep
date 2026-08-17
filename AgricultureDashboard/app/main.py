"""NiceGUI application assembly and launch."""
from __future__ import annotations

import logging

from config import settings

log = logging.getLogger(__name__)


def start(host: str = settings.DEFAULT_HOST, port: int = settings.DEFAULT_PORT,
          open_browser: bool = True, debug: bool = False) -> None:
    """Register pages, API, plugins and background jobs, then run the server."""
    from nicegui import ui

    import dashboard.pages  # noqa: F401 - registers every @ui.page route
    from api.routes import register_api
    from core import background
    from core.plugin_manager import load_plugins

    register_api()
    load_plugins()
    background.start_default_jobs()

    log.info("Dashboard ishga tushmoqda: http://%s:%d", host, port)
    ui.run(
        host=host,
        port=port,
        title=settings.APP_TITLE,
        favicon="🌾",
        storage_secret=settings.get_storage_secret(),
        reload=False,
        show=open_browser,
        uvicorn_logging_level="warning",
    )
