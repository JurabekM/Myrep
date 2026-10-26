"""Qurilma bo'yicha audit hash-zanjiri (prompt 5.4).

event_hash = SHA256(canonical({seq, prev_hash, actor_id, event_type, entity_id, payload_hash, created_at}))
device_sig = Ed25519(event_hash baytlari)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .canonical import canonical_json_bytes
from .hashing import sha256_hex
from .signing import SUPPORTED_SIG_ALGS, verify_signature

GENESIS_HASH = "0" * 64
_HEX64 = re.compile(r"[0-9a-f]{64}")
_ISO_MS = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z")


@dataclass(frozen=True)
class AuditEvent:
    device_id: str
    seq: int
    prev_hash: str
    event_hash: str
    actor_id: str
    event_type: str
    entity_id: str | None
    payload_hash: str
    created_at: str
    device_sig: str
    sig_alg: str


@dataclass(frozen=True)
class ChainVerification:
    ok: bool
    failed_index: int | None = None
    reason: str | None = None


def payload_hash(payload: object) -> str:
    return sha256_hex(canonical_json_bytes(payload))


def compute_event_hash(
    *,
    seq: int,
    prev_hash: str,
    actor_id: str,
    event_type: str,
    entity_id: str | None,
    payload_hash: str,
    created_at: str,
) -> str:
    return sha256_hex(
        canonical_json_bytes(
            {
                "seq": seq,
                "prev_hash": prev_hash,
                "actor_id": actor_id,
                "event_type": event_type,
                "entity_id": entity_id,
                "payload_hash": payload_hash,
                "created_at": created_at,
            }
        )
    )


def verify_chain(
    events: list[AuditEvent], *, public_key_hex: str, anchor: AuditEvent | None = None
) -> ChainVerification:
    """Zanjirni tekshiradi; birinchi xato indeksi va sababi. `anchor` — serverdagi oxirgi tasdiqlangan hodisa.

    Server `push` da bitta xato bo'lsa butun paketni rad etadi (prompt 7-bo'lim).
    """
    prev_seq = anchor.seq if anchor else 0
    prev_hash = anchor.event_hash if anchor else GENESIS_HASH
    device_id = anchor.device_id if anchor else (events[0].device_id if events else None)
    for i, e in enumerate(events):
        if (
            e.device_id != device_id
            or not _HEX64.fullmatch(e.prev_hash)
            or not _HEX64.fullmatch(e.event_hash)
            or not _HEX64.fullmatch(e.payload_hash)
            or not _ISO_MS.fullmatch(e.created_at)
        ):
            return ChainVerification(False, i, "invalid_format")
        if e.sig_alg not in SUPPORTED_SIG_ALGS:
            return ChainVerification(False, i, "unsupported_sig_alg")
        if e.seq != prev_seq + 1:
            return ChainVerification(False, i, "seq_gap")
        if e.prev_hash != prev_hash:
            return ChainVerification(False, i, "prev_hash_mismatch")
        expected = compute_event_hash(
            seq=e.seq,
            prev_hash=e.prev_hash,
            actor_id=e.actor_id,
            event_type=e.event_type,
            entity_id=e.entity_id,
            payload_hash=e.payload_hash,
            created_at=e.created_at,
        )
        if e.event_hash != expected:
            return ChainVerification(False, i, "event_hash_mismatch")
        if not verify_signature(
            sig_alg=e.sig_alg,
            public_key_hex=public_key_hex,
            message=bytes.fromhex(e.event_hash),
            signature_hex=e.device_sig,
        ):
            return ChainVerification(False, i, "bad_signature")
        prev_seq, prev_hash = e.seq, e.event_hash
    return ChainVerification(True)
