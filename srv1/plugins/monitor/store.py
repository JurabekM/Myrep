"""Tarix ombori: SQLite. Sinxron kod; `MonitorService` uni bitta ishchi oqimda chaqiradi."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from .alerts import Alert
from .models import MB, Sample

SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    ts REAL PRIMARY KEY,
    cpu REAL NOT NULL,
    memory REAL NOT NULL,
    memory_used INTEGER NOT NULL,
    memory_total INTEGER NOT NULL,
    srv1_rss INTEGER NOT NULL,
    disks TEXT NOT NULL
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    key TEXT NOT NULL,
    state TEXT NOT NULL,
    value REAL,
    threshold REAL,
    note TEXT NOT NULL DEFAULT ''
);
"""


def _unit(key: str) -> str:
    return " GB" if key.startswith("disk:") else " %"


def _amount(key: str, number: float | None) -> str:
    return "" if number is None else f"{number:.1f}{_unit(key)}"


class History:
    def __init__(self, db_file: Path) -> None:
        self._file = db_file
        self._db = sqlite3.connect(db_file)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.executescript(SCHEMA)
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    # --- o'lchovlar -------------------------------------------------------
    def add(self, sample: Sample, alerts: list[Alert]) -> None:
        disks = json.dumps([[d.mount, d.free, d.total] for d in sample.disks])
        self._db.execute(
            "INSERT OR REPLACE INTO samples VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                sample.ts,
                sample.cpu,
                sample.memory,
                sample.memory_used,
                sample.memory_total,
                sample.srv1_rss,
                disks,
            ),
        )
        self._insert_alerts(alerts)
        self._db.commit()

    def series(self, since: float, limit: int) -> list[dict[str, Any]]:
        """Oxirgi `limit` ta o'lchov (`since` dan keyingi), vaqt bo'yicha o'sish tartibida."""
        rows = self._db.execute(
            "SELECT ts, cpu, memory, srv1_rss FROM samples WHERE ts >= ? ORDER BY ts DESC LIMIT ?",
            (since, limit),
        ).fetchall()
        return [
            {"ts": ts, "cpu": cpu, "memory": memory, "srv1_mb": round(rss / MB, 1)}
            for ts, cpu, memory, rss in reversed(rows)
        ]

    def count(self) -> int:
        return int(self._db.execute("SELECT COUNT(*) FROM samples").fetchone()[0])

    def size(self) -> int:
        """Baza fayllarining diskdagi hajmi (WAL bilan birga), baytlarda."""
        files = (self._file, self._file.with_name(self._file.name + "-wal"))
        return sum(file.stat().st_size for file in files if file.is_file())

    # --- ogohlantirishlar ---------------------------------------------------
    def _insert_alerts(self, alerts: list[Alert]) -> None:
        self._db.executemany(
            "INSERT INTO alerts (ts, key, state, value, threshold, note) VALUES (?, ?, ?, ?, ?, ?)",
            [(a.ts, a.key, a.state, a.value, a.limit, a.note) for a in alerts],
        )

    def add_alert(self, alert: Alert) -> None:
        self._insert_alerts([alert])
        self._db.commit()

    def active_keys(self) -> list[str]:
        """Oxirgi yozuvi `raised` bo'lgan qoidalar (qayta ishga tushganda holatni tiklash uchun)."""
        rows = self._db.execute(
            "SELECT key FROM alerts AS a WHERE state = 'raised' "
            "AND id = (SELECT MAX(id) FROM alerts WHERE key = a.key) ORDER BY key"
        ).fetchall()
        return [row[0] for row in rows]

    def alerts(self, limit: int) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT ts, key, state, value, threshold, note FROM alerts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "ts": ts,
                "key": key,
                "state": state,
                "value": _amount(key, value),
                "limit": _amount(key, threshold),
                "note": note,
            }
            for ts, key, state, value, threshold, note in rows
        ]

    # --- tozalash -----------------------------------------------------------
    def purge(self, older_than: float, alerts_kept: int) -> int:
        """Eski o'lchovlarni o'chiradi; ogohlantirishlardan oxirgi `alerts_kept` tasi qoladi."""
        cursor = self._db.execute("DELETE FROM samples WHERE ts < ?", (older_than,))
        self._db.execute(
            "DELETE FROM alerts WHERE id <= (SELECT MAX(id) FROM alerts) - ?", (alerts_kept,)
        )
        self._db.commit()
        return cursor.rowcount

    def clear(self) -> tuple[int, int]:
        """Butun tarixni o'chiradi va faylni siqadi. Qaytaradi: (o'lchovlar, ogohlantirishlar)."""
        samples = self._db.execute("DELETE FROM samples").rowcount
        alerts = self._db.execute("DELETE FROM alerts").rowcount
        self._db.commit()
        self._db.execute("VACUUM")
        return samples, alerts
