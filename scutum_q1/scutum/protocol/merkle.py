"""Merkle daraxti (spec §7.1) — ikki rejimda.

SPEC:
    leaf_i   = SHA3-256(i || chunk_ciphertext_i)
    internal = SHA3-256(L || R)          <- barg va tugun BIR XIL xesh
    toq tugun -> oxirgisi DUBLIKAT qilinadi
  Muammolar (Y-3):
    * barg/tugun domen ajratilmagan -> tugun-turi chalkashligi
    * duplikat-tugun -> turli barglar to'plami bir xil root beradi
      (Bitcoin CVE-2012-2459 uslubi)
    * total_chunks ildizga bog'lanmagan -> truncation

HARDENED (RFC 6962 uslubi):
    leaf     = SHA3-256(0x00 || uint64be(i) || ct_i)
    internal = SHA3-256(0x01 || L || R)
    toq tugun -> yuqoriga KO'CHIRILADI (dublikat qilinmaydi)
    root     = SHA3-256(0x02 || uint64be(total_chunks) || tree_root)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..config import ProtocolConfig
from ..crypto.primitives import sha3_256, uint64be
from .errors import FileIntegrityError


def leaf_hash(index: int, ciphertext: bytes, cfg: ProtocolConfig) -> bytes:
    if cfg.merkle_domain_sep:
        return sha3_256(b"\x00", uint64be(index), ciphertext)
    # SPEC: `i` ning kodlanishi ham ta'riflanmagan; uint64be deb qabul qilamiz
    return sha3_256(uint64be(index), ciphertext)


def node_hash(left: bytes, right: bytes, cfg: ProtocolConfig) -> bytes:
    if cfg.merkle_domain_sep:
        return sha3_256(b"\x01", left, right)
    return sha3_256(left, right)


@dataclass
class MerkleTree:
    levels: list[list[bytes]]
    total: int
    cfg: ProtocolConfig

    @property
    def tree_root(self) -> bytes:
        return self.levels[-1][0]

    @property
    def root(self) -> bytes:
        if self.cfg.merkle_domain_sep:
            return sha3_256(b"\x02", uint64be(self.total), self.tree_root)
        return self.tree_root

    def proof(self, index: int) -> list[tuple[str, bytes]]:
        """-> [('L'|'R', sibling_hash), ...] pastdan yuqoriga."""
        if not 0 <= index < len(self.levels[0]):
            raise FileIntegrityError("indeks daraxt chegarasidan tashqarida")
        path: list[tuple[str, bytes]] = []
        idx = index
        for level in self.levels[:-1]:
            if idx % 2 == 0:
                sib = level[idx + 1] if idx + 1 < len(level) else None
                if sib is None:
                    if self.cfg.merkle_domain_sep:
                        idx //= 2
                        continue          # yuqoriga ko'chirildi — sherik yo'q
                    sib = level[idx]      # SPEC: o'zini dublikat qiladi
                path.append(("R", sib))
            else:
                path.append(("L", level[idx - 1]))
            idx //= 2
        return path


def build_tree(leaves: list[bytes], cfg: ProtocolConfig) -> MerkleTree:
    if not leaves:
        raise FileIntegrityError("bo'sh daraxt")
    levels = [list(leaves)]
    while len(levels[-1]) > 1:
        cur = levels[-1]
        nxt: list[bytes] = []
        i = 0
        while i < len(cur):
            if i + 1 < len(cur):
                nxt.append(node_hash(cur[i], cur[i + 1], cfg))
            else:
                if cfg.merkle_domain_sep:
                    nxt.append(cur[i])                      # ko'chirish
                else:
                    nxt.append(node_hash(cur[i], cur[i], cfg))  # dublikat
            i += 2
        levels.append(nxt)
    return MerkleTree(levels=levels, total=len(leaves), cfg=cfg)


def verify_proof(
    leaf: bytes,
    proof: list[tuple[str, bytes]],
    root: bytes,
    cfg: ProtocolConfig,
    *,
    total: Optional[int] = None,
) -> bool:
    h = leaf
    for side, sib in proof:
        h = node_hash(sib, h, cfg) if side == "L" else node_hash(h, sib, cfg)
    if cfg.merkle_domain_sep:
        if total is None:
            return False
        h = sha3_256(b"\x02", uint64be(total), h)
    return h == root


# ---------------------------------------------------------------------------
# Izchillik isboti (consistency proof) — RFC 6962 §2.1.2 / §2.1.4
#
# ROSTOR-1 v1.1 §8.3: mijoz oldingi ko'rgan (tree_size=m, root) holatini
# saqlaydi (lokal monoton checkpoint). Yangi STH kelganda, operator bu
# funksiya orqali "yangi daraxt (n) eskisining (m) FAQAT qo'shimchasi,
# hech narsa o'chirilmagan/o'zgartirilmagan" ekanini isbotlashi shart.
#
# Bizning bottom-up "chapdan o'ngga juftlash, toq tugunni yuqoriga
# ko'chirish" konstruksiyamiz (yuqoridagi build_tree) RFC 6962 ning
# yuqoridan-pastga "eng katta 2^k chegarasida bo'lish" MTH ta'rifi bilan
# MATEMATIK JIHATDAN BIR XIL daraxtni beradi — shuning uchun standart
# RFC 6962 PROOF/VERIFY algoritmlari to'g'ridan-to'g'ri qo'llaniladi.
# ---------------------------------------------------------------------------
def _mth(leaves: list[bytes], cfg: ProtocolConfig) -> bytes:
    """Berilgan barglar ustidan tree_root (STH root emas, ichki MTH)."""
    if len(leaves) == 1:
        return leaves[0]
    return build_tree(leaves, cfg).tree_root


def _largest_pow2_lt(n: int) -> int:
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def consistency_proof(leaves: list[bytes], m: int, cfg: ProtocolConfig) -> list[bytes]:
    """`m` (eski daraxt o'lchami) va `len(leaves)` (yangi, n) orasidagi
    izchillik isboti. `0 < m <= n` bo'lishi shart."""
    n = len(leaves)
    if not 0 < m <= n:
        raise FileIntegrityError("consistency_proof: 0 < m <= n bo'lishi shart")

    def subproof(m: int, d: list[bytes], b: bool) -> list[bytes]:
        n = len(d)
        if m == n:
            return [] if b else [_mth(d, cfg)]
        k = _largest_pow2_lt(n)
        if m <= k:
            proof = subproof(m, d[:k], b)
            proof.append(_mth(d[k:], cfg))
            return proof
        proof = subproof(m - k, d[k:], False)
        proof.append(_mth(d[:k], cfg))
        return proof

    return subproof(m, leaves, True)


def verify_consistency(
    m: int, n: int, proof: list[bytes], old_root: bytes, new_root: bytes,
    cfg: ProtocolConfig,
) -> bool:
    """RFC 6962 §2.1.4 — eski `tree_root` yangisining kengaytmasi ekanini
    tekshiradi. Bu yerdagi `old_root`/`new_root` — `tree_root` (ya'ni
    `.root` emas, `total`/`uint64be` bilan aralashtirilmagan ichki MTH),
    chaqiruvchi kerak bo'lsa `total` bog'lanishini alohida tekshiradi."""
    if m == n:
        return not proof and old_root == new_root
    if m == 0:
        return True   # bo'sh eski daraxt har qanday kengaytma bilan izchil

    proof = list(proof)
    fn, sn = m - 1, n - 1
    while fn & 1 == 1:
        fn >>= 1
        sn >>= 1
    if fn > 0:
        if not proof:
            return False
        fr = sr = proof.pop(0)
    else:
        fr = sr = old_root

    for c in proof:
        if sn == 0:
            return False
        if fn & 1 == 1 or fn == sn:
            fr = node_hash(c, fr, cfg)
            sr = node_hash(c, sr, cfg)
            while fn & 1 == 0 and fn != 0:
                fn >>= 1
                sn >>= 1
        else:
            sr = node_hash(sr, c, cfg)
        fn >>= 1
        sn >>= 1

    return fr == old_root and sr == new_root
