from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PaymentSession:
    external_id: str
    checkout_url: str


class PaymentProvider(ABC):
    """To'lov provayderlari uchun umumiy interfeys (Strategy pattern).

    Hozircha Click/Payme/UzumBank uchun mock implementatsiya ishlatiladi -
    haqiqiy checkout sahifasi o'rniga ichki mock URL qaytariladi va tasdiqlash
    `/payments/{id}/confirm` orqali qo'lda (yoki test/CI'da avtomatik) chaqiriladi.
    Real integratsiya uchun shu interfeysni implement qiluvchi yangi klass yetarli.
    """

    provider_code: str

    @abstractmethod
    async def create_checkout(self, payment_id: str, amount: Decimal, return_url: str) -> PaymentSession: ...

    @abstractmethod
    def verify_webhook_signature(self, payload: dict, signature: str) -> bool: ...
