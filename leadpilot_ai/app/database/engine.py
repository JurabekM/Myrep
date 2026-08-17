"""SQLAlchemy engine / session management for the local SQLite database."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import load_config

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def _configure_sqlite(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
    """Enable foreign keys and WAL journaling for every new connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def init_engine(database_url: str | None = None, echo: bool = False) -> Engine:
    """Create (once) and return the global engine."""
    global _engine, _SessionFactory
    if _engine is not None:
        return _engine
    url = database_url or load_config().database_url
    _engine = create_engine(
        url,
        echo=echo,
        future=True,
        connect_args={"check_same_thread": False, "timeout": 20},
    )
    event.listen(_engine, "connect", _configure_sqlite)
    _SessionFactory = sessionmaker(
        bind=_engine, autoflush=False, expire_on_commit=False, future=True
    )
    logger.info("Database engine initialised: %s", url)
    return _engine


def get_engine() -> Engine:
    """Return the global engine, creating it on first use."""
    return _engine or init_engine()


def get_session() -> Session:
    """Create a new session. Caller is responsible for closing it."""
    if _SessionFactory is None:
        init_engine()
    assert _SessionFactory is not None
    return _SessionFactory()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope: commits on success, rolls back on error."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Dispose the engine (used by tests to swap databases)."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None
