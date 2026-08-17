# -*- coding: utf-8 -*-
"""
config/secure.py
================
Maxfiy ma'lumotlarni (parollar, API kalitlar, proxy kredensiallari)
shifrlangan holda saqlash uchun oddiy va xavfsiz do'kon.

`cryptography.Fernet` (AES-128 CBC + HMAC) ishlatiladi. Shifrlash kaliti
`config/.secret.key` faylida saqlanadi va faqat egasiga o'qish huquqi
beriladi (POSIX tizimlarda). Bu SQL Injection emas, balki config
darajasidagi maxfiylikni ta'minlaydi.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

try:
    from cryptography.fernet import Fernet, InvalidToken
    _CRYPTO_AVAILABLE = True
except ImportError:  # pragma: no cover - kutubxona bo'lmasa
    _CRYPTO_AVAILABLE = False

from config.settings import CONFIG_DIR


KEY_FILE: Path = CONFIG_DIR / ".secret.key"
STORE_FILE: Path = CONFIG_DIR / ".secrets.enc"


def _restrict_permissions(path: Path) -> None:
    """Faylni faqat egasi o'qiy oladigan qilib belgilaydi (0o600)."""
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except (PermissionError, OSError):
        # Windows'da chmod cheklangan bo'lishi mumkin - jimgina o'tamiz
        pass


class SecureStore:
    """Kalit-qiymat ko'rinishidagi shifrlangan maxfiy do'kon."""

    def __init__(self) -> None:
        self._enabled = _CRYPTO_AVAILABLE
        self._fernet: "Fernet | None" = None
        if self._enabled:
            self._fernet = Fernet(self._load_or_create_key())

    # -------------------------------------------------------------
    def _load_or_create_key(self) -> bytes:
        """Shifrlash kalitini yuklaydi yoki yangisini yaratadi."""
        if KEY_FILE.exists():
            return KEY_FILE.read_bytes()
        key = Fernet.generate_key()
        KEY_FILE.write_bytes(key)
        _restrict_permissions(KEY_FILE)
        return key

    def _read_all(self) -> dict[str, str]:
        """Barcha shifrlangan yozuvlarni deshifrlab qaytaradi."""
        if not self._enabled or not STORE_FILE.exists():
            return {}
        try:
            decrypted = self._fernet.decrypt(STORE_FILE.read_bytes())  # type: ignore[union-attr]
            return json.loads(decrypted.decode("utf-8"))
        except (InvalidToken, json.JSONDecodeError, OSError):
            return {}

    def _write_all(self, data: dict[str, str]) -> None:
        """Barcha yozuvlarni shifrlab faylga yozadi."""
        if not self._enabled:
            return
        token = self._fernet.encrypt(json.dumps(data).encode("utf-8"))  # type: ignore[union-attr]
        STORE_FILE.write_bytes(token)
        _restrict_permissions(STORE_FILE)

    # -------------------------------------------------------------
    def set(self, key: str, value: str) -> None:
        """Maxfiy qiymatni saqlaydi."""
        data = self._read_all()
        data[key] = value
        self._write_all(data)

    def get(self, key: str, default: str = "") -> str:
        """Maxfiy qiymatni o'qiydi."""
        return self._read_all().get(key, default)

    def delete(self, key: str) -> None:
        """Maxfiy qiymatni o'chiradi."""
        data = self._read_all()
        data.pop(key, None)
        self._write_all(data)

    @property
    def available(self) -> bool:
        """Shifrlash mavjudligini bildiradi."""
        return self._enabled


# Global singleton
SECURE_STORE = SecureStore()
