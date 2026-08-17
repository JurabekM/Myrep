import hashlib
import secrets
import time
from dataclasses import dataclass

from app.core.config import settings
from app.services.exceptions import UnauthorizedError


@dataclass
class OtpRecord:
    code_hash: str
    expires_at: float
    attempts: int = 0


class InMemoryOtpStore:
    """Dev/single-instance uchun xotiradagi OTP ombori.

    Production'da (bir nechta backend instance) bu Redis'ga ko'chiriladi -
    interfeys (save/get/delete) o'zgarmaydi, faqat implementatsiya almashadi.
    """

    def __init__(self):
        self._records: dict[str, OtpRecord] = {}

    def save(self, phone: str, record: OtpRecord) -> None:
        self._records[phone] = record

    def get(self, phone: str) -> OtpRecord | None:
        return self._records.get(phone)

    def delete(self, phone: str) -> None:
        self._records.pop(phone, None)


class SmsSender:
    """SMS yuborish interfeysi. Production adapteri (masalan Eskiz.uz) shu klassni
    meros olib `send`ni implement qiladi."""

    def send(self, phone: str, code: str) -> None:  # pragma: no cover - mock hech narsa qilmaydi
        pass


class MockSmsSender(SmsSender):
    """Dev muhitda haqiqiy SMS yuborilmaydi - kod API javobida qaytariladi."""


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class OtpService:
    def __init__(self, store: InMemoryOtpStore, sms_sender: SmsSender):
        self.store = store
        self.sms_sender = sms_sender

    def request_code(self, phone: str) -> str:
        """6 xonali kod yaratadi, saqlaydi va SMS jo'natadi. Kodni qaytaradi -
        uni ochiq ko'rsatish yoki ko'rsatmaslik chaqiruvchi (router) zimmasida."""
        code = f"{secrets.randbelow(1_000_000):06d}"
        self.store.save(
            phone,
            OtpRecord(code_hash=_hash_code(code), expires_at=time.time() + settings.OTP_EXPIRE_SECONDS),
        )
        self.sms_sender.send(phone, code)
        return code

    def verify_code(self, phone: str, code: str) -> None:
        """Muvaffaqiyatda kod o'chiriladi (bir martalik). Xatoda UnauthorizedError."""
        record = self.store.get(phone)
        if record is None:
            raise UnauthorizedError("Kod so'ralmagan yoki muddati tugagan")

        if time.time() > record.expires_at:
            self.store.delete(phone)
            raise UnauthorizedError("Kod muddati tugagan, qaytadan so'rang")

        record.attempts += 1
        if record.attempts > settings.OTP_MAX_ATTEMPTS:
            self.store.delete(phone)
            raise UnauthorizedError("Urinishlar soni oshib ketdi, qaytadan kod so'rang")

        if record.code_hash != _hash_code(code):
            raise UnauthorizedError("Kod noto'g'ri")

        self.store.delete(phone)


# Jarayon darajasidagi singleton (dev). Production'da Redis store bilan almashtiriladi.
_otp_store = InMemoryOtpStore()
_otp_service: OtpService | None = None


def get_otp_service() -> OtpService:
    global _otp_service
    if _otp_service is None:
        _otp_service = OtpService(_otp_store, MockSmsSender())
    return _otp_service
