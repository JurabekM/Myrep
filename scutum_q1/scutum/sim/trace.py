"""Voqealar shinasi — GUI paneli va paket inspektori uchun."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class Level(str, Enum):
    INFO = "INFO"
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"
    ATTACK = "ATTACK"
    WIRE = "WIRE"


@dataclass
class Event:
    ts: float
    actor: str
    level: Level
    text: str
    data: dict = field(default_factory=dict)

    @property
    def clock(self) -> str:
        return time.strftime("%H:%M:%S", time.localtime(self.ts))


class Trace:
    def __init__(self, limit: int = 5000) -> None:
        self.events: list[Event] = []
        self.limit = limit
        self._subs: list[Callable[[Event], None]] = []

    def subscribe(self, fn: Callable[[Event], None]) -> None:
        self._subs.append(fn)

    def emit(
        self, actor: str, level: Level, text: str, **data: Any
    ) -> Event:
        ev = Event(time.time(), actor, level, text, data)
        self.events.append(ev)
        if len(self.events) > self.limit:
            del self.events[: len(self.events) - self.limit]
        for fn in list(self._subs):
            try:
                fn(ev)
            except Exception:
                pass
        return ev

    def info(self, actor: str, text: str, **d): return self.emit(actor, Level.INFO, text, **d)
    def ok(self, actor: str, text: str, **d): return self.emit(actor, Level.OK, text, **d)
    def warn(self, actor: str, text: str, **d): return self.emit(actor, Level.WARN, text, **d)
    def fail(self, actor: str, text: str, **d): return self.emit(actor, Level.FAIL, text, **d)
    def attack(self, actor: str, text: str, **d): return self.emit(actor, Level.ATTACK, text, **d)
    def wire(self, actor: str, text: str, **d): return self.emit(actor, Level.WIRE, text, **d)

    def clear(self) -> None:
        self.events.clear()
