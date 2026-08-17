# -*- coding: utf-8 -*-
"""
Ma'lumotlar bazasi ulanish qatlami.

* Standart — SQLite (hech qanday server kerak emas, WAL rejimida).
* ``psycopg2`` o'rnatilgan va PostgreSQL serveri javob bersa — avtomatik
  PostgreSQL ga ulanadi (``database.engine: auto``).
* Ikkala dvigatel ham bitta interfeys orqali ishlaydi; SQL so'rovlar
  ``?`` placeholderlarida yoziladi (PostgreSQL uchun avtomatik ``%s`` ga
  o'giriladi).

SQL injection himoyasi: BARCHA so'rovlar faqat parametrlangan holda bajariladi.
Jadval/ustun nomlari faqat koddan keladi va identifikator regex bilan tekshiriladi.
"""
from __future__ import annotations

import re
import sqlite3
import threading
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator, Sequence

from src.core.logger import get_logger

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _check_identifier(name: str) -> str:
    """Jadval/ustun nomi xavfsiz identifikator ekanligini tasdiqlaydi."""
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Yaroqsiz SQL identifikator: {name!r}")
    return name


class BaseDatabase:
    """
    Umumiy database interfeysi (SQLite va PostgreSQL uchun bitta API).

    Barcha metodlar thread-safe: bitta umumiy ulanish RLock bilan himoyalanadi.
    """

    engine: str = "base"
    placeholder: str = "?"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tx_depth = 0
        self._log = get_logger("db")

    # -- quyi darajadagi bajarish (dvigatelga xos) ---------------------- #

    def _execute(self, sql: str, params: Sequence[Any]) -> Any:
        """Kursorda so'rovni bajaradi va kursorni qaytaradi (override qilinadi)."""
        raise NotImplementedError

    def _prepare(self, sql: str) -> str:
        """SQL placeholderlarini dvigatel formatiga keltiradi."""
        return sql

    # -- ochiq API ------------------------------------------------------ #

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[dict]:
        """SELECT (yoki RETURNING) natijasini dict ro'yxati sifatida qaytaradi."""
        with self._lock:
            cur = self._execute(self._prepare(sql), params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> dict | None:
        """Bitta qator qaytaradi yoki None."""
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql: str, params: Sequence[Any] = (), default: Any = None) -> Any:
        """Birinchi qatorning birinchi ustunini qaytaradi."""
        row = self.query_one(sql, params)
        if not row:
            return default
        return next(iter(row.values()), default)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        """INSERT/UPDATE/DELETE bajaradi; ta'sirlangan qatorlar sonini qaytaradi."""
        with self._lock:
            cur = self._execute(self._prepare(sql), params)
            return cur.rowcount if cur.rowcount is not None else 0

    def executemany(self, sql: str, seq_params: Sequence[Sequence[Any]]) -> None:
        """Bitta so'rovni ko'p parametr to'plamlari bilan bajaradi."""
        prepared = self._prepare(sql)
        with self._lock:
            for params in seq_params:
                self._execute(prepared, params)

    def insert(self, table: str, data: dict[str, Any]) -> int:
        """
        Qator qo'shadi va yangi ``id`` ni qaytaradi.

        Ustun nomlari identifikator tekshiruvidan o'tadi — injection imkonsiz.
        """
        table = _check_identifier(table)
        cols = [_check_identifier(c) for c in data.keys()]
        placeholders = ", ".join(["?"] * len(cols))
        sql = (
            f"INSERT INTO {table} ({', '.join(cols)}) "
            f"VALUES ({placeholders}) RETURNING id"
        )
        with self._lock:
            cur = self._execute(self._prepare(sql), tuple(data.values()))
            row = cur.fetchone()
            return int(dict(row)["id"]) if row else 0

    def insert_no_id(self, table: str, data: dict[str, Any]) -> int:
        """``id`` ustuni bo'lmagan jadvalga qator qo'shadi (masalan, settings)."""
        table = _check_identifier(table)
        cols = [_check_identifier(c) for c in data.keys()]
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
        return self.execute(sql, tuple(data.values()))

    def update(self, table: str, data: dict[str, Any], where: str,
               params: Sequence[Any] = ()) -> int:
        """Qatorlarni yangilaydi; ta'sirlangan qatorlar sonini qaytaradi."""
        table = _check_identifier(table)
        sets = ", ".join(f"{_check_identifier(c)} = ?" for c in data.keys())
        sql = f"UPDATE {table} SET {sets} WHERE {where}"
        return self.execute(sql, tuple(data.values()) + tuple(params))

    def delete(self, table: str, where: str, params: Sequence[Any] = ()) -> int:
        """Qatorlarni o'chiradi; ta'sirlangan qatorlar sonini qaytaradi."""
        table = _check_identifier(table)
        return self.execute(f"DELETE FROM {table} WHERE {where}", params)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """
        Tranzaksiya konteksti. Ichma-ich chaqiruvlar qo'llab-quvvatlanadi
        (faqat eng tashqi blok COMMIT/ROLLBACK qiladi)::

            with db.transaction():
                db.insert(...)
                db.update(...)
        """
        with self._lock:
            self._tx_depth += 1
            is_outer = self._tx_depth == 1
            if is_outer:
                self._execute("BEGIN", ())
            try:
                yield
                if is_outer:
                    self._execute("COMMIT", ())
            except Exception:
                if is_outer:
                    try:
                        self._execute("ROLLBACK", ())
                    except Exception:  # noqa: BLE001
                        pass
                raise
            finally:
                self._tx_depth -= 1

    def table_names(self) -> list[str]:
        """Bazadagi jadval nomlari (selfcheck va monitoring uchun)."""
        raise NotImplementedError

    def close(self) -> None:
        """Ulanishni yopadi."""
        raise NotImplementedError


class SQLiteDatabase(BaseDatabase):
    """SQLite dvigateli: bitta fayl, WAL rejimi, Decimal qo'llab-quvvatlash."""

    engine = "sqlite"

    def __init__(self, db_path: Path) -> None:
        super().__init__()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # DECIMAL ustunlar avtomatik Decimal bo'lib o'qiladi
        sqlite3.register_adapter(Decimal, str)
        sqlite3.register_converter("DECIMAL", lambda b: Decimal(b.decode("ascii")))
        self._conn = sqlite3.connect(
            str(db_path),
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level=None,  # autocommit; tranzaksiyalar qo'lda (BEGIN)
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self.path = db_path
        self._log.info("SQLite ulanish ochildi: %s", db_path)

    def _execute(self, sql: str, params: Sequence[Any]) -> sqlite3.Cursor:
        return self._conn.execute(sql, tuple(params))

    def table_names(self) -> list[str]:
        rows = self.query(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [r["name"] for r in rows]

    def backup_to(self, dest_path: Path) -> None:
        """Bazani xavfsiz nusxalaydi (SQLite online backup API, WAL bilan mos)."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            dest = sqlite3.connect(str(dest_path))
            try:
                self._conn.backup(dest)
            finally:
                dest.close()

    def reopen(self) -> None:
        """
        Ulanishni yopib, o'sha faylga qayta ochadi (restore dan keyin).

        Barcha servislar shu obyektga havola saqlagani uchun almashtirish
        shaffof kechadi.
        """
        with self._lock:
            self._conn.close()
            self._conn = sqlite3.connect(
                str(self.path),
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES,
                isolation_level=None,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA busy_timeout = 5000")

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class PostgresDatabase(BaseDatabase):
    """PostgreSQL dvigateli (psycopg2 mavjud bo'lsa avtomatik tanlanadi)."""

    engine = "postgresql"

    def __init__(self, dsn: dict[str, Any]) -> None:
        super().__init__()
        import psycopg2
        import psycopg2.extras

        self._conn = psycopg2.connect(
            host=dsn["host"], port=dsn["port"], dbname=dsn["dbname"],
            user=dsn["user"], password=dsn["password"],
        )
        self._conn.autocommit = True
        self._cursor_factory = psycopg2.extras.RealDictCursor
        self._log.info("PostgreSQL ulanish ochildi: %s@%s/%s",
                       dsn["user"], dsn["host"], dsn["dbname"])

    def _prepare(self, sql: str) -> str:
        # Kod bo'ylab literal '?' SQL matnlarida ishlatilmaydi — bu shartnoma.
        return sql.replace("?", "%s")

    def _execute(self, sql: str, params: Sequence[Any]):
        cur = self._conn.cursor(cursor_factory=self._cursor_factory)
        cur.execute(sql, tuple(params))
        return cur

    def table_names(self) -> list[str]:
        rows = self.query(
            "SELECT table_name AS name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        return [r["name"] for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def create_database(config, base_dir: Path) -> BaseDatabase:
    """
    Konfiguratsiyaga qarab database yaratadi.

    ``engine: auto`` — PostgreSQL ga ulanishga harakat qiladi, imkoni
    bo'lmasa SQLite ga qaytadi (fallback). Hech qanday xato foydalanuvchiga
    to'siq bo'lmaydi — tizim doim ishga tushadi.
    """
    log = get_logger("db")
    engine = str(config.get("database.engine", "auto")).lower()

    if engine in ("auto", "postgresql"):
        try:
            import psycopg2  # noqa: F401

            dsn = {
                "host": config.get("database.postgresql.host", "localhost"),
                "port": config.get("database.postgresql.port", 5432),
                "dbname": config.get("database.postgresql.dbname", "uzerp"),
                "user": config.get("database.postgresql.user", "postgres"),
                "password": config.get("database.postgresql.password", ""),
            }
            try:
                return PostgresDatabase(dsn)
            except Exception:
                # Baza mavjud bo'lmasa — yaratishga urinamiz
                _try_create_pg_database(dsn)
                return PostgresDatabase(dsn)
        except Exception as exc:  # noqa: BLE001
            if engine == "postgresql":
                log.error("PostgreSQL ulanish xatosi: %s — SQLite ishlatiladi.", exc)
            else:
                log.info("PostgreSQL topilmadi (%s) — SQLite ishlatiladi.",
                         type(exc).__name__)

    sqlite_rel = config.get("database.sqlite_path", "data/erp.db")
    return SQLiteDatabase(base_dir / sqlite_rel)


def _try_create_pg_database(dsn: dict[str, Any]) -> None:
    """PostgreSQL da baza mavjud bo'lmasa uni yaratishga urinadi."""
    import psycopg2

    conn = psycopg2.connect(
        host=dsn["host"], port=dsn["port"], dbname="postgres",
        user=dsn["user"], password=dsn["password"],
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (dsn["dbname"],)
            )
            if not cur.fetchone():
                # Identifikator sifatida qo'shish uchun xavfsiz ekranlash
                dbname = dsn["dbname"].replace('"', '""')
                cur.execute(f'CREATE DATABASE "{dbname}"')
    finally:
        conn.close()
