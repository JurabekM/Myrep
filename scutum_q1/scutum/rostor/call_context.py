"""CALL_CONTEXT — push-first qo'ng'iroq autentifikatsiyasi, spec §11.3 (R2).

Tashqi audit topilmasi (2026-08-17, KRITIK #6): "Tekshiruv" (§10.3, avval
`institutions.py` GUI paneli) faqat institutsiya REESTRDA BORLIGINI
tasdiqlaydi — HOZIR SIZGA QO'NG'IROQ QILAYOTGAN TOMONNI emas. Firibgar
"men Markaziy bankman" desa, foydalanuvchi "Markaziy bank"ni qidiradi va
HA javobini oladi — bu hech narsani isbotlamaydi. Spec bu muammoni
`CALL_CONTEXT push-first` modeli bilan "tuzatilgan" deb belgilagan edi,
lekin bu modul kodda umuman yo'q edi.

Yechim: institutsiya haqiqiy qo'ng'iroqdan OLDIN yoki UNING DAVOMIDA
push qiladigan, imzolangan `CallContext`. `is_call_legitimate()` —
**fail-closed**: mos, haqiqiy, muddati o'tmagan yozuv topilmasa, natija
HAR DOIM `False` — qo'ng'iroq DAVOMIDA hujumchi nima desa ham buni
o'zgartira olmaydi (P8 qoidasi, spec §11.3).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from ..crypto import canonical
from ..crypto.primitives import HybridSignature, hybrid_sign, hybrid_verify, random_bytes

DEFAULT_TTL_SECS = 300


@dataclass
class CallContext:
    v: int
    call_id: bytes
    institution_id: bytes
    official_number: str        # institutsiyaning RASMIY, ro'yxatdan o'tgan raqami
    reason: str
    issued_at: int
    expires_at: int
    institution_sig: HybridSignature

    def _unsigned_dict(self) -> dict:
        return {
            "v": self.v, "call_id": self.call_id, "institution_id": self.institution_id,
            "official_number": self.official_number, "reason": self.reason,
            "issued_at": self.issued_at, "expires_at": self.expires_at,
        }

    def signed_payload(self) -> bytes:
        return b"ROSTOR-1/call-context" + canonical.encode(self._unsigned_dict())


def create_call_context(
    institution_idc, institution_id: bytes, official_number: str, reason: str,
    *, ttl_secs: int = DEFAULT_TTL_SECS, now: Optional[int] = None,
) -> CallContext:
    now = int(now if now is not None else time.time())
    cc = CallContext(
        v=1, call_id=random_bytes(16), institution_id=institution_id,
        official_number=official_number, reason=reason,
        issued_at=now, expires_at=now + ttl_secs,
        institution_sig=HybridSignature(b"", b""),
    )
    cc.institution_sig = hybrid_sign(institution_idc.ik_ed, institution_idc.ik_mldsa, cc.signed_payload())
    return cc


def verify_call_context(cc: CallContext, idc_dc: dict, *, now: Optional[int] = None) -> bool:
    now = int(now if now is not None else time.time())
    if now > cc.expires_at:
        return False
    return hybrid_verify(
        idc_dc["ed25519_pk"], idc_dc["mldsa65_pk"], cc.institution_sig, cc.signed_payload()
    )


def is_call_legitimate(
    incoming_number: str,
    active_contexts: list[CallContext],
    idc_dc_by_institution: dict,
    *, now: Optional[int] = None,
) -> bool:
    """P8 qoidasi (spec §3): "ROSTOR-mos institutsiya HECH QACHON oldindan
    CALL_CONTEXT push qilinmagan qo'ng'iroq orqali muhim operatsiyaga oid
    so'rov bermaydi." Bu funksiya faqat mos raqam + haqiqiy imzo + muddat
    ichida bo'lgan holatda `True` qaytaradi — aks holda **doim** `False`."""
    now = int(now if now is not None else time.time())
    for cc in active_contexts:
        if cc.official_number != incoming_number:
            continue
        idc_dc = idc_dc_by_institution.get(cc.institution_id)
        if idc_dc is None:
            continue
        if verify_call_context(cc, idc_dc, now=now):
            return True
    return False
