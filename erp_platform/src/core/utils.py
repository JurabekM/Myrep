# -*- coding: utf-8 -*-
"""
Umumiy yordamchi funksiyalar: pul (Decimal), sanalar, sahifalash,
hujjat raqamlash.

Barcha moliyaviy hisob-kitoblar ``decimal.Decimal`` bilan bajariladi —
suzuvchi nuqta (float) xatolaridan himoya.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Sequence

TWO_PLACES = Decimal("0.01")


# ---------------------------------------------------------------------- #
#  Pul / Decimal
# ---------------------------------------------------------------------- #

def D(value: Any, default: str = "0") -> Decimal:
    """
    Har qanday qiymatni xavfsiz tarzda 2 xonali Decimal ga aylantiradi.

    Bo'sh yoki yaroqsiz qiymat uchun ``default`` ishlatiladi.
    """
    if value is None or value == "":
        value = default
    try:
        if isinstance(value, float):
            value = repr(value)  # float artefaktlarini kamaytirish
        return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default).quantize(TWO_PLACES)


def money(value: Any, currency: str = "") -> str:
    """
    Pulni o'qish oson formatda qaytaradi: ``1 234 567.89``.

    Butun sonlarda kasr qismi tashlab yuboriladi: ``1 234 567``.
    """
    d = D(value)
    sign = "-" if d < 0 else ""
    d = abs(d)
    whole = int(d)
    frac = (d - whole).quantize(TWO_PLACES)
    whole_s = f"{whole:,}".replace(",", " ")
    out = whole_s if frac == 0 else f"{whole_s}.{str(frac)[2:]}"
    return f"{sign}{out} {currency}".strip()


# ---------------------------------------------------------------------- #
#  Sana / vaqt
# ---------------------------------------------------------------------- #

def now_str() -> str:
    """Joriy mahalliy vaqt: ``YYYY-MM-DD HH:MM:SS``."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    """Bugungi sana: ``YYYY-MM-DD``."""
    return date.today().isoformat()


def parse_date(value: str | None, default: date | None = None) -> date | None:
    """``YYYY-MM-DD`` matnini sanaga aylantiradi; yaroqsiz bo'lsa default."""
    if not value:
        return default
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return default


def month_bounds(year: int, month: int) -> tuple[str, str]:
    """Oyning birinchi va oxirgi kunini (ISO matn) qaytaradi."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start.isoformat(), (end - timedelta(days=1)).isoformat()


def last_n_months(n: int = 12) -> list[tuple[int, int]]:
    """Oxirgi ``n`` oy ro'yxatini (yil, oy) tartibida qaytaradi (eski -> yangi)."""
    today = date.today()
    result: list[tuple[int, int]] = []
    year, month = today.year, today.month
    for _ in range(n):
        result.append((year, month))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(result))


# ---------------------------------------------------------------------- #
#  Sahifalash (Pagination)
# ---------------------------------------------------------------------- #

@dataclass
class Page:
    """Sahifalangan natija: elementlar + navigatsiya ma'lumotlari."""

    items: list[dict] = field(default_factory=list)
    page: int = 1
    per_page: int = 25
    total: int = 0

    @property
    def pages(self) -> int:
        """Umumiy sahifalar soni (kamida 1)."""
        return max(1, -(-self.total // self.per_page))

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages


def clamp_page(page: Any, per_page: Any, max_per_page: int = 200) -> tuple[int, int]:
    """Sahifa parametrlarini xavfsiz oraliqqa keltiradi."""
    try:
        p = max(1, int(page or 1))
    except (ValueError, TypeError):
        p = 1
    try:
        pp = min(max(1, int(per_page or 25)), max_per_page)
    except (ValueError, TypeError):
        pp = 25
    return p, pp


# ---------------------------------------------------------------------- #
#  Hujjat raqamlash
# ---------------------------------------------------------------------- #

def next_document_number(db, prefix: str, width: int = 6) -> str:
    """
    Ketma-ket hujjat raqami generatsiya qiladi: ``INV-2026-000001``.

    Hisoblagichlar ``sequences`` jadvalida yil kesimida yuritiladi;
    UPSERT + RETURNING orqali poyga holatlaridan (race) himoyalangan.
    """
    year = date.today().year
    row = db.query_one(
        "INSERT INTO sequences (name, year, last_value) VALUES (?, ?, 1) "
        "ON CONFLICT (name, year) DO UPDATE SET last_value = last_value + 1 "
        "RETURNING last_value",
        (prefix, year),
    )
    value = row["last_value"] if row else 1
    return f"{prefix}-{year}-{value:0{width}d}"


# ---------------------------------------------------------------------- #
#  Turli mayda yordamchilar
# ---------------------------------------------------------------------- #

def rows_to_dicts(rows: Sequence[Any]) -> list[dict]:
    """sqlite3.Row / RealDictRow qatorlarini oddiy dict ro'yxatiga aylantiradi."""
    return [dict(r) for r in rows]


def safe_int(value: Any, default: int = 0) -> int:
    """Qiymatni xavfsiz int ga aylantiradi."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
