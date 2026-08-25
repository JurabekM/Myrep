"""Lokal SQLite bazasi — engine, sessiya va PRAGMA sozlamalari.

Bu yagona haqiqat manbai. Broker emas, server emas — shu fayl.
Shuning uchun WAL, foreign_keys va zaxira nusxa jiddiy qaraladi.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Barcha jadvallar uchun asos."""


def _configure_connection(dbapi_connection: Any, _record: Any) -> None:
    """Har bir ulanish uchun PRAGMA. SQLAlchemy pool ulanishni qayta
    ishlatgani uchun buni ulanish ochilganda qo'yish SHART."""
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    try:
        # WAL: o'qish yozishni bloklamaydi — UI fon sinxronizatsiyasi
        # ishlayotganda ham javob beradi.
        cursor.execute("PRAGMA journal_mode=WAL")
        # SQLite'da foreign key TEKSHIRUVI DEFAULT O'CHIQ. Yoqmasak
        # ma'lumot yaxlitligi jimgina buziladi.
        cursor.execute("PRAGMA foreign_keys=ON")
        # NORMAL + WAL = xavfsiz va tez (crash'da tranzaksiya yo'qolmaydi).
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Baza vaqtincha lock bo'lsa darhol xato bermasin (sync worker).
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        # Manfiy qiymat = KiB. 64 MiB sahifa keshi.
        cursor.execute("PRAGMA cache_size=-65536")
    finally:
        cursor.close()


def create_database_engine(path: Path | str, *, echo: bool = False) -> Engine:
    """Fayl bazasi uchun engine yaratadi va PRAGMA'larni ulaydi."""
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite+pysqlite:///{path}",
        echo=echo,
        future=True,
        # SQLite ulanishini oqimlar orasida ishlatishga ruxsat: PySide6
        # fon worker'lari uchun kerak. Xavfsizlik sessiya darajasida
        # ta'minlanadi (har worker o'z sessiyasini oladi).
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", _configure_connection)
    return engine


def create_memory_engine() -> Engine:
    """Test uchun xotiradagi baza (bitta ulanish, umumiy kesh)."""
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", _configure_connection)
    return engine


class Database:
    """Engine + sessiya fabrikasi. Unit-of-work chegarasini beradi."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._session_factory = sessionmaker(
            bind=engine, expire_on_commit=False, future=True
        )

    @classmethod
    def open(cls, path: Path | str, *, echo: bool = False) -> Database:
        return cls(create_database_engine(path, echo=echo))

    @classmethod
    def in_memory(cls) -> Database:
        return cls(create_memory_engine())

    def create_all(self) -> None:
        """Jadvallarni yaratadi — FAQAT test va vositalar uchun.

        Bu chaqiruv Alembic tarixini bilmaydi (`alembic_version` yozilmaydi).
        Ishlayotgan dastur bazasini shu bilan boshqarmaydi —
        `distribos.persistence.migrations.ensure_schema()` ishlatadi,
        chunki foydalanuvchi bazasi yangilanishda ustunlarni yo'qotmasligi
        kerak, `create_all()` esa faqat "hali yo'q" jadvallarni yaratadi.
        """
        from distribos.persistence import models  # noqa: F401  (jadvallarni ro'yxatga oladi)

        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        """Yangi sessiya. Chaqiruvchi o'zi yopadi."""
        return self._session_factory()

    @contextmanager
    def unit_of_work(self) -> Iterator[Session]:
        """Atomar tranzaksiya.

        Biznes o'zgarishi VA outbox yozuvi SHU chegara ichida bo'lishi SHART
        (topshiriq §7.1) — aks holda hodisa yo'qoladi yoki ikki marta
        yuboriladi.
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def checkpoint_wal(self) -> None:
        """WAL faylini asosiy bazaga yozadi (zaxira nusxadan oldin SHART)."""
        with self.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")

    def integrity_check(self) -> tuple[bool, str]:
        """Baza yaxlitligini tekshiradi (restore va diagnostika uchun)."""
        with self.engine.connect() as connection:
            result = connection.exec_driver_sql("PRAGMA integrity_check").scalar()
        text = str(result)
        return text == "ok", text

    def dispose(self) -> None:
        self.engine.dispose()
