"""Pul qabul qilish protokoli — spec §14 (R9 tuzatishi).

v1.0'da `PaymentIntent` imzosiz edi — istalgan kim o'zini "qabul
qiluvchi" sifatida ko'rsatishi mumkin edi. Bundan tashqari erkin `memo`
maydoni fishing havolasini olib yurishi mumkin edi.

Protokol invarianti (`MUST`): sxemada kredensial-shaklidagi maydon
(karta raqami, CVV, OTP) **umuman yo'q** — bu Classiscam-uslubidagi
"pul olish uchun kartangizni tasdiqlang" firibgarligini sxema darajasida
imkonsiz qiladi.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional

from ..crypto import canonical
from ..crypto.primitives import HybridSignature, hybrid_sign, hybrid_verify, random_bytes, sha3_256
from .errors import PolicyViolation

MAX_MEMO_LEN = 140
DEFAULT_TTL_SECS = 900

#: PaymentIntent sxemasida MUST NOT bo'lgan, kredensial-shaklidagi
#: maydon nomlari — tashqi manbadan kelgan xom dictni tekshirishda
#: ishlatiladi (§14: "qo'shimcha maydon bo'lsa klient rad etadi").
FORBIDDEN_FIELDS = {
    "card_number", "cvv", "cvv2", "otp", "pan", "expiry_date",
    "password", "pin", "card_pin", "security_code",
}
ALLOWED_FIELDS = {
    "v", "intent_id", "issuer_id", "payee_token", "amount_minor",
    "memo", "expires_at", "issuer_sig",
}

_URL_RE = re.compile(r"(https?://|www\.|\.uz\b|\.com\b|\.ru\b)", re.IGNORECASE)


def reject_unknown_fields(raw: dict) -> None:
    """Xom (masalan tarmoqdan kelgan) dict PaymentIntent sifatida
    ko'rsatilgan bo'lsa, ruxsat etilmagan/kredensial-shaklidagi maydon
    borligini tekshiradi."""
    extra = set(raw) - ALLOWED_FIELDS
    suspicious = extra & (FORBIDDEN_FIELDS | extra)
    if extra:
        raise PolicyViolation(
            f"PaymentIntent sxemasida yo'q maydon(lar) topildi: {sorted(extra)} — "
            "bu pul olish uchun kerak bo'lmagan ma'lumot so'rayotgan bo'lishi mumkin"
        )


def payee_token(issuer_ed25519_pk: bytes, nonce: bytes) -> bytes:
    """Opaque, DIK-bog'langan, MAXFIY EMAS identifikator — bank hisob
    raqami kabi ochiq bo'lishi mumkin, ruxsatsiz operatsiyaga imkon
    bermaydi."""
    return sha3_256(b"ROSTOR-1/payee-token", issuer_ed25519_pk, nonce)


def check_memo(memo: str) -> tuple[str, bool]:
    """-> (kesilgan_memo, url_ogohlantirish_kerakmi). Klient inert oddiy
    matn sifatida ko'rsatadi — hech qanday avtomatik havola/HTML render
    qilinmaydi (§14)."""
    trimmed = memo[:MAX_MEMO_LEN]
    return trimmed, bool(_URL_RE.search(trimmed))


@dataclass
class PaymentIntent:
    v: int
    intent_id: bytes
    issuer_id: bytes            # IDC device_id (§9)
    payee_token: bytes
    amount_minor: Optional[int]
    memo: str
    expires_at: int
    issuer_sig: HybridSignature

    def _unsigned_dict(self) -> dict:
        return {
            "v": self.v, "intent_id": self.intent_id, "issuer_id": self.issuer_id,
            "payee_token": self.payee_token, "amount_minor": self.amount_minor,
            "memo": self.memo, "expires_at": self.expires_at,
        }

    def signed_payload(self) -> bytes:
        return b"ROSTOR-1/payment-intent" + canonical.encode(self._unsigned_dict())


def create_payment_intent(
    issuer_idc, *, nonce: Optional[bytes] = None, amount_minor: Optional[int] = None,
    memo: str = "", ttl_secs: int = DEFAULT_TTL_SECS, now: Optional[int] = None,
) -> PaymentIntent:
    from ..crypto.primitives import ed25519_pub

    now = int(now if now is not None else time.time())
    memo_trimmed, has_url = check_memo(memo)
    if has_url:
        raise PolicyViolation(
            "memo havolaga o'xshash matn saqlaydi — PaymentIntent'ga qo'shilmaydi"
        )
    token = payee_token(ed25519_pub(issuer_idc.ik_ed), nonce or random_bytes(16))
    intent = PaymentIntent(
        v=1, intent_id=random_bytes(16), issuer_id=issuer_idc.device_id,
        payee_token=token, amount_minor=amount_minor, memo=memo_trimmed,
        expires_at=now + ttl_secs, issuer_sig=HybridSignature(b"", b""),
    )
    intent.issuer_sig = hybrid_sign(
        issuer_idc.ik_ed, issuer_idc.ik_mldsa, intent.signed_payload()
    )
    return intent


def verify_payment_intent(intent: PaymentIntent, issuer_dc: dict, *, now: Optional[int] = None) -> bool:
    """Tashqi audit (2026-08-17): `intent.issuer_id` endi taqdim etilgan
    `issuer_dc["device_id"]` bilan ANIQ mos kelishi tekshiriladi — bu
    chaqiruvchi kodni "intent o'zi da'vo qilgan issuer_id"ni ko'r-ko'rona
    ishonib qabul qilishdan (masalan noto'g'ri DC bilan chaqirishdan)
    himoyalaydi; asosiy himoya baribir gibrid imzo bo'lib qoladi."""
    now = int(now if now is not None else time.time())
    if now > intent.expires_at:
        return False
    if intent.issuer_id != issuer_dc["device_id"]:
        return False
    return hybrid_verify(
        issuer_dc["ed25519_pk"], issuer_dc["mldsa65_pk"],
        intent.issuer_sig, intent.signed_payload(),
    )
