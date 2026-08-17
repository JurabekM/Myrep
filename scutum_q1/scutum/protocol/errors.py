"""Protokol xatoliklari.

Spec §10.1 taqiqi: "xato sababi orqali kalit yoki decryption holatini oshkor
qiluvchi turli javoblar". Shu sababli TASHQARIGA (tarmoqqa) chiqadigan javob
har doim yagona umumiy kod bo'ladi — batafsil sabab faqat lokal log/GUI uchun.
"""
from __future__ import annotations


class ProtocolError(Exception):
    """Umumiy protokol xatosi."""

    #: tarmoqqa chiqariladigan yagona, ma'lumot bermaydigan kod
    WIRE_CODE = "QQ_ERR"

    def wire(self) -> str:
        return self.WIRE_CODE


class VerificationError(ProtocolError):
    """Imzo, sertifikat yoki bundle tekshiruvi muvaffaqiyatsiz."""


class DecryptionError(ProtocolError):
    """AEAD ochilmadi yoki kalit topilmadi."""


class ReplayError(ProtocolError):
    """Takroriy xabar yoki takroriy INIT."""


class RatchetError(ProtocolError):
    """Ratchet holati bilan bog'liq xato."""


class FileIntegrityError(ProtocolError):
    """S-FILE bo'lagi, Merkle isboti yoki manifest yaxlitligi buzilgan."""


class PolicyError(ProtocolError):
    """Siyosat buzilishi (downgrade, bekor qilingan qurilma, muddat va h.k.)."""
