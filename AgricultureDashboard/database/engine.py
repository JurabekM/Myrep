"""Database engine management for SQLite (+ optional SpatiaLite extension)."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

import pandas as pd
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from config import settings
from database.models import Base, Setting

log = logging.getLogger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker | None = None
spatialite_enabled = False


def _try_load_spatialite(dbapi_connection: Any) -> bool:
    """Attempt to load the SpatiaLite extension; plain SQLite is the fallback."""
    try:
        dbapi_connection.enable_load_extension(True)
        for candidate in ("mod_spatialite", "mod_spatialite.dll"):
            try:
                dbapi_connection.load_extension(candidate)
                return True
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass
    finally:
        try:
            dbapi_connection.enable_load_extension(False)
        except Exception:  # noqa: BLE001
            pass
    return False


def get_engine() -> Engine:
    """Create (once) and return the shared SQLite engine."""
    global _engine, _session_factory, spatialite_enabled
    if _engine is not None:
        return _engine

    settings.ensure_directories()
    _engine = create_engine(
        f"sqlite:///{settings.DB_PATH}",
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(_engine, "connect")
    def _on_connect(dbapi_connection: Any, _record: Any) -> None:
        global spatialite_enabled
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
        if not spatialite_enabled and _try_load_spatialite(dbapi_connection):
            spatialite_enabled = True
            log.info("SpatiaLite kengaytmasi yuklandi (geo-SQL yoqilgan).")

    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def dispose_engine() -> None:
    """Close all pooled connections (needed before restore/replace of the DB)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def init_db() -> None:
    """Create all tables and ensure default settings exist."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    with session_scope() as session:
        existing = {row.key for row in session.query(Setting).all()}
        for key, value in settings.DEFAULT_SETTINGS.items():
            if key not in existing:
                session.add(Setting(key=key, value=value))


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session context manager."""
    get_engine()
    assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def read_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Run a parametrised SQL query and return a pandas DataFrame."""
    with get_engine().connect() as connection:
        return pd.read_sql(text(sql), connection, params=params or {})


def get_setting(key: str, default: str = "") -> str:
    """Read a configuration value from the settings table."""
    try:
        with session_scope() as session:
            row = session.get(Setting, key)
            return row.value if row is not None else default
    except Exception:  # noqa: BLE001 - settings must never crash callers
        return default


def set_setting(key: str, value: str) -> None:
    """Upsert a configuration value in the settings table."""
    with session_scope() as session:
        row = session.get(Setting, key)
        if row is None:
            session.add(Setting(key=key, value=value))
        else:
            row.value = value


def db_stats() -> dict[str, int]:
    """Row counts per core table (used by health checks and the admin page)."""
    tables = [
        "users", "regions", "districts", "farmers", "farms", "fields", "crops",
        "yield_records", "weather_records", "market_prices",
        "irrigation_records", "finance_records", "satellite_indices",
    ]
    stats: dict[str, int] = {}
    with get_engine().connect() as connection:
        for table in tables:
            stats[table] = connection.execute(
                text(f"SELECT COUNT(*) FROM {table}")  # noqa: S608 - fixed names
            ).scalar_one()
    return stats
