"""Kross-platforma test vektorlari (docs/sync-mqtt.md, 11-bo'lim). Mobil (Dart) testi aynan shu qiymatlarni tekshiradi."""

import base64

from omborai_desktop.sync.crypto import canonical_bytes, topic_for, verify_op
from omborai_desktop.sync.identity import DeviceIdentity

KEY = bytes(range(32))  # do'kon kaliti: 0x00..0x1f
SEED = bytes(range(32))  # qurilma kaliti seed: 0x00..0x1f
TOPIC = "omborai/v2/b562beb66f2a7f7fe4d0830bfd2f84c4/ops"
PUBLIC_KEY = "03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8"
CANONICAL = (
    '{"device":"11111111-1111-1111-1111-111111111111",'
    '"op_id":"00000000-0000-0000-0000-000000000001","payload":{"name":"Do\'kon"},'
    '"store_id":"22222222-2222-2222-2222-222222222222","ts":"2026-10-11T10:00:00.000000Z",'
    '"type":"store"}'
)
SIGNATURE = (
    "hMu8/t+NEx/0Bld56LCTZeGIcoW9kp7eDEBPyzyeUkcogppx//4i6zf4rv5BqiM/iuquDMhSz6NTcv3p55+kBA=="
)


def _op() -> dict:
    return {
        "op_id": "00000000-0000-0000-0000-000000000001",
        "type": "store",
        "device": "11111111-1111-1111-1111-111111111111",
        "ts": "2026-10-11T10:00:00.000000Z",
        "store_id": "22222222-2222-2222-2222-222222222222",
        "payload": {"name": "Do'kon"},
    }


def test_topic_vector():
    assert topic_for(KEY) == TOPIC


def test_public_key_vector():
    assert DeviceIdentity(SEED).public_key_hex == PUBLIC_KEY


def test_canonical_bytes_vector():
    assert canonical_bytes(_op()).decode("utf-8") == CANONICAL


def test_signature_vector_is_deterministic_and_verifies():
    op = _op()
    op["sig"] = base64.b64encode(DeviceIdentity(SEED).sign(canonical_bytes(op))).decode()
    assert op["sig"] == SIGNATURE
    assert verify_op(op, PUBLIC_KEY)
