"""Lokal autentifikatsiya va juftlash kodi (serversiz rejim).

Parol PBKDF2-HMAC-SHA256 bilan xeshlanadi. Mobil ilova (Dart) bir xil parametrlarni ishlatadi:
100 000 iteratsiya, 16 baytli tasodifiy tuz, 32 baytli natija. Juftlash kodi: "<store_id>:<kalit hex>".
"""

import hashlib
import hmac
import re
import secrets
import uuid

PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16
HEX_KEY = re.compile(r"^[0-9a-f]{64}$")


def hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    """(salt_hex, hash_hex) qaytaradi. salt_hex berilmasa yangi tuz yaratiladi."""
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    _, candidate = hash_password(password, salt_hex)
    return hmac.compare_digest(candidate, hash_hex)


def normalize_login(login: str) -> str:
    return login.strip().lower()


def make_pairing_code(store_id: str, key_hex: str) -> str:
    return f"{store_id}:{key_hex}"


def parse_pairing_code(code: str) -> tuple[str, str]:
    """Juftlash kodini tekshiradi. Noto'g'ri bo'lsa ValueError."""
    store_id, sep, key_hex = code.strip().lower().partition(":")
    if not sep:
        raise ValueError("Juftlash kodi noto'g'ri formatda")
    try:
        uuid.UUID(store_id)
    except ValueError as exc:
        raise ValueError("Juftlash kodida do'kon ID noto'g'ri") from exc
    if not HEX_KEY.match(key_hex):
        raise ValueError("Juftlash kodida kalit noto'g'ri (64 belgi kerak)")
    return store_id, key_hex
