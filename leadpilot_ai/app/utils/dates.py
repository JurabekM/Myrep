"""Date/time helpers.

All business timestamps are stored and displayed in the ``Asia/Tashkent``
timezone.  SQLite cannot round-trip ``tzinfo`` reliably, therefore datetimes are
kept *naive but always local to Asia/Tashkent*.  Use :func:`now` everywhere
instead of ``datetime.now()`` so the whole application shares one clock.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.config import DATE_FORMAT, DATETIME_FORMAT, TIME_FORMAT, TIMEZONE

TASHKENT = ZoneInfo(TIMEZONE)


def now() -> datetime:
    """Current wall-clock time in Asia/Tashkent as a naive datetime."""
    return datetime.now(TASHKENT).replace(tzinfo=None)


def today() -> date:
    """Current date in Asia/Tashkent."""
    return now().date()


def aware(value: datetime) -> datetime:
    """Attach the Asia/Tashkent timezone to a naive datetime."""
    return value if value.tzinfo else value.replace(tzinfo=TASHKENT)


def naive(value: datetime) -> datetime:
    """Convert any datetime into naive Asia/Tashkent local time."""
    if value.tzinfo is None:
        return value
    return value.astimezone(TASHKENT).replace(tzinfo=None)


def fmt_date(value: date | datetime | None) -> str:
    """Format as ``01.08.2026``."""
    if value is None:
        return "—"
    return value.strftime(DATE_FORMAT)


def fmt_datetime(value: datetime | None) -> str:
    """Format as ``01.08.2026 14:30``."""
    if value is None:
        return "—"
    return value.strftime(DATETIME_FORMAT)


def fmt_time(value: datetime | time | None) -> str:
    """Format as ``14:30``."""
    if value is None:
        return "—"
    return value.strftime(TIME_FORMAT)


def start_of_day(value: date | datetime) -> datetime:
    """Return 00:00:00 of the given day."""
    d = value.date() if isinstance(value, datetime) else value
    return datetime.combine(d, time.min)


def end_of_day(value: date | datetime) -> datetime:
    """Return 23:59:59.999999 of the given day."""
    d = value.date() if isinstance(value, datetime) else value
    return datetime.combine(d, time.max)


def start_of_week(value: date | None = None) -> date:
    """Monday of the week that contains ``value``."""
    d = value or today()
    return d - timedelta(days=d.weekday())


def humanize_delta(value: datetime | None, reference: datetime | None = None) -> str:
    """Return a short relative description such as ``5 daq`` or ``2 kun``."""
    if value is None:
        return "—"
    ref = reference or now()
    delta = ref - value
    seconds = int(delta.total_seconds())
    if seconds < 0:
        seconds = abs(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


def parse_hhmm(value: str) -> time:
    """Parse ``HH:MM`` into a :class:`datetime.time` (fallback 09:00)."""
    try:
        hour, minute = value.strip().split(":")
        return time(int(hour), int(minute))
    except Exception:
        return time(9, 0)


def minutes_between(start: datetime, end: datetime) -> int:
    """Whole minutes between two datetimes."""
    return int((end - start).total_seconds() // 60)
