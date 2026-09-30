"""§5 — Merkle daraxti. Toq tugun NUSXALANMAYDI, o'zgarishsiz ko'tariladi.

Daraxt partiyaga BIR MARTA quriladi (`Daraxt`), barcha isbotlar shundan
olinadi — har kupyuraga qayta qurish O(n²) bo'ladi (§5, tuzoq 8).
"""

from __future__ import annotations

from .ibtido import sha3


def tugun(chap: bytes, ong: bytes) -> bytes:
    return sha3(b"\x01" + chap + ong)


def qavatlar(barglar: list[bytes]) -> list[list[bytes]]:
    if not barglar:
        return [[bytes(32)]]
    q = [list(barglar)]
    while len(q[-1]) > 1:
        j = q[-1]
        k = [tugun(j[i], j[i + 1]) for i in range(0, len(j) - 1, 2)]
        if len(j) % 2:
            k.append(j[-1])
        q.append(k)
    return q


def isbot(q: list[list[bytes]], i: int) -> list[bytes]:
    yol = []
    for qavat in q[:-1]:
        s = i + 1 if i % 2 == 0 else i - 1
        if s < len(qavat):
            yol.append(qavat[s])
        i //= 2
    return yol


def isbot_togri(barg: bytes, yol: list[bytes], i: int, soni: int, ildiz: bytes) -> bool:
    if soni == 0 or not 0 <= i < soni:
        return False
    x, j, n = barg, 0, soni
    while n > 1:
        s = i + 1 if i % 2 == 0 else i - 1
        if s < n:
            if j >= len(yol):
                return False
            x = tugun(x, yol[j]) if i % 2 == 0 else tugun(yol[j], x)
            j += 1
        i //= 2
        n = (n + 1) // 2
    return j == len(yol) and x == ildiz


def isbot_baytlari(yol: list[bytes]) -> bytes:
    return b"".join(yol)


def isbot_ajrat(b: bytes) -> list[bytes] | None:
    """Fayldagi isbot baytlarini ro'yxatga. Uzunlik 32 ga karrali bo'lmasa — None."""
    if len(b) % 32:
        return None
    return [b[i:i + 32] for i in range(0, len(b), 32)]


class Daraxt:
    """Bir marta quriladigan daraxt."""

    def __init__(self, barglar: list[bytes]):
        self.soni = len(barglar)
        self.q = qavatlar(barglar)

    @property
    def ildiz(self) -> bytes:
        return self.q[-1][0]

    def isbot(self, i: int) -> list[bytes]:
        return isbot(self.q, i)


def ildiz(barglar: list[bytes]) -> bytes:
    return qavatlar(barglar)[-1][0]
