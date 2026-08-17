"""
Migration Manager Module
========================

Provides a lightweight, automatic migration system for the Enterprise ERP
platform.  Instead of generating explicit migration scripts, it tracks
schema versions in a ``_migrations`` table and uses ``CREATE_ALL`` for
initial setup combined with introspection-based ``ALTER TABLE`` for
subsequent changes.

Classes:
    MigrationManager: Schema versioning, migration detection, and application.

Usage::

    manager = MigrationManager(db_engine)
    manager.create_tables()
    pending = manager.check_pending_migrations()
    if pending:
        manager.apply_migrations()
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Table,
    MetaData,
    inspect,
    text,
)
from sqlalchemy.orm import Session

from src.core.exceptions import DatabaseError
from src.database.engine import DatabaseEngine
from src.database.models import Base

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Migration tracking table (managed outside the ORM Base metadata)
# ------------------------------------------------------------------

_migration_meta = MetaData()

_migrations_table = Table(
    "_migrations",
    _migration_meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("version", String(50), nullable=False, unique=True),
    Column("description", String(255), nullable=True),
    Column("applied_at", DateTime, default=datetime.datetime.utcnow),
)


class MigrationManager:
    """Lightweight schema migration manager.

    Tracks schema versions in a dedicated ``_migrations`` table and
    applies changes automatically by comparing the current database
    schema against the SQLAlchemy model metadata.

    Attributes:
        db_engine: The :class:`DatabaseEngine` instance managing connections.
    """

    # Bump this when the application schema changes materially.
    CURRENT_SCHEMA_VERSION: str = "1.0.0"

    def __init__(self, db_engine: DatabaseEngine) -> None:
        """Initialise the migration manager.

        Args:
            db_engine: A connected :class:`DatabaseEngine`.

        Raises:
            DatabaseError: If the engine is not connected.
        """
        if not db_engine.is_connected():
            raise DatabaseError(
                "DatabaseEngine must be connected before initialising "
                "MigrationManager."
            )
        self.db_engine: DatabaseEngine = db_engine

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_tables(self) -> None:
        """Create all ORM-defined tables and the migrations tracking table.

        Existing tables are left untouched (``CREATE TABLE IF NOT EXISTS``
        semantics).

        Raises:
            DatabaseError: If table creation fails.
        """
        try:
            engine = self.db_engine.engine
            # 1. Ensure the migrations tracking table exists.
            _migration_meta.create_all(bind=engine)
            # 2. Create all application tables.
            Base.metadata.create_all(bind=engine)
            # 3. Record the initial version if not yet tracked.
            self._record_version_if_missing(
                self.CURRENT_SCHEMA_VERSION, "Initial schema creation"
            )
            logger.info("All database tables created / verified.")
        except Exception as exc:
            raise DatabaseError(f"Failed to create tables: {exc}") from exc

    def check_pending_migrations(self) -> list[dict[str, Any]]:
        """Detect pending schema migrations.

        Compares columns defined in the ORM models against those present
        in the live database and returns a list of ``ALTER TABLE ADD
        COLUMN`` operations that need to be applied.

        Returns:
            A list of dictionaries describing pending column additions,
            each with keys ``table``, ``column``, and ``type``.

        Raises:
            DatabaseError: If introspection fails.
        """
        try:
            pending: list[dict[str, Any]] = []
            db_inspector = inspect(self.db_engine.engine)
            existing_tables: set[str] = set(db_inspector.get_table_names())

            for table_name, table in Base.metadata.tables.items():
                if table_name not in existing_tables:
                    # Whole table is missing — create_tables will handle it.
                    pending.append(
                        {
                            "table": table_name,
                            "column": "*",
                            "type": "CREATE TABLE",
                        }
                    )
                    continue

                # Compare columns.
                existing_columns: set[str] = {
                    col["name"] for col in db_inspector.get_columns(table_name)
                }
                for column in table.columns:
                    if column.name not in existing_columns:
                        pending.append(
                            {
                                "table": table_name,
                                "column": column.name,
                                "type": str(column.type),
                            }
                        )

            if pending:
                logger.info(
                    "%d pending migration(s) detected.", len(pending)
                )
            else:
                logger.info("No pending migrations.")

            return pending
        except Exception as exc:
            raise DatabaseError(
                f"Failed to check pending migrations: {exc}"
            ) from exc

    def apply_migrations(self) -> None:
        """Apply all pending migrations.

        For missing tables, ``create_all`` is invoked.  For missing
        columns, ``ALTER TABLE ADD COLUMN`` statements are executed
        directly.

        Raises:
            DatabaseError: If any migration step fails.
        """
        try:
            pending = self.check_pending_migrations()
            if not pending:
                logger.info("Nothing to migrate — schema is up to date.")
                return

            # Ensure any entirely new tables are created first.
            Base.metadata.create_all(bind=self.db_engine.engine)

            # Handle missing columns via ALTER TABLE.
            for migration in pending:
                if migration["column"] == "*":
                    # Already handled by create_all above.
                    continue
                self._add_column(
                    table=migration["table"],
                    column_name=migration["column"],
                    column_type=migration["type"],
                )

            # Bump the version.
            new_version = self._next_version()
            self._record_version_if_missing(
                new_version, f"Auto-migration: {len(pending)} change(s)"
            )
            logger.info(
                "Applied %d migration(s). Schema version: %s",
                len(pending),
                new_version,
            )
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(f"Migration failed: {exc}") from exc

    def get_current_version(self) -> str:
        """Return the latest recorded schema version.

        Returns:
            The version string, or ``"0.0.0"`` if no version has been
            recorded yet.

        Raises:
            DatabaseError: If the query fails.
        """
        try:
            with self.db_engine.get_session() as session:
                result = session.execute(
                    text(
                        "SELECT version FROM _migrations "
                        "ORDER BY id DESC LIMIT 1"
                    )
                ).fetchone()
                return result[0] if result else "0.0.0"
        except Exception:
            # Table may not exist yet.
            return "0.0.0"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _add_column(
        self, table: str, column_name: str, column_type: str
    ) -> None:
        """Execute an ``ALTER TABLE ADD COLUMN`` statement.

        Args:
            table: The target table name.
            column_name: The new column name.
            column_type: The SQL type string (e.g. ``'VARCHAR(255)'``).

        Raises:
            DatabaseError: If the DDL statement fails.
        """
        # Normalise type strings emitted by SQLAlchemy.
        sql_type = self._normalise_type(column_type)

        ddl = f"ALTER TABLE {table} ADD COLUMN {column_name} {sql_type}"
        try:
            with self.db_engine.engine.begin() as conn:
                conn.execute(text(ddl))
            logger.info("Added column %s.%s (%s)", table, column_name, sql_type)
        except Exception as exc:
            logger.warning(
                "Could not add column %s.%s: %s", table, column_name, exc
            )

    @staticmethod
    def _normalise_type(type_str: str) -> str:
        """Map common SQLAlchemy type names to portable SQL types.

        Args:
            type_str: The raw type string from SQLAlchemy.

        Returns:
            A normalised SQL type string.
        """
        mapping: dict[str, str] = {
            "VARCHAR": "VARCHAR(255)",
            "STRING": "VARCHAR(255)",
            "TEXT": "TEXT",
            "INTEGER": "INTEGER",
            "FLOAT": "REAL",
            "BOOLEAN": "BOOLEAN",
            "DATETIME": "TIMESTAMP",
            "DATE": "DATE",
            "NUMERIC": "NUMERIC",
        }

        upper = type_str.upper().strip()
        for key, value in mapping.items():
            if upper.startswith(key):
                return value
        return "TEXT"

    def _record_version_if_missing(
        self, version: str, description: str
    ) -> None:
        """Insert a version record if it does not already exist.

        Args:
            version: The version string to record.
            description: A human-readable description of the migration.
        """
        try:
            with self.db_engine.engine.begin() as conn:
                existing = conn.execute(
                    text("SELECT id FROM _migrations WHERE version = :v"),
                    {"v": version},
                ).fetchone()
                if existing is None:
                    conn.execute(
                        text(
                            "INSERT INTO _migrations (version, description, applied_at) "
                            "VALUES (:v, :d, :t)"
                        ),
                        {
                            "v": version,
                            "d": description,
                            "t": datetime.datetime.utcnow(),
                        },
                    )
        except Exception as exc:
            logger.warning("Could not record migration version: %s", exc)

    def _next_version(self) -> str:
        """Derive the next patch version from the current version.

        Returns:
            A version string with the patch component incremented by one.
        """
        current = self.get_current_version()
        try:
            parts = current.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            return ".".join(parts)
        except (ValueError, IndexError):
            return f"{current}.1"
