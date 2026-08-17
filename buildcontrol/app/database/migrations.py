"""Lightweight forward-only migration runner.

The application ships without Alembic to keep the frozen ``.exe`` small.
Schema state is tracked in a ``schema_version`` table; each migration is a
callable taking a raw DB-API connection.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import text

from app.database.session import create_all, get_engine

logger = logging.getLogger(__name__)

Migration = Callable[[object], None]


def _v1_baseline(_conn) -> None:
    """Baseline schema — created by ``Base.metadata.create_all``."""


def _columns(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
    return {row[1] for row in rows}


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": table},
    ).fetchone()
    return row is not None


def _v2_sync_columns(conn) -> None:
    """Add the replication identity (``uid``, ``sync_ts``) to existing tables.

    Fresh databases already get the columns from ``create_all``; this migration
    upgrades installations created before synchronisation existed and backfills
    a unique identifier for every existing row.
    """
    from app.sync.registry import SYNC_ENTITIES

    for model in SYNC_ENTITIES:
        table = model.__tablename__
        if not _table_exists(conn, table):
            continue
        existing = _columns(conn, table)
        if "uid" not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN uid VARCHAR(32)"))
        if "sync_ts" not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN sync_ts DATETIME"))

        rows = conn.execute(
            text(f"SELECT id FROM {table} WHERE uid IS NULL OR uid = ''")
        ).fetchall()
        for (row_id,) in rows:
            conn.execute(
                text(
                    f"UPDATE {table} SET uid = :uid, "
                    f"sync_ts = COALESCE(sync_ts, :ts) WHERE id = :id"
                ),
                {"uid": uuid.uuid4().hex, "ts": datetime.now().isoformat(sep=" "), "id": row_id},
            )
        conn.execute(
            text(f"UPDATE {table} SET sync_ts = :ts WHERE sync_ts IS NULL"),
            {"ts": datetime.now().isoformat(sep=" ")},
        )
        conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{table}_uid ON {table} (uid)"))


def _v3_uid_alias(_conn) -> None:
    """``sync_uid_alias`` is created by ``create_all``; recorded for traceability."""


#: Ordered registry. Append new entries, never edit released ones.
MIGRATIONS: list[tuple[int, str, Migration]] = [
    (1, "baseline", _v1_baseline),
    (2, "sync_columns", _v2_sync_columns),
    (3, "uid_alias", _v3_uid_alias),
]

CURRENT_VERSION: int = MIGRATIONS[-1][0]


def _ensure_version_table(conn) -> None:
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS schema_version ("
            "version INTEGER PRIMARY KEY, name TEXT, applied_at TEXT)"
        )
    )


def current_version(conn) -> int:
    row = conn.execute(text("SELECT COALESCE(MAX(version), 0) FROM schema_version")).fetchone()
    return int(row[0]) if row else 0


def run_migrations() -> int:
    """Create missing tables and apply pending migrations. Returns the version."""
    # Importing the models registers every table (including the sync tables)
    # with the metadata before ``create_all`` runs.
    import app.models.entities  # noqa: F401
    import app.sync.models  # noqa: F401

    create_all()
    engine = get_engine()
    with engine.begin() as conn:
        _ensure_version_table(conn)
        version = current_version(conn)
        for number, name, func in MIGRATIONS:
            if number <= version:
                continue
            logger.info("Applying migration %s (%s)", number, name)
            func(conn)
            conn.execute(
                text(
                    "INSERT INTO schema_version(version, name, applied_at) "
                    "VALUES (:v, :n, datetime('now'))"
                ),
                {"v": number, "n": name},
            )
            version = number
    return version
