"""Structured JSON logging via structlog.

Every log line carries request_id (set by middleware) so a single request can
be traced across API, Celery and AI-provider calls.
"""

import logging
import sys

import structlog

_REQUEST_ID_KEY = "request_id"


def configure_logging(log_level: str = "INFO", *, json_output: bool = True) -> None:
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: structlog.types.Processor
    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )


def bind_request_id(request_id: str) -> None:
    structlog.contextvars.bind_contextvars(**{_REQUEST_ID_KEY: request_id})


def clear_request_context() -> None:
    structlog.contextvars.clear_contextvars()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
