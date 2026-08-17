"""Tranzaksiya tasdiqlash — spec §11-12 (R7 tuzatishi).

Markaziy anti-vishing mexanizmi: OTP kod umuman yo'q, faqat tuzilgan,
ko'rsatiladigan ma'lumotni imzolash bor. `render_for_display()` faqat
tekshirilgan, dekodlangan maydonlardan qaytaradi — sxemada alohida
"displey matni" maydoni ATAYLAB YO'Q, shuning uchun klassik "ekranda
bitta narsa, imzoda boshqa narsa" hujumi SXEMA DARAJASIDA imkonsiz
(WYSIWYS — What You See Is What You Sign).

`TxnConfirmResponse.request_hash` **butun so'rovni** (v1.0'da tashqarida
qolgan `currency`/`purpose`/`institution_id`/`expires_at` bilan birga)
transitiv ravishda qamrab oladi — bu R7'ning to'g'ridan-to'g'ri tuzatishi.

DIQQAT (halol chegara, §12.3): WYSIWYS faqat "displey ≠ imzo"
chalkashligini yo'q qiladi. Foydalanuvchi TO'G'RI ko'rsatilgan firibgar
so'rovni ongli ravishda (bosim ostida) tasdiqlashi — bu hamon ijtimoiy
muhandislik g'alabasi bo'lishi mumkin. `requires_cooling_off()` — bunga
qarshi qo'shimcha, TO'LIQ BO'LMAGAN ishqalanish qatlami.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from ..crypto import canonical
from ..crypto.primitives import HybridSignature, hybrid_sign, hybrid_verify, sha3_256
from .errors import BindingError

DEFAULT_TTL_SECS = 120

#: §12.3 — yuqori-summali/notanish-qabul-qiluvchi operatsiyalar uchun
#: qo'shimcha ishqalanish tavsiyasi (SHOULD, to'liq yechim emas)
COOLING_OFF_AMOUNT_THRESHOLD = 500_000_00   # tiyin (= 500 000 so'm)
COOLING_OFF_SECONDS = 30


# ---------------------------------------------------------------------------
# So'rov
# ---------------------------------------------------------------------------
@dataclass
class TxnConfirmRequest:
    v: int
    txn_id: bytes
    institution_id: bytes
    amount_minor: int
    currency: str
    recipient_masked: str
    purpose: str
    expires_at: int
    institution_sig: HybridSignature

    def _unsigned_dict(self) -> dict:
        return {
            "v": self.v, "txn_id": self.txn_id, "institution_id": self.institution_id,
            "amount_minor": self.amount_minor, "currency": self.currency,
            "recipient_masked": self.recipient_masked, "purpose": self.purpose,
            "expires_at": self.expires_at,
        }

    def signed_payload(self) -> bytes:
        return b"ROSTOR-1/txn-request" + canonical.encode(self._unsigned_dict())

    def request_hash(self) -> bytes:
        """R7: `TxnConfirmResponse` shu qiymatni imzolaydi — barcha
        maydonlarni (jumladan `currency`/`purpose`/`institution_id`/
        `expires_at`ni) transitiv ravishda qamrab oladi."""
        return sha3_256(canonical.encode(self._unsigned_dict()))

    def render_for_display(self) -> dict:
        """WYSIWYS: UI **faqat** shu funksiya natijasini ko'rsatishi
        MUST — boshqa, alohida "matn" maydoni sxemada yo'q."""
        return {
            "institution_id": self.institution_id,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "recipient_masked": self.recipient_masked,
            "purpose": self.purpose,
        }

    def requires_cooling_off(self, *, is_known_recipient: bool = False) -> bool:
        return (
            self.amount_minor >= COOLING_OFF_AMOUNT_THRESHOLD
            or not is_known_recipient
        )


def create_txn_confirm_request(
    institution_idc, institution_id: bytes, *,
    amount_minor: int, currency: str, recipient_masked: str, purpose: str,
    ttl_secs: int = DEFAULT_TTL_SECS, now: Optional[int] = None,
    txn_id: Optional[bytes] = None,
) -> TxnConfirmRequest:
    from ..crypto.primitives import random_bytes

    now = int(now if now is not None else time.time())
    req = TxnConfirmRequest(
        v=1, txn_id=txn_id or random_bytes(16), institution_id=institution_id,
        amount_minor=amount_minor, currency=currency, recipient_masked=recipient_masked,
        purpose=purpose, expires_at=now + ttl_secs,
        institution_sig=HybridSignature(b"", b""),
    )
    signed = req.signed_payload()
    req.institution_sig = hybrid_sign(institution_idc.ik_ed, institution_idc.ik_mldsa, signed)
    return req


def verify_txn_confirm_request(req: TxnConfirmRequest, idc_dc: dict) -> bool:
    return hybrid_verify(
        idc_dc["ed25519_pk"], idc_dc["mldsa65_pk"], req.institution_sig, req.signed_payload()
    )


# ---------------------------------------------------------------------------
# Javob
# ---------------------------------------------------------------------------
@dataclass
class TxnConfirmResponse:
    request_hash: bytes
    decision: str          # "APPROVE" | "DENY"
    account_id: bytes
    device_id: bytes
    responded_at: int
    device_sig: HybridSignature

    def signed_payload(self) -> bytes:
        return b"ROSTOR-1/txn-response" + canonical.encode({
            "request_hash": self.request_hash, "decision": self.decision,
            "account_id": self.account_id, "device_id": self.device_id,
            "responded_at": self.responded_at,
        })


def create_txn_confirm_response(
    user_device, request: TxnConfirmRequest, decision: str, account_id: bytes,
    *, now: Optional[int] = None,
) -> TxnConfirmResponse:
    if decision not in ("APPROVE", "DENY"):
        raise BindingError(f"noto'g'ri decision: {decision}")
    now = int(now if now is not None else time.time())
    resp = TxnConfirmResponse(
        request_hash=request.request_hash(), decision=decision, account_id=account_id,
        device_id=user_device.device_id, responded_at=now,
        device_sig=HybridSignature(b"", b""),
    )
    resp.device_sig = hybrid_sign(user_device.ik_ed, user_device.ik_mldsa, resp.signed_payload())
    return resp


def verify_txn_confirm_response(
    resp: TxnConfirmResponse, user_dc: dict, request: TxnConfirmRequest,
    *, account_state=None, now: Optional[int] = None,
) -> bool:
    """`resp.request_hash` `request.request_hash()`ga MOS kelishi shart
    — aks holda javob boshqa (masalan kichikroq, zararsiz ko'ringan)
    so'rovga berilgan bo'lib, bu so'rovga "yopishtirilishi" mumkin edi.

    `account_state` (ixtiyoriy, `rostor.account.AccountAuthState`)
    berilsa — tashqi audit topilmasi: avval `resp.device_id` HECH QACHON
    `resp.account_id` uchun ruxsat etilgan qurilmalar ro'yxati bilan
    solishtirilmasdi. Bekor qilingan/begona qurilma imzosi (agar u
    negadir haqiqiy `user_dc` kaliti bilan kelsa — masalan chaqiruvchi
    kodi noto'g'ri DC ni tekshiruvga bergan bo'lsa) endi rad etiladi.

    DIQQAT: bir martalik iste'mol (`txn_id` qayta ishlatilishining
    oldini olish) protokol darajasidan tashqarida — bank backend'i
    o'zi qaysi `txn_id` lar allaqachon hisobga olinganini kuzatishi
    `MUST` (odatiy idempotency-key naqshi)."""
    now = int(now if now is not None else time.time())
    if resp.request_hash != request.request_hash():
        return False
    if now > request.expires_at:
        return False
    if account_state is not None:
        if resp.account_id != account_state.account_id:
            return False
        if not account_state.is_authorized(resp.device_id):
            return False
    return hybrid_verify(
        user_dc["ed25519_pk"], user_dc["mldsa65_pk"], resp.device_sig, resp.signed_payload()
    )
