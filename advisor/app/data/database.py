"""SQLite ulanish menejeri — thread-safe, WAL rejimi.

PyQt UI thread'i va fon workerlari bir vaqtda bazaga murojaat qilgani uchun
ulanish har bir thread uchun alohida ochiladi (SQLite obyektlari thread'lar
aro almashtirilmaydi). WAL rejimi bir vaqtli o'qish/yozishni yaxshilaydi.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from app.core.logging_setup import get_logger

logger = get_logger(__name__)


class Database:
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._local = threading.local()
        self._init_lock = threading.Lock()

    def connection(self) -> sqlite3.Connection:
        """Joriy thread uchun ulanishni qaytaradi (kerak bo'lsa ochadi)."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                self._db_path,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return conn

    def executescript(self, script: str) -> None:
        conn = self.connection()
        with conn:
            conn.executescript(script)

    def close_all(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None
