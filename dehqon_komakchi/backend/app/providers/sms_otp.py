"""Provider-agnostic SMS/OTP sending.

Swap `DemoSmsOtpProvider` for a real gateway (e.g. Eskiz.uz, Play Mobile) by implementing
`SmsOtpProvider` and wiring it in `get_sms_provider()`. The API key for a real gateway must
only ever live in this backend's environment (`SMS_PROVIDER_API_KEY` in `.env`) -- it must
never be shipped inside the mobile app.
"""

from abc import ABC, abstractmethod

from app.config import get_settings

DEMO_CODE = "123456"


class SmsOtpProvider(ABC):
    @abstractmethod
    def send_otp(self, phone_number: str, code: str) -> None: ...


class DemoSmsOtpProvider(SmsOtpProvider):
    """Does not send a real SMS; the code is always DEMO_CODE. Safe for zero-cost local dev."""

    def send_otp(self, phone_number: str, code: str) -> None:
        return None


def get_sms_provider() -> SmsOtpProvider:
    settings = get_settings()
    if settings.auth_otp_mode == "sms" and settings.sms_provider_api_key:
        # A real implementation would be selected here, e.g.:
        # return EskizSmsOtpProvider(api_key=settings.sms_provider_api_key)
        raise NotImplementedError(
            "AUTH_OTP_MODE=sms requires a real SmsOtpProvider implementation; none is wired in yet.",
        )
    return DemoSmsOtpProvider()
