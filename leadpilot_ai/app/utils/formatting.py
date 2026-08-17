"""Money / number / phone formatting helpers."""

from __future__ import annotations

import re
from decimal import Decimal

_NON_DIGIT = re.compile(r"\D+")


def fmt_money(value: float | int | Decimal | None, currency: str = "so'm") -> str:
    """Format money as ``12 500 000 so'm``."""
    if value is None:
        return "—"
    amount = int(round(float(value)))
    grouped = f"{amount:,}".replace(",", " ")
    return f"{grouped} {currency}".strip()


def fmt_number(value: float | int | None, decimals: int = 0) -> str:
    """Format a number with thin space grouping."""
    if value is None:
        return "—"
    if decimals:
        text = f"{float(value):,.{decimals}f}"
    else:
        text = f"{int(round(float(value))):,}"
    return text.replace(",", " ")


def fmt_percent(value: float | None, decimals: int = 1) -> str:
    """Format a ratio already expressed in percent units."""
    if value is None:
        return "—"
    return f"{value:.{decimals}f}%"


def fmt_duration(seconds: int | None) -> str:
    """Format a duration in seconds as ``mm:ss`` or ``h:mm:ss``."""
    if seconds is None:
        return "—"
    seconds = int(seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def normalize_phone(raw: str | None, default_country: str = "998") -> str | None:
    """Normalise a phone number to E.164-like ``+998901234567``.

    Returns ``None`` when the input contains no usable digits.
    """
    if not raw:
        return None
    digits = _NON_DIGIT.sub("", raw)
    if not digits:
        return None
    if raw.strip().startswith("+"):
        return "+" + digits
    if digits.startswith("00"):
        return "+" + digits[2:]
    if digits.startswith(default_country) and len(digits) >= 12:
        return "+" + digits
    if len(digits) == 9:  # local Uzbek number without country code
        return f"+{default_country}{digits}"
    if len(digits) == 10 and digits.startswith("0"):
        return f"+{default_country}{digits[1:]}"
    return "+" + digits


def pretty_phone(value: str | None) -> str:
    """Human friendly phone rendering: ``+998 90 123 45 67``."""
    if not value:
        return "—"
    digits = _NON_DIGIT.sub("", value)
    if len(digits) == 12 and digits.startswith("998"):
        return f"+{digits[:3]} {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:]}"
    return value


def initials(full_name: str | None) -> str:
    """Return up to two uppercase initials for an avatar chip."""
    if not full_name:
        return "?"
    parts = [p for p in full_name.split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def truncate(text: str | None, limit: int = 60) -> str:
    """Shorten a string for table cells."""
    if not text:
        return ""
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


def mask_secret(value: str | None) -> str:
    """Mask a credential so it never leaks into the UI or logs."""
    if not value:
        return ""
    if len(value) <= 6:
        return "•" * len(value)
    return value[:3] + "•" * (len(value) - 6) + value[-3:]
