"""
Database Engine Module
======================

Manages database connections for the Enterprise ERP platform with automatic
PostgreSQL detection and SQLite fallback. Provides session management via
context managers, connection pooling for PostgreSQL, and engine lifecycle
control.

Classes:
    DatabaseEngine: Core database connection and session management.

Usage::

    config = {
        "type": "sqlite",
        "path": "data/db/erp.db",
        "postgresql": {
            "host": "localhost",
            "port": 5432,
            "name": "erp_db",
            "user": "erp_user",
            "password": "secret",
        },
    }
    engine = DatabaseEngine(config)
    engine.connect()

    with engine.get_session() as session:
        # perform database operations
        ...

    engine.close()
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from src.core.exceptions import DatabaseError
from src.core.utils import get_project_root

logger = logging.getLogger(__name__)


class DatabaseEngine:
    """Manages database engine lifecycle, connections, and session factories.

    Supports automatic PostgreSQL detection with graceful SQLite fallback.
    Provides thread-safe session management through context managers and
    configurable connection pooling.

    Attributes:
        config: Database configuration dictionary.
        engine: The underlying SQLAlchemy ``Engine`` instance (set after connect).
        SessionLocal: A ``sessionmaker`` bound to the engine (set after connect).
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the database engine with the given configuration.

        Args:
            config: Database configuration dictionary with keys:
                - ``type`` (str): ``'sqlite'`` or ``'postgresql'``.
                - ``path`` (str): Relative path for the SQLite database file.
                - ``postgresql`` (dict): PostgreSQL connection parameters with
                  keys ``host``, ``port``, ``name``, ``user``, ``password``.
        """
        self.config: dict[str, Any] = config
        self.engine: Engine | None = None
        self.SessionLocal: sessionmaker | None = None
        self._is_postgresql: bool = False
        self._is_connected: bool = False

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Create the database engine and session factory.

        Attempts to connect to PostgreSQL when configured.  If the
        ``psycopg2`` driver is unavailable or the connection fails, the
        engine falls back to SQLite automatically.

        Raises:
            DatabaseError: If neither PostgreSQL nor SQLite can be initialised.
        """
        try:
            if self.config.get("type") == "postgresql":
                try:
                    self._connect_postgresql()
                    return
                except Exception as exc:
                    logger.warning(
                        "PostgreSQL connection failed (%s). Falling back to SQLite.",
                        exc,
                    )

            self._connect_sqlite()
        except Exception as exc:
            raise DatabaseError(f"Failed to initialise database engine: {exc}") from exc

    def _connect_postgresql(self) -> None:
        """Establish a PostgreSQL connection with connection pooling.

        Raises:
            ImportError: If ``psycopg2`` is not installed.
            Exception: If the connection test query fails.
        """
        try:
            import psycopg2  # noqa: F401 — availability check
        except ImportError as exc:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. "
                "Install it with: pip install psycopg2-binary"
            ) from exc

        pg_config: dict[str, Any] = self.config.get("postgresql", {})
        host: str = pg_config.get("host", "localhost")
        port: int = int(pg_config.get("port", 5432))
        name: str = pg_config.get("name", "erp_db")
        user: str = pg_config.get("user", "erp_user")
        password: str = pg_config.get("password", "")

        url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

        self.engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )

        # Verify that the connection is actually working.
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        self._is_postgresql = True
        self._is_connected = True
        self.SessionLocal = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False
        )
        logger.info("Connected to PostgreSQL at %s:%s/%s", host, port, name)

    def _connect_sqlite(self) -> None:
        """Establish an SQLite connection with WAL mode enabled.

        The database file is placed relative to the project root inside
        the ``data/db/`` directory.

        Raises:
            DatabaseError: If the SQLite engine cannot be created.
        """
        db_relative_path: str = self.config.get("path", "data/db/erp.db")
        project_root: str = str(get_project_root())
        db_path: str = os.path.join(project_root, db_relative_path)

        # Ensure parent directories exist.
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        url = f"sqlite:///{db_path}"

        self.engine = create_engine(
            url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=False,
        )

        # Enable WAL mode and foreign-key enforcement for every connection.
        @event.listens_for(self.engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Quick sanity check.
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        self._is_postgresql = False
        self._is_connected = True
        self.SessionLocal = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False
        )
        logger.info("Connected to SQLite database at %s", db_path)

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provide a transactional database session as a context manager.

        The session is automatically committed on success and rolled back
        on failure.  It is always closed upon exiting the context.

        Yields:
            A SQLAlchemy ``Session`` instance.

        Raises:
            DatabaseError: If the engine has not been connected yet, or if
                a session operation fails.
        """
        if self.SessionLocal is None:
            raise DatabaseError(
                "Database engine is not connected. Call connect() first."
            )

        session: Session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("Session error — rolled back: %s", exc)
            raise DatabaseError(f"Database session error: {exc}") from exc
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def create_tables(self, base: Any) -> None:
        """Create all tables defined in the given declarative base.

        Args:
            base: A SQLAlchemy declarative base whose ``metadata`` contains
                the table definitions.

        Raises:
            DatabaseError: If tables cannot be created.
        """
        if self.engine is None:
            raise DatabaseError(
                "Database engine is not connected. Call connect() first."
            )

        try:
            base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created/verified successfully.")
        except Exception as exc:
            raise DatabaseError(f"Failed to create database tables: {exc}") from exc

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def is_postgresql(self) -> bool:
        """Return ``True`` if the active engine is backed by PostgreSQL."""
        return self._is_postgresql

    def is_connected(self) -> bool:
        """Return ``True`` if the engine has been initialised and connected."""
        return self._is_connected

    def get_engine_info(self) -> dict[str, Any]:
        """Return diagnostic information about the current engine.

        Returns:
            A dictionary with keys ``backend``, ``url`` (sanitised),
            ``connected``, ``pool_size``, and ``pool_class``.
        """
        info: dict[str, Any] = {
            "backend": "postgresql" if self._is_postgresql else "sqlite",
            "connected": self._is_connected,
            "url": None,
            "pool_size": None,
            "pool_class": None,
        }

        if self.engine is not None:
            # Sanitise the URL to avoid leaking credentials.
            raw_url = str(self.engine.url)
            if "@" in raw_url:
                # Mask password portion.
                parts = raw_url.split("@", 1)
                scheme_user = parts[0].rsplit(":", 1)[0]
                info["url"] = f"{scheme_user}:***@{parts[1]}"
            else:
                info["url"] = raw_url

            pool = self.engine.pool
            info["pool_class"] = type(pool).__name__
            if hasattr(pool, "size"):
                info["pool_size"] = pool.size()

        return info

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Dispose of the engine and release all pooled connections."""
        if self.engine is not None:
            self.engine.dispose()
            self._is_connected = False
            logger.info("Database engine closed.")
