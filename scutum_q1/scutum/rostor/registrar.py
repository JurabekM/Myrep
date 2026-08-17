"""Registrator konsorsiumi — spec §4.1 (R5 tuzatishi).

v1.0 "k-of-n imzo kerak" deb aytgan, lekin kimning kaliti DASTLAB
ro'yxatga kiritilishini, uni kim o'zgartira olishini ta'riflamagan edi
(tashqi audit topilmasi). Bu modul:

  * `GenesisAnchor` — tashqi kanalda tarqatiladigan, kod ichida qattiq
    yozilgan dastlabki tarkib (huquqiy/tashkiliy qaror, texnik jihatdan
    faqat "shu ro'yxatdan boshlanadi" deb belgilanadi);
  * `RegistrarRoster` — o'z-o'zini kengaytiruvchi zanjir: har yangi tarkib
    OLDINGI tarkibning k-of-n roziligi bilan tasdiqlanadi;
  * `RegistrarApproval` — IC/PC chiqarish yoki bekor qilishni domen
    ajratilgan, kontekstga bog'langan tarzda tasdiqlaydi (log_id, action,
    epoch — v1.0'da yo'q edi).

Muhim: haqiqiy threshold-imzo sxemasi (masalan FROST) O'RNIGA k ta
ALOHIDA gibrid imzo ishlatiladi — chunki post-kvant threshold sxemalari
hali tekshirilgan kutubxonalarda yo'q (P7 tamoyili).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..crypto import canonical
from ..crypto.primitives import HybridSignature, hybrid_verify, sha3_256
from .errors import TrustError


# ---------------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RegistrarEntry:
    registrar_id: bytes
    ed25519_pk: bytes
    mldsa65_pk: bytes
    display_name: str

    def to_dict(self) -> dict:
        return {
            "registrar_id": self.registrar_id, "ed25519_pk": self.ed25519_pk,
            "mldsa65_pk": self.mldsa65_pk, "display_name": self.display_name,
        }

    @staticmethod
    def from_dict(d: dict) -> "RegistrarEntry":
        return RegistrarEntry(d["registrar_id"], d["ed25519_pk"], d["mldsa65_pk"],
                              d["display_name"])


@dataclass
class GenesisAnchor:
    v: int
    roster_epoch: int   # = 0
    registrars: list[RegistrarEntry]
    published_at: int


@dataclass
class RegistrarRosterUpdate:
    v: int
    roster_epoch: int
    added: list[RegistrarEntry]
    removed: list[bytes]        # registrar_id lar
    effective_at: int
    approvals: list[tuple[bytes, HybridSignature]] = field(default_factory=list)

    def signed_payload(self) -> bytes:
        return b"ROSTOR-1/roster-update" + canonical.encode({
            "roster_epoch": self.roster_epoch,
            "added": [e.to_dict() for e in self.added],
            "removed": self.removed,
            "effective_at": self.effective_at,
        })


class RegistrarRoster:
    """Joriy tarkibni ushlab turadi, epoch monotonligini majburlaydi."""

    def __init__(self, genesis: GenesisAnchor) -> None:
        if genesis.roster_epoch != 0:
            raise TrustError("GenesisAnchor.roster_epoch=0 bo'lishi shart")
        self.epoch = 0
        self.members: dict[bytes, RegistrarEntry] = {
            r.registrar_id: r for r in genesis.registrars
        }

    def apply_update(self, update: RegistrarRosterUpdate, k: int) -> None:
        """`update.roster_epoch` joriy epoch+1 bo'lishi va kamida `k` ta
        ALOHIDA a'zo (JORIY, YANGILANISHDAN OLDINGI tarkibdan) uni
        tasdiqlashi shart — bu o'z-o'zini kengaytiruvchi zanjirni
        ta'minlaydi."""
        _require_positive_k(k, len(self.members))
        if update.roster_epoch != self.epoch + 1:
            raise TrustError(
                f"roster_epoch ketma-ketligi buzildi: kutilgan {self.epoch + 1}, "
                f"kelgan {update.roster_epoch}"
            )
        signed = update.signed_payload()
        valid_ids: set[bytes] = set()
        for rid, sig in update.approvals:
            member = self.members.get(rid)
            if member and hybrid_verify(member.ed25519_pk, member.mldsa65_pk, sig, signed):
                valid_ids.add(rid)
        if len(valid_ids) < k:
            raise TrustError(
                f"roster yangilanishi uchun approval yetarli emas: "
                f"{len(valid_ids)} < {k}"
            )
        for rid in update.removed:
            self.members.pop(rid, None)
        for entry in update.added:
            self.members[entry.registrar_id] = entry
        self.epoch = update.roster_epoch

    def verify_member_sig(self, registrar_id: bytes, sig: HybridSignature,
                          signed: bytes) -> bool:
        member = self.members.get(registrar_id)
        if member is None:
            return False
        return hybrid_verify(member.ed25519_pk, member.mldsa65_pk, sig, signed)


# ---------------------------------------------------------------------------
# RegistrarApproval — IC/PC chiqarish/bekor qilish uchun (R5 ikkinchi qismi)
# ---------------------------------------------------------------------------
ACTIONS = ("issue_ic", "issue_pc", "revoke", "roster_update")


def registrar_approval_payload(
    log_id: bytes, action: str, roster_epoch: int, target_hash: bytes,
) -> bytes:
    """v1.0'dagi `ic_hash`ga o'xshash qiymatni imzolash o'rniga — endi
    qaysi jurnal (`log_id`), qaysi amal (`action`) va qaysi epoch ekanligi
    imzoning o'zida, boshqa kontekstda qayta ishlatib bo'lmaydigan tarzda."""
    if action not in ACTIONS:
        raise TrustError(f"noma'lum amal turi: {action}")
    return b"ROSTOR-1/registrar-approval" + canonical.encode({
        "log_id": log_id, "action": action,
        "roster_epoch": roster_epoch, "target_hash": target_hash,
    })


@dataclass
class RegistrarApproval:
    log_id: bytes
    action: str
    roster_epoch: int
    target_hash: bytes
    approvals: list[tuple[bytes, HybridSignature]] = field(default_factory=list)

    def signed_payload(self) -> bytes:
        return registrar_approval_payload(
            self.log_id, self.action, self.roster_epoch, self.target_hash
        )


def _require_positive_k(k: int, n_members: int) -> None:
    """Tashqi audit (2026-08-17): `k` chaqiruvchi argumentidan olinardi,
    siyosatdan emas — `k=0` (yoki manfiy) berilsa, HAR QANDAY (hatto
    bo'sh) `approvals` ro'yxati "tasdiqlangan" deb hisoblanardi. Bu —
    butun k-of-n konsorsium modelini chetlab o'tish edi."""
    if k < 1:
        raise TrustError(f"k >= 1 bo'lishi shart, berildi: {k}")
    if k > n_members:
        raise TrustError(f"k ({k}) a'zolar sonidan ({n_members}) katta bo'lishi mumkin emas")


def verify_registrar_approval(
    approval: RegistrarApproval, roster: RegistrarRoster, k: int,
) -> bool:
    _require_positive_k(k, len(roster.members))
    if approval.roster_epoch != roster.epoch:
        return False   # eskirgan yoki kelajakdagi epoch bilan tasdiqlashga urinish
    signed = approval.signed_payload()
    valid_ids = {
        rid for rid, sig in approval.approvals
        if roster.verify_member_sig(rid, sig, signed)
    }
    return len(valid_ids) >= k
