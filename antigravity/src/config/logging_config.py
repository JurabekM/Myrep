"""Logging configuration for the Enterprise ERP platform.

Provides a :func:`setup_logging` function that configures the Python
standard-library logging system with:

- A **console handler** for immediate terminal feedback.
- A **rotating file handler** that caps individual log files at 10 MB
  and retains up to 5 historical backups.

Both handlers share a unified format::

    2026-01-15 14:30:00,123 - module_name - INFO - Log message here

Usage::

    from src.config.logging_config import setup_logging

    setup_logging(log_level='DEBUG')

A convenience :func:`get_logger` wrapper is also provided for modules
that need a named logger.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# Default format shared by all handlers
_LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
"""Standard log record format string."""

_LOG_DATE_FORMAT: str = '%Y-%m-%d %H:%M:%S'
"""Date format used within log records."""


def setup_logging(
    log_dir: Optional[str] = None,
    log_level: str = 'INFO',
    log_file: str = 'erp.log',
) -> logging.Logger:
    """Configure application-wide logging with console and file output.

    Sets up the root logger with two handlers:

    1. **StreamHandler** — writes to ``stderr`` for console visibility.
    2. **RotatingFileHandler** — writes to *log_dir*/*log_file*, rotating
       at 10 MB with 5 backup copies retained.

    If the log directory does not exist it is created automatically.

    Args:
        log_dir: Directory for log files.  When ``None``, defaults to
            ``<project_root>/data/logs`` (via :func:`~src.core.utils.get_log_dir`).
        log_level: Logging level name (e.g. ``'DEBUG'``, ``'INFO'``,
            ``'WARNING'``, ``'ERROR'``, ``'CRITICAL'``).
        log_file: Name of the log file within *log_dir*.

    Returns:
        The configured root :class:`logging.Logger`.
    """
    # Resolve log directory
    if log_dir is None:
        # Lazy import to avoid circular dependency at module level
        from src.core.utils import get_log_dir
        log_path = get_log_dir()
    else:
        log_path = Path(log_dir)

    log_path.mkdir(parents=True, exist_ok=True)

    # Resolve numeric log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Prevent duplicate handlers on repeated calls
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter(
        fmt=_LOG_FORMAT,
        datefmt=_LOG_DATE_FORMAT,
    )

    # Console handler
    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Rotating file handler — 10 MB max, keep 5 backups
    file_handler = RotatingFileHandler(
        filename=str(log_path / log_file),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8',
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    root_logger.debug(
        'Logging configured: level=%s, file=%s',
        log_level.upper(),
        log_path / log_file,
    )

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Obtain a named logger.

    Convenience wrapper around :func:`logging.getLogger` for use by
    application modules.

    Args:
        name: Logger name — typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)
