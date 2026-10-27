"""Kuzatuv: strukturalangan JSON log, Prometheus metrikalari, xato hisobotlari adapteri (standart — o'chiq).

Logga so'rov tanasi, sarlavhalar (Authorization), query satri va haqiqiy yo'l yozilmaydi — faqat marshrut shabloni
(`/v/{qr_token}`), shuning uchun token va shaxsiy ma'lumot logga tushmaydi (CLAUDE.md, 8-qoida).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Protocol

from prometheus_client import CollectorRegistry, Counter, Histogram


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            data.update(extra)
        if record.exc_info and record.exc_info[0] is not None:
            data["exc"] = record.exc_info[0].__name__
        return json.dumps(data, ensure_ascii=False)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("zanjir")
    root.handlers[:] = [handler]
    root.setLevel(level)
    root.propagate = False


class Metrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "zanjir_http_requests_total", "HTTP so'rovlar", ["method", "route", "status"], registry=self.registry
        )
        self.latency = Histogram(
            "zanjir_http_request_seconds", "So'rov davomiyligi", ["method", "route"], registry=self.registry
        )
        self.sync_rejected = Counter(
            "zanjir_sync_push_rejected_total", "Rad etilgan push paketlari", ["reason"], registry=self.registry
        )


class ErrorReporter(Protocol):
    def report(self, exc: BaseException, *, route: str) -> None: ...


class NullErrorReporter:
    """Standart: tashqi xizmatga hech narsa yuborilmaydi (ma'lumot lokalizatsiyasi, docs/DEPLOY.md)."""

    def report(self, exc: BaseException, *, route: str) -> None:
        return None
