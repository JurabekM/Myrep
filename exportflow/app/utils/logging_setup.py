"""Rotating file + console logging with secret redaction."""

from __future__ import annotations

import logging
import logging.handlers
import re
import sys

from app.config import PATHS

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization)\s*[=:]\s*\"?([^\s\"',}]+)"),
    re.compile(r"(?i)(sk-[A-Za-z0-9_\-]{8,})"),
]


class RedactingFilter(logging.Filter):
    """Strip credential-like substrings before anything reaches a log sink."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            return True
        redacted = message
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub(lambda m: f"{m.group(1)}=***", redacted)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the root logger once; safe to call repeatedly."""
    global _CONFIGURED
    logger = logging.getLogger()
    if _CONFIGURED:
        return logger

    PATHS.ensure()
    logger.setLevel(level)
    formatter = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    file_handler = logging.handlers.RotatingFileHandler(
        PATHS.logs_dir / "exportflow.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(RedactingFilter())
    logger.addHandler(file_handler)

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    stream.addFilter(RedactingFilter())
    logger.addHandler(stream)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    _CONFIGURED = True
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger."""
    return logging.getLogger(name)
