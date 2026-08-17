"""Sparse Merkle Tree (verifiable map) — spec §8.2.

v1.0 dagi oddiy append-only Merkle jurnal **borlikni** isbotlar edi, lekin
**yo'qlikni** isbotlay olmasdi (tashqi audit topilmasi R3, KRITIK). Bu
modul har bir mumkin bo'lgan 256-bitli kalit uchun ANIQ, oldindan
belgilangan pozitsiyaga ega daraxt quradi: kalit band bo'lsa — inclusion
proof, bo'sh bo'lsa — o'sha aniq pozitsiyada "bo'sh" sentinel borligini
ko'rsatuvchi, xuddi shunday Merkle yo'l (non-inclusion proof).

    leaf(key, value) = SHA3-256( 0x03 || key || value )
    node(L, R)        = SHA3-256( 0x04 || L || R )
    EMPTY              = SHA3-256( "ROSTOR-1/smt-empty" )

DIQQAT (murakkablik): `prove()` har chaqirilganda barcha yozuvlarni qayta
bo'ladi — bu referens/demo miqyosida (minglab yozuv) yetarli, lekin
millionlab yozuv uchun optimallashtirilmagan (indekslashtirilmagan
ma'lumotlar bazasi kerak bo'lardi). `verify()` esa har doim O(256) xesh
amali — ishlab chiqarishga yaroqli tezlikda.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..crypto.primitives import sha3_256

DEPTH = 256  # SHA3-256 chiqishi bilan bir xil, bit birligida

EMPTY = sha3_256(b"ROSTOR-1/smt-empty")


def smt_key(raw_id: bytes) -> bytes:
    """Ixtiyoriy uzunlikdagi identifikatorni bir xil taqsimlangan
    256-bitli SMT kalitiga aylantiradi."""
    return sha3_256(b"ROSTOR-1/smt-key", raw_id)


def leaf_hash(key: bytes, value: bytes) -> bytes:
    return sha3_256(b"\x03", key, value)


def node_hash(left: bytes, right: bytes) -> bytes:
    return sha3_256(b"\x04", left, right)


def _bit(key: bytes, i: int) -> int:
    """i-bit, 0 = eng muhim bit (MSB-first)."""
    byte_i, bit_i = divmod(i, 8)
    return (key[byte_i] >> (7 - bit_i)) & 1


def _build_defaults() -> list[bytes]:
    """`defaults[d]` — depth_consumed=d dagi bo'sh qism-daraxt ildizi.
    `defaults[DEPTH]` = EMPTY (barg darajasi), `defaults[0]` = butun
    kalit maydoni bo'sh bo'lganda ildiz."""
    out = [b""] * (DEPTH + 1)
    out[DEPTH] = EMPTY
    for d in range(DEPTH - 1, -1, -1):
        out[d] = node_hash(out[d + 1], out[d + 1])
    return out


_DEFAULTS = _build_defaults()


@dataclass(frozen=True)
class SMTProof:
    key: bytes
    value: Optional[bytes]          # None => non-inclusion (yo'qlik) isboti
    siblings: list[bytes]           # barg -> ildiz tartibida, uzunlik = DEPTH

    @property
    def is_inclusion(self) -> bool:
        return self.value is not None


def _subtree_hash(entries: list[tuple[bytes, bytes]], depth_consumed: int) -> bytes:
    if depth_consumed == DEPTH:
        if not entries:
            return _DEFAULTS[DEPTH]
        (key, value), = entries
        return leaf_hash(key, value)
    if not entries:
        return _DEFAULTS[depth_consumed]
    left = [(k, v) for k, v in entries if _bit(k, depth_consumed) == 0]
    right = [(k, v) for k, v in entries if _bit(k, depth_consumed) == 1]
    return node_hash(
        _subtree_hash(left, depth_consumed + 1),
        _subtree_hash(right, depth_consumed + 1),
    )


class SparseMerkleTree:
    """256-chuqurlikdagi SMT. `entries`: 32-baytli kalit -> qiymat."""

    def __init__(self, entries: Optional[dict[bytes, bytes]] = None) -> None:
        self.entries: dict[bytes, bytes] = dict(entries or {})

    def set(self, key: bytes, value: bytes) -> None:
        if len(key) != 32:
            raise ValueError("SMT kaliti 32 bayt bo'lishi kerak (smt_key() orqali)")
        self.entries[key] = value

    def remove(self, key: bytes) -> None:
        self.entries.pop(key, None)

    def root(self) -> bytes:
        return _subtree_hash(list(self.entries.items()), 0)

    def prove(self, key: bytes) -> SMTProof:
        if len(key) != 32:
            raise ValueError("SMT kaliti 32 bayt bo'lishi kerak (smt_key() orqali)")
        siblings: list[bytes] = []

        def rec(entries: list[tuple[bytes, bytes]], depth_consumed: int) -> None:
            if depth_consumed == DEPTH:
                return
            left = [(k, v) for k, v in entries if _bit(k, depth_consumed) == 0]
            right = [(k, v) for k, v in entries if _bit(k, depth_consumed) == 1]
            bit = _bit(key, depth_consumed)
            mine, sib = (left, right) if bit == 0 else (right, left)
            sib_hash = _subtree_hash(sib, depth_consumed + 1)
            rec(mine, depth_consumed + 1)
            siblings.append(sib_hash)   # post-order -> barg->ildiz tartibi

        rec(list(self.entries.items()), 0)
        return SMTProof(key=key, value=self.entries.get(key), siblings=siblings)


def verify_smt_proof(proof: SMTProof, root: bytes) -> bool:
    """Borlik VA yo'qlik isbotini bir xil funksiya bilan tekshiradi —
    `proof.value is None` bo'lsa, bu "aynan shu pozitsiyada hech narsa
    yo'q" degan isbot."""
    if len(proof.siblings) != DEPTH:
        return False
    h = leaf_hash(proof.key, proof.value) if proof.value is not None else _DEFAULTS[DEPTH]
    for i, sib in enumerate(proof.siblings):
        depth_consumed = DEPTH - 1 - i
        bit = _bit(proof.key, depth_consumed)
        h = node_hash(h, sib) if bit == 0 else node_hash(sib, h)
    return h == root
