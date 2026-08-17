"""Password hashing and secret storage helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os

import bcrypt

from app.config import KEYRING_SERVICE

logger = logging.getLogger(__name__)

try:  # keyring is optional at runtime (headless CI, portable builds)
    import keyring

    _KEYRING_AVAILABLE = True
except Exception:  # pragma: no cover
    keyring = None  # type: ignore[assignment]
    _KEYRING_AVAILABLE = False


def hash_password(password: str) -> str:
    """Hash a plain password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str | None) -> bool:
    """Verify a plain password against a bcrypt hash."""
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def password_strength(password: str) -> tuple[bool, str]:
    """Return ``(is_valid, reason_key)`` for a candidate password."""
    if len(password) < 6:
        return False, "password_too_short"
    if password.isdigit():
        return False, "password_only_digits"
    return True, ""


# --------------------------------------------------------------------------- #
# Credential storage
# --------------------------------------------------------------------------- #
def _fallback_key() -> bytes:
    """Machine-bound key used when the OS keyring is unavailable."""
    seed = f"{KEYRING_SERVICE}:{os.environ.get('COMPUTERNAME', 'local')}"
    return hashlib.sha256(seed.encode("utf-8")).digest()


def obfuscate(value: str) -> str:
    """Reversible at-rest encoding for the DB fallback (not a substitute for a keyring)."""
    key = _fallback_key()
    raw = value.encode("utf-8")
    stream = bytearray()
    counter = 0
    while len(stream) < len(raw):
        stream.extend(hmac.new(key, counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    mixed = bytes(a ^ b for a, b in zip(raw, stream, strict=False))
    return base64.urlsafe_b64encode(mixed).decode("ascii")


def deobfuscate(value: str) -> str:
    """Inverse of :func:`obfuscate`."""
    try:
        mixed = base64.urlsafe_b64decode(value.encode("ascii"))
    except Exception:
        return ""
    key = _fallback_key()
    stream = bytearray()
    counter = 0
    while len(stream) < len(mixed):
        stream.extend(hmac.new(key, counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(a ^ b for a, b in zip(mixed, stream, strict=False)).decode(
        "utf-8", errors="replace"
    )


def store_secret(name: str, value: str) -> bool:
    """Store a credential in the OS keyring. Returns ``True`` on success."""
    if not _KEYRING_AVAILABLE:
        return False
    try:
        keyring.set_password(KEYRING_SERVICE, name, value)
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("Keyring write failed for %s: %s", name, type(exc).__name__)
        return False


def read_secret(name: str) -> str | None:
    """Read a credential from the OS keyring."""
    if not _KEYRING_AVAILABLE:
        return None
    try:
        return keyring.get_password(KEYRING_SERVICE, name)
    except Exception:  # pragma: no cover
        return None


def delete_secret(name: str) -> None:
    """Remove a credential from the OS keyring, ignoring absence."""
    if not _KEYRING_AVAILABLE:
        return
    try:
        keyring.delete_password(KEYRING_SERVICE, name)
    except Exception:  # pragma: no cover
        pass


def keyring_available() -> bool:
    """Whether an OS keyring backend is usable."""
    return _KEYRING_AVAILABLE
