"""Jurnal: structlog -> JSON qatorlar, aylanuvchi fayl `logs/srv1.log`."""

import asyncio
import json
import logging
import sys
import threading
from collections import deque
from collections.abc import Callable, Mapping
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import structlog
from structlog.typing import Processor

from srv1_core.settings import LoggingSettings

LOG_FILE_NAME = "srv1.log"
LOG_TOPIC = "log"
LOG_BUFFER_SIZE = 500
_HANDLER_TAG = "_srv1_handler"


def _shared_processors() -> list[Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.format_exc_info,
    ]


def _formatter(renderer: Processor) -> structlog.stdlib.ProcessorFormatter:
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_shared_processors(),
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
    )


def _install(handler: logging.Handler, renderer: Processor) -> None:
    handler.setFormatter(_formatter(renderer))
    setattr(handler, _HANDLER_TAG, True)
    logging.getLogger().addHandler(handler)


def configure_logging(logs_dir: Path, cfg: LoggingSettings, *, console: bool = False) -> Path:
    """Jurnalni sozlaydi va fayl yo'lini qaytaradi. Qayta chaqirish xavfsiz."""
    shutdown_logging()
    structlog.configure(
        processors=[
            *_shared_processors(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    log_file = logs_dir / LOG_FILE_NAME
    file_handler = RotatingFileHandler(
        log_file, maxBytes=cfg.max_bytes, backupCount=cfg.backup_count, encoding="utf-8"
    )
    _install(file_handler, structlog.processors.JSONRenderer(ensure_ascii=False))
    if console:
        _install(logging.StreamHandler(sys.stderr), structlog.dev.ConsoleRenderer(colors=False))
    logging.getLogger().setLevel(cfg.level)
    return log_file


class BusLogHandler(logging.Handler):
    """Log yozuvlarini hodisalar shinasiga chiqaradi va oxirgilarini xotirada saqlaydi.

    DEBUG yozuvlari chiqarilmaydi: aks holda WebSocket'ning o'z DEBUG loglari
    cheksiz halqa hosil qiladi.
    """

    def __init__(self, publish: Callable[[str, Mapping[str, Any]], object]) -> None:
        super().__init__(level=logging.INFO)
        self._publish = publish
        self._loop = asyncio.get_running_loop()
        self._loop_thread = threading.get_ident()
        self._recent: deque[dict[str, Any]] = deque(maxlen=LOG_BUFFER_SIZE)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry: dict[str, Any] = json.loads(self.format(record))
        except Exception:  # log yozish hech qachon dasturni yiqitmasin
            return
        self._recent.append(entry)
        if threading.get_ident() == self._loop_thread:
            self._publish(LOG_TOPIC, entry)
        elif not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._publish, LOG_TOPIC, entry)

    def tail(self, count: int) -> list[dict[str, Any]]:
        recent = list(self._recent)
        return recent[-count:] if count < len(recent) else recent


def attach_bus_handler(publish: Callable[[str, Mapping[str, Any]], object]) -> BusLogHandler:
    """Event loop ichidan chaqiriladi. `shutdown_logging` uni ham olib tashlaydi."""
    handler = BusLogHandler(publish)
    _install(handler, structlog.processors.JSONRenderer(ensure_ascii=False, default=str))
    return handler


def shutdown_logging() -> None:
    """O'zimiz o'rnatgan handlerlarni yopadi (Windows'da fayl qulfini bo'shatadi)."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_TAG, False):
            root.removeHandler(handler)
            handler.close()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.stdlib.get_logger(name)
