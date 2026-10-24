"""§2 — kriptografik ibtidolar.

Faqat kutubxona ibtidolari ishlatiladi. Istisno: AQ-KMAC256 (§2.2) —
`hashlib.shake_256` ustiga yig'ilgan, standart KMAC EMAS.
"""

from __future__ import annotations

import hashlib
import hmac

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.asymmetric import mldsa
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

# --- §2.1 SHA3-256 -----------------------------------------------------------


def sha3(b: bytes) -> bytes:
    return hashlib.sha3_256(b).digest()


# --- §2.2 AQ-KMAC256 ⚠ ----------------------------------------------------

RATE = 136  # SHAKE256 rate


def _left_encode(x: int) -> bytes:
    s = x.to_bytes(max(1, (x.bit_length() + 7) // 8), "big")
    return bytes([len(s)]) + s


def _right_encode(x: int) -> bytes:
    s = x.to_bytes(max(1, (x.bit_length() + 7) // 8), "big")
    return s + bytes([len(s)])


def _encode_string(s: bytes) -> bytes:
    return _left_encode(len(s) * 8) + s


def _bytepad(x: bytes, w: int = RATE) -> bytes:
    z = _left_encode(w) + x
    return z + bytes((-len(z)) % w)


def aq_cshake256(x: bytes, n: int, name: bytes, custom: bytes) -> bytes:
    if not name and not custom:
        return hashlib.shake_256(x).digest(n)
    prefiks = _bytepad(_encode_string(name) + _encode_string(custom))
    # Ataylab oddiy SHAKE256 (padding 0x1F), cSHAKE (0x04) emas — §2.2.
    return hashlib.shake_256(prefiks + x).digest(n)


def aq_kmac256(key: bytes, data: bytes, custom: bytes, n: int = 32) -> bytes:
    """AQ-KMAC256: parametrlar tartibi (kalit, ma'lumot, domen yorlig'i, uzunlik)."""
    x = _bytepad(_encode_string(key)) + data + _right_encode(n * 8)
    return aq_cshake256(x, n, b"KMAC", custom)


# --- §2.3 HKDF-Expand (SHA3-256) -------------------------------------------


def hkdf_expand(prk: bytes, info: bytes, n: int) -> bytes:
    if not 0 < n <= 255 * 32:
        raise ValueError("HKDF uzunligi 1..8160")
    out, t, c = b"", b"", 1
    while len(out) < n:
        t = hmac.new(prk, t + info + bytes([c]), hashlib.sha3_256).digest()
        out += t
        c += 1
    return out[:n]


# --- §2.4 ChaCha20-Poly1305 ------------------------------------------------


def aead_seal(kalit: bytes, nonce: bytes, ochiq: bytes, aad: bytes) -> bytes:
    return ChaCha20Poly1305(kalit).encrypt(nonce, ochiq, aad)


def aead_open(kalit: bytes, nonce: bytes, muhr: bytes, aad: bytes) -> bytes | None:
    """Teg mos kelmasa `None` — sabab aytilmaydi (§4.4)."""
    try:
        return ChaCha20Poly1305(kalit).decrypt(nonce, muhr, aad)
    except (InvalidTag, ValueError):
        return None


# --- §2.5 ML-DSA-65 --------------------------------------------------------

MaxfiyKalit = mldsa.MLDSA65PrivateKey


def kalit_urugdan(urug: bytes) -> mldsa.MLDSA65PrivateKey:
    if len(urug) != 32:
        raise ValueError("ML-DSA urug'i 32 bayt bo'lishi kerak")
    return mldsa.MLDSA65PrivateKey.from_seed_bytes(urug)


def ochiq_kalit(sk: mldsa.MLDSA65PrivateKey) -> bytes:
    return sk.public_key().public_bytes_raw()


def imzola(sk: mldsa.MLDSA65PrivateKey, xabar: bytes) -> bytes:
    return sk.sign(xabar)


def imzo_togri(ochiq: bytes, imzo: bytes, xabar: bytes) -> bool:
    """Fail-closed: har qanday xato — `False`, istisno tashlamaydi."""
    try:
        mldsa.MLDSA65PublicKey.from_public_bytes(bytes(ochiq)).verify(bytes(imzo), bytes(xabar))
        return True
    except Exception:  # noqa: BLE001 — ataylab: har qanday xato = yaroqsiz
        return False


# --- §2.6 kanonik kodlash: IKKI xil qoida ----------------------------------


def lp(buf: bytearray, d: bytes) -> None:
    """(a) kichik-endian u64 uzunlik prefiksi — sarlavha va partiya imzo xabari."""
    buf += len(d).to_bytes(8, "little") + d


def u64le(n: int) -> bytes:
    return n.to_bytes(8, "little")


def u128le(n: int) -> bytes:
    return n.to_bytes(16, "little")


def u64be(n: int) -> bytes:
    return n.to_bytes(8, "big")


def tagged_hash(label: bytes, *parts: bytes) -> bytes:
    """(b) katta-endian u32 prefiks — sertifikat, cheklov, mint_auth."""
    b = bytearray()
    for p in (label, *parts):
        b += len(p).to_bytes(4, "big") + p
    return sha3(bytes(b))


# --- §2.7 kalit izi ---------------------------------------------------------


def iz(ochiq: bytes) -> str:
    h = sha3(ochiq).hex().upper()[:24]
    return "-".join(h[i:i + 4] for i in range(0, 24, 4))
