"""Sinxronlash sim formati: jadval qatori ↔ JSON. Ustun nomlari ilovadagi bilan bir xil.

- Vaqt: ISO-8601 UTC, millisekund bilan (`2026-10-27T08:00:00.000Z`); qabul qilishda ofsetli ham bo'ladi.
- `bytea` (PDF): base64. JSON ustunlar: obyekt yoki ro'yxat.
- Serverga xos ustunlar (`server_rev`, `password_hash`, `phone`) sim formatiga kirmaydi.
"""

from __future__ import annotations

import base64
import binascii
import math
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.schema import Column, Table

from zanjir_server.crypto.canonical import canonical_json_bytes
from zanjir_server.db.models import SYNC_MODELS, Base

HIDDEN = {"server_rev"}
HIDDEN_BY_TABLE = {"app_user": {"password_hash", "phone"}}
LIST_COLUMNS = {"target_node_ids", "steps", "warnings"}
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$")


class WireError(ValueError):
    """Qator sim formatiga mos emas; `reason` — barqaror kod."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def wire_columns(table: str) -> list[Column[Any]]:
    model = SYNC_MODELS[table]
    hidden = HIDDEN | HIDDEN_BY_TABLE.get(table, set())
    table_obj: Table = model.__table__  # type: ignore[assignment]
    return [c for c in table_obj.columns if c.name not in hidden]


def iso(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.astimezone(UTC).microsecond // 1000:03d}Z"


def to_wire(table: str, obj: Base) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for c in wire_columns(table):
        v = getattr(obj, c.key)
        if isinstance(v, datetime):
            v = iso(v)
        elif isinstance(v, bytes):
            v = base64.b64encode(v).decode()
        out[c.name] = v
    return out


def _parse(table: str, c: Column[Any], v: Any) -> Any:
    name = f"{table}.{c.name}"
    if v is None:
        if not c.nullable:
            raise WireError(f"null:{name}")
        return None
    t = c.type
    if isinstance(t, Boolean):
        if not isinstance(v, bool):
            raise WireError(f"type:{name}")
        return v
    if isinstance(t, (Integer, BigInteger)):
        if not isinstance(v, int) or isinstance(v, bool):
            raise WireError(f"type:{name}")
        return v
    if isinstance(t, Float):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            raise WireError(f"type:{name}")
        return float(v)
    if isinstance(t, DateTime):
        if not isinstance(v, str) or not _ISO.match(v):
            raise WireError(f"type:{name}")
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return d.astimezone(UTC)
    if isinstance(t, JSONB):
        want = list if c.name in LIST_COLUMNS else dict
        if not isinstance(v, want):
            raise WireError(f"type:{name}")
        try:
            canonical_json_bytes(v)  # NaN/Infinity, 2^53 dan katta son — hash'lab bo'lmaydi (ADR-0014)
        except ValueError as e:
            raise WireError(f"type:{name}") from e
        return v
    if isinstance(t, LargeBinary):
        if not isinstance(v, str):
            raise WireError(f"type:{name}")
        try:
            return base64.b64decode(v, validate=True)
        except binascii.Error as e:
            raise WireError(f"type:{name}") from e
    if isinstance(t, (String, Text)):
        if not isinstance(v, str):
            raise WireError(f"type:{name}")
        if isinstance(t, String) and t.length is not None and len(v) > t.length:
            raise WireError(f"too_long:{name}")
        return v
    raise WireError(f"type:{name}")  # pragma: no cover — barcha ustun turlari yuqorida


def from_wire(table: str, row: dict[str, Any]) -> dict[str, Any]:
    """Sim qatori → ustun qiymatlari (Python). Noma'lum kalit yoki majburiy ustun yo'qligi — `WireError`."""
    cols = {c.name: c for c in wire_columns(table)}
    unknown = set(row) - set(cols)
    if unknown:
        raise WireError(f"unknown_column:{table}.{sorted(unknown)[0]}")
    out: dict[str, Any] = {}
    for name, c in cols.items():
        if name not in row:
            if c.nullable:
                out[c.key] = None
                continue
            raise WireError(f"missing:{table}.{name}")
        out[c.key] = _parse(table, c, row[name])
    return out


def normalized(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Taqqoslash uchun: ustun qiymatlari → sim ko'rinishi."""
    out: dict[str, Any] = {}
    for c in wire_columns(table):
        v = values.get(c.key)
        if isinstance(v, datetime):
            v = iso(v)
        elif isinstance(v, bytes):
            v = base64.b64encode(v).decode()
        out[c.name] = v
    return out
