"""Parollarni xavfsiz saqlash.

Parol hech qachon ochiq yoki qaytariladigan ko'rinishda saqlanmaydi: bazaga
faqat tuzlangan, sekin KDF (kalit hosil qilish funksiyasi) natijasi yoziladi.

- Asosiy algoritm: scrypt, N=2^17, r=8, p=1 (OWASP Password Storage
  Cheat Sheet tavsiyasi) — xotira talab qiladi, GPU hujumini qimmatlashtiradi.
- Zaxira: PBKDF2-HMAC-SHA256, 600 000 iteratsiya — Python OpenSSL'siz
  (masalan LibreSSL bilan) yig'ilgan va scrypt mavjud bo'lmagan muhit uchun.

Xesh satri o'z parametrlarini o'zida saqlaydi, shuning uchun parametrlar
kuchaytirilganda eski xeshlar keyingi muvaffaqiyatli kirishda yangilanadi.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
from dataclasses import dataclass

from .validation import normalize_password

SALT_BYTES = 16
KEY_BYTES = 32

_SCRYPT = "scrypt"
_PBKDF2 = "pbkdf2-sha256"

# Bazadan o'qilgan parametrlar uchun yuqori chegaralar: buzilgan yoki
# almashtirilgan xesh satri tekshiruv paytida xotira/CPU'ni yeb qo'ymasin.
_MAX_SCRYPT_LN = 20
_MAX_SCRYPT_R = 16
_MAX_SCRYPT_P = 4
_MAX_PBKDF2_ITERATIONS = 10_000_000


def scrypt_available() -> bool:
    return hasattr(hashlib, "scrypt")


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64decode(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"), validate=True)


def _scrypt(password: bytes, salt: bytes, ln: int, r: int, p: int) -> bytes:
    n = 1 << ln
    # OpenSSL talabi: 128*r*(N + p + 2) bayt; biroz zaxira bilan.
    maxmem = 128 * r * (n + p + 2) + 1024 * 1024
    return hashlib.scrypt(password, salt=salt, n=n, r=r, p=p, maxmem=maxmem, dklen=KEY_BYTES)


def _pbkdf2(password: bytes, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password, salt, iterations, dklen=KEY_BYTES)


@dataclass(frozen=True)
class PasswordHasher:
    """Parol xeshlovchi. Standart qiymatlar — ishlab chiqarish uchun.

    Testlar tezligi uchun kichikroq parametr berish mumkin; ilova kodi
    har doim standart qiymatlardan foydalanadi.
    """

    scrypt_ln: int = 17
    scrypt_r: int = 8
    scrypt_p: int = 1
    pbkdf2_iterations: int = 600_000
    prefer_scrypt: bool = True

    def _use_scrypt(self) -> bool:
        return self.prefer_scrypt and scrypt_available()

    def hash(self, password: str) -> str:
        """Yangi tasodifiy tuz bilan xesh satrini qaytaradi."""
        secret = normalize_password(password).encode("utf-8")
        salt = secrets.token_bytes(SALT_BYTES)
        if self._use_scrypt():
            key = _scrypt(secret, salt, self.scrypt_ln, self.scrypt_r, self.scrypt_p)
            params = f"ln={self.scrypt_ln},r={self.scrypt_r},p={self.scrypt_p}"
            return f"{_SCRYPT}${params}${_b64encode(salt)}${_b64encode(key)}"
        key = _pbkdf2(secret, salt, self.pbkdf2_iterations)
        return f"{_PBKDF2}$i={self.pbkdf2_iterations}${_b64encode(salt)}${_b64encode(key)}"

    def verify(self, password: str, encoded: str) -> bool:
        """Parol xeshga mos kelsa `True`. Buzilgan xesh satri — `False`."""
        try:
            algo, params, salt, expected = _parse(encoded)
        except ValueError:
            return False
        secret = normalize_password(password).encode("utf-8")
        if algo == _SCRYPT:
            if not scrypt_available():
                return False
            actual = _scrypt(secret, salt, params["ln"], params["r"], params["p"])
        else:
            actual = _pbkdf2(secret, salt, params["i"])
        # Doimiy vaqtli solishtirish: javob vaqti mos kelgan baytlar soniga bog'liq emas.
        return hmac.compare_digest(actual, expected)

    def needs_rehash(self, encoded: str) -> bool:
        """Xesh joriy siyosatdan zaifroq parametr bilan yaratilganmi."""
        try:
            algo, params, _salt, _key = _parse(encoded)
        except ValueError:
            return True
        if self._use_scrypt():
            return algo != _SCRYPT or (
                params["ln"] < self.scrypt_ln
                or params["r"] < self.scrypt_r
                or params["p"] < self.scrypt_p
            )
        if algo == _SCRYPT:
            # Bu muhitda scrypt yo'q; mavjud scrypt xeshini zaiflashtirmaymiz.
            return False
        return params["i"] < self.pbkdf2_iterations


def _parse(encoded: str) -> tuple[str, dict[str, int], bytes, bytes]:
    """Xesh satrini qat'iy ajratadi; har qanday nomuvofiqlik — `ValueError`."""
    if not isinstance(encoded, str) or len(encoded) > 512:
        raise ValueError("hash")
    parts = encoded.split("$")
    if len(parts) != 4:
        raise ValueError("hash")
    algo, raw_params, raw_salt, raw_key = parts
    params: dict[str, int] = {}
    for item in raw_params.split(","):
        name, sep, number = item.partition("=")
        if not sep or not number.isascii() or not number.isdigit() or name in params:
            raise ValueError("hash")
        params[name] = int(number)
    try:
        salt, key = _b64decode(raw_salt), _b64decode(raw_key)
    except (binascii.Error, UnicodeEncodeError):
        raise ValueError("hash") from None
    if len(salt) != SALT_BYTES or len(key) != KEY_BYTES:
        raise ValueError("hash")
    if algo == _SCRYPT:
        if set(params) != {"ln", "r", "p"}:
            raise ValueError("hash")
        if not (
            1 <= params["ln"] <= _MAX_SCRYPT_LN
            and 1 <= params["r"] <= _MAX_SCRYPT_R
            and 1 <= params["p"] <= _MAX_SCRYPT_P
        ):
            raise ValueError("hash")
    elif algo == _PBKDF2:
        if set(params) != {"i"} or not 1 <= params["i"] <= _MAX_PBKDF2_ITERATIONS:
            raise ValueError("hash")
    else:
        raise ValueError("hash")
    return algo, params, salt, key
