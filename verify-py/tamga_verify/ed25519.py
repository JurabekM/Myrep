"""Ed25519 imzo tekshiruvi (RFC 8032 §5.1.7), qat'iy rejim — spec §7.2.

Qat'iylik (ed25519-dalek `verify_strict` bilan bir xil natija berish uchun):
- S < L (kanonik skalyar);
- A va R kanonik kodlangan (y < p) va kichik tartibli emas ([8]P ≠ O);
- cofactor'siz tenglama: encode([S]B − [h]A) == R baytlari.

Faqat tekshirish uchun — yashirin vaqt talab qilinmaydi (maxfiy ma'lumot yo'q).
"""

import hashlib

P = 2**255 - 19
L = 2**252 + 27742317777372353535851937790883648493
D = (-121665 * pow(121666, P - 2, P)) % P
SQRT_M1 = pow(2, (P - 1) // 4, P)
_IDENT = (0, 1, 1, 0)


def _inv(x: int) -> int:
    return pow(x, P - 2, P)


def _add(p, q):
    x1, y1, z1, t1 = p
    x2, y2, z2, t2 = q
    a = (y1 - x1) * (y2 - x2) % P
    b = (y1 + x1) * (y2 + x2) % P
    c = t1 * 2 * D * t2 % P
    d = z1 * 2 * z2 % P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % P, g * h % P, f * g % P, e * h % P)


def _mul(s: int, p):
    q = _IDENT
    while s > 0:
        if s & 1:
            q = _add(q, p)
        p = _add(p, p)
        s >>= 1
    return q


def _neg(p):
    x, y, z, t = p
    return ((-x) % P, y, z, (-t) % P)


def _is_identity(p) -> bool:
    x, y, z, _ = p
    return x % P == 0 and (y - z) % P == 0


def _recover_x(y: int, sign: int):
    if y >= P:
        return None
    x2 = (y * y - 1) * _inv(D * y * y + 1) % P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P != 0:
        x = x * SQRT_M1 % P
    if (x * x - x2) % P != 0:
        return None
    if (x & 1) != sign:
        x = P - x
    return x


def _decompress(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % P)


def _compress(p) -> bytes:
    x, y, z, _ = p
    zi = _inv(z)
    x, y = x * zi % P, y * zi % P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


_GY = 4 * _inv(5) % P
G = (_recover_x(_GY, 0), _GY, 1, _recover_x(_GY, 0) * _GY % P)


def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    if len(public_key) != 32 or len(signature) != 64:
        return False
    a = _decompress(public_key)
    r_bytes = signature[:32]
    r = _decompress(r_bytes)
    if a is None or r is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= L:
        return False
    if _is_identity(_mul(8, a)) or _is_identity(_mul(8, r)):
        return False
    h = int.from_bytes(hashlib.sha512(r_bytes + public_key + message).digest(), "little") % L
    check = _add(_mul(s, G), _mul(h, _neg(a)))
    return _compress(check) == r_bytes
