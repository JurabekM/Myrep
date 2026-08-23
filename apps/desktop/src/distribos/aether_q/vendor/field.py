"""
AETHER-Q v5.1 — Maydon va Shamir t-of-n secret sharing.

Threshold KEM (0x07) uchun. Funksiyalar modulus-parametrik: sekret guruh
TARTIBI (order) Q bo'yicha bo'linishi kerak (threshold ElGamal), maydon primi
bo'yicha emas — aks holda eksponentdagi Lagrange interpolatsiyasi buziladi.
Bu HAQIQIY Shamir/Lagrange — mock emas: t-of-n tiklash matematik jihatdan to'g'ri.
"""

import secrets

# secp256k1 field prime (default; threshold Q ni beradi)
P = 2**256 - 2**32 - 977


def _inv(a: int, mod: int) -> int:
    return pow(a % mod, mod - 2, mod)


def rand_scalar(mod: int = P) -> int:
    return secrets.randbelow(mod - 1) + 1


def shamir_split(secret: int, t: int, n: int, mod: int = P, rng=None):
    """
    secret ni GF(mod) da t-of-n bo'ladi. Daraja (t-1) polinom f, f(0)=secret.
    Ulushlar: [(i, f(i)) for i in 1..n]. Istalgan t tasi yetarli.
    rng: test uchun determinist koeffitsientlar (list[int]).
    """
    if rng is None:
        coeffs = [secret % mod] + [rand_scalar(mod) for _ in range(t - 1)]
    else:
        coeffs = [secret % mod] + [c % mod for c in rng[: t - 1]]
    shares = []
    for i in range(1, n + 1):
        y = 0
        for power, c in enumerate(coeffs):
            y = (y + c * pow(i, power, mod)) % mod
        shares.append((i, y))
    return shares


def lagrange_at_zero(points, mod: int = P):
    """{(x_i, y_i)} dan f(0) ni Lagrange bilan tiklaydi (kamida t nuqta)."""
    secret = 0
    xs = [x for x, _ in points]
    for xi, yi in points:
        num, den = 1, 1
        for xj in xs:
            if xj == xi:
                continue
            num = (num * (-xj)) % mod
            den = (den * (xi - xj)) % mod
        secret = (secret + yi * num * _inv(den, mod)) % mod
    return secret % mod


def lagrange_coeff_at_zero(xi: int, xs, mod: int = P) -> int:
    """x=0 dagi Lagrange koeffitsienti λ_i (mod bo'yicha)."""
    num, den = 1, 1
    for xj in xs:
        if xj == xi:
            continue
        num = (num * (-xj)) % mod
        den = (den * (xi - xj)) % mod
    return (num * _inv(den, mod)) % mod


def to_bytes32(x: int, mod: int = P) -> bytes:
    return (x % mod).to_bytes(32, "big")


def from_bytes32(b: bytes, mod: int = P) -> int:
    return int.from_bytes(b, "big") % mod
