from app.integrations.payments.base import PaymentProvider
from app.integrations.payments.mock_provider import MockPaymentProvider

SUPPORTED_PAYMENT_PROVIDERS = ("click", "payme", "uzum")


def get_payment_provider(provider_code: str) -> PaymentProvider:
    if provider_code not in SUPPORTED_PAYMENT_PROVIDERS:
        raise ValueError(f"Noma'lum to'lov provayderi: {provider_code}")
    return MockPaymentProvider(provider_code)
