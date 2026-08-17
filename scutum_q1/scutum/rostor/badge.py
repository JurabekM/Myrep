"""Tasdiqlangan jo'natuvchi belgisi — spec §10.1, §10.4.

`derive_badge` — **deterministik, auditga ochiq** funksiya, hech qachon
serverning o'z hukmiga tayanmaydi. Fishing manba `institution_id`ga mos
`ed25519_sk`/`mldsa65_sk` maxfiy kalitlariga ega bo'la olmaydi (ular
institutsiyaning apparat himoyalangan saqlovida), shuning uchun
`HybridVerify` doim yiqiladi va belgi hech qachon `VERIFIED` bo'lmaydi.

DIQQAT (§10.4, R10): bu faqat imzoning KRIPTOGRAFIK asosini himoyalaydi.
`✓` belgisi ROSTOR nazorat qilmaydigan sirtda (fishing sahifa, soxta
skrinshot) TAQLID QILINISHI mumkin — bu shu modul yolg'iz hal qila
olmaydigan, OS darajasidagi ishonchli sirt talab qiladigan muammo.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..crypto.primitives import HybridSignature, hybrid_verify

FLAG_THRESHOLD = 15   # fraud_report.py dagi SCORE_THRESHOLD bilan bir xil


class Badge(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    REVOKED = "REVOKED"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    KNOWN_MALICIOUS = "KNOWN_MALICIOUS"
    FLAGGED = "FLAGGED"
    VERIFIED = "VERIFIED"


@dataclass
class LogSnapshot:
    """Mijoz allaqachon `LogClient.accept_sth()` orqali ishonch bilan
    tekshirgan STH'ga mos, lookup natijalarining oddiy ko'rinishi. Bu
    qatlam SMT proof-tekshiruvidan (`transparency.py`/`smt.py`, alohida
    testlangan) ATAYLAB ajratilgan — `derive_badge` faqat ishonch
    zanjiri MANTIG'INI ifodalaydi, proof mexanikasini emas."""

    institutions: dict[bytes, dict] = field(default_factory=dict)     # institution_id -> IC dict
    endorsements: dict[bytes, "object"] = field(default_factory=dict)  # idc_device_id -> IDCEndorsement
    malicious_hashes: set[bytes] = field(default_factory=set)
    fraud_scores: dict[bytes, int] = field(default_factory=dict)

    def lookup_institution(self, institution_id: bytes) -> Optional[dict]:
        return self.institutions.get(institution_id)

    def lookup_endorsement(self, idc_device_id: bytes):
        return self.endorsements.get(idc_device_id)

    def is_malicious(self, h: bytes) -> bool:
        return h in self.malicious_hashes

    def fraud_score(self, institution_id: bytes) -> int:
        return self.fraud_scores.get(institution_id, 0)


@dataclass
class BadgeResult:
    badge: Badge
    display_name: Optional[str] = None
    category: Optional[str] = None


def derive_badge(
    *,
    idc_dc: Optional[dict],
    sig: Optional[HybridSignature],
    signed_payload: bytes,
    snapshot: LogSnapshot,
    sender_hash: Optional[bytes] = None,
    flag_threshold: int = FLAG_THRESHOLD,
    now: Optional[int] = None,
) -> BadgeResult:
    """Spec §10.1 pseudokodining to'g'ridan-to'g'ri amalga oshirilishi,
    §9.2 dagi IC->IDC zanjiri bilan kengaytirilgan.

    KRITIK TUZATISH (tashqi audit, 2026-08-17): avvalgi versiya
    endorsement'ni faqat `idc_dc["device_id"]` bo'yicha qidirib topardi,
    lekin `endorsement.dc_hash` ni TAQDIM ETILGAN `idc_dc`ning o'ziga hech
    qachon solishtirmasdi. `device_id` — OCHIQ maydon (istalgan xabarda
    ko'rinadi); hujumchi haqiqiy institutsiyaning `device_id`sini olib,
    ICHIGA O'Z ochiq kalitlarini qo'ygan SOXTA DC yasab, o'z maxfiy kaliti
    bilan imzolab, `VERIFIED` belgisini olishi mumkin edi (PoC bilan
    isbotlangan). Endi `identity.verify_endorsement()` — bu funksiya
    `dc_hash`ni ANIQ TEKSHIRADI — qayta ishlatiladi, mantiq ikki joyda
    duplikat qilinmaydi (aynan shu duplikatsiya avvalgi bug'ning sababi
    edi)."""
    from .identity import verify_endorsement

    now = int(now if now is not None else time.time())

    if idc_dc is None or sig is None:
        return BadgeResult(Badge.UNVERIFIED)

    endorsement = snapshot.lookup_endorsement(idc_dc["device_id"])
    if endorsement is None:
        return BadgeResult(Badge.UNVERIFIED)
    if now > endorsement.expires_at:
        return BadgeResult(Badge.UNVERIFIED)

    ic = snapshot.lookup_institution(endorsement.institution_id)
    if ic is None:
        return BadgeResult(Badge.UNVERIFIED)
    if ic.get("revoked_at") is not None and now >= ic["revoked_at"]:
        return BadgeResult(Badge.REVOKED)

    if not verify_endorsement(endorsement, ic, idc_dc, now=now):
        return BadgeResult(Badge.INVALID_SIGNATURE)

    idc_ok = hybrid_verify(idc_dc["ed25519_pk"], idc_dc["mldsa65_pk"], sig, signed_payload)
    if not idc_ok:
        return BadgeResult(Badge.INVALID_SIGNATURE)

    if sender_hash is not None and snapshot.is_malicious(sender_hash):
        return BadgeResult(Badge.KNOWN_MALICIOUS)

    if snapshot.fraud_score(ic["institution_id"]) >= flag_threshold:
        return BadgeResult(Badge.FLAGGED, ic["display_name"], ic["category"])

    return BadgeResult(Badge.VERIFIED, ic["display_name"], ic["category"])
