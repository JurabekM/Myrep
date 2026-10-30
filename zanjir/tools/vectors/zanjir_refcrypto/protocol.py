"""Protokol imzosi (prompt 5.4): signature = Ed25519(payload_sha256 ‖ pdf_sha256) — 32 + 32 xom bayt."""

from __future__ import annotations

from .canonical import canonical_json_bytes
from .hashing import sha256_hex
from .signing import verify_signature


def protocol_message(payload_sha256: str, pdf_sha256: str) -> bytes:
    return bytes.fromhex(payload_sha256) + bytes.fromhex(pdf_sha256)


def qr_token_message(org_id: str, number: str) -> bytes:
    """QR token (ADR-0014): `qr_sig = Ed25519("zanjir.qr/1\\n<org_id>\\n<raqam>")`, `qr_token = sha256(qr_sig)[:32]`.

    Token qurilma kalitisiz yasalmaydi va oldindan bilinmaydi — boshqa tashkilot uni "band qila" olmaydi.
    """
    return f"zanjir.qr/1\n{org_id}\n{number}".encode()


def qr_token_from_signature(qr_sig_hex: str) -> str:
    return sha256_hex(bytes.fromhex(qr_sig_hex))[:32]


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
