"""
AETHER-Q v5.1 — KDF yadrosi (HKDF-SHA3-256, KMAC256, cSHAKE256).

v5.0 dagi yalang'och `SHA3(a||b||c)` combiner'lari o'rniga (v5.1 §4, N2)
standart kalit ajratish primitivlari. Faqat stdlib `hashlib` + `hmac`.
"""

import hashlib
import hmac


# --- Asosiy hash / XOF ---------------------------------------------------

def sha3_256(data: bytes) -> bytes:
    return hashlib.sha3_256(data).digest()


def shake_256(data: bytes, length: int) -> bytes:
    return hashlib.shake_256(data).digest(length)


# --- HKDF (RFC 5869, SHA3-256 bilan) ------------------------------------

def hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    """PRK = HMAC-SHA3-256(salt, ikm). Bo'sh salt → 32 bayt nol."""
    if not salt:
        salt = b"\x00" * 32
    return hmac.new(salt, ikm, hashlib.sha3_256).digest()


def hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    """RFC 5869 Expand, SHA3-256 bilan."""
    if length > 255 * 32:
        raise ValueError("HKDF-Expand: length juda katta")
    t, okm, counter = b"", b"", 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha3_256).digest()
        okm += t
        counter += 1
    return okm[:length]


# --- SP 800-185 yordamchilar --------------------------------------------

def _left_encode(x: int) -> bytes:
    if x == 0:
        s = b"\x00"
    else:
        s = b""
        v = x
        while v > 0:
            s = bytes([v & 0xFF]) + s
            v >>= 8
    return bytes([len(s)]) + s


def _right_encode(x: int) -> bytes:
    if x == 0:
        s = b"\x00"
    else:
        s = b""
        v = x
        while v > 0:
            s = bytes([v & 0xFF]) + s
            v >>= 8
    return s + bytes([len(s)])


def _encode_string(s: bytes) -> bytes:
    return _left_encode(len(s) * 8) + s


def _bytepad(x: bytes, w: int) -> bytes:
    out = _left_encode(w) + x
    if len(out) % w != 0:
        out += b"\x00" * (w - (len(out) % w))
    return out


def cshake_256(x: bytes, length: int, name: bytes = b"", custom: bytes = b"") -> bytes:
    """cSHAKE256 (SP 800-185). name/custom bo'sh bo'lsa → oddiy SHAKE256."""
    if not name and not custom:
        return shake_256(x, length)
    prefix = _bytepad(_encode_string(name) + _encode_string(custom), 136)
    return hashlib.shake_256(prefix + x).digest(length)


def kmac256(key: bytes, data: bytes, length: int, custom: bytes = b"") -> bytes:
    """KMAC256 (SP 800-185). Keyed MAC / domain-separated XOF."""
    newx = _bytepad(_encode_string(key), 136) + data + _right_encode(length * 8)
    return cshake_256(newx, length, name=b"KMAC", custom=custom)


# --- Constant-time yordamchilar -----------------------------------------

def ct_eq(a: bytes, b: bytes) -> bool:
    """Constant-time tenglik (hmac.compare_digest ustidan)."""
    return hmac.compare_digest(a, b)


def ct_select(cond: bool, a: bytes, b: bytes) -> bytes:
    """
    Constant-time tanlash: cond→a, else→b. a va b bir xil uzunlikda bo'lishi shart.
    Reference: haqiqiy HW-CT emas (Python), lekin tarmoq bo'yicha kuzatiladigan
    tarmoqli oqim bir xil bo'ladi (branchsiz baytlararo maskalash).
    """
    assert len(a) == len(b), "ct_select: uzunliklar teng bo'lishi kerak"
    mask = 0xFF if cond else 0x00
    return bytes((x & mask) | (y & (~mask & 0xFF)) for x, y in zip(a, b))
