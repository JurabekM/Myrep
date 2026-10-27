"""Sinxronlash sxemasi shartnomasi: `tools/vectors/sync_schema.json` — Dart testi (zanjir_data) ham shu fayldan
o'qib, lokal jadvallar server ustunlariga mosligini tekshiradi (ADR-0012).

Yangilash: `ZANJIR_UPDATE_SYNC_SCHEMA=1 uv run pytest tests/test_sync_schema.py`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB

from zanjir_server.db.models import APPEND_ONLY, SYNC_MODELS
from zanjir_server.sync.service import PUSH_ROLES
from zanjir_server.sync.wire import LIST_COLUMNS, wire_columns

PATH = Path(__file__).resolve().parents[2] / "tools" / "vectors" / "sync_schema.json"


def _type(c: object) -> str:
    t = getattr(c, "type", None)
    name = getattr(c, "name", "")
    if isinstance(t, Boolean):
        return "bool"
    if isinstance(t, (Integer, BigInteger)):
        return "int"
    if isinstance(t, Float):
        return "real"
    if isinstance(t, DateTime):
        return "datetime"
    if isinstance(t, JSONB):
        return "json_list" if name in LIST_COLUMNS else "json_map"
    if isinstance(t, LargeBinary):
        return "base64"
    return "text"


def schema() -> dict[str, object]:
    return {
        "tables": [
            {
                "name": t,
                "pushable": t in PUSH_ROLES,
                "append_only": t in APPEND_ONLY,
                "columns": [{"name": c.name, "type": _type(c), "nullable": bool(c.nullable)} for c in wire_columns(t)],
            }
            for t in SYNC_MODELS
        ]
    }


def test_sync_schema_file_is_current() -> None:
    text = json.dumps(schema(), ensure_ascii=False, indent=2) + "\n"
    if os.environ.get("ZANJIR_UPDATE_SYNC_SCHEMA") == "1":
        PATH.write_text(text, encoding="utf-8")
    assert PATH.read_text(encoding="utf-8") == text, (
        "eskirgan: ZANJIR_UPDATE_SYNC_SCHEMA=1 uv run pytest tests/test_sync_schema.py"
    )
