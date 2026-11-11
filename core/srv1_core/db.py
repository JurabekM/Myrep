"""SQLite (WAL) + SQLAlchemy 2 async. Sxema versiyasi `schema_version` jadvalida."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override

from sqlalchemy import JSON, DateTime, Dialect, String, event, select
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import ConnectionPoolEntry
from sqlalchemy.types import TypeDecorator

SCHEMA_VERSION = 1


class SchemaMismatchError(RuntimeError):
    """Bazadagi sxema versiyasi kod kutgan versiyadan farq qiladi."""


class UtcDateTime(TypeDecorator[datetime]):
    """Faqat tz-aware vaqtni qabul qiladi; SQLite'dan o'qiganda UTC ni qaytarib qo'yadi."""

    impl = DateTime
    cache_ok = True

    @override
    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime qabul qilinmaydi; tzinfo bering")
        return value.astimezone(UTC).replace(tzinfo=None)

    @override
    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    pass


class SchemaVersion(Base):
    __tablename__ = "schema_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int]


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str] = mapped_column(String(512))
    ok: Mapped[bool]
    detail: Mapped[dict[str, Any]] = mapped_column(JSON)


def _set_pragmas(dbapi_connection: DBAPIConnection, _record: ConnectionPoolEntry) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


class Database:
    """Bitta SQLite fayli ustidagi async dvigatel va sessiya fabrikasi."""

    def __init__(self, db_file: Path) -> None:
        self._db_file = db_file
        self._engine: AsyncEngine | None = None
        self._sessions: async_sessionmaker[AsyncSession] | None = None

    async def start(self) -> None:
        engine = create_async_engine(f"sqlite+aiosqlite:///{self._db_file.as_posix()}")
        event.listen(engine.sync_engine, "connect", _set_pragmas)
        self._engine = engine
        self._sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await self._check_schema_version()

    async def stop(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._sessions = None

    def session(self) -> AsyncSession:
        if self._sessions is None:
            raise RuntimeError("Database.start() chaqirilmagan")
        return self._sessions()

    async def journal_mode(self) -> str:
        async with self.session() as session:
            result = await session.connection()
            row = (await result.exec_driver_sql("PRAGMA journal_mode")).scalar_one()
            return str(row)

    async def _check_schema_version(self) -> None:
        async with self.session() as session, session.begin():
            current = await session.scalar(select(SchemaVersion.version))
            if current is None:
                session.add(SchemaVersion(id=1, version=SCHEMA_VERSION))
            elif current != SCHEMA_VERSION:
                raise SchemaMismatchError(
                    f"baza sxemasi v{current}, kod v{SCHEMA_VERSION} kutadi; migratsiya kerak"
                )
