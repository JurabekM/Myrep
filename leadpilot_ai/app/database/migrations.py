"""Lightweight, dependency-free migration mechanism.

The application ships with ``Base.metadata.create_all`` as the baseline and a
small ordered list of additive revisions.  Every applied revision is recorded in
``schema_versions`` so upgrades are idempotent and safe to run on every start.
Alembic can be layered on top later without changing the calling code.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import Engine, inspect, text

from app.models import Base
from app.utils.dates import now

logger = logging.getLogger(__name__)

Revision = tuple[str, Callable[[Engine], None]]


def _column_exists(engine: Engine, table: str, column: str) -> bool:
    """Whether ``table.column`` exists in the current schema."""
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def _add_column(engine: Engine, table: str, column: str, ddl_type: str) -> None:
    """Add a column when it is missing (SQLite compatible)."""
    if _column_exists(engine, table, column):
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
    logger.info("Migration: added %s.%s", table, column)


def _rev_0002_lead_indexes(engine: Engine) -> None:
    """Create supporting indexes for the busiest lead queries."""
    statements = [
        "CREATE INDEX IF NOT EXISTS ix_leads_status_owner ON leads (status, owner_id)",
        "CREATE INDEX IF NOT EXISTS ix_messages_conv_created ON messages (conversation_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_bookings_range ON bookings (starts_at, ends_at)",
        "CREATE INDEX IF NOT EXISTS ix_tasks_due_status ON tasks (due_at, status)",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def _rev_0003_lead_extra_columns(engine: Engine) -> None:
    """Additive columns introduced after the first public build."""
    _add_column(engine, "leads", "phone_raw", "VARCHAR(48) DEFAULT ''")
    _add_column(engine, "leads", "merged_into_id", "INTEGER")


REVISIONS: list[Revision] = [
    ("0002_lead_indexes", _rev_0002_lead_indexes),
    ("0003_lead_extra_columns", _rev_0003_lead_extra_columns),
]


def _applied_revisions(engine: Engine) -> set[str]:
    """Read the set of revisions already applied."""
    inspector = inspect(engine)
    if "schema_versions" not in inspector.get_table_names():
        return set()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT revision FROM schema_versions")).fetchall()
    return {row[0] for row in rows}


def run_migrations(engine: Engine) -> list[str]:
    """Create missing tables and apply pending revisions.

    Returns the list of revision identifiers applied during this call.
    """
    Base.metadata.create_all(engine)
    applied = _applied_revisions(engine)
    newly_applied: list[str] = []
    for revision, func in REVISIONS:
        if revision in applied:
            continue
        try:
            func(engine)
        except Exception:
            logger.exception("Migration %s failed", revision)
            raise
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO schema_versions (revision, applied_at) VALUES (:r, :a)"),
                {"r": revision, "a": now()},
            )
        newly_applied.append(revision)
        logger.info("Migration applied: %s", revision)
    return newly_applied
