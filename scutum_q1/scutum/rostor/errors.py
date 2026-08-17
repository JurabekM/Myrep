"""ROSTOR-1 xatoliklari.

SCUTUM-Q1 `protocol/errors.py` naqshini davom ettiradi: tashqariga (log
mijozlariga, boshqa institutsiyalarga) chiqadigan xato hech qachon ichki
sababni oshkor qilmasligi kerak (spec §10.1 falsafasi shu yerda ham).
"""
from __future__ import annotations

from ..protocol.errors import ProtocolError


class RostorError(ProtocolError):
    """ROSTOR-1 ilova qatlamidagi umumiy xato."""


class TrustError(RostorError):
    """Ishonch zanjiri (IC/IDC/registrator) tekshiruvidan o'tmadi."""


class LogError(RostorError):
    """Shaffoflik jurnali izchilligi yoki freshness buzilgan."""


class BindingError(RostorError):
    """WYSIWYS yoki so'rov/javob bog'lanishi buzilgan (masalan request_hash mos emas)."""


class PolicyViolation(RostorError):
    """Sxema invarianti buzilgan (masalan PaymentIntent'da kredensial maydon)."""


class AccountAuthError(RostorError):
    """Akkount avtorizatsiyasi: policy_epoch, kvorum yoki muddat xatosi."""
