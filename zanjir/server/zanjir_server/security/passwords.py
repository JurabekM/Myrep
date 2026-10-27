"""Parol hash'i: argon2id. Parol va hash hech qachon logga yozilmaydi."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from zanjir_server.config import Argon2Params

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128


class Passwords:
    def __init__(self, params: Argon2Params) -> None:
        self._h = PasswordHasher(
            time_cost=params.time_cost, memory_cost=params.memory_kib, parallelism=params.parallelism
        )
        # Foydalanuvchi topilmaganda ham bir xil vaqt sarflash uchun (telefon raqamini sanab bo'lmasin).
        self._dummy = self._h.hash("zanjir-dummy-password")

    def hash(self, password: str) -> str:
        return self._h.hash(password)

    def verify(self, stored: str | None, password: str) -> bool:
        try:
            return self._h.verify(stored or self._dummy, password) and stored is not None
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, stored: str) -> bool:
        return self._h.check_needs_rehash(stored)
