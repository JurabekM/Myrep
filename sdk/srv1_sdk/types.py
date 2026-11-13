"""Plaginlar yadroga beradigan oddiy tuzilmalar."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

EventCallback = Callable[[str, Mapping[str, Any]], Awaitable[None]]
JobCallback = Callable[[], Awaitable[None]]


class PermissionDenied(PermissionError):
    """Plagin manifestida so'ralmagan resursga murojaat qildi."""


@dataclass(frozen=True, slots=True)
class EventHandler:
    """Hodisa obunasi. `pattern` — to'liq mavzu naqshi: `system.*`, `plugin.monitor.alert`."""

    pattern: str
    handler: EventCallback


@dataclass(frozen=True, slots=True)
class Job:
    """Rejalashtirilgan vazifa: `interval_s` yoki `cron` (5 maydonli) dan aynan bittasi."""

    id: str
    func: JobCallback
    interval_s: float | None = None
    cron: str | None = None

    def __post_init__(self) -> None:
        if (self.interval_s is None) == (self.cron is None):
            raise ValueError(f"vazifa {self.id!r}: interval_s yoki cron dan aynan bittasi kerak")
        if self.interval_s is not None and self.interval_s <= 0:
            raise ValueError(f"vazifa {self.id!r}: interval_s musbat bo'lishi kerak")
