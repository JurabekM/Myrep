"""Logging configuration with a rotating file handler and secret redaction."""

from __future__ import annotations

import logging
import logging.handlers
import re
import sys
from pathlib import Path

_SECRET_PATTERNS = [
    re.compile(r"(?i)(bot)?token[\"'\s:=]+([A-Za-z0-9:_\-\.]{8,})"),
    re.compile(r"(?i)api[_-]?key[\"'\s:=]+([A-Za-z0-9\-_\.]{8,})"),
    re.compile(r"(?i)(password|secret|auth_token)[\"'\s:=]+(\S{4,})"),
    re.compile(r"(?i)bearer\s+([A-Za-z0-9\-_\.]{8,})"),
]


class SecretRedactingFilter(logging.Filter):
    """Replace anything that looks like a credential with ``***``."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D102
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover
            return True
        redacted = message
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub(lambda m: m.group(0).replace(m.groups()[-1], "***"), redacted)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def setup_logging(logs_dir: Path, level: str = "INFO") -> logging.Logger:
    """Configure the root logger; returns the application logger."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    for handler in list(root.handlers):
        root.removeHandler(handler)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    redactor = SecretRedactingFilter()

    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "leadpilot.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.addFilter(redactor)
    root.addHandler(file_handler)

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    stream.addFilter(redactor)
    root.addHandler(stream)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    return logging.getLogger("leadpilot")


def install_excepthook(logger: logging.Logger) -> None:
    """Route uncaught exceptions to the log instead of crashing silently."""

    def _hook(exc_type, exc_value, exc_tb):  # type: ignore[no-untyped-def]
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _hook
