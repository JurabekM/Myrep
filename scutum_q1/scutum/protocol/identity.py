"""Spec §3: identifikatsiya, Device Certificate, pre-key bundle."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from ..config import PROTOCOL_VERSION, ProtocolConfig
from ..crypto import canonical
from ..crypto.primitives import (
    HybridSignature,
    ed25519_generate,
    ed25519_pub,
    hybrid_sign,
    hybrid_verify,
    mldsa_generate,
    mldsa_pub,
    mlkem_generate,
    mlkem_pub,
    random_bytes,
    sha3_256,
    x25519_generate,
    x25519_pub,
)
from .errors import ProtocolError, VerificationError

DAY = 86400


# ---------------------------------------------------------------------------
# Device Certificate
# ---------------------------------------------------------------------------
def build_dc(
    device_id: bytes,
    x25519_pk: bytes,
    ed25519_pk: bytes,
    mldsa65_pk: bytes,
    created_at: int,
    expires_at: int,
) -> dict:
    """Spec §3.1 kanonik DC obyekti."""
    return {
        "v": PROTOCOL_VERSION,
        "device_id": device_id,
        "x25519_pk": x25519_pk,
        "ed25519_pk": ed25519_pk,
        "mldsa65_pk": mldsa65_pk,
        "created_at": created_at,
        "expires_at": expires_at,
    }


def dc_bytes(dc: dict, cfg: ProtocolConfig) -> bytes:
    return canonical.encode(dc, cfg.encoding)


def device_fingerprint(dc: dict, cfg: ProtocolConfig) -> bytes:
    """Foydalanuvchi tasdiqlaydigan identifikator.

    SPEC (§3.1):  SHA3-256(canonical_DC)  -> created_at/expires_at ham kiradi,
                  ya'ni DC har yangilanganda fingerprint o'zgaradi (Y-7).
    HARDENED:     faqat identity ochiq kalitlar ustidan -> barqaror.
    """
    if cfg.fingerprint_keys_only:
        return sha3_256(
            b"SCUTUM-Q1/fp",
            dc["x25519_pk"],
            dc["ed25519_pk"],
            dc["mldsa65_pk"],
        )
    return sha3_256(dc_bytes(dc, cfg))


def fingerprint_words(fp: bytes, groups: int = 8) -> str:
    """Xavfsizlik raqami — QR/og'zaki solishtirish uchun guruhlangan format."""
    digits = "".join(f"{b:03d}" for b in fp[: groups * 2])
    return " ".join(digits[i : i + 5] for i in range(0, len(digits), 5))


# ---------------------------------------------------------------------------
# Qurilma kalitlari
# ---------------------------------------------------------------------------
@dataclass
class OneTimePreKey:
    opk_id: bytes
    sk: object
    pk: bytes


@dataclass
class DeviceKeys:
    """Spec §3: DIK + SPK + OPK to'plami (bitta qurilmaning butun kalit holati)."""

    name: str
    device_id: bytes
    ik_x: object
    ik_ed: object
    ik_mldsa: object
    spk_x: object
    spk_mlkem: object
    spk_created_at: int
    spk_expiry: int
    created_at: int
    expires_at: int
    opks: dict[bytes, OneTimePreKey] = field(default_factory=dict)
    revoke_epoch: int = 0
    revoked: bool = False

    # --- yaratish ---
    @classmethod
    def generate(
        cls, name: str, cfg: ProtocolConfig, now: Optional[int] = None
    ) -> "DeviceKeys":
        now = int(now if now is not None else time.time())
        dev = cls(
            name=name,
            device_id=random_bytes(16),
            ik_x=x25519_generate(),
            ik_ed=ed25519_generate(),
            ik_mldsa=mldsa_generate(),
            spk_x=x25519_generate(),
            spk_mlkem=mlkem_generate(),
            spk_created_at=now,
            spk_expiry=now + cfg.spk_lifetime_days * DAY,
            created_at=now,
            expires_at=now + cfg.dik_lifetime_days * DAY,
        )
        dev.refill_opks(count=8)
        return dev

    # --- ochiq materiallar ---
    @property
    def ik_x_pk(self) -> bytes:
        return x25519_pub(self.ik_x)

    @property
    def ik_ed_pk(self) -> bytes:
        return ed25519_pub(self.ik_ed)

    @property
    def ik_mldsa_pk(self) -> bytes:
        return mldsa_pub(self.ik_mldsa)

    @property
    def spk_x_pk(self) -> bytes:
        return x25519_pub(self.spk_x)

    @property
    def spk_mlkem_pk(self) -> bytes:
        return mlkem_pub(self.spk_mlkem)

    def dc(self) -> dict:
        return build_dc(
            self.device_id,
            self.ik_x_pk,
            self.ik_ed_pk,
            self.ik_mldsa_pk,
            self.created_at,
            self.expires_at,
        )

    def fingerprint(self, cfg: ProtocolConfig) -> bytes:
        return device_fingerprint(self.dc(), cfg)

    # --- rotatsiya (spec §8) ---
    def rotate_spk(self, cfg: ProtocolConfig, now: Optional[int] = None) -> None:
        now = int(now if now is not None else time.time())
        self.spk_x = x25519_generate()
        self.spk_mlkem = mlkem_generate()
        self.spk_created_at = now
        self.spk_expiry = now + cfg.spk_lifetime_days * DAY

    def rotate_dik(self, cfg: ProtocolConfig, now: Optional[int] = None) -> None:
        now = int(now if now is not None else time.time())
        self.ik_x = x25519_generate()
        self.ik_ed = ed25519_generate()
        self.ik_mldsa = mldsa_generate()
        self.created_at = now
        self.expires_at = now + cfg.dik_lifetime_days * DAY
        self.revoke_epoch += 1

    def renew_dc(self, cfg: ProtocolConfig, now: Optional[int] = None) -> None:
        """Kalitlarni o'zgartirmasdan DC muddatini uzaytirish.

        Y-7 namoyishi: SPEC rejimda bu fingerprint'ni ham o'zgartiradi.
        """
        now = int(now if now is not None else time.time())
        self.created_at = now
        self.expires_at = now + cfg.dik_lifetime_days * DAY

    def refill_opks(self, count: int = 8) -> None:
        for _ in range(count):
            sk = x25519_generate()
            opk = OneTimePreKey(random_bytes(8), sk, x25519_pub(sk))
            self.opks[opk.opk_id] = opk

    def take_opk(self, opk_id: bytes) -> Optional[OneTimePreKey]:
        """Spec §5.2: ishlatilgan OPK atomik tarzda o'chirilishi MUST."""
        return self.opks.pop(opk_id, None)

    def peek_opk(self) -> Optional[OneTimePreKey]:
        for opk in self.opks.values():
            return opk
        return None


# ---------------------------------------------------------------------------
# PreKeyBundle (spec §5.1)
# ---------------------------------------------------------------------------
def _bundle_signed_message(bundle: dict, cfg: ProtocolConfig) -> bytes:
    """Imzo ostiga tushadigan bayt ketma-ketligi.

    SPEC:      sig(DC || SPK)  — xom konkatenatsiya, uzunlik prefiksi yo'q,
               SPK_expiry va OPK imzo TASHQARISIDA (Y-6).
    HARDENED:  domen prefiksi + butun kanonik bundle.
    """
    if cfg.sign_full_bundle:
        payload = {
            "dc": bundle["dc"],
            "spk_x": bundle["spk_x_pk"],
            "spk_mlkem": bundle["spk_mlkem_pk"],
            "spk_expiry": bundle["spk_expiry"],
            "opk_id": bundle.get("opk_id"),
            "opk_pk": bundle.get("opk_pk"),
            # tashqi audit (2026-08-17): revoke_epoch avval imzo tashqarisida
            # qolgan edi -> server buni istalgan qiymatga almashtira olardi,
            # DC/SPK imzosi hali ham haqiqiy ko'rinardi -> Y-8 anti-rollback
            # himoyasi to'liq chetlab o'tilardi.
            "revoke_epoch": bundle.get("revoke_epoch", 0),
        }
        return b"SCUTUM-Q1/prekey" + canonical.encode(payload, cfg.encoding)
    return (
        canonical.encode(bundle["dc"], cfg.encoding)
        + bundle["spk_x_pk"]
        + bundle["spk_mlkem_pk"]
    )


def build_prekey_bundle(
    dev: DeviceKeys, cfg: ProtocolConfig, *, with_opk: bool = True
) -> dict:
    opk = dev.peek_opk() if with_opk else None
    bundle = {
        "dc": dev.dc(),
        "spk_x_pk": dev.spk_x_pk,
        "spk_mlkem_pk": dev.spk_mlkem_pk,
        "spk_expiry": dev.spk_expiry,
        "opk_id": opk.opk_id if opk else None,
        "opk_pk": opk.pk if opk else None,
        "revoke_epoch": dev.revoke_epoch,
    }
    msg = _bundle_signed_message(bundle, cfg)
    sig = hybrid_sign(dev.ik_ed, dev.ik_mldsa, msg)
    bundle["sig_ed25519"] = sig.ed25519
    bundle["sig_mldsa65"] = sig.mldsa65
    return bundle


def verify_prekey_bundle(
    bundle: dict, cfg: ProtocolConfig, *, now: Optional[int] = None
) -> None:
    """Spec §5.1: "Klient ikkala imzoni tekshirmasdan bundle'ni qabul qilishi MUST NOT"."""
    dc = bundle["dc"]
    msg = _bundle_signed_message(bundle, cfg)
    sig = HybridSignature(bundle["sig_ed25519"], bundle["sig_mldsa65"])
    if not hybrid_verify(dc["ed25519_pk"], dc["mldsa65_pk"], sig, msg):
        raise VerificationError("PreKeyBundle gibrid imzosi haqiqiy emas")

    now = int(now if now is not None else time.time())
    if now > dc["expires_at"]:
        raise VerificationError("Device Certificate muddati o'tgan")
    if now > bundle["spk_expiry"]:
        raise VerificationError("Signed Pre-Key muddati o'tgan")

    if cfg.strict_encoding and not canonical.is_deterministic(
        canonical.encode(dc, cfg.encoding), cfg.encoding
    ):
        raise VerificationError("DC kanonik kodlanmagan")
