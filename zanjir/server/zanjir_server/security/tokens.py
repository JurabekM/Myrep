"""Access JWT (HS256, 15 daqiqa) va refresh tokenlar (tasodifiy 256 bit; bazada faqat SHA-256 hash'i)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

_ALG = "HS256"
_ISSUER = "zanjir"
_LEEWAY_SECONDS = 30


@dataclass(frozen=True)
class AccessClaims:
    user_id: str
    org_id: str
    role: str


class TokenError(Exception):
    pass


class AccessTokens:
    """Muddat ilova soati (`clock`) bo'yicha tekshiriladi — testlarda vaqtni boshqarish mumkin."""

    def __init__(
        self, secret: str, ttl_seconds: int, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._secret = secret
        self._ttl = ttl_seconds
        self._clock = clock

    def issue(self, claims: AccessClaims, now: datetime | None = None) -> str:
        now = now or self._clock()
        payload = {
            "iss": _ISSUER,
            "sub": claims.user_id,
            "org": claims.org_id,
            "role": claims.role,
            "typ": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self._ttl)).timestamp()),
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(payload, self._secret, algorithm=_ALG)

    def decode(self, token: str) -> AccessClaims:
        try:
            p = jwt.decode(
                token,
                self._secret,
                algorithms=[_ALG],
                issuer=_ISSUER,
                options={"require": ["exp", "iat", "sub", "org", "typ"], "verify_exp": False, "verify_iat": False},
            )
        except jwt.PyJWTError as e:
            raise TokenError(type(e).__name__) from e
        now = self._clock().timestamp()
        if not isinstance(p["exp"], int) or not isinstance(p["iat"], int):
            raise TokenError("invalid_claims")
        if p["exp"] <= now:
            raise TokenError("expired")
        if p["iat"] > now + _LEEWAY_SECONDS:
            raise TokenError("issued_in_future")
        if p.get("typ") != "access":
            raise TokenError("wrong_type")
        return AccessClaims(user_id=str(p["sub"]), org_id=str(p["org"]), role=str(p.get("role", "")))


def new_secret_token() -> str:
    """Refresh token / taklif kodi: 256 bit, URL-xavfsiz."""
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_invite_code() -> str:
    """Taklif kodi qo'lda kiritilishi mumkin: 16 belgi (A–Z, 2–9; o'xshash belgilarsiz), ~80 bit."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(16))
