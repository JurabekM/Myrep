import hashlib
import hmac
from decimal import Decimal

from app.core.config import settings
from app.integrations.payments.base import PaymentProvider, PaymentSession


class MockPaymentProvider(PaymentProvider):
    """Click/Payme/UzumBank uchun umumiy mock asos - haqiqiy hosted checkout o'rniga
    ichki mock URL qaytaradi. Imzo tekshiruvi HMAC-SHA256 bilan simulyatsiya qilinadi
    (real provayderlar ham shunga o'xshash webhook imzosidan foydalanadi).
    """

    def __init__(self, provider_code: str):
        self.provider_code = provider_code

    async def create_checkout(self, payment_id: str, amount: Decimal, return_url: str) -> PaymentSession:
        return PaymentSession(
            external_id=f"{self.provider_code}-{payment_id}",
            checkout_url=f"https://mock-{self.provider_code}.smartmoliya.local/checkout/{payment_id}?amount={amount}&return_url={return_url}",
        )

    def sign(self, payload: dict) -> str:
        message = f"{payload.get('payment_id')}:{payload.get('amount')}:{self.provider_code}"
        return hmac.new(settings.JWT_SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()

    def verify_webhook_signature(self, payload: dict, signature: str) -> bool:
        return hmac.compare_digest(self.sign(payload), signature)
