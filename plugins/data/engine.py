"""DuckDB mexanizmi: to'plamlar ustida faqat o'qiydigan so'rovlar, xotira chegarasi bilan.

Xavfsizlik:
- tashqi fayllarga murojaat yopiq (`enable_external_access = false`), ruxsat faqat
  plaginning `datasets`, `exports` va vaqtinchalik papkalariga; sozlama qulflangan;
- foydalanuvchi so'rovi aynan bitta `SELECT` turidagi ifoda bo'lishi shart
  (`SUMMARIZE` va `DESCRIBE` ham shu turga kiradi) — `COPY`, `ATTACH`, `INSTALL`,
  `SET` va boshqalar rad etiladi.

Sinxron kod: `asyncio.to_thread` bilan chaqiriladi; `interrupt()` boshqa oqimdan xavfsiz.
"""

import math
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from datetime import time as clock
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from .models import Column, DataConfig

CELL_MAX_CHARS = 500
_ALLOWED = (duckdb.StatementType.SELECT, duckdb.StatementType.EXPLAIN)


class QueryError(Exception):
    """So'rov bajarilmadi; `status` — klientga qaytadigan HTTP kodi."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True, slots=True)
class QueryResult:
    columns: list[Column]
    rows: list[list[Any]]
    truncated: bool
    seconds: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "columns": [column.model_dump() for column in self.columns],
            "rows": self.rows,
            "truncated": self.truncated,
            "seconds": self.seconds,
        }


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def quote_literal(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def to_json(value: Any) -> Any:  # noqa: ANN401 — DuckDB qiymat turlari ko'p
    """DuckDB qiymatini JSON'ga mos ko'rinishga keltiradi."""
    if value is None or isinstance(value, bool | int | str):
        if isinstance(value, str) and len(value) > CELL_MAX_CHARS:
            return value[: CELL_MAX_CHARS - 1] + "…"
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        return float(value) if value.is_finite() else None
    if isinstance(value, datetime | date | clock):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, bytes | bytearray):
        return f"<{len(value)} bayt>"
    return to_json(str(value))


def check_statement(sql: str) -> str:
    """So'rov aynan bitta o'qiydigan ifoda ekanini tekshiradi va uni qaytaradi."""
    text = sql.strip().rstrip(";").strip()
    if not text:
        raise QueryError(400, "so'rov bo'sh")
    try:
        statements = duckdb.extract_statements(text)
    except duckdb.Error as exc:
        raise QueryError(400, f"SQL xatosi: {str(exc)[:400]}") from exc
    if len(statements) != 1:
        raise QueryError(400, "bir vaqtda faqat bitta so'rov bajariladi")
    if statements[0].type not in _ALLOWED:
        kind = statements[0].type.name
        raise QueryError(403, f"faqat SELECT so'rovlariga ruxsat bor ({kind} mumkin emas)")
    return text


class Engine:
    def __init__(
        self, cfg: DataConfig, datasets_dir: Path, exports_dir: Path, tmp_dir: Path
    ) -> None:
        self._cfg = cfg
        self._datasets_dir = datasets_dir
        self._exports_dir = exports_dir
        self._db = duckdb.connect(":memory:")
        # So'rov alohida kursorda ishlaydi; to'xtatish buyrug'i aynan unga berilishi kerak.
        self._active: duckdb.DuckDBPyConnection | None = None
        allowed = ", ".join(
            quote_literal(directory.as_posix())
            for directory in (datasets_dir, exports_dir, tmp_dir)
        )
        for statement in (
            f"SET memory_limit = {quote_literal(cfg.memory_limit)}",
            f"SET threads = {cfg.threads}",
            f"SET temp_directory = {quote_literal(tmp_dir.as_posix())}",
            f"SET max_temp_directory_size = {quote_literal(cfg.temp_limit)}",
            "SET autoinstall_known_extensions = false",
            "SET autoload_known_extensions = false",
            f"SET allowed_directories = [{allowed}]",
            "SET enable_external_access = false",
            "SET lock_configuration = true",
        ):
            self._db.execute(statement)

    def close(self) -> None:
        self._db.close()

    def interrupt(self) -> None:
        """Bajarilayotgan so'rovni to'xtatadi (boshqa oqimdan chaqiriladi)."""
        active = self._active
        if active is not None:
            active.interrupt()
        self._db.interrupt()

    def version(self) -> str:
        return str(duckdb.__version__)

    # --- to'plamlar ---------------------------------------------------------
    def dataset_file(self, name: str) -> Path:
        return self._datasets_dir / f"{name}.parquet"

    def register(self, name: str) -> None:
        """To'plamni SQL'da `name` nomli jadval (view) sifatida ko'rinadigan qiladi."""
        path = quote_literal(self.dataset_file(name).as_posix())
        # Nom va yo'l qo'shtirnoqlanadi; nom NAME_PATTERN bilan cheklangan.
        view = quote_identifier(name)
        self._db.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet({path})")  # noqa: S608

    def unregister(self, name: str) -> None:
        self._db.execute(f"DROP VIEW IF EXISTS {quote_identifier(name)}")

    # --- so'rovlar ----------------------------------------------------------
    def _execute(self, sql: str) -> duckdb.DuckDBPyConnection:
        cursor = self._db.cursor()
        self._active = cursor
        try:
            cursor.execute(sql)
        except duckdb.InterruptException as exc:
            raise QueryError(408, "so'rov vaqt chegarasidan oshdi va to'xtatildi") from exc
        except duckdb.OutOfMemoryException as exc:
            limit = self._cfg.memory_limit
            raise QueryError(507, f"so'rovga xotira yetmadi (chegara {limit})") from exc
        except duckdb.PermissionException as exc:
            raise QueryError(403, "tashqi fayl yoki manbaga murojaat taqiqlangan") from exc
        except duckdb.Error as exc:
            raise QueryError(400, f"SQL xatosi: {str(exc)[:400]}") from exc
        return cursor

    def query(self, sql: str, limit: int, offset: int = 0) -> QueryResult:
        """Bitta `SELECT` ni bajaradi; `offset` dan boshlab ko'pi bilan `limit` qator qaytaradi."""
        text = check_statement(sql)
        started = time.perf_counter()
        cursor = self._execute(text)
        try:
            description = cursor.description or []
            columns = [Column(name=str(item[0]), type=str(item[1])) for item in description]
            remaining = offset
            while remaining > 0:
                skipped = cursor.fetchmany(min(remaining, 10_000))
                if not skipped:
                    break
                remaining -= len(skipped)
            fetched = cursor.fetchmany(limit + 1)
        except duckdb.InterruptException as exc:
            raise QueryError(408, "so'rov vaqt chegarasidan oshdi va to'xtatildi") from exc
        except duckdb.OutOfMemoryException as exc:
            limit_text = self._cfg.memory_limit
            raise QueryError(507, f"so'rovga xotira yetmadi (chegara {limit_text})") from exc
        except duckdb.Error as exc:
            raise QueryError(400, f"SQL xatosi: {str(exc)[:400]}") from exc
        finally:
            cursor.close()
        rows = [[to_json(value) for value in row] for row in fetched[:limit]]
        seconds = round(time.perf_counter() - started, 3)
        return QueryResult(columns, rows, truncated=len(fetched) > limit, seconds=seconds)

    def copy_to(self, sql: str, target: Path, *, parquet: bool) -> int:
        """`SELECT` natijasini faylga yozadi (CSV yoki Parquet) va qatorlar sonini qaytaradi."""
        text = check_statement(sql)
        options = "(FORMAT parquet, COMPRESSION zstd)" if parquet else "(FORMAT csv, HEADER)"
        path = quote_literal(target.as_posix())
        cursor = self._execute(f"COPY ({text}) TO {path} {options}")
        try:
            row = cursor.fetchone()
        finally:
            cursor.close()
        return int(row[0]) if row else 0
