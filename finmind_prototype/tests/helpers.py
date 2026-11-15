"""Testlar uchun umumiy yordamchilar."""

from __future__ import annotations

from datetime import date

from fintx import db
from fintx.app import App
from fintx.security import PasswordHasher

# Testlarda tezlik uchun arzon parametrlar; ishlab chiqarish qiymatlari
# test_security.py da alohida tekshiriladi.
FAST_HASHER = PasswordHasher(scrypt_ln=8, pbkdf2_iterations=1_000)

TODAY = date(2026, 11, 15)
PASSWORD = "Tog'lar-ortida-quyosh-2026"
OTHER_PASSWORD = "Daryo-bo'yida-tong-1991"


class FakeClock:
    """Qo'lda suriladigan soat: qulf va sessiya muddatini kutmasdan sinash uchun."""

    def __init__(self, start: float = 1_800_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_app(path: str = db.MEMORY, clock: FakeClock | None = None) -> App:
    return App.open(
        path,
        hasher=FAST_HASHER,
        clock=clock or FakeClock(),
        today=lambda: TODAY,
    )
