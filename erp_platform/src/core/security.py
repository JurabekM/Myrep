# -*- coding: utf-8 -*-
"""
Xavfsizlik yadrosi.

* Parol xeshlash — PBKDF2-HMAC-SHA256 (240 000 iteratsiya, tuz bilan)
* Imzolangan tokenlar — HMAC-SHA256 (API va sessiyalar uchun)
* Rate limiting — sirg'aluvchi oyna (sliding window), xotirada
* CSRF himoya — sessiyaga bog'langan HMAC token (stateless)
* XSS himoya — HTML escape yordamchilari

SQL injection himoyasi database qatlamida parametrlangan so'rovlar
bilan ta'minlanadi (hech qayerda string-format SQL ishlatilmaydi).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import secrets
import threading
import time
from collections import defaultdict, deque

_PBKDF2_ITERATIONS = 240_000
_ALGO = "pbkdf2_sha256"


# ---------------------------------------------------------------------- #
#  Parol xeshlash
# ---------------------------------------------------------------------- #

def hash_password(password: str) -> str:
    """
    Parolni qaytarilmas xeshga aylantiradi.

    Format: ``pbkdf2_sha256$<iteratsiya>$<tuz_hex>$<xesh_hex>``
    """
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"{_ALGO}${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Parolni saqlangan xesh bilan doimiy vaqtda (timing-safe) solishtiradi."""
    try:
        algo, iterations_s, salt_hex, digest_hex = stored.split("$")
        if algo != _ALGO:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations_s),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


def check_password_policy(password: str, min_length: int = 8) -> str | None:
    """
    Parol siyosatini tekshiradi.

    Muammo bo'lsa — o'zbekcha xato matnini, hammasi joyida bo'lsa None qaytaradi.
    """
    if len(password) < min_length:
        return f"Parol kamida {min_length} ta belgidan iborat bo'lishi kerak."
    if not any(c.isdigit() for c in password):
        return "Parolda kamida bitta raqam bo'lishi kerak."
    if not any(c.isalpha() for c in password):
        return "Parolda kamida bitta harf bo'lishi kerak."
    return None


def generate_password(length: int = 12) -> str:
    """Siyosatga mos tasodifiy parol generatsiya qiladi (admin uchun)."""
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if check_password_policy(pwd) is None:
            return pwd


# ---------------------------------------------------------------------- #
#  Imzolangan tokenlar (HMAC)
# ---------------------------------------------------------------------- #

class SignedTokenFactory:
    """
    HMAC-SHA256 bilan imzolangan, muddatli tokenlar.

    Server xotirasiz (stateless) tekshiruv uchun — API tokenlarida ishlatiladi.
    """

    def __init__(self, secret_key: str) -> None:
        self._key = secret_key.encode("utf-8")

    def sign(self, data: dict, ttl_seconds: int = 3600) -> str:
        """Ma'lumotni imzolab token qaytaradi (ttl — amal qilish muddati)."""
        payload = dict(data)
        payload["exp"] = int(time.time()) + ttl_seconds
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        body = base64.urlsafe_b64encode(raw).rstrip(b"=")
        sig = hmac.new(self._key, body, hashlib.sha256).hexdigest()
        return f"{body.decode('ascii')}.{sig}"

    def verify(self, token: str) -> dict | None:
        """Tokenni tekshiradi; yaroqsiz yoki muddati o'tgan bo'lsa None."""
        try:
            body_s, sig = token.rsplit(".", 1)
            body = body_s.encode("ascii")
            expected = hmac.new(self._key, body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, sig):
                return None
            padded = body + b"=" * (-len(body) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded))
            if int(payload.get("exp", 0)) < time.time():
                return None
            payload.pop("exp", None)
            return payload
        except (ValueError, TypeError, json.JSONDecodeError):
            return None


# ---------------------------------------------------------------------- #
#  Rate limiting
# ---------------------------------------------------------------------- #

class RateLimiter:
    """
    Sirg'aluvchi oynali (sliding window) rate limiter.

    Har bir kalit (masalan, IP manzil) uchun oynadagi so'rovlar soni
    cheklovdan oshsa ``allow()`` False qaytaradi.
    """

    def __init__(self, max_requests: int = 120, window_seconds: float = 60.0) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """So'rovga ruxsat bor-yo'qligini tekshiradi va hisobga oladi."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self._window:
                hits.popleft()
            if len(hits) >= self._max:
                return False
            hits.append(now)
            return True

    def reset(self, key: str) -> None:
        """Kalit bo'yicha hisobni tozalaydi (masalan, muvaffaqiyatli logindan keyin)."""
        with self._lock:
            self._hits.pop(key, None)


# ---------------------------------------------------------------------- #
#  CSRF himoya
# ---------------------------------------------------------------------- #

class CSRFProtect:
    """
    Sessiyaga bog'langan CSRF tokenlar (stateless, HMAC asosida).

    Token sessiya identifikatoridan hosil qilinadi — serverda saqlash shart emas.
    """

    def __init__(self, secret_key: str) -> None:
        self._key = (secret_key + ":csrf").encode("utf-8")

    def issue(self, session_token: str) -> str:
        """Berilgan sessiya uchun CSRF token yaratadi."""
        return hmac.new(self._key, session_token.encode("utf-8"), hashlib.sha256).hexdigest()

    def validate(self, session_token: str, csrf_token: str) -> bool:
        """Forma bilan kelgan CSRF tokenni tekshiradi."""
        if not session_token or not csrf_token:
            return False
        return hmac.compare_digest(self.issue(session_token), csrf_token)


# ---------------------------------------------------------------------- #
#  XSS himoya
# ---------------------------------------------------------------------- #

def escape_html(value: object) -> str:
    """Foydalanuvchi kiritgan matnni HTML uchun xavfsiz ko'rinishga o'tkazadi."""
    return html.escape(str(value if value is not None else ""), quote=True)


def new_session_token() -> str:
    """Kriptografik tasodifiy sessiya tokeni (URL-safe, 43 belgi)."""
    return secrets.token_urlsafe(32)
