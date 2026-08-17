# -*- coding: utf-8 -*-
"""
exporters/exporter.py
=====================
Ajratib olingan ma'lumotlarni turli formatlarga eksport qilish:

    - CSV
    - XLSX (Excel)
    - JSON
    - SQLite (alohida fayl)
    - PostgreSQL (SQLAlchemy orqali)

Ma'lumotlar dinamik strukturaga ega bo'lgani uchun (har xil kalitlar),
pandas DataFrame yordamida normalizatsiya qilinadi.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import DATA_DIR
from logs.logger import get_logger

log = get_logger(__name__)


def _flatten(record: dict[str, Any]) -> dict[str, Any]:
    """Ichma-ich (nested) qiymatlarni JSON string ga aylantiradi (jadval uchun)."""
    flat: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, (dict, list)):
            flat[key] = json.dumps(value, ensure_ascii=False, default=str)
        else:
            flat[key] = value
    return flat


class Exporter:
    """Ma'lumotlarni turli formatlarga eksport qiluvchi klass."""

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data or []

    def _dataframe(self) -> pd.DataFrame:
        """Ma'lumotlarni normalizatsiya qilib DataFrame qaytaradi."""
        if not self.data:
            return pd.DataFrame()
        return pd.DataFrame([_flatten(r) for r in self.data])

    # -----------------------------------------------------------------
    def to_csv(self, path: str | Path) -> Path:
        """CSV formatiga eksport qiladi."""
        path = Path(path)
        self._dataframe().to_csv(path, index=False, encoding="utf-8-sig")
        log.info("CSV eksport qilindi: {} ({} yozuv)", path, len(self.data))
        return path

    def to_xlsx(self, path: str | Path) -> Path:
        """XLSX (Excel) formatiga eksport qiladi."""
        path = Path(path)
        self._dataframe().to_excel(path, index=False, engine="openpyxl")
        log.info("XLSX eksport qilindi: {} ({} yozuv)", path, len(self.data))
        return path

    def to_json(self, path: str | Path) -> Path:
        """JSON formatiga eksport qiladi (chiroyli formatlangan)."""
        path = Path(path)
        path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        log.info("JSON eksport qilindi: {} ({} yozuv)", path, len(self.data))
        return path

    def to_sqlite(self, path: str | Path, table: str = "results") -> Path:
        """Alohida SQLite fayliga eksport qiladi."""
        path = Path(path)
        conn = sqlite3.connect(str(path))
        try:
            self._dataframe().to_sql(table, conn, if_exists="replace", index=False)
        finally:
            conn.close()
        log.info("SQLite eksport qilindi: {} (jadval: {})", path, table)
        return path

    def to_postgresql(self, connection_url: str, table: str = "results") -> None:
        """PostgreSQL bazasiga eksport qiladi."""
        from sqlalchemy import create_engine
        engine = create_engine(connection_url)
        try:
            self._dataframe().to_sql(table, engine, if_exists="append", index=False)
            log.info("PostgreSQL'ga eksport qilindi (jadval: {})", table)
        finally:
            engine.dispose()

    # -----------------------------------------------------------------
    def export(self, fmt: str, path: str | Path | None = None) -> Path | None:
        """
        Formatga qarab mos eksport usulini chaqiradi.

        Args:
            fmt: csv | xlsx | json | sqlite
            path: chiqish fayli (bo'lmasa data/ ichida avtomatik yaratiladi).
        """
        fmt = fmt.lower()
        if path is None:
            path = DATA_DIR / f"export.{fmt}"
        dispatch = {
            "csv": self.to_csv,
            "xlsx": self.to_xlsx,
            "json": self.to_json,
            "sqlite": self.to_sqlite,
        }
        func = dispatch.get(fmt)
        if not func:
            log.error("Noma'lum eksport formati: {}", fmt)
            return None
        return func(path)
