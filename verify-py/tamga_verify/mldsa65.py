"""ML-DSA-65 imzo tekshiruvi (FIPS 204, Algorithm 3 va 8) — sof Python, faqat `hashlib` SHAKE.

Faqat tekshirish (ochiq ma'lumot), shuning uchun yashirin vaqt talab qilinmaydi.
"""

import hashlib

Q = 8380417
N = 256
D = 13
TAU = 49
LAMBDA = 192
GAMMA1 = 1 << 19
GAMMA2 = (Q - 1) // 32
K, L = 6, 5
ETA = 4
BETA = TAU * ETA
OMEGA = 55

PK_LEN = 32 + K * 320
SIG_LEN = LAMBDA // 4 + L * 640 + OMEGA + K
_ZETA = 1753


def _brv8(x: int) -> int:
    return int(f"{x:08b}"[::-1], 2)


ZETAS = [pow(_ZETA, _brv8(k), Q) for k in range(256)]
N_INV = pow(256, Q - 2, Q)


def _h(data: bytes, n: int) -> bytes:
    return hashlib.shake_256(data).digest(n)


def ntt(a: list[int]) -> list[int]:
    w = [x % Q for x in a]
    m, length = 0, 128
    while length >= 1:
        start = 0
        while start < 256:
            m += 1
            z = ZETAS[m]
            for j in range(start, start + length):
                t = z * w[j + length] % Q
                w[j + length] = (w[j] - t) % Q
                w[j] = (w[j] + t) % Q
            start += 2 * length
        length //= 2
    return w


def intt(w: list[int]) -> list[int]:
    a = list(w)
    m, length = 256, 1
    while length < 256:
        start = 0
        while start < 256:
            m -= 1
            z = -ZETAS[m] % Q
            for j in range(start, start + length):
                t = a[j]
                a[j] = (t + a[j + length]) % Q
                a[j + length] = z * (t - a[j + length]) % Q
            start += 2 * length
        length *= 2
    return [x * N_INV % Q for x in a]


def _unpack(data: bytes, bits: int) -> list[int]:
    v = int.from_bytes(data, "little")
    mask = (1 << bits) - 1
    return [(v >> (i * bits)) & mask for i in range(N)]


def _pack(coeffs: list[int], bits: int) -> bytes:
    v = 0
    for i, c in enumerate(coeffs):
        v |= c << (i * bits)
    return v.to_bytes(N * bits // 8, "little")


def _rej_ntt_poly(seed: bytes) -> list[int]:
    # SHAKE128 oqimidan 3 baytli nomzodlar (FIPS 204 Algorithm 30/14).
    stream = hashlib.shake_128(seed).digest(3 * 1024)
    out, pos = [], 0
    while len(out) < N:
        if pos + 3 > len(stream):
            stream = hashlib.shake_128(seed).digest(len(stream) * 2)
        b0, b1, b2 = stream[pos], stream[pos + 1], stream[pos + 2] & 0x7F
        pos += 3
        z = (b2 << 16) | (b1 << 8) | b0
        if z < Q:
            out.append(z)
    return out


def _expand_a(rho: bytes) -> list[list[list[int]]]:
    return [[_rej_ntt_poly(rho + bytes([s, r])) for s in range(L)] for r in range(K)]


def _sample_in_ball(seed: bytes) -> list[int]:
    stream = hashlib.shake_256(seed).digest(8 + 1024)
    signs = int.from_bytes(stream[:8], "little")
    c = [0] * N
    pos = 8
    for i in range(N - TAU, N):
        while True:
            j = stream[pos]
            pos += 1
            if j <= i:
                break
        c[i] = c[j]
        c[j] = -1 if (signs >> (i + TAU - N)) & 1 else 1
    return c


def _hint_unpack(y: bytes):
    h = [[0] * N for _ in range(K)]
    index = 0
    for i in range(K):
        limit = y[OMEGA + i]
        if limit < index or limit > OMEGA:
            return None
        first = index
        while index < limit:
            if index > first and y[index - 1] >= y[index]:
                return None
            h[i][y[index]] = 1
            index += 1
    if any(y[i] != 0 for i in range(index, OMEGA)):
        return None
    return h


def _decompose(r: int) -> tuple[int, int]:
    rp = r % Q
    r0 = rp % (2 * GAMMA2)
    if r0 > GAMMA2:
        r0 -= 2 * GAMMA2
    if rp - r0 == Q - 1:
        return 0, r0 - 1
    return (rp - r0) // (2 * GAMMA2), r0


def _use_hint(h: int, r: int) -> int:
    m = (Q - 1) // (2 * GAMMA2)
    r1, r0 = _decompose(r)
    if h == 1:
        return (r1 + 1) % m if r0 > 0 else (r1 - 1) % m
    return r1


def verify(public_key: bytes, message: bytes, signature: bytes, ctx: bytes = b"") -> bool:
    if len(public_key) != PK_LEN or len(signature) != SIG_LEN or len(ctx) > 255:
        return False
    # Algorithm 3: M' = 0 || |ctx| || ctx || M
    m_prime = bytes([0, len(ctx)]) + ctx + message

    rho = public_key[:32]
    t1 = [_unpack(public_key[32 + 320 * i : 32 + 320 * (i + 1)], 10) for i in range(K)]
    c_tilde = signature[: LAMBDA // 4]
    off = LAMBDA // 4
    z = []
    for i in range(L):
        raw = _unpack(signature[off + 640 * i : off + 640 * (i + 1)], 20)
        z.append([GAMMA1 - x for x in raw])
    h = _hint_unpack(signature[off + 640 * L :])
    if h is None:
        return False
    if any(abs(c) >= GAMMA1 - BETA for poly in z for c in poly):
        return False

    a_hat = _expand_a(rho)
    tr = _h(public_key, 64)
    mu = _h(tr + m_prime, 64)
    c_hat = ntt(_sample_in_ball(c_tilde))
    z_hat = [ntt(p) for p in z]
    w1 = []
    for i in range(K):
        acc = [0] * N
        for j in range(L):
            a, zz = a_hat[i][j], z_hat[j]
            for n in range(N):
                acc[n] += a[n] * zz[n]
        t1_hat = ntt([c << D for c in t1[i]])
        w = intt([(acc[n] - c_hat[n] * t1_hat[n]) % Q for n in range(N)])
        w1.append([_use_hint(h[i][n], w[n]) for n in range(N)])
    w1_enc = b"".join(_pack(p, 4) for p in w1)
    return _h(mu + w1_enc, LAMBDA // 4) == c_tilde
