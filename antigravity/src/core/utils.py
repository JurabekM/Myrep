"""Utility functions for the Enterprise ERP platform.

Provides a curated set of helpers for common operations including:

- **ID generation**: UUIDs and formatted document codes.
- **Formatting**: Currency, date, and datetime display strings.
- **Validation**: Email and phone number pattern checks.
- **Text processing**: Slugification and truncation.
- **Type coercion**: Safe int/float casting with defaults.
- **Path helpers**: Canonical project directory accessors and directory
  bootstrapping.

All functions are stateless and side-effect-free unless explicitly noted
(e.g. :func:`ensure_directories`).
"""

import re
import uuid
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Union

from .constants import DATE_FORMAT, DATETIME_FORMAT


# ---------------------------------------------------------------------------
# ID / code generation
# ---------------------------------------------------------------------------

def generate_uuid() -> str:
    """Generate a new UUID4 string.

    Returns:
        A lowercase hex UUID string (e.g. ``'a1b2c3d4-...'``).
    """
    return str(uuid.uuid4())


def generate_code(prefix: str, number: int) -> str:
    """Generate a formatted document code.

    Args:
        prefix: Short alphabetic prefix (e.g. ``'INV'``, ``'SO'``).
        number: Sequential number to embed.

    Returns:
        Formatted code string (e.g. ``'INV-00001'``).
    """
    return f'{prefix}-{number:05d}'


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_currency(amount: float, currency: str = 'UZS') -> str:
    """Format a monetary amount with thousands separators.

    Args:
        amount: Numeric amount to format.
        currency: ISO 4217 currency code appended to the result.

    Returns:
        Formatted string (e.g. ``'1,234,567.00 UZS'``).
    """
    return f'{amount:,.2f} {currency}'


def format_date(dt: Union[date, datetime, None]) -> str:
    """Format a date or datetime using the standard date pattern.

    Args:
        dt: A :class:`date` or :class:`datetime` instance, or ``None``.

    Returns:
        Formatted date string, or empty string if *dt* is ``None``.
    """
    if dt is None:
        return ''
    return dt.strftime(DATE_FORMAT)


def format_datetime(dt: Union[datetime, None]) -> str:
    """Format a datetime using the standard datetime pattern.

    Args:
        dt: A :class:`datetime` instance, or ``None``.

    Returns:
        Formatted datetime string, or empty string if *dt* is ``None``.
    """
    if dt is None:
        return ''
    return dt.strftime(DATETIME_FORMAT)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

_PHONE_RE = re.compile(
    r'^\+?[1-9]\d{6,14}$'
)


def validate_email(email: str) -> bool:
    """Check whether *email* matches a standard email pattern.

    Args:
        email: The email address string to validate.

    Returns:
        ``True`` if the format is valid, ``False`` otherwise.
    """
    if not email or not isinstance(email, str):
        return False
    return bool(_EMAIL_RE.match(email.strip()))


def validate_phone(phone: str) -> bool:
    """Check whether *phone* matches an international phone pattern.

    Accepts optional leading ``+`` followed by 7–15 digits.

    Args:
        phone: The phone number string to validate.

    Returns:
        ``True`` if the format is valid, ``False`` otherwise.
    """
    if not phone or not isinstance(phone, str):
        return False
    # Strip common separators before matching
    cleaned = re.sub(r'[\s\-().]+', '', phone.strip())
    return bool(_PHONE_RE.match(cleaned))


# ---------------------------------------------------------------------------
# Text processing
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Convert arbitrary text into a URL-safe slug.

    Performs NFKD normalisation, strips non-ASCII characters, lowercases,
    and replaces whitespace/special characters with hyphens.

    Args:
        text: The input string to slugify.

    Returns:
        A lowercase, hyphen-separated slug string.
    """
    if not text:
        return ''
    # Normalise unicode and strip accents
    normalised = unicodedata.normalize('NFKD', text)
    ascii_text = normalised.encode('ascii', 'ignore').decode('ascii')
    # Lowercase and replace non-alphanumeric chars with hyphens
    slug = re.sub(r'[^\w\s-]', '', ascii_text).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug


def truncate(text: str, length: int = 50, suffix: str = '...') -> str:
    """Truncate *text* to *length* characters, appending *suffix* if cut.

    Args:
        text: The input string.
        length: Maximum length of the returned string (including suffix).
        suffix: String appended when truncation occurs.

    Returns:
        The original string if short enough, otherwise a truncated version
        ending with *suffix*.
    """
    if not text or len(text) <= length:
        return text or ''
    return text[: length - len(suffix)] + suffix


# ---------------------------------------------------------------------------
# Safe type coercion
# ---------------------------------------------------------------------------

def safe_int(value: object, default: int = 0) -> int:
    """Safely cast *value* to ``int``, returning *default* on failure.

    Args:
        value: Any value to attempt integer conversion on.
        default: Fallback value if conversion fails.

    Returns:
        The integer representation of *value*, or *default*.
    """
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def safe_float(value: object, default: float = 0.0) -> float:
    """Safely cast *value* to ``float``, returning *default* on failure.

    Args:
        value: Any value to attempt float conversion on.
        default: Fallback value if conversion fails.

    Returns:
        The float representation of *value*, or *default*.
    """
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    """Determine the project root directory.

    Walks upward from this file's location until a directory containing a
    ``src`` sub-directory is found.  Falls back to three levels above
    ``__file__`` if the heuristic fails.

    Returns:
        Absolute :class:`Path` to the project root.
    """
    current = Path(__file__).resolve().parent
    for _ in range(10):  # safety limit
        if (current / 'src').is_dir():
            return current
        parent = current.parent
        if parent == current:
            break  # filesystem root reached
        current = parent
    # Fallback: src/core/utils.py → three levels up
    return Path(__file__).resolve().parent.parent.parent


def get_data_dir() -> Path:
    """Return the canonical ``data/`` directory path.

    Returns:
        ``<project_root>/data``
    """
    return get_project_root() / 'data'


def get_db_dir() -> Path:
    """Return the database directory path.

    Returns:
        ``<project_root>/data/db``
    """
    return get_data_dir() / 'db'


def get_backup_dir() -> Path:
    """Return the backup directory path.

    Returns:
        ``<project_root>/data/backups``
    """
    return get_data_dir() / 'backups'


def get_log_dir() -> Path:
    """Return the log directory path.

    Returns:
        ``<project_root>/data/logs``
    """
    return get_data_dir() / 'logs'


def get_export_dir() -> Path:
    """Return the export directory path.

    Returns:
        ``<project_root>/data/exports``
    """
    return get_data_dir() / 'exports'


def get_upload_dir() -> Path:
    """Return the upload directory path.

    Returns:
        ``<project_root>/data/uploads``
    """
    return get_data_dir() / 'uploads'


def ensure_directories() -> None:
    """Create all standard data directories if they do not already exist.

    Creates the following directory tree under the project root::

        data/
        ├── db/
        ├── backups/
        ├── logs/
        ├── exports/
        └── uploads/

    This function is idempotent and safe to call multiple times.
    """
    directories = [
        get_data_dir(),
        get_db_dir(),
        get_backup_dir(),
        get_log_dir(),
        get_export_dir(),
        get_upload_dir(),
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
