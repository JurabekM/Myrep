from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pandas as pd


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(slots=True)
class Dataset:
    name: str
    frame: pd.DataFrame
    source: str = "memory"
    kind: str = "table"
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=utc_now)
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    revision: int = 0

    @property
    def shape(self) -> tuple[int, int]:
        return self.frame.shape

    @property
    def memory_bytes(self) -> int:
        return int(self.frame.memory_usage(index=True, deep=True).sum())


@dataclass(slots=True)
class AuditEvent:
    action: str
    dataset_id: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class ImportResult:
    frame: pd.DataFrame
    name: str
    source: str
    kind: str
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

