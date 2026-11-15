"""Daromad va xarajatlarni yozish, tarix va o'chirish.

Har bir amal avval sessiyani tekshiradi va har bir so'rov `user_id` bilan
cheklanadi: foydalanuvchi boshqa birovning yozuvini ko'ra ham, o'chira ham
olmaydi (begona `id` "topilmadi" bilan bir xil javob oladi).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone

from .auth import AuthService, Session
from .errors import NotFound, ValidationError
from .money import parse_amount
from .validation import (
    KIND_INCOME,
    parse_date,
    validate_category,
    validate_kind,
    validate_note,
)

HISTORY_LIMIT_MAX = 500

# So'rov matni o'zgarmas: filtrlar SQL satrini yig'ish orqali emas, NULL bo'lishi
# mumkin bo'lgan parametrlar orqali yoqiladi.
_HISTORY_SQL = """
    SELECT id, kind, amount_minor, category, note, occurred_on, created_at
    FROM transactions
    WHERE user_id = ?
      AND (? IS NULL OR kind = ?)
      AND (? IS NULL OR occurred_on >= ?)
      AND (? IS NULL OR occurred_on <= ?)
    ORDER BY occurred_on DESC, id DESC
    LIMIT ? OFFSET ?
"""


@dataclass(frozen=True)
class Transaction:
    id: int
    kind: str
    amount_minor: int
    category: str
    note: str
    occurred_on: date
    created_at: str

    @property
    def signed_minor(self) -> int:
        """Balansga ta'siri: daromad musbat, xarajat manfiy."""
        return self.amount_minor if self.kind == KIND_INCOME else -self.amount_minor


def _from_row(row: sqlite3.Row) -> Transaction:
    return Transaction(
        id=int(row["id"]),
        kind=row["kind"],
        amount_minor=int(row["amount_minor"]),
        category=row["category"],
        note=row["note"],
        occurred_on=date.fromisoformat(row["occurred_on"]),
        created_at=row["created_at"],
    )


class TransactionService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        auth: AuthService,
        *,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._conn = conn
        self._auth = auth
        self._today = today

    def add(
        self,
        session: Session,
        *,
        kind: object,
        amount: object,
        category: object,
        occurred_on: object = None,
        note: object = "",
    ) -> Transaction:
        """Yangi tranzaksiya. Barcha maydonlar xom (ishonchsiz) qiymat sifatida keladi."""
        self._auth.require(session)
        today = self._today()
        clean_kind = validate_kind(kind)
        amount_minor = parse_amount(amount)
        clean_category = validate_category(clean_kind, category)
        if occurred_on is None or occurred_on == "":
            when = today
        else:
            when = parse_date(occurred_on, today=today)
        clean_note = validate_note(note)
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO transactions "
                "(user_id, kind, amount_minor, category, note, occurred_on, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session.user_id,
                    clean_kind,
                    amount_minor,
                    clean_category,
                    clean_note,
                    when.isoformat(),
                    created_at,
                ),
            )
        return Transaction(
            id=int(cursor.lastrowid),
            kind=clean_kind,
            amount_minor=amount_minor,
            category=clean_category,
            note=clean_note,
            occurred_on=when,
            created_at=created_at,
        )

    def history(
        self,
        session: Session,
        *,
        kind: object = None,
        date_from: object = None,
        date_to: object = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        """Joriy foydalanuvchining tranzaksiyalari, eng yangisi birinchi."""
        self._auth.require(session)
        today = self._today()
        clean_kind = validate_kind(kind) if kind not in (None, "") else None
        start = end = None
        if date_from not in (None, ""):
            start = parse_date(date_from, today=today, field="date_from", allow_future=True)
        if date_to not in (None, ""):
            end = parse_date(date_to, today=today, field="date_to", allow_future=True)
        if start is not None and end is not None and start > end:
            raise ValidationError(
                "Davr boshi davr oxiridan keyin bo'lishi mumkin emas.", "date_from"
            )
        if not isinstance(limit, int) or not isinstance(offset, int):
            raise ValidationError("Sahifalash qiymatlari butun son bo'lishi kerak.")
        limit = max(1, min(limit, HISTORY_LIMIT_MAX))
        offset = max(0, offset)
        first_day = start.isoformat() if start else None
        last_day = end.isoformat() if end else None
        rows = self._conn.execute(
            _HISTORY_SQL,
            (
                session.user_id,
                clean_kind,
                clean_kind,
                first_day,
                first_day,
                last_day,
                last_day,
                limit,
                offset,
            ),
        ).fetchall()
        return [_from_row(row) for row in rows]

    def delete(self, session: Session, transaction_id: object) -> None:
        """Faqat o'z tranzaksiyasini o'chiradi."""
        self._auth.require(session)
        if isinstance(transaction_id, str):
            text = transaction_id.strip()
            is_number = text.isascii() and text.isdigit() and len(text) <= 19
            transaction_id = int(text) if is_number else None
        if (
            not isinstance(transaction_id, int)
            or isinstance(transaction_id, bool)
            or not 0 < transaction_id < 2**63
        ):
            raise ValidationError("Tranzaksiya raqami noto'g'ri.", "id")
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM transactions WHERE id = ? AND user_id = ?",
                (transaction_id, session.user_id),
            )
        if cursor.rowcount == 0:
            raise NotFound("Bunday tranzaksiya topilmadi.")
