"""SCUTUM-Q1 kriptografik primitivlari.

Barcha algoritmlar tekshirilgan kutubxonalardan olinadi (spec §2: "o'z qo'li bilan
yozishi MUST NOT"):
  * X25519, Ed25519, ChaCha20-Poly1305, HKDF-SHA-512, SHA-3-256  -> `cryptography`
  * ML-KEM-768, ML-DSA-65                                        -> `cryptography` (OpenSSL)
  * Argon2id                                                     -> `argon2-cffi`
"""
from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from typing import Tuple

from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.asymmetric.mldsa import (
    MLDSA65PrivateKey,
    MLDSA65PublicKey,
)
from cryptography.hazmat.primitives.asymmetric.mlkem import (
    MLKEM768PrivateKey,
    MLKEM768PublicKey,
)
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.exceptions import InvalidSignature, InvalidTag

# ---------------------------------------------------------------------------
# O'lchamlar (FIPS 203 / 204)
# ---------------------------------------------------------------------------
MLKEM768_PK = 1184
MLKEM768_CT = 1088
MLKEM768_SS = 32
MLDSA65_PK = 1952
MLDSA65_SIG = 3309
ED25519_PK = 32
ED25519_SIG = 64
X25519_PK = 32


class CryptoError(Exception):
    """Kriptografik amal muvaffaqiyatsiz tugadi."""


# ---------------------------------------------------------------------------
# Tasodifiylik  (spec kamchiligi: CSPRNG talabi hujjatda umuman yo'q)
# ---------------------------------------------------------------------------
def random_bytes(n: int) -> bytes:
    """Kriptografik xavfsiz tasodifiy baytlar (OS CSPRNG)."""
    return os.urandom(n)


# ---------------------------------------------------------------------------
# Xesh va MAC
# ---------------------------------------------------------------------------
def sha3_256(*parts: bytes) -> bytes:
    h = hashes.Hash(hashes.SHA3_256())
    for p in parts:
        h.update(p)
    return h.finalize()


def sha512(*parts: bytes) -> bytes:
    h = hashes.Hash(hashes.SHA512())
    for p in parts:
        h.update(p)
    return h.finalize()


def hmac_sha512(key: bytes, data: bytes) -> bytes:
    m = hmac.HMAC(key, hashes.SHA512())
    m.update(data)
    return m.finalize()


def hmac_sha256(key: bytes, data: bytes) -> bytes:
    m = hmac.HMAC(key, hashes.SHA256())
    m.update(data)
    return m.finalize()


def uint64be(n: int) -> bytes:
    return struct.pack(">Q", n)


# ---------------------------------------------------------------------------
# KDF
# ---------------------------------------------------------------------------
def hkdf_sha512(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    """HKDF-SHA-512 (extract + expand)."""
    return HKDF(
        algorithm=hashes.SHA512(), length=length, salt=salt, info=info
    ).derive(ikm)


def argon2id(
    password: bytes,
    salt: bytes,
    *,
    memory_kib: int = 65536,
    time_cost: int = 3,
    parallelism: int = 1,
    length: int = 32,
) -> bytes:
    """Argon2id KDF.

    Spec §3.2 faqat "platformaga mos profil" deydi — minimal pol bermaydi.
    Bu yerda OWASP tavsiyasidan yuqori standart pol qo'yilgan: m=64 MiB, t=3, p=1.
    """
    from argon2.low_level import Type, hash_secret_raw

    return hash_secret_raw(
        secret=password,
        salt=salt,
        time_cost=time_cost,
        memory_cost=memory_kib,
        parallelism=parallelism,
        hash_len=length,
        type=Type.ID,
    )


# ---------------------------------------------------------------------------
# AEAD
# ---------------------------------------------------------------------------
def aead_seal(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> bytes:
    if len(key) != 32:
        raise CryptoError(f"ChaCha20-Poly1305 kaliti 32 bayt bo'lishi kerak, {len(key)} berildi")
    if len(nonce) != 12:
        raise CryptoError(f"nonce 12 bayt bo'lishi kerak, {len(nonce)} berildi")
    return ChaCha20Poly1305(key).encrypt(nonce, plaintext, aad)


def aead_open(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes) -> bytes:
    try:
        return ChaCha20Poly1305(key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise CryptoError("AEAD tegi noto'g'ri (o'zgartirilgan yoki kalit mos emas)") from exc


def key_commitment(key: bytes) -> bytes:
    """Kalit-majburiyat tegi (Y-2 tuzatishi).

    ChaCha20-Poly1305 key-committing emas; bu teg bir ciphertext'ning bir nechta
    kalit ostida "haqiqiy" ko'rinishini (partitioning oracle / invisible
    salamander) to'sadi.
    """
    return hmac_sha256(key, b"SCUTUM-Q1/commit")


# ---------------------------------------------------------------------------
# X25519
# ---------------------------------------------------------------------------
def x25519_generate() -> X25519PrivateKey:
    return X25519PrivateKey.generate()


def x25519_pub(sk: X25519PrivateKey) -> bytes:
    return sk.public_key().public_bytes_raw()


def x25519_dh(sk: X25519PrivateKey, peer_pk: bytes) -> bytes:
    return sk.exchange(X25519PublicKey.from_public_bytes(peer_pk))


def x25519_from_raw(raw: bytes) -> X25519PrivateKey:
    return X25519PrivateKey.from_private_bytes(raw)


def x25519_raw(sk: X25519PrivateKey) -> bytes:
    return sk.private_bytes_raw()


# ---------------------------------------------------------------------------
# Ed25519
# ---------------------------------------------------------------------------
def ed25519_generate() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def ed25519_pub(sk: Ed25519PrivateKey) -> bytes:
    return sk.public_key().public_bytes_raw()


def ed25519_sign(sk: Ed25519PrivateKey, msg: bytes) -> bytes:
    return sk.sign(msg)


def ed25519_from_raw(raw: bytes) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(raw)


def ed25519_verify(pk: bytes, sig: bytes, msg: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(pk).verify(sig, msg)
        return True
    except (InvalidSignature, ValueError):
        return False


# ---------------------------------------------------------------------------
# ML-DSA-65  (FIPS 204)
# ---------------------------------------------------------------------------
def mldsa_generate() -> MLDSA65PrivateKey:
    return MLDSA65PrivateKey.generate()


def mldsa_pub(sk: MLDSA65PrivateKey) -> bytes:
    return sk.public_key().public_bytes_raw()


def mldsa_sign(sk: MLDSA65PrivateKey, msg: bytes) -> bytes:
    return sk.sign(msg)


def mldsa_from_seed(seed: bytes) -> MLDSA65PrivateKey:
    """FIPS 204 §xi: 32-baytli urug'dan deterministik kalit."""
    return MLDSA65PrivateKey.from_seed_bytes(seed)


def mldsa_verify(pk: bytes, sig: bytes, msg: bytes) -> bool:
    try:
        MLDSA65PublicKey.from_public_bytes(pk).verify(sig, msg)
        return True
    except (InvalidSignature, ValueError):
        return False


# ---------------------------------------------------------------------------
# ML-KEM-768  (FIPS 203)
# ---------------------------------------------------------------------------
def mlkem_generate() -> MLKEM768PrivateKey:
    return MLKEM768PrivateKey.from_seed_bytes(random_bytes(64))


def mlkem_from_seed(seed: bytes) -> MLKEM768PrivateKey:
    """FIPS 203: 64-baytli urug' (d‖z) dan deterministik kalit."""
    return MLKEM768PrivateKey.from_seed_bytes(seed)


def mlkem_pub(sk: MLKEM768PrivateKey) -> bytes:
    return sk.public_key().public_bytes_raw()


def mlkem_encaps(pk_raw: bytes) -> Tuple[bytes, bytes]:
    """-> (shared_secret, ciphertext)"""
    ss, ct = MLKEM768PublicKey.from_public_bytes(pk_raw).encapsulate()
    return ss, ct


def mlkem_decaps(sk: MLKEM768PrivateKey, ct: bytes) -> bytes:
    try:
        return sk.decapsulate(ct)
    except ValueError as exc:
        raise CryptoError("ML-KEM decapsulation muvaffaqiyatsiz") from exc


# ---------------------------------------------------------------------------
# Gibrid imzo (spec §5.3)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class HybridSignature:
    ed25519: bytes
    mldsa65: bytes

    def to_bytes(self) -> bytes:
        """Spec: Ed25519.Sign(M) || ML-DSA-65.Sign(M) — xom konkatenatsiya.

        Uzunliklar qat'iy (64 + 3309) bo'lgani uchun parsing noaniq emas, ammo
        uzunlik-prefiks bo'lmagani spec'ning umumiy kanonizatsiya bo'shlig'i.
        """
        return self.ed25519 + self.mldsa65

    @staticmethod
    def from_bytes(raw: bytes) -> "HybridSignature":
        if len(raw) != ED25519_SIG + MLDSA65_SIG:
            raise CryptoError(
                f"gibrid imzo uzunligi noto'g'ri: {len(raw)} "
                f"(kutilgan {ED25519_SIG + MLDSA65_SIG})"
            )
        return HybridSignature(raw[:ED25519_SIG], raw[ED25519_SIG:])


def hybrid_sign(
    ed_sk: Ed25519PrivateKey, mldsa_sk: MLDSA65PrivateKey, msg: bytes
) -> HybridSignature:
    return HybridSignature(ed25519_sign(ed_sk, msg), mldsa_sign(mldsa_sk, msg))


def hybrid_verify(
    ed_pk: bytes, mldsa_pk: bytes, sig: HybridSignature, msg: bytes
) -> bool:
    """Spec §5.3: HAR IKKI imzo haqiqiy bo'lgandagina muvaffaqiyatli.

    "bittasi o'tsa bo'ldi" siyosati MUST NOT — shuning uchun `and`, va ikkala
    tekshiruv ham har doim bajariladi (short-circuit yo'q -> vaqt oqishi kamroq).
    """
    ok_ed = ed25519_verify(ed_pk, sig.ed25519, msg)
    ok_pq = mldsa_verify(mldsa_pk, sig.mldsa65, msg)
    return ok_ed and ok_pq
