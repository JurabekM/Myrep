"""Password hashing and secure credential storage."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os

from app.utils.logging_setup import get_logger

log = get_logger(__name__)

try:  # pragma: no cover - depends on environment
    import bcrypt

    _HAS_BCRYPT = True
except Exception:  # pragma: no cover
    _HAS_BCRYPT = False

try:  # pragma: no cover - depends on environment
    import keyring

    _HAS_KEYRING = True
except Exception:  # pragma: no cover
    _HAS_KEYRING = False

_PBKDF2_ROUNDS = 240_000
_SERVICE = "ExportFlow"


def hash_password(password: str) -> str:
    """Hash a plaintext password.

    Uses bcrypt when available and falls back to PBKDF2-HMAC-SHA256 so that the
    application still works on machines without a compiled bcrypt wheel.
    """
    if not password:
        raise ValueError("password must not be empty")
    if _HAS_BCRYPT:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return "pbkdf2$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, hashed: str | None) -> bool:
    """Constant-time verification of a password against a stored hash."""
    if not password or not hashed:
        return False
    try:
        if hashed.startswith("pbkdf2$"):
            _, salt_b64, digest_b64 = hashed.split("$", 2)
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(digest_b64)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
            return hmac.compare_digest(expected, actual)
        if _HAS_BCRYPT:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception as exc:  # pragma: no cover - malformed hash
        log.warning("Password verification failed: %s", type(exc).__name__)
    return False


# --------------------------------------------------------------------------- secrets


def _fallback_store_path():
    from app.config import PATHS

    PATHS.ensure()
    return PATHS.root / "credentials.local.json"


def _fallback_read() -> dict[str, str]:
    path = _fallback_store_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover
        return {}


def _fallback_write(data: dict[str, str]) -> None:
    path = _fallback_store_path()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_secret(key: str, value: str) -> None:
    """Persist a credential in the OS keyring (never in the database or logs)."""
    if not value:
        delete_secret(key)
        return
    if _HAS_KEYRING:
        try:
            keyring.set_password(_SERVICE, key, value)
            return
        except Exception as exc:  # pragma: no cover - no backend available
            log.warning("Keyring unavailable (%s), using local fallback store", type(exc).__name__)
    data = _fallback_read()
    data[key] = base64.b64encode(value.encode("utf-8")).decode()
    _fallback_write(data)


def load_secret(key: str) -> str | None:
    """Read a stored credential, or ``None`` when it was never saved."""
    if _HAS_KEYRING:
        try:
            found = keyring.get_password(_SERVICE, key)
            if found:
                return found
        except Exception:  # pragma: no cover
            pass
    raw = _fallback_read().get(key)
    if raw is None:
        return None
    try:
        return base64.b64decode(raw).decode("utf-8")
    except Exception:  # pragma: no cover
        return None


def delete_secret(key: str) -> None:
    """Remove a stored credential from every backend."""
    if _HAS_KEYRING:
        try:
            keyring.delete_password(_SERVICE, key)
        except Exception:  # pragma: no cover - not stored there
            pass
    data = _fallback_read()
    if key in data:
        data.pop(key)
        _fallback_write(data)


def mask(value: str | None) -> str:
    """Mask a credential for display (``sk-…4f2a``)."""
    if not value:
        return ""
    if len(value) <= 6:
        return "•" * len(value)
    return f"{value[:3]}{'•' * 6}{value[-3:]}"
