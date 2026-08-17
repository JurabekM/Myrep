"""Centralised logging configuration with rotating files and crash reports."""
from __future__ import annotations

import logging
import sys
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler

from config import settings

_configured = False


def setup_logging(debug: bool = False) -> logging.Logger:
    """Configure root logging once: console + rotating file + crash hook."""
    global _configured
    logger = logging.getLogger()
    if _configured:
        logger.setLevel(logging.DEBUG if debug else logging.INFO)
        return logger

    settings.ensure_directories()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        settings.LOG_DIR / "agrovision.log",
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    console.setLevel(logging.INFO if not debug else logging.DEBUG)
    logger.addHandler(console)

    # Quieten noisy third-party loggers.
    for noisy in ("watchfiles", "urllib3", "httpx", "matplotlib", "fontTools"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    sys.excepthook = _crash_hook
    _configured = True
    return logger


def _crash_hook(exc_type, exc_value, exc_tb) -> None:
    """Write an unhandled exception to a timestamped crash report file."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = settings.LOG_DIR / f"crash_{stamp}.txt"
    try:
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        report.write_text(
            f"{settings.APP_NAME} {settings.APP_VERSION} crash report\n"
            f"Time: {datetime.now().isoformat()}\n\n{text}",
            encoding="utf-8",
        )
    except OSError:
        pass
    logging.getLogger("crash").critical(
        "Unhandled exception", exc_info=(exc_type, exc_value, exc_tb)
    )
