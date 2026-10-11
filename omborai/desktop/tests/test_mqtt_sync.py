"""MQTT qatlami (protokol v2): konvert, mavzu, xabarlarni yo'naltirish va xatolarga chidamlilik (Y2)."""

import json
import os
import uuid
from types import SimpleNamespace

import pytest
from helpers import STORE_ID, Device, make_owner, product_op

from omborai_desktop.sync import crypto
from omborai_desktop.sync import ops as o
from omborai_desktop.sync.crypto import DecryptionError, open_envelope, seal, topic_for
from omborai_desktop.sync.mqtt_sync import MqttSync


def test_envelope_roundtrip_and_topic_binding():
    key = os.urandom(32)
    topic = topic_for(key)
    assert topic.startswith("omborai/v2/") and topic.endswith("/ops")
    message = {"hello": "dunyo", "n": 1}
    raw = seal(key, message, topic)
    assert json.loads(raw)["v"] == 2
    assert open_envelope(key, raw, topic) == message
    with pytest.raises(DecryptionError):
        open_envelope(key, raw, topic + "x")  # AAD: boshqa mavzu
    with pytest.raises(DecryptionError):
        open_envelope(os.urandom(32), raw, topic)  # boshqa kalit


def test_v1_envelope_is_rejected():
    key = os.urandom(32)
    topic = topic_for(key)
    raw = json.loads(seal(key, {"a": 1}, topic))
    raw["v"] = 1
    with pytest.raises(DecryptionError):
        open_envelope(key, json.dumps(raw).encode(), topic)


@pytest.mark.parametrize("junk", [b"[]", b'"x"', b"123", b"not json", b"{}"])
def test_malformed_payloads_raise_only_decryption_error(junk):
    """Y2: JSON ob'ekt bo'lmagan xabar ham DecryptionError bo'lishi kerak (thread o'lmasin)."""
    with pytest.raises(DecryptionError):
        open_envelope(os.urandom(32), junk, topic_for(os.urandom(32)))


def _sync(device_id: str, applied: list, requests: list, joins: list) -> MqttSync:
    key = bytes(range(32))
    return MqttSync(
        key,
        device_id=device_id,
        apply_op=lambda op: applied.append(op) or "applied",
        on_request=requests.append,
        on_join_request=joins.append,
        tls=False,
    )


def _message(sync: MqttSync, payload: dict, key: bytes = bytes(range(32))) -> SimpleNamespace:
    return SimpleNamespace(payload=seal(key, payload, sync.topic))


def test_dispatch_routes_requests_and_applies_others():
    applied, requests, joins = [], [], []
    sync = _sync(str(uuid.uuid4()), applied, requests, joins)
    base = {
        "op_id": str(uuid.uuid4()),
        "device": str(uuid.uuid4()),
        "ts": "2026-10-11T10:00:00.000000Z",
        "store_id": STORE_ID,
        "payload": {},
        "sig": "x",
    }
    sync._on_message(None, None, _message(sync, {**base, "type": o.PRODUCT}))
    sync._on_message(None, None, _message(sync, {**base, "type": o.SNAPSHOT_REQUEST}))
    sync._on_message(None, None, _message(sync, {**base, "type": o.JOIN_REQUEST}))
    assert [op["type"] for op in applied] == [o.PRODUCT]
    assert [op["type"] for op in requests] == [o.SNAPSHOT_REQUEST]
    assert [op["type"] for op in joins] == [o.JOIN_REQUEST]


def test_own_messages_are_ignored():
    applied = []
    own = str(uuid.uuid4())
    sync = _sync(own, applied, [], [])
    sync._on_message(None, None, _message(sync, {"type": o.PRODUCT, "device": own}))
    assert applied == []


def test_callback_exceptions_do_not_escape_the_mqtt_thread(caplog):
    """Y2: buzilgan xabar yoki ishlovchi xatosi paho thread'ini to'xtatmasligi kerak."""

    def boom(_op):
        raise RuntimeError("ichki xato")

    sync = MqttSync(bytes(range(32)), device_id="d", apply_op=boom, tls=False)
    sync._on_message(None, None, SimpleNamespace(payload=b"[]"))  # buzilgan
    sync._on_message(None, None, _message(sync, {"type": "x", "device": "other"}))  # ishlovchi xatosi
    assert "Xabarni qayta ishlashda xato" in caplog.text


def test_signed_product_op_passes_through_envelope_intact():
    owner = make_owner(3)
    op = product_op(owner, str(uuid.UUID(int=9)), 1000)
    key = bytes(range(32))
    back = open_envelope(key, seal(key, op, topic_for(key)), topic_for(key))
    assert crypto.verify_op(back, owner.identity.public_key_hex)
    assert back["device"] == owner.id


def test_device_helper_is_usable_with_sync_identity():
    device = Device(4)
    assert len(device.identity.public_key_hex) == 64
