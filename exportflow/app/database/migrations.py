"""Lightweight schema migration mechanism.

Alembic is intentionally avoided: a single-file SQLite database shipped with a
desktop application only needs a linear, forward-only migration chain. The
current schema version is stored in the ``schema_version`` table and each step
is an idempotent callable.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Connection, inspect, text

from app.database.engine import get_engine
from app.models import Base
from app.utils.logging_setup import get_logger

log = get_logger(__name__)

SCHEMA_VERSION = 1


def _ensure_version_table(conn: Connection) -> None:
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS schema_version ("
            "  id INTEGER PRIMARY KEY CHECK (id = 1),"
            "  version INTEGER NOT NULL"
            ")"
        )
    )
    row = conn.execute(text("SELECT version FROM schema_version WHERE id = 1")).first()
    if row is None:
        conn.execute(text("INSERT INTO schema_version (id, version) VALUES (1, 0)"))


def current_version() -> int:
    """Read the schema version currently stored in the database."""
    with get_engine().begin() as conn:
        _ensure_version_table(conn)
        row = conn.execute(text("SELECT version FROM schema_version WHERE id = 1")).first()
        return int(row[0]) if row else 0


def _set_version(conn: Connection, version: int) -> None:
    conn.execute(text("UPDATE schema_version SET version = :v WHERE id = 1"), {"v": version})


def add_column_if_missing(conn: Connection, table: str, column: str, ddl_type: str) -> None:
    """Idempotently add a column to an existing table."""
    inspector = inspect(conn)
    if table not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns(table)}
    if column in existing:
        return
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
    log.info("Migration: added column %s.%s", table, column)


def _step_1(conn: Connection) -> None:
    """Initial schema - tables are created by ``Base.metadata.create_all``."""
    return None


#: Ordered migration steps; index N upgrades the database to version N+1.
STEPS: list[Callable[[Connection], None]] = [_step_1]


def run_migrations() -> int:
    """Create missing tables and apply every pending migration step."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        _ensure_version_table(conn)
        row = conn.execute(text("SELECT version FROM schema_version WHERE id = 1")).first()
        version = int(row[0]) if row else 0
        for index in range(version, len(STEPS)):
            STEPS[index](conn)
            version = index + 1
            _set_version(conn, version)
            log.info("Migration applied: schema version -> %s", version)
        if version != SCHEMA_VERSION:
            _set_version(conn, SCHEMA_VERSION)
            version = SCHEMA_VERSION
    return version
