"""Telemetriya ombori: SQLite. Yozuvlar to'planib, to'plam bo'lib yoziladi.

Sinxron kod; `IotService` uni bitta ishchi oqimda chaqiradi.
"""

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry (
    ts REAL NOT NULL,
    source TEXT NOT NULL,
    key TEXT NOT NULL,
    value REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS telemetry_series ON telemetry (source, key, ts);
CREATE INDEX IF NOT EXISTS telemetry_ts ON telemetry (ts);
CREATE TABLE IF NOT EXISTS latest (
    source TEXT NOT NULL,
    key TEXT NOT NULL,
    value REAL NOT NULL,
    ts REAL NOT NULL,
    PRIMARY KEY (source, key)
);
"""
MAX_FIELDS = 32
_PAIR = re.compile(
    r"\s*([A-Za-z_][A-Za-z0-9_.-]{0,31})\s*[=:]\s*(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*"
)


@dataclass(frozen=True, slots=True)
class Sample:
    ts: float
    source: str
    key: str
    value: float

    def as_dict(self) -> dict[str, Any]:
        return {"ts": self.ts, "source": self.source, "key": self.key, "value": self.value}


def _number(value: Any) -> float | None:  # noqa: ANN401
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int | float) and value == value and abs(value) != float("inf"):
        return float(value)
    return None


def parse_values(text: str) -> dict[str, float]:
    """Matndan sonli qiymatlarni ajratadi.

    Qo'llab-quvvatlanadi: bitta son (`21.5` -> `value`), JSON obyekt (sonli maydonlari),
    `kalit=qiymat` juftliklari (`temp=21.5,hum=40` yoki bo'shliq bilan).
    """
    stripped = text.strip()
    if not stripped:
        return {}
    try:
        parsed: Any = json.loads(stripped)
    except ValueError:
        parsed = None
    single = _number(parsed)
    if single is not None:
        return {"value": single}
    if isinstance(parsed, dict):
        fields = cast(dict[Any, Any], parsed)
        numbers = ((str(key)[:32], _number(value)) for key, value in fields.items())
        return dict([(key, value) for key, value in numbers if value is not None][:MAX_FIELDS])
    pairs: dict[str, float] = {}
    for chunk in re.split(r"[,;\s]+", stripped):
        match = _PAIR.fullmatch(chunk)
        if match is not None and len(pairs) < MAX_FIELDS:
            pairs[match[1]] = float(match[2])
    return pairs


class TelemetryStore:
    def __init__(self, db_file: Path) -> None:
        self._db = sqlite3.connect(db_file)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.executescript(SCHEMA)
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def write(self, samples: list[Sample]) -> int:
        rows = [(s.ts, s.source, s.key, s.value) for s in samples]
        self._db.executemany("INSERT INTO telemetry VALUES (?, ?, ?, ?)", rows)
        self._db.executemany(
            "INSERT INTO latest (ts, source, key, value) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (source, key) DO UPDATE SET value = excluded.value, ts = excluded.ts "
            "WHERE excluded.ts >= latest.ts",
            rows,
        )
        self._db.commit()
        return len(rows)

    def latest(self, source_prefix: str = "") -> list[Sample]:
        rows = self._db.execute(
            "SELECT ts, source, key, value FROM latest WHERE source LIKE ? ESCAPE '\\' "
            "ORDER BY source, key",
            (source_prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",),
        ).fetchall()
        return [Sample(*row) for row in rows]

    def series(self, source: str, key: str, since: float, limit: int) -> list[Sample]:
        """Oxirgi `limit` ta nuqta (`since` dan keyingi), vaqt bo'yicha o'sish tartibida."""
        rows = self._db.execute(
            "SELECT ts, source, key, value FROM telemetry "
            "WHERE source = ? AND key = ? AND ts >= ? ORDER BY ts DESC LIMIT ?",
            (source, key, since, limit),
        ).fetchall()
        return [Sample(*row) for row in reversed(rows)]

    def count(self) -> int:
        return int(self._db.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0])

    def purge(self, older_than: float) -> int:
        """`older_than` dan eski yozuvlarni o'chiradi (oxirgi qiymatlar jadvali ham)."""
        cursor = self._db.execute("DELETE FROM telemetry WHERE ts < ?", (older_than,))
        self._db.execute("DELETE FROM latest WHERE ts < ?", (older_than,))
        self._db.commit()
        return cursor.rowcount
