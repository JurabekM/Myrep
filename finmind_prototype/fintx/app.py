"""Ilova yadrosi: baza ulanishi va xizmatlarni bir joyga yig'adi.

Terminal va desktop interfeyslari aynan shu obyekt orqali ishlaydi, shuning
uchun tekshiruv va xavfsizlik qoidalari ikkalasida bir xil.
"""

from __future__ import annotations

import os
import sqlite3
import time
from collections.abc import Callable
from datetime import date
from typing import Any

from . import db
from .auth import IDLE_TIMEOUT_SECONDS, AuthService, Session
from .reports import Report, build_report
from .security import PasswordHasher
from .transactions import HISTORY_LIMIT_MAX, Transaction, TransactionService

# Hisobot bitta so'rovda o'qiydigan tranzaksiyalar soni chegarasi.
_REPORT_PAGE = HISTORY_LIMIT_MAX


class App:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        hasher: PasswordHasher | None = None,
        clock: Callable[[], float] = time.time,
        today: Callable[[], date] = date.today,
        idle_timeout: float = IDLE_TIMEOUT_SECONDS,
    ) -> None:
        self.conn = conn
        self.auth = AuthService(conn, hasher=hasher, clock=clock, idle_timeout=idle_timeout)
        self.transactions = TransactionService(conn, self.auth, today=today)
        self.today = today

    @classmethod
    def open(cls, path: str | os.PathLike[str] | None = None, **options: Any) -> App:
        """Bazani ochadi; `options` — konstruktorning kalit so'zli parametrlari."""
        return cls(db.connect(path), **options)

    def report(
        self, session: Session, *, date_from: object = None, date_to: object = None
    ) -> Report:
        """Tanlangan davr (yoki butun tarix) bo'yicha hisobot."""
        collected: list[Transaction] = []
        offset = 0
        while True:
            page = self.transactions.history(
                session,
                date_from=date_from,
                date_to=date_to,
                limit=_REPORT_PAGE,
                offset=offset,
            )
            collected.extend(page)
            if len(page) < _REPORT_PAGE:
                break
            offset += _REPORT_PAGE
        return build_report(collected)

    def close(self) -> None:
        self.conn.close()
