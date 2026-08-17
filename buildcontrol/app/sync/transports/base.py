"""Transport contract shared by every replication backend."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


class TransportError(Exception):
    """Raised when the backend is unreachable or rejects a request."""


@dataclass
class Change:
    """One replicated row operation travelling through the shared log."""

    entity: str
    uid: str
    op: str
    payload: dict = field(default_factory=dict)
    ts: str = ""
    device: str = ""
    #: Assigned by the backend on pull; opaque and monotonically increasing.
    cursor: str = ""

    def to_wire(self, tenant: str) -> dict:
        """Return the JSON body sent to the backend."""
        return {
            "tenant": tenant,
            "device": self.device,
            "entity": self.entity,
            "uid": self.uid,
            "op": self.op,
            "payload": self.payload,
            "ts": self.ts or datetime.now().isoformat(),
        }

    @staticmethod
    def from_wire(row: dict, cursor: str) -> Change:
        """Rebuild a change from a backend row."""
        payload = row.get("payload") or {}
        if isinstance(payload, str):
            payload = json.loads(payload or "{}")
        return Change(
            entity=str(row.get("entity") or ""),
            uid=str(row.get("uid") or ""),
            op=str(row.get("op") or "upsert"),
            payload=payload,
            ts=str(row.get("ts") or ""),
            device=str(row.get("device") or ""),
            cursor=cursor,
        )


class SyncTransport(Protocol):
    """Minimal append-only log a backend must provide."""

    #: Short identifier stored in the settings (``supabase``, ``folder`` ...).
    key: str

    def describe(self) -> str:
        """Human readable target, shown in the settings page."""

    def check(self) -> str:
        """Verify connectivity. Returns a status line, raises on failure."""

    def push(self, changes: list[Change]) -> int:
        """Append changes to the shared log. Returns how many were accepted."""

    def pull(self, after: str, limit: int = 500) -> list[Change]:
        """Return changes newer than the ``after`` cursor, oldest first."""
