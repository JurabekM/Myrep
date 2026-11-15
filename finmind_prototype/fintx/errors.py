"""Foydalanuvchiga ko'rsatish xavfsiz bo'lgan xatolar.

Bu yerdagi har bir xato matni interfeysda aynan ko'rsatiladi, shuning uchun
ularga ichki tafsilot (SQL, yo'l, stack) hech qachon yozilmaydi.
"""

from __future__ import annotations


class FinTxError(Exception):
    """Barcha kutilgan (foydalanuvchiga tushuntiriladigan) xatolar asosi."""


class ValidationError(FinTxError):
    """Kiritilgan qiymat qoidaga mos emas."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class AuthError(FinTxError):
    """Kirish rad etildi. Sababi ataylab umumiy: login yoki parol."""


class AccountLocked(AuthError):
    """Ketma-ket xato urinishlardan keyin hisob vaqtincha qulflangan."""

    def __init__(self, retry_after: float) -> None:
        self.retry_after = max(1, int(retry_after + 0.999))
        super().__init__(
            f"Juda ko'p xato urinish. {self.retry_after} soniyadan keyin qayta urining."
        )


class SessionExpired(AuthError):
    """Sessiya tugagan yoki yopilgan: qayta kirish kerak."""

    def __init__(self) -> None:
        super().__init__("Sessiya muddati tugadi. Qaytadan kiring.")


class NotFound(FinTxError):
    """Yozuv topilmadi yoki joriy foydalanuvchiga tegishli emas."""
