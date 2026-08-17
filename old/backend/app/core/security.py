"""Authentication primitives: password hashing, JWT, refresh rotation, TOTP 2FA."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.infrastructure.cache.redis import RedisManager

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]

_REFRESH_PREFIX = "auth:refresh:"


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


class TokenService:
    """Issues/verifies JWTs. Refresh tokens are single-use (rotation): the
    active token id per user+device is stored in Redis; presenting an old one
    revokes the whole chain (theft detection)."""

    def __init__(self, settings: Settings, redis: RedisManager):
        self._settings = settings
        self._redis = redis

    def _encode(self, payload: dict[str, Any], expires_delta: timedelta) -> str:
        now = datetime.now(timezone.utc)
        payload = {**payload, "iat": now, "exp": now + expires_delta}
        return jwt.encode(
            payload,
            self._settings.secret_key.get_secret_value(),
            algorithm=self._settings.jwt_algorithm,
        )

    def _decode(self, token: str, expected_type: TokenType) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self._settings.secret_key.get_secret_value(),
                algorithms=[self._settings.jwt_algorithm],
            )
        except JWTError as exc:
            raise AuthenticationError("Token yaroqsiz yoki muddati o'tgan") from exc
        if payload.get("type") != expected_type:
            raise AuthenticationError("Token turi noto'g'ri")
        return payload

    def create_access_token(self, user_id: str, role: str, plan: str) -> str:
        return self._encode(
            {"sub": user_id, "role": role, "plan": plan, "type": "access"},
            timedelta(minutes=self._settings.access_token_expire_minutes),
        )

    async def create_refresh_token(self, user_id: str, device_id: str) -> str:
        jti = secrets.token_urlsafe(32)
        token = self._encode(
            {"sub": user_id, "jti": jti, "device": device_id, "type": "refresh"},
            timedelta(days=self._settings.refresh_token_expire_days),
        )
        await self._redis.client.set(
            f"{_REFRESH_PREFIX}{user_id}:{device_id}",
            jti,
            ex=self._settings.refresh_token_expire_days * 86400,
        )
        return token

    def verify_access_token(self, token: str) -> dict[str, Any]:
        return self._decode(token, "access")

    async def rotate_refresh_token(self, token: str) -> tuple[str, str]:
        """Validate a refresh token and return (user_id, new_refresh_token)."""
        payload = self._decode(token, "refresh")
        user_id, device_id, jti = payload["sub"], payload["device"], payload["jti"]
        key = f"{_REFRESH_PREFIX}{user_id}:{device_id}"
        current_jti = await self._redis.client.get(key)
        if current_jti != jti:
            # Reuse of a rotated token — revoke the device chain entirely.
            await self._redis.client.delete(key)
            raise AuthenticationError("Refresh token bekor qilingan")
        new_token = await self.create_refresh_token(user_id, device_id)
        return user_id, new_token

    async def revoke_refresh_tokens(self, user_id: str, device_id: str | None = None) -> None:
        if device_id is not None:
            await self._redis.client.delete(f"{_REFRESH_PREFIX}{user_id}:{device_id}")
            return
        pattern = f"{_REFRESH_PREFIX}{user_id}:*"
        async for key in self._redis.client.scan_iter(match=pattern):
            await self._redis.client.delete(key)


class TwoFactorService:
    def __init__(self, settings: Settings):
        self._issuer = settings.two_fa_issuer

    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def provisioning_uri(self, secret: str, account_email: str) -> str:
        return pyotp.TOTP(secret).provisioning_uri(name=account_email, issuer_name=self._issuer)

    def verify(self, secret: str, code: str) -> bool:
        return pyotp.TOTP(secret).verify(code, valid_window=1)
