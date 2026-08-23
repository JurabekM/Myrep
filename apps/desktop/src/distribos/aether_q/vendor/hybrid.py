"""
AETHER-Q v5.1 — Hybrid KEM combiner'lari (Profile 0x01 / 0x03).

MVP uchun asosiy profillar:
  0x01 DEFAULT  — X25519 + ML-KEM-768 (hybrid: klassik + post-kvant)
  0x03 MINIMAL  — ML-KEM-768 standalone (faqat post-kvant)

NEGA HYBRID: real dunyoda migratsiya davrida "hybrid" talab qilinadi — agar
post-kvant sxemada kutilmagan zaiflik topilsa, klassik X25519 himoyani ushlab
turadi (va aksincha). Bu NIST/IETF tavsiyasi.

COMBINER (spec §4 N2/N3/N4 ga mos):
    Transcript = H(profile_id ‖ LABEL ‖ ct_M ‖ ct_X ‖ pk_X)
    PRK        = HKDF-Extract(salt = Transcript, ikm = ss_M ‖ ss_X ‖ LABEL)
    SS         = HKDF-Expand(PRK, "0xNN/ss" ‖ profile_id, 32)

⚠ X-Wing (RFC draft) standarti aynan `SHA3-256(ss_M ‖ ss_X ‖ ct_X ‖ pk_X ‖ label)`
  konkatenatsiyasini ishlatadi. Biz AETHER-Q ning majburiy HKDF + profile_id
  binding qoidasiga (S5 downgrade himoyasi) rioya qilamiz → X-Wing bilan
  bayt-darajasida interop YO'Q, lekin xavfsizlik xususiyatlari kuchliroq.

⚠ 0x02 PARANOID (X25519+ML-KEM+HQC) HQC-192 mavjud emasligi sababli hali
  IMPLEMENTATSIYA QILINMAGAN (liboqs kerak; HQC hali FIPS emas). `SUPPORTED`
  ro'yxatiga kiritilmagan.
"""

from typing import Tuple

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey, X25519PublicKey,
)

from .kem import MLKEM768, PK_LEN as MK_PK, CT_LEN as MK_CT
from .kdf import sha3_256, hkdf_extract, hkdf_expand

PROFILE_DEFAULT = 0x01          # X25519 + ML-KEM-768
PROFILE_MINIMAL = 0x03          # ML-KEM-768 standalone

DEFAULT_LABEL = b"AETHER-Q-v5.1-XWING/L3/v1"
MINIMAL_LABEL = b"AETHER-Q-v5.1-MINIMAL/L3/v1"

X_PK_LEN = 32                   # X25519 public key / ciphertext (ephemeral pk)

#: Ushbu implementatsiyada haqiqatan qo'llab-quvvatlanadigan KEM profillari.
#: (0x02 PARANOID — HQC yo'q; 0x06/0x07/0x08 — alohida modullarda.)
SUPPORTED = (PROFILE_DEFAULT, PROFILE_MINIMAL)


def _dk_obj(priv_bundle: dict):
    """
    ML-KEM privat kalit obyektini LAZY keshlaydi. `dk_m` (seed bytes) serializatsiya
    uchun saqlanadi, lekin har decaps'da undan obyekt qurish ~0.2 ms — bu kesh uni
    bir martaga tushiradi (bundle qayta ishlatilganda).
    """
    obj = priv_bundle.get("_dk_obj")
    if obj is None:
        obj = MLKEM768.load_sk(priv_bundle["dk_m"])
        priv_bundle["_dk_obj"] = obj
    return obj


def _combine(profile_id: int, label: bytes, ss_M: bytes,
             ct_M: bytes, ss_X: bytes = b"", ct_X: bytes = b"",
             pk_X: bytes = b"") -> bytes:
    transcript = sha3_256(bytes([profile_id]) + label + ct_M + ct_X + pk_X)
    prk = hkdf_extract(transcript, ss_M + ss_X + label)
    return hkdf_expand(prk, bytes([profile_id]) + b"/ss", 32)


class HybridKEM:
    """Profile 0x01 — X25519 + ML-KEM-768 hybrid KEM."""

    profile_id = PROFILE_DEFAULT
    label = DEFAULT_LABEL
    pk_len = MK_PK + X_PK_LEN       # 1184 + 32 = 1216
    ct_len = MK_CT + X_PK_LEN       # 1088 + 32 = 1120

    @staticmethod
    def keygen() -> Tuple[bytes, dict]:
        """Qaytaradi: (public_bundle_bytes, private_bundle)."""
        ek_m, dk_m = MLKEM768.keygen()
        x_priv = X25519PrivateKey.generate()
        pk_x = x_priv.public_key().public_bytes_raw()
        return ek_m + pk_x, {"dk_m": dk_m, "x_priv": x_priv, "pk_x": pk_x}

    @staticmethod
    def encaps(pk_bundle: bytes) -> Tuple[bytes, bytes]:
        """Qaytaradi: (ct_bundle_bytes, shared_secret)."""
        if len(pk_bundle) != HybridKEM.pk_len:
            raise ValueError("0x01: public bundle uzunligi noto'g'ri")
        ek_m, pk_x = pk_bundle[:MK_PK], pk_bundle[MK_PK:]
        ct_m, ss_m = MLKEM768.encaps(ek_m)
        eph = X25519PrivateKey.generate()
        ct_x = eph.public_key().public_bytes_raw()          # X25519 "ciphertext" = ephemeral pk
        ss_x = eph.exchange(X25519PublicKey.from_public_bytes(pk_x))
        ss = _combine(HybridKEM.profile_id, HybridKEM.label, ss_m, ct_m, ss_x, ct_x, pk_x)
        return ct_m + ct_x, ss

    @staticmethod
    def decaps(priv_bundle: dict, ct_bundle: bytes) -> bytes:
        if len(ct_bundle) != HybridKEM.ct_len:
            raise ValueError("0x01: ciphertext bundle uzunligi noto'g'ri")
        ct_m, ct_x = ct_bundle[:MK_CT], ct_bundle[MK_CT:]
        ss_m = MLKEM768.decaps(_dk_obj(priv_bundle), ct_m)  # implicit rejection ichida
        ss_x = priv_bundle["x_priv"].exchange(X25519PublicKey.from_public_bytes(ct_x))
        return _combine(HybridKEM.profile_id, HybridKEM.label, ss_m, ct_m,
                        ss_x, ct_x, priv_bundle["pk_x"])


class MinimalKEM:
    """Profile 0x03 — ML-KEM-768 standalone (faqat post-kvant)."""

    profile_id = PROFILE_MINIMAL
    label = MINIMAL_LABEL
    pk_len = MK_PK
    ct_len = MK_CT

    @staticmethod
    def keygen() -> Tuple[bytes, dict]:
        ek_m, dk_m = MLKEM768.keygen()
        return ek_m, {"dk_m": dk_m}

    @staticmethod
    def encaps(pk_bundle: bytes) -> Tuple[bytes, bytes]:
        if len(pk_bundle) != MinimalKEM.pk_len:
            raise ValueError("0x03: public key uzunligi noto'g'ri")
        ct_m, ss_m = MLKEM768.encaps(pk_bundle)
        return ct_m, _combine(MinimalKEM.profile_id, MinimalKEM.label, ss_m, ct_m)

    @staticmethod
    def decaps(priv_bundle: dict, ct_bundle: bytes) -> bytes:
        if len(ct_bundle) != MinimalKEM.ct_len:
            raise ValueError("0x03: ciphertext uzunligi noto'g'ri")
        ss_m = MLKEM768.decaps(_dk_obj(priv_bundle), ct_bundle)
        return _combine(MinimalKEM.profile_id, MinimalKEM.label, ss_m, ct_bundle)


#: profile_id → KEM implementatsiyasi (handshake shu jadvaldan foydalanadi)
KEM_BY_PROFILE = {
    PROFILE_DEFAULT: HybridKEM,
    PROFILE_MINIMAL: MinimalKEM,
}


def kem_for(profile_id: int):
    """Profil bo'yicha KEM olish; qo'llab-quvvatlanmasa ValueError."""
    try:
        return KEM_BY_PROFILE[profile_id]
    except KeyError:
        raise ValueError(f"0x{profile_id:02x} profili uchun KEM implementatsiyasi yo'q")
