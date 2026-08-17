"""Security services: password hashing, HMAC tokens, RBAC, rate limiting, audit."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
from typing import Any

from config import settings

log = logging.getLogger(__name__)

PBKDF2_ITERATIONS = 120_000

# Role -> set of granted permissions.
ROLES: dict[str, set[str]] = {
    "admin": {
        "view_dashboard", "edit_data", "import_data", "export_reports",
        "manage_users", "manage_settings", "backup", "use_ai", "view_finance",
    },
    "manager": {
        "view_dashboard", "edit_data", "import_data", "export_reports",
        "use_ai", "view_finance",
    },
    "viewer": {"view_dashboard", "use_ai"},
}


# --------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256, constant-time verification)
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a password as ``pbkdf2$iterations$salt$digest`` (all hex)."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time verification of a password against a stored hash."""
    try:
        scheme, iterations, salt, digest = stored.split("$")
        if scheme != "pbkdf2":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        ).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------
# Signed API tokens (JWT-style: base64(payload).hex(hmac_sha256))
# --------------------------------------------------------------------------
def create_token(username: str, role: str, ttl: int | None = None) -> str:
    """Create a signed, expiring API token for the given user."""
    payload = {
        "sub": username,
        "role": role,
        "exp": int(time.time()) + (ttl or settings.TOKEN_TTL_SECONDS),
        "jti": secrets.token_hex(8),
    }
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode()
    signature = hmac.new(
        settings.get_storage_secret().encode("utf-8"), body.encode(), hashlib.sha256
    ).hexdigest()
    return f"{body}.{signature}"


def verify_token(token: str) -> dict[str, Any] | None:
    """Return the payload for a valid non-expired token, else ``None``."""
    try:
        body, signature = token.split(".")
        expected = hmac.new(
            settings.get_storage_secret().encode("utf-8"), body.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body.encode()))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


# --------------------------------------------------------------------------
# RBAC helpers
# --------------------------------------------------------------------------
def has_permission(role: str | None, permission: str) -> bool:
    """Check whether a role grants a permission."""
    return permission in ROLES.get(role or "", set())


# --------------------------------------------------------------------------
# Login rate limiting (in-process, per username)
# --------------------------------------------------------------------------
class RateLimiter:
    """Counts failures per key and locks the key after too many attempts."""

    def __init__(self, max_attempts: int, lock_minutes: int) -> None:
        self.max_attempts = max_attempts
        self.lock_seconds = lock_minutes * 60
        self._attempts: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}
        self._lock = threading.Lock()

    def is_locked(self, key: str) -> bool:
        with self._lock:
            until = self._locked_until.get(key, 0)
            if until > time.time():
                return True
            self._locked_until.pop(key, None)
            return False

    def register_failure(self, key: str) -> None:
        now = time.time()
        with self._lock:
            history = [t for t in self._attempts.get(key, []) if now - t < 600]
            history.append(now)
            self._attempts[key] = history
            if len(history) >= self.max_attempts:
                self._locked_until[key] = now + self.lock_seconds
                self._attempts[key] = []

    def register_success(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
            self._locked_until.pop(key, None)


login_limiter = RateLimiter(settings.LOGIN_MAX_ATTEMPTS, settings.LOGIN_LOCK_MINUTES)
api_limiter = RateLimiter(settings.API_RATE_LIMIT_PER_MINUTE, 1)


# --------------------------------------------------------------------------
# Audit trail
# --------------------------------------------------------------------------
def audit(action: str, username: str = "system", details: str = "") -> None:
    """Persist an audit record; failures are logged, never raised."""
    try:
        from database.engine import session_scope
        from database.models import AuditLog

        with session_scope() as session:
            session.add(AuditLog(username=username, action=action, details=details[:1000]))
    except Exception as exc:  # noqa: BLE001 - audit must never break the app
        log.warning("Audit yozuvi saqlanmadi (%s): %s", action, exc)
