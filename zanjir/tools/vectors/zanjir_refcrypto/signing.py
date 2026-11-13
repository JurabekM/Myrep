"""Qurilma imzosi.

`sig_alg` har bir yozuvda saqlanadi — kelajakda ML-DSA gibrid yoki E-IMZO'ga o'tish sxemani buzmaydi.
"""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

SIG_ALG_ED25519 = "Ed25519"
SUPPORTED_SIG_ALGS = frozenset({SIG_ALG_ED25519})


class UnsupportedSigAlgError(ValueError):
    pass


class Ed25519Signer:
    """Faqat testlar va vektor generatori uchun: serverda maxfiy kalit saqlanmaydi."""

    sig_alg = SIG_ALG_ED25519

    def __init__(self, seed: bytes) -> None:
        if len(seed) != 32:
            raise ValueError("Ed25519 seed 32 bayt bo'lishi kerak")
        self._key = Ed25519PrivateKey.from_private_bytes(seed)

    @property
    def public_key_hex(self) -> str:
        return self._key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    def sign(self, message: bytes) -> bytes:
        return self._key.sign(message)


def verify_signature(*, sig_alg: str, public_key_hex: str, message: bytes, signature_hex: str) -> bool:
    """Imzo to'g'rimi. Noma'lum algoritm — `UnsupportedSigAlgError`; noto'g'ri format — False."""
    if sig_alg not in SUPPORTED_SIG_ALGS:
        raise UnsupportedSigAlgError(sig_alg)
    try:
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        key.verify(bytes.fromhex(signature_hex), message)
    except (ValueError, InvalidSignature):
        return False
    return True
