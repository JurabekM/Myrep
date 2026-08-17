"""Institutsiya identiteti — ikki qatlamli model, spec §9 (R6 tuzatishi).

v1.0'dagi `InstitutionCertificate` statik x25519/ML-KEM kalitlarini
berardi, lekin SCUTUM-Q1 handshake (meros, o'zgarishsiz) `SPK`/`OPK`/
muddatli-`ML-KEM` prekey talab qiladi. Bu yerda ikkiga bo'lingan:

  * `InstitutionKeys` / IC — FAQAT imzolash uchun, uzoq muddatli, sessiya
    ochmaydi;
  * `IDCEndorsement` — IC ning imzosi bilan "bu oddiy SCUTUM-Q1 qurilmasi
    (DeviceKeys/DC — `protocol/identity.py`dan BAYT-BAYT o'zgarishsiz)
    haqiqatan shu institutsiyaga tegishli" deb tasdiqlovchi ko'prik.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from ..crypto import canonical
from ..crypto.primitives import (
    HybridSignature,
    ed25519_generate,
    ed25519_pub,
    hybrid_sign,
    hybrid_verify,
    mldsa_generate,
    mldsa_pub,
    random_bytes,
    sha3_256,
)
from .errors import TrustError

DAY = 86400
CATEGORIES = ("bank", "government", "marketplace", "telecom", "software_publisher")


# ---------------------------------------------------------------------------
# InstitutionCertificate (IC) — ildiz, faqat imzolash
# ---------------------------------------------------------------------------
@dataclass
class InstitutionKeys:
    institution_id: bytes
    category: str
    display_name: str
    ed_sk: object
    mldsa_sk: object
    registered_at: int
    expires_at: int
    revoked_at: Optional[int] = None

    @classmethod
    def generate(cls, category: str, display_name: str, *,
                lifetime_days: int = 730, now: Optional[int] = None) -> "InstitutionKeys":
        if category not in CATEGORIES:
            raise TrustError(f"noma'lum kategoriya: {category}")
        now = int(now if now is not None else time.time())
        return cls(
            institution_id=random_bytes(16), category=category, display_name=display_name,
            ed_sk=ed25519_generate(), mldsa_sk=mldsa_generate(),
            registered_at=now, expires_at=now + lifetime_days * DAY,
        )

    @property
    def ed25519_pk(self) -> bytes:
        return ed25519_pub(self.ed_sk)

    @property
    def mldsa65_pk(self) -> bytes:
        return mldsa_pub(self.mldsa_sk)

    def certificate(self) -> dict:
        """Kanonik `InstitutionCertificate` (spec §9.2)."""
        return {
            "v": 1, "institution_id": self.institution_id, "category": self.category,
            "display_name": self.display_name, "ed25519_pk": self.ed25519_pk,
            "mldsa65_pk": self.mldsa65_pk, "registered_at": self.registered_at,
            "expires_at": self.expires_at, "revoked_at": self.revoked_at,
        }

    def revoke(self, *, now: Optional[int] = None) -> None:
        self.revoked_at = int(now if now is not None else time.time())


def ic_bytes(ic: dict) -> bytes:
    return canonical.encode(ic)


def ic_hash(ic: dict) -> bytes:
    return sha3_256(ic_bytes(ic))


# ---------------------------------------------------------------------------
# IDCEndorsement — IC "bu SCUTUM-Q1 DC menga tegishli" deb tasdiqlaydi
# ---------------------------------------------------------------------------
@dataclass
class IDCEndorsement:
    institution_id: bytes
    dc_hash: bytes
    issued_at: int
    expires_at: int
    ic_sig: HybridSignature

    def signed_payload(self) -> bytes:
        return endorsement_payload(
            self.institution_id, self.dc_hash, self.issued_at, self.expires_at
        )


def endorsement_payload(
    institution_id: bytes, dc_hash: bytes, issued_at: int, expires_at: int,
) -> bytes:
    return b"ROSTOR-1/idc-endorsement" + canonical.encode({
        "institution_id": institution_id, "dc_hash": dc_hash,
        "issued_at": issued_at, "expires_at": expires_at,
    })


def issue_endorsement(
    ic: InstitutionKeys, idc_dc: dict, *,
    lifetime_days: int = 7, now: Optional[int] = None,
) -> IDCEndorsement:
    """Institutsiya o'zining bitta SCUTUM-Q1 qurilmasini (masalan
    "ilova-backend #1") tez-tez yangilanadigan endorsement bilan
    tasdiqlaydi — `IC`ning o'zi muddat jihatidan uzoqroq, `IDC` muddati
    esa qisqaroq va SPK kabi tez-tez rotatsiya qilinadi."""
    now = int(now if now is not None else time.time())
    d_hash = sha3_256(canonical.encode(idc_dc))
    endorsement = IDCEndorsement(
        institution_id=ic.institution_id, dc_hash=d_hash,
        issued_at=now, expires_at=now + lifetime_days * DAY,
        ic_sig=HybridSignature(b"", b""),
    )
    endorsement.ic_sig = hybrid_sign(ic.ed_sk, ic.mldsa_sk, endorsement.signed_payload())
    return endorsement


def verify_endorsement(
    endorsement: IDCEndorsement, ic: dict, idc_dc: dict, *, now: Optional[int] = None,
) -> bool:
    now = int(now if now is not None else time.time())
    if now > endorsement.expires_at:
        return False
    if sha3_256(canonical.encode(idc_dc)) != endorsement.dc_hash:
        return False
    if ic.get("revoked_at") is not None and now >= ic["revoked_at"]:
        return False
    return hybrid_verify(
        ic["ed25519_pk"], ic["mldsa65_pk"], endorsement.ic_sig, endorsement.signed_payload()
    )
