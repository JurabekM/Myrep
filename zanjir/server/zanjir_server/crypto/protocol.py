"""Protokol imzosi (prompt 5.4): signature = Ed25519(payload_sha256 ‖ pdf_sha256) — 32 + 32 xom bayt."""

from __future__ import annotations

from .canonical import canonical_json_bytes
from .hashing import sha256_hex
from .signing import verify_signature


def protocol_message(payload_sha256: str, pdf_sha256: str) -> bytes:
    return bytes.fromhex(payload_sha256) + bytes.fromhex(pdf_sha256)


def verify_protocol(
    *,
    payload: object,
    pdf: bytes,
    payload_sha256: str,
    pdf_sha256: str,
    signature_hex: str,
    sig_alg: str,
    public_key_hex: str,
) -> str | None:
    """Xato sababi yoki None (hammasi to'g'ri)."""
    if sha256_hex(canonical_json_bytes(payload)) != payload_sha256:
        return "payload_hash_mismatch"
    if sha256_hex(pdf) != pdf_sha256:
        return "pdf_hash_mismatch"
    message = protocol_message(payload_sha256, pdf_sha256)
    valid = verify_signature(
        sig_alg=sig_alg, public_key_hex=public_key_hex, message=message, signature_hex=signature_hex
    )
    if not valid:
        return "bad_signature"
    return None
