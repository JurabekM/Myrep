"""Password hashing helpers.

``bcrypt`` is used directly; ``passlib`` is accepted as a fallback so the app
still runs in environments where only one of the two is installed.
"""

from __future__ import annotations

try:  # pragma: no cover - depends on the installed environment
    import bcrypt

    _BACKEND = "bcrypt"
except ImportError:  # pragma: no cover
    bcrypt = None  # type: ignore[assignment]
    from passlib.hash import bcrypt as _passlib_bcrypt

    _BACKEND = "passlib"

MIN_PASSWORD_LENGTH = 6


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash of ``password``."""
    if _BACKEND == "bcrypt":
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return _passlib_bcrypt.hash(password)  # pragma: no cover


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time check of ``password`` against ``hashed``."""
    if not password or not hashed:
        return False
    try:
        if _BACKEND == "bcrypt":
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        return _passlib_bcrypt.verify(password, hashed)  # pragma: no cover
    except (ValueError, TypeError):
        return False


def validate_password(password: str) -> str | None:
    """Return an i18n key describing the problem, or ``None`` when valid."""
    if len(password or "") < MIN_PASSWORD_LENGTH:
        return "password_too_short"
    return None
