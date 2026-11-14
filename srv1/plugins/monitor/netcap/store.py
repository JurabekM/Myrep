"""Ushlangan paketlar va xavf signallari ombori (SQLite). Sinxron; bitta oqimda chaqiriladi."""

import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS packets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    proto TEXT NOT NULL,
    src TEXT NOT NULL,
    sport INTEGER,
    dst TEXT NOT NULL,
    dport INTEGER,
    length INTEGER NOT NULL,
    info TEXT NOT NULL DEFAULT '',
    mark TEXT NOT NULL DEFAULT '',
    payload TEXT
);
CREATE TABLE IF NOT EXISTS net_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);
"""

_TEXT_MAX = 400


def _text(value: object, limit: int = _TEXT_MAX) -> str:
    return str(value if value is not None else "")[:limit]


def _port(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _number(value: object) -> float:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else 0.0


def _endpoint(address: str, port: int | None) -> str:
    if port is None:
        return address
    return f"[{address}]:{port}" if ":" in address else f"{address}:{port}"


class NetStore:
    def __init__(self, db_file: Path) -> None:
        self._file = db_file
        self._db = sqlite3.connect(db_file)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.executescript(SCHEMA)
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def add(
        self,
        packets: Sequence[Mapping[str, Any]],
        alerts: Sequence[Mapping[str, Any]],
        keep_packets: int,
        keep_alerts: int,
    ) -> None:
        """Bitta tranzaksiyada yozadi va eng eski ortiqcha qatorlarni o'chiradi."""
        self._db.executemany(
            "INSERT INTO packets (ts, proto, src, sport, dst, dport, length, info, mark, payload)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    _number(p.get("ts")),
                    _text(p.get("proto"), 16),
                    _text(p.get("src"), 64),
                    _port(p.get("sport")),
                    _text(p.get("dst"), 64),
                    _port(p.get("dport")),
                    int(_number(p.get("len"))),
                    _text(p.get("info")),
                    _text(p.get("mark"), 32),
                    None if p.get("payload") is None else _text(p.get("payload"), 2048),
                )
                for p in packets
            ],
        )
        self._db.executemany(
            "INSERT INTO net_alerts (ts, kind, src, dst, note) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    _number(a.get("ts")),
                    _text(a.get("kind"), 32),
                    _text(a.get("src"), 64),
                    _text(a.get("dst"), 64),
                    _text(a.get("note")),
                )
                for a in alerts
            ],
        )
        self._trim("packets", keep_packets)
        self._trim("net_alerts", keep_alerts)
        self._db.commit()

    def _trim(self, table: str, keep: int) -> None:
        # `table` — faqat shu modul ichidagi ikki doimiy nom.
        self._db.execute(
            f"DELETE FROM {table} WHERE id <= (SELECT MAX(id) FROM {table}) - ?",  # noqa: S608
            (keep,),
        )

    def packets(self, limit: int, ip: str = "", proto: str = "") -> list[dict[str, Any]]:
        """Eng yangilari birinchi. `ip` — manba yoki manzil; `proto` — aniq mos."""
        where: list[str] = []
        args: list[object] = []
        if ip:
            where.append("(src = ? OR dst = ?)")
            args += [ip, ip]
        if proto:
            where.append("proto = ?")
            args.append(proto.upper())
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        rows = self._db.execute(
            "SELECT ts, proto, src, sport, dst, dport, length, info, mark, payload"  # noqa: S608
            f" FROM packets {clause} ORDER BY id DESC LIMIT ?",
            (*args, limit),
        ).fetchall()
        return [
            {
                "ts": ts,
                "proto": protocol,
                "src": _endpoint(src, sport),
                "dst": _endpoint(dst, dport),
                "src_ip": src,
                "dst_ip": dst,
                "length": length,
                "info": info,
                "mark": mark,
                "payload": payload or "",
            }
            for ts, protocol, src, sport, dst, dport, length, info, mark, payload in rows
        ]

    def alerts(self, limit: int) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT ts, kind, src, dst, note FROM net_alerts ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            {"ts": ts, "kind": kind, "src": src, "dst": dst, "note": note}
            for ts, kind, src, dst, note in rows
        ]

    def counts(self) -> tuple[int, int]:
        packets = self._db.execute("SELECT COUNT(*) FROM packets").fetchone()[0]
        alerts = self._db.execute("SELECT COUNT(*) FROM net_alerts").fetchone()[0]
        return int(packets), int(alerts)

    def clear(self) -> tuple[int, int]:
        counts = self.counts()
        self._db.execute("DELETE FROM packets")
        self._db.execute("DELETE FROM net_alerts")
        self._db.commit()
        self._db.execute("VACUUM")
        return counts

    def size(self) -> int:
        return sum(
            path.stat().st_size
            for suffix in ("", "-wal", "-shm")
            if (path := self._file.with_name(self._file.name + suffix)).is_file()
        )
