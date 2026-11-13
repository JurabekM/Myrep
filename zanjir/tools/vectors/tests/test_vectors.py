"""Umumiy vektorlar (`tools/vectors/*.json`) — Dart testlari ham aynan shu fayllarni o'qiydi."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from zanjir_refcrypto.canonical import canonical_json, canonical_json_bytes
from zanjir_refcrypto.hash_chain import AuditEvent, compute_event_hash, payload_hash, verify_chain
from zanjir_refcrypto.hashing import sha256_hex
from zanjir_refcrypto.protocol import protocol_message, qr_token_from_signature, qr_token_message, verify_protocol
from zanjir_refcrypto.signing import Ed25519Signer, UnsupportedSigAlgError, verify_signature

VECTORS = Path(__file__).resolve().parents[3] / "tools" / "vectors"


def load(name: str) -> Any:
    return json.loads((VECTORS / name).read_text(encoding="utf-8"))


CANON = load("canonical_json.json")
ED = load("ed25519.json")
CHAIN = load("hash_chain.json")
PROTO = load("protocol_signature.json")


@pytest.mark.parametrize("case", CANON["cases"], ids=lambda c: c["name"])
def test_canonical_cases(case: dict[str, Any]) -> None:
    got = canonical_json(json.loads(case["input_json"]))
    assert got == case["canonical"]
    assert sha256_hex(got.encode()) == case["sha256"]


@pytest.mark.parametrize("case", CANON["errors"], ids=lambda c: c["name"])
def test_canonical_errors(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        canonical_json(json.loads(case["input_json"]))


@pytest.mark.parametrize("case", CANON["datetimes"], ids=lambda c: c["canonical"])
def test_canonical_datetimes(case: dict[str, Any]) -> None:
    y, mo, d, h, mi, s, us = case["utc"]
    assert canonical_json(datetime(y, mo, d, h, mi, s, us, tzinfo=UTC)) == case["canonical"]


@pytest.mark.parametrize("case", ED["cases"], ids=lambda c: c["name"])
def test_ed25519(case: dict[str, Any]) -> None:
    signer = Ed25519Signer(bytes.fromhex(case["secret"]))
    assert signer.public_key_hex == case["public"]
    message = bytes.fromhex(case["message"])
    assert signer.sign(message).hex() == case["signature"]
    kwargs = {"sig_alg": ED["sig_alg"], "public_key_hex": case["public"], "signature_hex": case["signature"]}
    assert verify_signature(message=message, **kwargs)
    assert not verify_signature(message=message + b"\x00", **kwargs)


@pytest.mark.parametrize("case", ED["reject"], ids=lambda c: c["name"])
def test_ed25519_reject(case: dict[str, Any]) -> None:
    message = bytes.fromhex(case["message"])
    assert not verify_signature(
        sig_alg=ED["sig_alg"], public_key_hex=case["public"], message=message, signature_hex=case["signature"]
    )


def test_verify_signature_rejects_garbage_and_unknown_alg() -> None:
    case = ED["cases"][0]
    assert not verify_signature(sig_alg="Ed25519", public_key_hex="zz", message=b"", signature_hex=case["signature"])
    assert not verify_signature(sig_alg="Ed25519", public_key_hex=case["public"], message=b"", signature_hex="00")
    with pytest.raises(UnsupportedSigAlgError):
        verify_signature(
            sig_alg="ML-DSA-65", public_key_hex=case["public"], message=b"", signature_hex=case["signature"]
        )
    with pytest.raises(ValueError):
        Ed25519Signer(b"short")


def _events(raw: list[dict[str, Any]]) -> list[AuditEvent]:
    return [AuditEvent(**{k: v for k, v in e.items() if k != "payload"}) for e in raw]


def test_chain_events_recomputed() -> None:
    signer = Ed25519Signer(bytes.fromhex(CHAIN["device_seed"]))
    assert signer.public_key_hex == CHAIN["public_key"]
    for e in CHAIN["events"]:
        assert payload_hash(e["payload"]) == e["payload_hash"]
        eh = compute_event_hash(
            seq=e["seq"],
            prev_hash=e["prev_hash"],
            actor_id=e["actor_id"],
            event_type=e["event_type"],
            entity_id=e["entity_id"],
            payload_hash=e["payload_hash"],
            created_at=e["created_at"],
        )
        assert eh == e["event_hash"]
        assert signer.sign(bytes.fromhex(eh)).hex() == e["device_sig"]
    assert CHAIN["events"][0]["prev_hash"] == CHAIN["genesis_hash"]
    assert verify_chain(_events(CHAIN["events"]), public_key_hex=CHAIN["public_key"]).ok


def test_chain_anchor() -> None:
    events = _events(CHAIN["events"])
    a = CHAIN["anchor_case"]
    r = verify_chain(events[a["events_from"] :], public_key_hex=CHAIN["public_key"], anchor=events[a["anchor_index"]])
    assert r.ok is a["ok"]
    # Anchor'siz o'rtadan boshlangan zanjir — rad etiladi.
    assert verify_chain(events[2:], public_key_hex=CHAIN["public_key"]).reason == "seq_gap"


def test_chain_empty_is_ok() -> None:
    assert verify_chain([], public_key_hex=CHAIN["public_key"]).ok


@pytest.mark.parametrize("case", CHAIN["tamper"], ids=lambda c: c["name"])
def test_chain_tamper(case: dict[str, Any]) -> None:
    raw = [dict(e) for e in CHAIN["events"]]
    if case["op"] == "drop":
        del raw[case["index"]]
    else:
        raw[case["index"]][case["field"]] = case["value"]
    r = verify_chain(_events(raw), public_key_hex=CHAIN["public_key"])
    assert (r.ok, r.failed_index, r.reason) == (False, case["failed_index"], case["reason"])


def test_chain_wrong_public_key() -> None:
    other = ED["cases"][1]["public"]
    r = verify_chain(_events(CHAIN["events"]), public_key_hex=other)
    assert (r.ok, r.failed_index, r.reason) == (False, 0, "bad_signature")


def test_chain_every_signature_bit_flip_detected() -> None:
    events = _events(CHAIN["events"])
    sig = bytes.fromhex(events[3].device_sig)
    for i in range(len(sig)):
        bad = bytearray(sig)
        bad[i] ^= 0x01
        tampered = [*events[:3], replace(events[3], device_sig=bad.hex()), *events[4:]]
        assert verify_chain(tampered, public_key_hex=CHAIN["public_key"]).reason == "bad_signature", i


def _proto_kwargs(**override: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "payload": PROTO["payload"],
        "pdf": bytes.fromhex(PROTO["pdf_hex"]),
        "payload_sha256": PROTO["payload_sha256"],
        "pdf_sha256": PROTO["pdf_sha256"],
        "signature_hex": PROTO["signature"],
        "sig_alg": PROTO["sig_alg"],
        "public_key_hex": PROTO["public_key"],
    }
    kwargs.update(override)
    return kwargs


def test_protocol_vector() -> None:
    assert canonical_json(PROTO["payload"]) == PROTO["payload_canonical"]
    assert sha256_hex(canonical_json_bytes(PROTO["payload"])) == PROTO["payload_sha256"]
    assert sha256_hex(bytes.fromhex(PROTO["pdf_hex"])) == PROTO["pdf_sha256"]
    message = protocol_message(PROTO["payload_sha256"], PROTO["pdf_sha256"])
    assert message.hex() == PROTO["message_hex"]
    signer = Ed25519Signer(bytes.fromhex(CHAIN["device_seed"]))
    assert signer.sign(message).hex() == PROTO["signature"]
    assert verify_protocol(**_proto_kwargs()) is None


def test_protocol_every_pdf_byte_change_detected() -> None:
    pdf = bytes.fromhex(PROTO["pdf_hex"])
    for i in range(len(pdf)):
        bad = bytearray(pdf)
        bad[i] ^= 0xFF
        assert verify_protocol(**_proto_kwargs(pdf=bytes(bad))) == "pdf_hash_mismatch", i


def test_protocol_payload_change_detected() -> None:
    payload = json.loads(json.dumps(PROTO["payload"]))
    payload["measurements"][1]["verdict"] = "PASS"
    assert verify_protocol(**_proto_kwargs(payload=payload)) == "payload_hash_mismatch"


def test_protocol_signature_or_hash_substitution_detected() -> None:
    sig = bytes.fromhex(PROTO["signature"])
    for i in range(len(sig)):
        bad = bytearray(sig)
        bad[i] ^= 0x80
        assert verify_protocol(**_proto_kwargs(signature_hex=bad.hex())) == "bad_signature", i
    # Hash'larni ham, PDF'ni ham almashtirish — imzo mos kelmaydi.
    other_pdf = b"%PDF-1.7\nboshqa\n%%EOF\n"
    forged = _proto_kwargs(pdf=other_pdf, pdf_sha256=sha256_hex(other_pdf))
    assert verify_protocol(**forged) == "bad_signature"


def test_qr_token_vector() -> None:
    qr = PROTO["qr_token"]
    message = qr_token_message(qr["org_id"], qr["number"])
    assert message.hex() == qr["message_hex"]
    assert Ed25519Signer(bytes.fromhex(CHAIN["device_seed"])).sign(message).hex() == qr["qr_sig"]
    assert verify_signature(
        sig_alg="Ed25519", public_key_hex=PROTO["public_key"], message=message, signature_hex=qr["qr_sig"]
    )
    assert qr_token_from_signature(qr["qr_sig"]) == qr["qr_token"]
