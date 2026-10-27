"""SMS OTP adapteri — interfeys tayyor, MVP'da o'chiq (`ZANJIR_SMS_OTP_ENABLED=false`, prompt 7-bo'lim)."""

from __future__ import annotations

from typing import Protocol


class OtpSender(Protocol):
    async def send(self, phone: str, code: str) -> None: ...


class DisabledOtpSender:
    async def send(self, phone: str, code: str) -> None:
        raise RuntimeError("SMS OTP o'chirilgan")
