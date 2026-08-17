"""Number, money and date formatting helpers."""

from __future__ import annotations

from datetime import date, datetime

from app.config import BASE_CURRENCY, CURRENCY_SUFFIX, PY_DATE_FORMAT, PY_DATETIME_FORMAT
from app.utils.i18n import current_language

NBSP = " "


def group_number(value: float, decimals: int = 0) -> str:
    """Format ``value`` with non-breaking thin group separators."""
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        return "0"
    text = f"{number:,.{decimals}f}".replace(",", NBSP)
    if decimals:
        text = text.replace(".", ",")
    return text


def fmt_money(value: float | None, currency: str = BASE_CURRENCY, with_suffix: bool = True) -> str:
    """Render an amount as ``12 500 000 so'm``."""
    text = group_number(value or 0.0, 0)
    if not with_suffix:
        return text
    suffix = CURRENCY_SUFFIX.get(currency, {}).get(current_language(), currency)
    return f"{text}{NBSP}{suffix}"


def fmt_qty(value: float | None) -> str:
    """Render a quantity, dropping trailing zeros."""
    number = float(value or 0.0)
    if abs(number - round(number)) < 1e-9:
        return group_number(number, 0)
    return group_number(number, 2)


def fmt_percent(value: float | None, decimals: int = 1) -> str:
    """Render a percentage value."""
    return f"{float(value or 0.0):.{decimals}f}%".replace(".", ",")


def fmt_date(value: date | datetime | None) -> str:
    """Render a date as ``31.07.2026`` (empty string when ``None``)."""
    if value is None:
        return "—"
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime(PY_DATE_FORMAT)


def fmt_datetime(value: datetime | None) -> str:
    """Render a timestamp as ``31.07.2026 14:05``."""
    if value is None:
        return "—"
    return value.strftime(PY_DATETIME_FORMAT)


def parse_number(text: str) -> float:
    """Parse a user typed number tolerating spaces and comma decimals."""
    cleaned = (text or "").replace(NBSP, "").replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def short(text: str | None, limit: int = 60) -> str:
    """Truncate long free text for table cells."""
    value = (text or "").strip().replace("\n", " ")
    return value if len(value) <= limit else value[: limit - 1] + "…"
