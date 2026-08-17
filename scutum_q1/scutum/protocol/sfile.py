"""Spec §7: S-FILE — faylni bo'laklab shifrlash, manifest va Merkle tekshiruvi."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterator, Optional

from ..config import PROTOCOL_VERSION, ProtocolConfig
from ..crypto import canonical
from ..crypto.primitives import (
    aead_open,
    aead_seal,
    hkdf_sha512,
    key_commitment,
    random_bytes,
    sha3_256,
    uint64be,
)
from .envelope import file_chunk_nonce
from .errors import FileIntegrityError
from .merkle import MerkleTree, build_tree, leaf_hash, verify_proof

COMMIT_LEN = 32


# ---------------------------------------------------------------------------
# Kalit derivatsiyasi
# ---------------------------------------------------------------------------
def chunk_key(fk: bytes, file_salt: bytes, file_id: bytes, index: int) -> bytes:
    """chunk_key_i = HKDF-SHA-512(FK, salt=file_salt,
                                  info="SCUTUM-Q1/FILE/CHUNK"||file_id||uint64be(i))"""
    return hkdf_sha512(
        fk, file_salt, b"SCUTUM-Q1/FILE/CHUNK" + file_id + uint64be(index), 32
    )


def meta_key(fk: bytes, file_salt: bytes, file_id: bytes, cfg: ProtocolConfig) -> bytes:
    """Y-4: spec `name_enc`/`mime_enc` uchun kalitni umuman ta'riflamaydi.

    SPEC rejimda simulyator eng ehtimolli (va xato) amaliyotni takrorlaydi:
    FK ning o'zi kalit sifatida, sobit nonce bilan.
    """
    if cfg.separate_meta_key:
        return hkdf_sha512(
            fk, file_salt, b"SCUTUM-Q1/FILE/META" + file_id, 32
        )
    return fk[:32]


def meta_nonce(file_id: bytes, field_name: str, cfg: ProtocolConfig) -> bytes:
    if cfg.separate_meta_key:
        return sha3_256(b"SCUTUM-Q1/FILE/META", file_id, field_name.encode())[:12]
    return b"\x00" * 12   # SPEC: ta'riflanmagan -> amalda sobit nonce


# ---------------------------------------------------------------------------
# Natijalar
# ---------------------------------------------------------------------------
@dataclass
class EncryptedChunk:
    index: int
    ciphertext: bytes
    leaf: bytes

    @property
    def size(self) -> int:
        return len(self.ciphertext)


@dataclass
class EncryptedFile:
    fk: bytes
    manifest: dict
    chunks: list[EncryptedChunk]
    tree: MerkleTree

    @property
    def file_id(self) -> bytes:
        return self.manifest["file_id"]

    @property
    def total_ciphertext(self) -> int:
        return sum(c.size for c in self.chunks)

    def proof(self, index: int):
        return self.tree.proof(index)


# ---------------------------------------------------------------------------
# Shifrlash
# ---------------------------------------------------------------------------
def chunk_aad(
    file_id: bytes, index: int, total: int, plaintext_size: int, cfg: ProtocolConfig
) -> bytes:
    """AAD_i = canonical({v, file_id, i, total_chunks, plaintext_size})  — spec §7.1"""
    return canonical.encode(
        {
            "v": PROTOCOL_VERSION,
            "file_id": file_id,
            "i": index,
            "total_chunks": total,
            "plaintext_size": plaintext_size,
        },
        cfg.encoding,
    )


def encrypt_file(
    data: bytes,
    cfg: ProtocolConfig,
    *,
    name: Optional[str] = None,
    mime: Optional[str] = None,
    fk: Optional[bytes] = None,
    file_id: Optional[bytes] = None,
    file_salt: Optional[bytes] = None,
    now: Optional[int] = None,
) -> EncryptedFile:
    fk = fk or random_bytes(32)
    file_id = file_id or random_bytes(16)
    file_salt = file_salt or random_bytes(32)
    size = len(data)
    cs = cfg.chunk_size
    total = max(1, (size + cs - 1) // cs)

    chunks: list[EncryptedChunk] = []
    leaves: list[bytes] = []
    for i in range(total):
        pt = data[i * cs : (i + 1) * cs]
        k = chunk_key(fk, file_salt, file_id, i)
        ct = aead_seal(
            k, file_chunk_nonce(file_id, i), pt, chunk_aad(file_id, i, total, size, cfg)
        )
        if cfg.key_commitment:
            ct = key_commitment(k) + ct
        leaf = leaf_hash(i, ct, cfg)
        chunks.append(EncryptedChunk(i, ct, leaf))
        leaves.append(leaf)

    tree = build_tree(leaves, cfg)

    mk = meta_key(fk, file_salt, file_id, cfg)
    def _enc_meta(value: Optional[str], fname: str) -> Optional[bytes]:
        if value is None:
            return None
        return aead_seal(
            mk,
            meta_nonce(file_id, fname, cfg),
            value.encode("utf-8"),
            canonical.encode({"file_id": file_id, "f": fname}, cfg.encoding),
        )

    manifest = {
        "v": PROTOCOL_VERSION,
        "file_id": file_id,
        "name_enc": _enc_meta(name, "name"),
        "mime_enc": _enc_meta(mime, "mime"),
        "plaintext_size": size,
        "chunk_size": cs,
        "total_chunks": total,
        "file_salt": file_salt,
        "root_hash": tree.root,
        "created_at": int(now if now is not None else time.time()),
    }
    return EncryptedFile(fk=fk, manifest=manifest, chunks=chunks, tree=tree)


# ---------------------------------------------------------------------------
# Qabul qilish va tekshirish (spec §7.2)
# ---------------------------------------------------------------------------
@dataclass
class ChunkReport:
    index: int
    ok: bool
    reason: str = ""


@dataclass
class ReceiveResult:
    ok: bool
    data: Optional[bytes]
    reports: list[ChunkReport] = field(default_factory=list)
    root_ok: bool = False
    error: str = ""

    @property
    def failed(self) -> list[int]:
        return [r.index for r in self.reports if not r.ok]


def receive_file(
    manifest: dict,
    fk: bytes,
    chunks: list[EncryptedChunk],
    cfg: ProtocolConfig,
    *,
    proofs: Optional[dict[int, list]] = None,
) -> ReceiveResult:
    """Spec §7.2: har bo'lakning AEAD tegi, indeksi va Merkle isboti tekshiriladi;
    `root_hash` ochiq matnga yig'ishdan OLDIN tekshirilishi MUST."""
    file_id = manifest["file_id"]
    total = manifest["total_chunks"]
    size = manifest["plaintext_size"]
    salt = manifest["file_salt"]
    reports: list[ChunkReport] = []

    if len(chunks) != total:
        return ReceiveResult(
            False, None, reports, False,
            f"bo'laklar soni mos emas: {len(chunks)} != {total} (truncation?)",
        )

    by_index: dict[int, EncryptedChunk] = {}
    for c in chunks:
        if c.index in by_index:
            return ReceiveResult(False, None, reports, False,
                                 f"takroriy bo'lak indeksi {c.index}")
        by_index[c.index] = c
    if sorted(by_index) != list(range(total)):
        return ReceiveResult(False, None, reports, False, "indekslar to'liq emas")

    # --- 1) Merkle: ildizni yig'ishdan OLDIN tekshirish ---
    leaves = [leaf_hash(i, by_index[i].ciphertext, cfg) for i in range(total)]
    tree = build_tree(leaves, cfg)
    root_ok = tree.root == manifest["root_hash"]
    if not root_ok:
        return ReceiveResult(False, None, reports, False, "root_hash mos emas")

    if proofs:
        for i, proof in proofs.items():
            if not verify_proof(leaves[i], proof, manifest["root_hash"], cfg, total=total):
                return ReceiveResult(False, None, reports, True,
                                     f"bo'lak {i} uchun Merkle isboti noto'g'ri")

    # --- 2) AEAD ---
    out = bytearray()
    for i in range(total):
        c = by_index[i]
        k = chunk_key(fk, salt, file_id, i)
        body = c.ciphertext
        try:
            if cfg.key_commitment:
                if len(body) < COMMIT_LEN:
                    raise FileIntegrityError("kalit-majburiyat tegi yo'q")
                import hmac as _hmac

                if not _hmac.compare_digest(body[:COMMIT_LEN], key_commitment(k)):
                    raise FileIntegrityError("kalit-majburiyat tegi mos emas")
                body = body[COMMIT_LEN:]
            pt = aead_open(
                k, file_chunk_nonce(file_id, i), body,
                chunk_aad(file_id, i, total, size, cfg),
            )
            out += pt
            reports.append(ChunkReport(i, True))
        except Exception as exc:  # noqa: BLE001 — GUI uchun sabab kerak
            reports.append(ChunkReport(i, False, str(exc)))

    if any(not r.ok for r in reports):
        return ReceiveResult(False, None, reports, True, "bo'lak(lar) ochilmadi")
    if len(out) != size:
        return ReceiveResult(False, None, reports, True,
                             f"o'lcham mos emas: {len(out)} != {size}")
    return ReceiveResult(True, bytes(out), reports, True)


def decrypt_metadata(manifest: dict, fk: bytes, cfg: ProtocolConfig) -> dict:
    mk = meta_key(fk, manifest["file_salt"], manifest["file_id"], cfg)
    out = {}
    for fname in ("name", "mime"):
        blob = manifest.get(f"{fname}_enc")
        if not blob:
            out[fname] = None
            continue
        try:
            out[fname] = aead_open(
                mk,
                meta_nonce(manifest["file_id"], fname, cfg),
                blob,
                canonical.encode(
                    {"file_id": manifest["file_id"], "f": fname}, cfg.encoding
                ),
            ).decode("utf-8")
        except Exception:
            out[fname] = None
    return out
