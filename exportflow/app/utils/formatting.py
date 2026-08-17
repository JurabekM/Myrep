"""Date, money and text formatting helpers (Asia/Tashkent, dd.mm.yyyy)."""

from __future__ import annotations

import datetime as dt
import re
from zoneinfo import ZoneInfo

from app.config import DATE_FORMAT, DATETIME_FORMAT, DEFAULT_TIMEZONE

TZ = ZoneInfo(DEFAULT_TIMEZONE)

CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "UZS": "so'm"}


def now() -> dt.datetime:
    """Current timezone-aware timestamp in the application timezone."""
    return dt.datetime.now(TZ)


def today() -> dt.date:
    """Current date in the application timezone."""
    return now().date()


def as_aware(value: dt.datetime | None) -> dt.datetime | None:
    """Attach the application timezone to a naive datetime."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=TZ)
    return value.astimezone(TZ)


def fmt_date(value: dt.date | dt.datetime | None) -> str:
    """Format a date as ``01.08.2026``; empty string for ``None``."""
    if value is None:
        return ""
    if isinstance(value, dt.datetime):
        value = as_aware(value)
        return value.strftime(DATE_FORMAT)
    return value.strftime(DATE_FORMAT)


def fmt_datetime(value: dt.datetime | None) -> str:
    """Format a timestamp as ``01.08.2026 14:30``."""
    if value is None:
        return ""
    return as_aware(value).strftime(DATETIME_FORMAT)


def parse_date(text: str | None) -> dt.date | None:
    """Parse ``dd.mm.yyyy`` (or ISO) text into a date, returning None when invalid."""
    if not text:
        return None
    text = text.strip()
    for fmt in (DATE_FORMAT, "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def fmt_money(amount: float | int | None, currency: str = "USD", decimals: int = 2) -> str:
    """Format a monetary amount with thin thousand separators."""
    if amount is None:
        return ""
    quantized = round(float(amount), decimals)
    text = f"{quantized:,.{decimals}f}".replace(",", " ")
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    if currency == "UZS":
        return f"{text} {symbol}"
    return f"{symbol}{text}"


def fmt_number(value: float | int | None, decimals: int = 2) -> str:
    """Format a plain number with space thousand separators."""
    if value is None:
        return ""
    return f"{float(value):,.{decimals}f}".replace(",", " ")


def fmt_percent(value: float | None, decimals: int = 1) -> str:
    """Format a ratio already expressed in percent units."""
    if value is None:
        return ""
    return f"{value:.{decimals}f}%"


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, fallback: str = "item") -> str:
    """Lowercase ASCII slug usable as a file name."""
    translit = (
        text.lower()
        .replace("'", "")
        .replace("‘", "")
        .replace("’", "")
        .replace("o‘", "o")
        .replace("g‘", "g")
    )
    slug = _SLUG_RE.sub("-", translit).strip("-")
    return slug or fallback


def truncate(text: str | None, limit: int = 60) -> str:
    """Shorten a string for table display."""
    if not text:
        return ""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def days_until(target: dt.date | None) -> int | None:
    """Whole days from today until ``target`` (negative when overdue)."""
    if target is None:
        return None
    return (target - today()).days
