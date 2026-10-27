"""Dart va Python uchun umumiy kripto test vektorlarini yaratadi (ADR-0007).

Python implementatsiyasi (`zanjir_server.crypto`) avval RFC 8785 va RFC 8032 rasmiy natijalari bilan tekshiriladi,
keyin vektorlar yoziladi. Dart (`zanjir_core`) shu fayllarni mustaqil tekshiradi — ikki implementatsiya bir-birini nazorat qiladi.

Foydalanish (server muhitida):
    cd server && uv run python -I ../tools/vectors/generate.py          # yozish
    cd server && uv run python -I ../tools/vectors/generate.py --check  # CI: fayllar eskirmaganmi
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from zanjir_server.crypto.canonical import canonical_json, canonical_json_bytes
from zanjir_server.crypto.hash_chain import GENESIS_HASH, AuditEvent, compute_event_hash, payload_hash, verify_chain
from zanjir_server.crypto.hashing import sha256_hex
from zanjir_server.crypto.protocol import protocol_message, qr_token_from_signature, qr_token_message
from zanjir_server.crypto.signing import SIG_ALG_ED25519, Ed25519Signer, verify_signature

OUT = Path(__file__).resolve().parent

# RFC 8032, 7.1 — TEST 1..3.
RFC8032 = [
    {
        "name": "RFC 8032 TEST 1",
        "secret": "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
        "public": "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
        "message": "",
        "signature": "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
    },
    {
        "name": "RFC 8032 TEST 2",
        "secret": "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
        "public": "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
        "message": "72",
        "signature": "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
    },
    {
        "name": "RFC 8032 TEST 3",
        "secret": "c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
        "public": "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
        "message": "af82",
        "signature": "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a",
    },
]

# RFC 8785, 3.2.4 va 3.2.3 misollari (kutilgan natija qo'lda — standartdan).
RFC8785_CASES = [
    (
        "RFC 8785 3.2.4 misoli",
        '{"numbers": [333333333.33333329, 1E30, 4.50, 2e-3, 0.000000000000000000000000001],'
        ' "string": "\\u20ac$\\u000F\\u000aA\'\\u0042\\u0022\\u005c\\\\\\"\\/", "literals": [null, true, false]}',
        '{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
        '"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}',
    ),
    (
        "RFC 8785 3.2.3 kalitlarni saralash",
        '{"\\u20ac": "Euro Sign", "\\r": "Carriage Return", "\\ufb33": "Hebrew Letter Dalet With Dagesh",'
        ' "1": "One", "\\ud83d\\ude00": "Emoji: Grinning Face", "\\u0080": "Control", "\\u00f6": "Latin Small Letter O With Diaeresis"}',
        '{"\\r":"Carriage Return","1":"One","\u0080":"Control","ö":"Latin Small Letter O With Diaeresis",'
        '"€":"Euro Sign","😀":"Emoji: Grinning Face","\ufb33":"Hebrew Letter Dalet With Dagesh"}',
    ),
]

EXTRA_CASES = [
    ("bo'sh obyekt", "{}"),
    ("bo'sh massiv", "[]"),
    ("ichma-ich", '{"b": {"d": [1, {"f": null, "e": true}], "c": ""}, "a": []}'),
    (
        "sonlar",
        "[0, -0.0, 1, -1, 16.0, 2.5, 0.1, -0.000001, 0.0000001, 1e21, 1e20, 123e-20, 1.5e300, 5e-324, "
        "1.7976931348623157e308, 9007199254740991, -9007199254740991, 4.000000000000001, 100.0, 0.001]",
    ),
    ("o'zbek va rus matni", '{"izoh": "Ўзбекча — ПУЭ 1.7.79, «UZO» €", "label": "QF1 → SHR-1"}'),
    ("boshqaruv belgilari", '"\\u0000\\u0001\\u001f\\u007f\\b\\f\\n\\r\\t/"'),
    (
        "o'lchov qiymatlari",
        '{"INSULATION": {"test_voltage_v": 1000, "pairs": [{"pair": "L1-PE", "mohm": 120.0}, {"pair": "L1-N", "mohm": 0.5}]},'
        ' "RCD_TRIP": {"multiplier": 1.0, "trip_time_ms": 24, "trip_current_ma": 21, "tripped": true}}',
    ),
]

ERROR_CASES = [
    ("yolg'iz surrogat", '"\\ud800"', "lone_surrogate"),
    ("yolg'iz past surrogat", '{"a": "x\\udc00"}', "lone_surrogate"),
    ("2^53", "9007199254740992", "unsafe_integer"),
    ("cheksiz son", "1e400", "non_finite"),
]

DATETIMES = [
    ([2026, 10, 26, 7, 5, 3, 120999], '"2026-10-26T07:05:03.120Z"'),
    ([2026, 1, 1, 0, 0, 0, 0], '"2026-01-01T00:00:00.000Z"'),
    ([1999, 12, 31, 23, 59, 59, 999999], '"1999-12-31T23:59:59.999Z"'),
    ([5, 1, 1, 0, 0, 0, 1000], '"0005-01-01T00:00:00.001Z"'),
]

# Ed25519 guruh tartibi (RFC 8032, 5.1).
ED25519_L = 2**252 + 27742317777372353535851937790883648493

DEVICE_SEED = RFC8032[0]["secret"]
DEVICE_ID = "01920000-0000-7000-8000-00000000d001"
ACTOR_ID = "01920000-0000-7000-8000-0000000000a1"


def canonical_vectors() -> dict[str, Any]:
    cases = []
    for name, raw, expected in RFC8785_CASES:
        got = canonical_json(json.loads(raw))
        assert got == expected, f"{name}: {got!r} != {expected!r}"
        cases.append({"name": name, "input_json": raw, "canonical": got, "sha256": sha256_hex(got.encode())})
    for name, raw in EXTRA_CASES:
        got = canonical_json(json.loads(raw))
        cases.append({"name": name, "input_json": raw, "canonical": got, "sha256": sha256_hex(got.encode())})
    errors = []
    for name, raw, kind in ERROR_CASES:
        try:
            canonical_json(json.loads(raw))
        except ValueError:
            errors.append({"name": name, "input_json": raw, "error": kind})
        else:
            raise AssertionError(f"{name}: xato kutilgan edi")
    return {
        "description": "Kanonik JSON (RFC 8785). input_json — xom JSON matni, har bir til o'z parseri bilan o'qiydi.",
        "cases": cases,
        "errors": errors,
        "datetimes": [
            {"utc": dt, "canonical": expected, "comment": "[yil, oy, kun, soat, daqiqa, soniya, mikrosekund]"}
            for dt, expected in DATETIMES
        ],
    }


def ed25519_vectors() -> dict[str, Any]:
    for v in RFC8032:
        signer = Ed25519Signer(bytes.fromhex(v["secret"]))
        assert signer.public_key_hex == v["public"], v["name"]
        assert signer.sign(bytes.fromhex(v["message"])).hex() == v["signature"], v["name"]
        assert verify_signature(
            sig_alg=SIG_ALG_ED25519,
            public_key_hex=v["public"],
            message=bytes.fromhex(v["message"]),
            signature_hex=v["signature"],
        )
    # Rad etilishi shart: noto'g'ri ochiq kalitlar va o'zgaruvchan (S + L) imzo — RFC 8032, 5.1.7.
    t1 = RFC8032[0]
    sig = bytes.fromhex(t1["signature"])
    malleable = sig[:32] + (int.from_bytes(sig[32:], "little") + ED25519_L).to_bytes(32, "little")
    reject = [
        {
            "name": "S + L (malleability)",
            "public": t1["public"],
            "message": t1["message"],
            "signature": malleable.hex(),
        },
        {"name": "ochiq kalit ff…ff", "public": "ff" * 32, "message": "01", "signature": "00" * 64},
        {"name": "ochiq kalit 00…00", "public": "00" * 32, "message": "01", "signature": "00" * 64},
        {"name": "boshqa xabar", "public": t1["public"], "message": "00", "signature": t1["signature"]},
    ]
    for r in reject:
        assert not verify_signature(
            sig_alg=SIG_ALG_ED25519,
            public_key_hex=r["public"],
            message=bytes.fromhex(r["message"]),
            signature_hex=r["signature"],
        ), r["name"]
    return {
        "description": "Ed25519 (RFC 8032, 7.1). Barcha qiymatlar hex. reject — tekshiruv false qaytarishi shart.",
        "sig_alg": SIG_ALG_ED25519,
        "cases": RFC8032,
        "reject": reject,
    }


def _event(
    signer: Ed25519Signer, seq: int, prev: str, event_type: str, entity_id: str | None, payload: Any, created_at: str
) -> dict[str, Any]:
    ph = payload_hash(payload)
    eh = compute_event_hash(
        seq=seq,
        prev_hash=prev,
        actor_id=ACTOR_ID,
        event_type=event_type,
        entity_id=entity_id,
        payload_hash=ph,
        created_at=created_at,
    )
    return {
        "device_id": DEVICE_ID,
        "seq": seq,
        "prev_hash": prev,
        "event_hash": eh,
        "actor_id": ACTOR_ID,
        "event_type": event_type,
        "entity_id": entity_id,
        "payload": payload,
        "payload_hash": ph,
        "created_at": created_at,
        "device_sig": signer.sign(bytes.fromhex(eh)).hex(),
        "sig_alg": SIG_ALG_ED25519,
    }


def hash_chain_vectors() -> dict[str, Any]:
    signer = Ed25519Signer(bytes.fromhex(DEVICE_SEED))
    specs = [
        (
            "SESSION_STARTED",
            "01920000-0000-7000-8000-0000000005e1",
            {"site_id": "s-1", "kind": "DAVRIY", "ambient_temp_c": 21.5},
            "2026-10-26T07:00:00.000Z",
        ),
        (
            "MEASUREMENT_ADDED",
            "01920000-0000-7000-8000-00000000000e",
            {"type": "LOOP_IMPEDANCE", "values": {"pair": "L1-PE", "zs_ohm": 0.84}, "verdict": "PASS"},
            "2026-10-26T07:05:03.120Z",
        ),
        (
            "MEASUREMENT_ADDED",
            "01920000-0000-7000-8000-00000000000f",
            {
                "type": "INSULATION",
                "values": {"test_voltage_v": 1000, "pairs": [{"pair": "L1-PE", "mohm": 0.3}]},
                "verdict": "FAIL",
                "izoh": "Ўзбекча",
            },
            "2026-10-26T07:06:10.000Z",
        ),
        ("SETTINGS_CHANGED", None, {"k_corr": 0.8}, "2026-10-26T07:07:00.001Z"),
        (
            "PROTOCOL_REVOKED",
            "01920000-0000-7000-8000-0000000000b0",
            {"reason": "Xato asbob"},
            "2026-10-26T08:00:00.000Z",
        ),
    ]
    events = []
    prev = GENESIS_HASH
    for seq, (etype, entity, payload, created) in enumerate(specs, start=1):
        e = _event(signer, seq, prev, etype, entity, payload, created)
        events.append(e)
        prev = e["event_hash"]

    def as_events(raw: list[dict[str, Any]]) -> list[AuditEvent]:
        return [AuditEvent(**{k: v for k, v in e.items() if k != "payload"}) for e in raw]

    assert verify_chain(as_events(events), public_key_hex=signer.public_key_hex).ok
    flipped_sig = events[2]["device_sig"][:-2] + ("00" if events[2]["device_sig"][-2:] != "00" else "01")
    tamper = [
        {
            "name": "payload_hash o'zgargan",
            "op": "set",
            "index": 1,
            "field": "payload_hash",
            "value": sha256_hex(b"x"),
            "failed_index": 1,
            "reason": "event_hash_mismatch",
        },
        {
            "name": "event_hash boshqa",
            "op": "set",
            "index": 0,
            "field": "event_hash",
            "value": sha256_hex(b"y"),
            "failed_index": 0,
            "reason": "event_hash_mismatch",
        },
        {
            "name": "imzoning oxirgi bayti",
            "op": "set",
            "index": 2,
            "field": "device_sig",
            "value": flipped_sig,
            "failed_index": 2,
            "reason": "bad_signature",
        },
        {
            "name": "seq sakrashi",
            "op": "set",
            "index": 3,
            "field": "seq",
            "value": 5,
            "failed_index": 3,
            "reason": "seq_gap",
        },
        {
            "name": "prev_hash noto'g'ri",
            "op": "set",
            "index": 1,
            "field": "prev_hash",
            "value": GENESIS_HASH,
            "failed_index": 1,
            "reason": "prev_hash_mismatch",
        },
        {"name": "hodisa o'chirilgan", "op": "drop", "index": 1, "failed_index": 1, "reason": "seq_gap"},
        {
            "name": "aktor o'zgargan",
            "op": "set",
            "index": 4,
            "field": "actor_id",
            "value": "01920000-0000-7000-8000-0000000000a2",
            "failed_index": 4,
            "reason": "event_hash_mismatch",
        },
        {
            "name": "vaqt o'zgargan",
            "op": "set",
            "index": 0,
            "field": "created_at",
            "value": "2026-10-26T07:00:00.001Z",
            "failed_index": 0,
            "reason": "event_hash_mismatch",
        },
        {
            "name": "vaqt formati",
            "op": "set",
            "index": 0,
            "field": "created_at",
            "value": "2026-10-26T07:00:00Z",
            "failed_index": 0,
            "reason": "invalid_format",
        },
        {
            "name": "boshqa qurilma",
            "op": "set",
            "index": 2,
            "field": "device_id",
            "value": "01920000-0000-7000-8000-00000000d002",
            "failed_index": 2,
            "reason": "invalid_format",
        },
        {
            "name": "noma'lum algoritm",
            "op": "set",
            "index": 0,
            "field": "sig_alg",
            "value": "ML-DSA-65",
            "failed_index": 0,
            "reason": "unsupported_sig_alg",
        },
        {
            "name": "katta harfli hash",
            "op": "set",
            "index": 0,
            "field": "prev_hash",
            "value": "0" * 63 + "A",
            "failed_index": 0,
            "reason": "invalid_format",
        },
    ]
    for t in tamper:
        raw = [dict(e) for e in events]
        if t["op"] == "drop":
            del raw[t["index"]]
        else:
            raw[t["index"]][t["field"]] = t["value"]
        r = verify_chain(as_events(raw), public_key_hex=signer.public_key_hex)
        assert (r.ok, r.failed_index, r.reason) == (False, t["failed_index"], t["reason"]), (t["name"], r)
    anchored = verify_chain(as_events(events[2:]), public_key_hex=signer.public_key_hex, anchor=as_events(events)[1])
    assert anchored.ok
    return {
        "description": "Audit hash-zanjiri (prompt 5.4). event_hash = SHA256(canonical({seq, prev_hash, actor_id, event_type,"
        " entity_id, payload_hash, created_at})); device_sig = Ed25519(event_hash xom baytlari). payload — faqat payload_hash ni"
        " tekshirish uchun, zanjir maydoni emas.",
        "genesis_hash": GENESIS_HASH,
        "device_seed": DEVICE_SEED,
        "public_key": signer.public_key_hex,
        "events": events,
        "anchor_case": {"anchor_index": 1, "events_from": 2, "ok": True},
        "tamper": tamper,
    }


def protocol_vectors() -> dict[str, Any]:
    signer = Ed25519Signer(bytes.fromhex(DEVICE_SEED))
    payload = {
        "session": {
            "id": "01920000-0000-7000-8000-0000000005e1",
            "kind": "DAVRIY",
            "ambient_temp_c": 21.5,
            "humidity_pct": 60,
        },
        "site": {"name": "«Baraka» savdo markazi", "earthing_system": "TN-C-S", "u0_volts": 220},
        "norm_set_version": "0.1.0",
        "instruments": [
            {"serial_no": "MI3152-001", "verification_cert_no": "QV-2026/123", "verified_until": "2027-03-01"}
        ],
        "measurements": [
            {
                "id": "01920000-0000-7000-8000-00000000000e",
                "node": "SOCK1",
                "type": "LOOP_IMPEDANCE",
                "values": {"pair": "L1-PE", "zs_ohm": 0.84},
                "verdict": "PASS",
                "norm_id": "LOOP-TN-FINAL",
            },
            {
                "id": "01920000-0000-7000-8000-00000000000f",
                "node": "CAB1",
                "type": "INSULATION",
                "values": {"test_voltage_v": 1000, "pairs": [{"pair": "L1-PE", "mohm": 0.3}]},
                "verdict": "FAIL",
                "norm_id": "INS-WIRING",
            },
        ],
    }
    pdf = b"%PDF-1.7\n" + bytes(range(256)) + b"\n%%EOF\n"
    payload_sha = sha256_hex(canonical_json_bytes(payload))
    pdf_sha = sha256_hex(pdf)
    message = protocol_message(payload_sha, pdf_sha)
    return {
        "description": "Protokol imzosi (prompt 5.4): signature = Ed25519(payload_sha256 ‖ pdf_sha256), 32+32 xom bayt.",
        "public_key": signer.public_key_hex,
        "sig_alg": SIG_ALG_ED25519,
        "payload": payload,
        "payload_canonical": canonical_json(payload),
        "payload_sha256": payload_sha,
        "pdf_hex": pdf.hex(),
        "pdf_sha256": pdf_sha,
        "message_hex": message.hex(),
        "signature": signer.sign(message).hex(),
        "qr_token": qr_vector(signer),
    }


def qr_vector(signer: Ed25519Signer) -> dict[str, str]:
    org_id, number = "01920000-0000-7000-8000-0000000000a1", "2026-0005E1-001"
    message = qr_token_message(org_id, number)
    qr_sig = signer.sign(message).hex()
    return {
        "description": 'QR token (ADR-0014): qr_sig = Ed25519("zanjir.qr/1\\n<org_id>\\n<number>"), '
        "qr_token = sha256(qr_sig)[:32 hex]",
        "org_id": org_id,
        "number": number,
        "message_hex": message.hex(),
        "qr_sig": qr_sig,
        "qr_token": qr_token_from_signature(qr_sig),
    }


def main() -> int:
    check = "--check" in sys.argv[1:]
    outputs = {
        "canonical_json.json": canonical_vectors(),
        "ed25519.json": ed25519_vectors(),
        "hash_chain.json": hash_chain_vectors(),
        "protocol_signature.json": protocol_vectors(),
    }
    stale = []
    for name, data in outputs.items():
        text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        path = OUT / name
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.write_text(text, encoding="utf-8")
            print(f"{name}: yozildi")
    if stale:
        print("Eskirgan vektorlar: " + ", ".join(stale) + " — generate.py ni qayta ishga tushiring", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
