"""Firibgarlik hisoboti — spec §15 (R11 tuzatishi).

v1.0'da `ReporterProof` ta'riflanmagan, `MIN_K`/`SCORE_THRESHOLD` kabi
normativ qiymatlar yo'q edi. Bu yerda aniq, testlanadigan konstantalar.

Signal, hukm emas: bitta `FraudReport` hech kimni avtomatik "tasdiqlangan
firibgar" qilmaydi. `score_reports()` ikki shartni BIRGA talab qiladi —
`SCORE_THRESHOLD` VA `MIN_K` (distinct reporterlar) — bitta yuqori
og'irlikdagi hisobot yagona o'zi hech kimni belgilay olmaydi.

DIQQAT: `RateLimiter` DIK-asoslangan tezlik cheklash — bu **to'liq
Sybil-qarshilik EMAS** (arzon DIK yaratish mumkin), faqat v1.0 dagi
qaror ustidan qo'shilgan ishqalanish qatlami (spec §20 ochiq masala).
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from ..crypto import canonical
from ..crypto.primitives import HybridSignature, hybrid_sign, hybrid_verify, sha3_256
from .errors import RostorError

CATEGORIES = ("T1", "T2", "T3", "T4", "T5", "T6")
TARGET_TYPES = ("phone", "card_hash", "wallet", "domain", "apk_hash", "institution_id")

# --- §15.2 normativ konstantalar ---
BASE_WEIGHT = 1
INTERACTION_WEIGHT = 3
MIN_K = 5
SCORE_THRESHOLD = 15
RATE_LIMIT_PER_DAY = 10
DECAY_WINDOW_SECS = 90 * 86400


def target_hash(target_type: str, normalized_value: bytes) -> bytes:
    """§8.5 bilan bir xil ochiq, deterministik funksiya — maxfiylik
    xeshning o'zida emas, so'rov usulida (prefiks/lokal sinxronizatsiya)."""
    if target_type not in TARGET_TYPES:
        raise RostorError(f"noma'lum target_type: {target_type}")
    return sha3_256(b"ROSTOR-1/report-target", target_type.encode(), normalized_value)


def report_content_hash(
    target_type: str, target_value_hash: bytes, category: str,
    evidence_hash: Optional[bytes], submitted_at: int,
) -> bytes:
    """KRITIK TUZATISH (tashqi audit, 2026-08-17): avval `ReporterProof`
    faqat `report_id`/`reporter_device_id`/`interaction_ref`ni imzolar
    edi — `target`, `category`, `evidence_hash` va `submitted_at` imzo
    TASHQARISIDA qolardi. Oraliq (ishonchsiz) server haqiqiy imzoni
    saqlagan holda kim ayblanayotganini yoki dalilni ALMASHTIRA olardi.
    Endi reporter AYNAN shu maydonlarning xeshini imzolaydi."""
    return sha3_256(b"ROSTOR-1/report-content", canonical.encode({
        "target_type": target_type, "target_value_hash": target_value_hash,
        "category": category, "evidence_hash": evidence_hash, "submitted_at": submitted_at,
    }))


@dataclass
class ReporterProof:
    reporter_device_id: bytes
    interaction_ref: Optional[bytes]
    device_sig: HybridSignature

    def signed_payload(self, report_id: bytes, content_hash: bytes) -> bytes:
        return b"ROSTOR-1/reporter-proof" + canonical.encode({
            "report_id": report_id, "content_hash": content_hash,
            "reporter_device_id": self.reporter_device_id, "interaction_ref": self.interaction_ref,
        })


@dataclass
class FraudReport:
    v: int
    report_id: bytes
    target_type: str
    target_value_hash: bytes
    category: str
    evidence_hash: Optional[bytes]
    reporter_proof: ReporterProof
    submitted_at: int

    def content_hash(self) -> bytes:
        return report_content_hash(
            self.target_type, self.target_value_hash, self.category,
            self.evidence_hash, self.submitted_at,
        )


def create_fraud_report(
    reporter_device, target_type: str, normalized_value: bytes, category: str,
    *, evidence_hash: Optional[bytes] = None, interaction_ref: Optional[bytes] = None,
    now: Optional[int] = None,
) -> FraudReport:
    from ..crypto.primitives import random_bytes

    if category not in CATEGORIES:
        raise RostorError(f"noma'lum kategoriya: {category}")
    now = int(now if now is not None else time.time())
    report_id = random_bytes(16)
    target_value_hash = target_hash(target_type, normalized_value)
    content_hash = report_content_hash(target_type, target_value_hash, category, evidence_hash, now)

    proof = ReporterProof(
        reporter_device_id=reporter_device.device_id, interaction_ref=interaction_ref,
        device_sig=HybridSignature(b"", b""),
    )
    proof.device_sig = hybrid_sign(
        reporter_device.ik_ed, reporter_device.ik_mldsa,
        proof.signed_payload(report_id, content_hash),
    )
    return FraudReport(
        v=1, report_id=report_id, target_type=target_type,
        target_value_hash=target_value_hash, category=category,
        evidence_hash=evidence_hash, reporter_proof=proof, submitted_at=now,
    )


def verify_fraud_report(report: FraudReport, reporter_dc: dict) -> bool:
    """Endi `report`ning TO'LIQ mazmuni (`content_hash()` orqali)
    tekshiriladi — oraliq server `target`/`category`/`evidence_hash`ni
    almashtirsa, imzo endi mos kelmaydi."""
    return hybrid_verify(
        reporter_dc["ed25519_pk"], reporter_dc["mldsa65_pk"],
        report.reporter_proof.device_sig,
        report.reporter_proof.signed_payload(report.report_id, report.content_hash()),
    )


# ---------------------------------------------------------------------------
# Ballash (§14.2 / §15.2)
# ---------------------------------------------------------------------------
def score_reports(reports: list[FraudReport], *, now: Optional[int] = None) -> tuple[int, int]:
    """-> (score, distinct_reporters). Faqat `DECAY_WINDOW_SECS` ichidagi
    hisobotlar hisoblanadi."""
    now = int(now if now is not None else time.time())
    score = 0
    distinct: set[bytes] = set()
    for r in reports:
        if now - r.submitted_at > DECAY_WINDOW_SECS:
            continue
        weight = INTERACTION_WEIGHT if r.reporter_proof.interaction_ref else BASE_WEIGHT
        score += weight
        distinct.add(r.reporter_proof.reporter_device_id)
    return score, len(distinct)


def is_flagged(reports: list[FraudReport], *, now: Optional[int] = None) -> bool:
    """`MUST`: ikkala shart BIRGA — `score >= SCORE_THRESHOLD` VA
    `distinct_reporters >= MIN_K`."""
    score, distinct = score_reports(reports, now=now)
    return score >= SCORE_THRESHOLD and distinct >= MIN_K


class RateLimiter:
    """DIK-asoslangan tezlik cheklash — Sybil-qarshilikning TO'LIQ EMAS,
    faqat interim (v1.0) qatlami."""

    def __init__(self, limit_per_day: int = RATE_LIMIT_PER_DAY) -> None:
        self.limit = limit_per_day
        self._log: dict[bytes, list[int]] = defaultdict(list)

    def allow(self, reporter_device_id: bytes, *, now: Optional[int] = None) -> bool:
        now = int(now if now is not None else time.time())
        recent = [t for t in self._log[reporter_device_id] if now - t < 86400]
        self._log[reporter_device_id] = recent
        if len(recent) >= self.limit:
            return False
        self._log[reporter_device_id].append(now)
        return True
