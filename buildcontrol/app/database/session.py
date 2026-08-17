"""Engine / session factory and transaction helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import config
from app.database.base import Base

_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def _configure_sqlite(dbapi_connection, _record) -> None:  # pragma: no cover - driver hook
    """Enable foreign keys and WAL for every new SQLite connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def init_engine(db_url: str | None = None, echo: bool = False) -> Engine:
    """Create (once) and return the global SQLAlchemy engine."""
    global _engine, _SessionFactory
    if _engine is not None:
        return _engine
    url = db_url or config.DB_URL
    _engine = create_engine(
        url,
        echo=echo,
        future=True,
        connect_args={"check_same_thread": False},
    )
    event.listen(_engine, "connect", _configure_sqlite)
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def get_engine() -> Engine:
    """Return the global engine, creating it if needed."""
    return _engine or init_engine()


def reset_engine() -> None:
    """Dispose the engine (used by tests and by backup restore)."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None


def create_all() -> None:
    """Create any missing tables."""
    Base.metadata.create_all(get_engine())


def new_session() -> Session:
    """Return a brand new session (caller owns the lifecycle)."""
    if _SessionFactory is None:
        init_engine()
    assert _SessionFactory is not None
    return _SessionFactory()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope: commits on success, rolls back on any exception."""
    session = new_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
