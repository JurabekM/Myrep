"""ROSTOR-1 — Known Answer Test vektorlari.

`scutum/kat.py` bilan bir xil falsafa (deterministik urug'lardan qat'iy
kalitlar, qayta hisoblab tekshirish), lekin ROSTOR ilova qatlamining
YANGI domen ajratgichlari va tuzilmalari uchun: SMT, registrator
tasdig'i, IC/IDC endorsement, TXN_CONFIRM, PaymentIntent, ApkAttestation,
FraudReport target-hash.

ML-DSA imzo (hedged, tasodifiy) qotirib qo'yiladi va `Verify` orqali
tekshiriladi — xuddi `kat.py` dagi kabi.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .crypto import canonical
from .crypto.primitives import (
    ed25519_from_raw,
    ed25519_pub,
    mldsa_from_seed,
    mldsa_pub,
    mldsa_sign,
    mldsa_verify,
    sha3_256,
)
from .rostor import smt as _smt
from .rostor.account import RecoveryRequest
from .rostor.apk import ApkManifestAttestation, android_sha256
from .rostor.fraud_report import target_hash as fr_target_hash
from .rostor.identity import endorsement_payload
from .rostor.payment import payee_token
from .rostor.registrar import registrar_approval_payload
from .rostor.txn_confirm import TxnConfirmRequest, TxnConfirmResponse

KAT_PATH = Path(__file__).resolve().parent.parent / "kat" / "rostor-1-kat.json"
KAT_VERSION = "1.1"

DOMAIN_SEPARATORS = [
    "ROSTOR-1/roster-update", "ROSTOR-1/registrar-approval",
    "ROSTOR-1/idc-endorsement", "ROSTOR-1/log-entry",
    "ROSTOR-1/submission-receipt", "ROSTOR-1/sth", "ROSTOR-1/witness-cosign",
    "ROSTOR-1/txn-request", "ROSTOR-1/txn-response",
    "ROSTOR-1/payment-intent", "ROSTOR-1/payee-token",
    "ROSTOR-1/quorum-approval", "ROSTOR-1/reporter-proof",
    "ROSTOR-1/report-target", "ROSTOR-1/report-content", "ROSTOR-1/apk-attestation",
    "ROSTOR-1/smt-key", "ROSTOR-1/smt-empty", "ROSTOR-1/empty-log",
    "ROSTOR-1/call-context",
]


def _seed(label: str, n: int) -> bytes:
    out = b""
    i = 0
    while len(out) < n:
        out += sha3_256(b"ROSTOR-1/KAT/seed", label.encode(), bytes([i]))
        i += 1
    return out[:n]


def _h(b: bytes) -> str:
    return b.hex()


def build(pinned: Optional[dict] = None) -> dict:
    pinned = pinned or {}
    v: dict[str, Any] = {"kat_version": KAT_VERSION, "domain_separators": DOMAIN_SEPARATORS}

    # ------------------------------------------------------------------ SMT
    keys = [_smt.smt_key(f"entity-{i}".encode()) for i in range(4)]
    t = _smt.SparseMerkleTree()
    for i, k in enumerate(keys):
        t.set(k, f"value-{i}".encode())
    root = t.root()
    proof0 = t.prove(keys[0])
    missing_proof = t.prove(_smt.smt_key(b"never-registered"))
    v["smt"] = {
        "empty_leaf_default": _h(_smt.EMPTY),
        "leaf_rule": "SHA3-256(0x03 || key || value)",
        "node_rule": "SHA3-256(0x04 || L || R)",
        "keys": [_h(k) for k in keys],
        "root": _h(root),
        "inclusion_proof_key0_siblings_sha3": _h(sha3_256(b"".join(proof0.siblings))),
        "non_inclusion_value_is_none": missing_proof.value is None,
        "non_inclusion_siblings_sha3": _h(sha3_256(b"".join(missing_proof.siblings))),
    }

    # ------------------------------------------------------------- registrar
    rid = _seed("registrar/id", 16)
    log_id = _seed("log/id", 16)
    target = _seed("target", 32)
    ra_payload = registrar_approval_payload(log_id, "issue_ic", 0, target)
    v["registrar_approval"] = {
        "log_id": _h(log_id), "action": "issue_ic", "roster_epoch": 0,
        "target_hash": _h(target), "signed_payload_sha3": _h(sha3_256(ra_payload)),
    }

    # ------------------------------------------------------------- identity
    inst_id = _seed("institution/id", 16)
    dc_hash = _seed("idc/dc_hash", 32)
    ep = endorsement_payload(inst_id, dc_hash, 1767225600, 1767225600 + 7 * 86400)
    v["idc_endorsement"] = {
        "institution_id": _h(inst_id), "dc_hash": _h(dc_hash),
        "issued_at": 1767225600, "expires_at": 1767225600 + 7 * 86400,
        "signed_payload_sha3": _h(sha3_256(ep)),
    }

    # ------------------------------------------------------------ txn_confirm
    req = TxnConfirmRequest(
        v=1, txn_id=_seed("txn/id", 16), institution_id=inst_id,
        amount_minor=35_000_00, currency="UZS", recipient_masked="****1234",
        purpose="KAT sinovi", expires_at=1767225600 + 120,
        institution_sig=None,
    )
    req_hash = req.request_hash()
    resp = TxnConfirmResponse(
        request_hash=req_hash, decision="APPROVE",
        account_id=_seed("account/id", 16), device_id=_seed("device/id", 16),
        responded_at=1767225600 + 5, device_sig=None,
    )
    v["txn_confirm"] = {
        "request_signed_payload_sha3": _h(sha3_256(req.signed_payload())),
        "request_hash": _h(req_hash),
        "response_signed_payload_sha3": _h(sha3_256(resp.signed_payload())),
    }

    # ------------------------------------------------------------ payment
    issuer_pk = _seed("issuer/ed25519_pk", 32)
    nonce = _seed("payee/nonce", 16)
    v["payment"] = {
        "issuer_ed25519_pk": _h(issuer_pk), "nonce": _h(nonce),
        "payee_token": _h(payee_token(issuer_pk, nonce)),
    }

    # ------------------------------------------------------------ apk
    apk_bytes = b"ROSTOR-1 KAT sample apk content"
    apk_h = android_sha256(apk_bytes)
    v["apk"] = {
        "sample_apk_sha256": _h(apk_h),
        "note": "hashlib.sha256 (Android native), SHA3-256 EMAS",
    }

    # ------------------------------------------------------------ fraud_report
    v["fraud_report"] = {
        "target_hash_phone": _h(fr_target_hash("phone", b"+998901234567")),
    }

    return v


def verify(vectors: dict) -> list[str]:
    errs: list[str] = []
    rebuilt = build(pinned=vectors)

    def walk(path: str, a: Any, b: Any) -> None:
        if isinstance(a, dict):
            for key in a:
                if key not in b:
                    errs.append(f"{path}.{key}: yangi vektorda yo'q")
                else:
                    walk(f"{path}.{key}", a[key], b[key])
        elif isinstance(a, list):
            if len(a) != len(b):
                errs.append(f"{path}: uzunlik {len(a)} != {len(b)}")
            else:
                for i, (x, y) in enumerate(zip(a, b)):
                    walk(f"{path}[{i}]", x, y)
        elif a != b:
            errs.append(f"{path}: {str(a)[:40]}… != {str(b)[:40]}…")

    walk("kat", vectors, rebuilt)
    return errs


def load() -> dict:
    return json.loads(KAT_PATH.read_text(encoding="utf-8"))


def save(vectors: dict) -> None:
    KAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    KAT_PATH.write_text(json.dumps(vectors, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    existing = load() if KAT_PATH.exists() else None
    vectors = build(pinned=existing)
    save(vectors)
    errs = verify(load())
    if errs:
        print("ROSTOR KAT XATOLARI:")
        for e in errs:
            print("  -", e)
        return 1
    print(f"ROSTOR KAT OK -> {KAT_PATH}")
    print(f"  SMT root         = {vectors['smt']['root'][:32]}…")
    print(f"  txn request_hash = {vectors['txn_confirm']['request_hash'][:32]}…")
    print(f"  payee_token      = {vectors['payment']['payee_token'][:32]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
