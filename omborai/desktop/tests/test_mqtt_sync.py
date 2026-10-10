import shutil
import socket
import subprocess
import time
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

from omborai_desktop.offline.store import LocalStore
from omborai_desktop.sync.crypto import DecryptionError, generate_store_key, open_envelope, seal, topic_for
from omborai_desktop.sync.mqtt_sync import MqttSync

STORE = str(uuid.uuid4())
PRODUCT = str(uuid.uuid4())


def _sale(op_id: str, qty: str) -> dict:
    return {
        "op_id": op_id,
        "type": "sale",
        "device": "dev-a",
        "ts": "2026-10-10T10:00:00+00:00",
        "store_id": STORE,
        "payload": {"items": [{"product_id": PRODUCT, "qty": qty}]},
    }


# --- shifrlash ----------------------------------------------------------------


def test_roundtrip_and_no_plaintext_on_wire():
    key = generate_store_key()
    topic = topic_for(key)
    raw = seal(key, {"secret": "Maxfiy-savdo-42"}, topic)
    assert b"Maxfiy-savdo-42" not in raw
    assert open_envelope(key, raw, topic) == {"secret": "Maxfiy-savdo-42"}


def test_wrong_key_wrong_topic_or_tampering_is_rejected():
    key, other = generate_store_key(), generate_store_key()
    topic = topic_for(key)
    raw = seal(key, {"a": 1}, topic)
    with pytest.raises(DecryptionError):
        open_envelope(other, raw, topic_for(other))
    with pytest.raises(DecryptionError):
        open_envelope(key, raw, topic + "x")  # AAD mos emas
    tampered = raw.replace(b'"c": "', b'"c": "A')
    with pytest.raises(DecryptionError):
        open_envelope(key, tampered, topic)


def test_topic_is_deterministic_and_unrelated_to_key_bytes():
    key = generate_store_key()
    assert topic_for(key) == topic_for(key)
    assert key.hex() not in topic_for(key)
    assert topic_for(key) != topic_for(generate_store_key())


def test_key_length_enforced():
    with pytest.raises(ValueError):
        topic_for(b"short")


# --- qo'llash (dedupe) --------------------------------------------------------


def test_sale_op_reduces_stock_once_even_if_delivered_twice():
    store = LocalStore()
    store.apply_pull(
        {
            "products": [
                {"id": PRODUCT, "name": "Shakar", "unit": "kg", "sale_price": 14500, "barcodes": []}
            ],
            "movements": [
                {"id": "m1", "store_id": STORE, "product_id": PRODUCT, "qty": "10", "kind": "receipt"}
            ],
            "cursors": {},
            "has_more": False,
        }
    )
    op = _sale(str(uuid.uuid4()), "3")
    assert store.apply_op(op) is True
    assert store.apply_op(op) is False
    assert store.balance(STORE, PRODUCT) == Decimal(7)
    store.close()


def test_refund_and_movement_and_product_ops():
    store = LocalStore()
    sale = _sale(str(uuid.uuid4()), "2")
    store.apply_op(sale)
    store.apply_op(
        {
            "op_id": str(uuid.uuid4()),
            "type": "refund",
            "device": "dev-a",
            "ts": "t",
            "store_id": STORE,
            "payload": {"items": [{"product_id": PRODUCT, "qty": "2"}]},
        }
    )
    assert store.balance(STORE, PRODUCT) == Decimal(0)
    store.apply_op(
        {
            "op_id": str(uuid.uuid4()),
            "type": "movement",
            "device": "dev-a",
            "ts": "t",
            "store_id": STORE,
            "payload": {"product_id": PRODUCT, "kind": "adjustment", "qty": "5"},
        }
    )
    assert store.balance(STORE, PRODUCT) == Decimal(5)
    store.apply_op(
        {
            "op_id": str(uuid.uuid4()),
            "type": "product",
            "device": "dev-a",
            "ts": "t",
            "store_id": STORE,
            "payload": {"id": PRODUCT, "name": "Shakar 2", "unit": "kg", "sale_price": 15000},
        }
    )
    assert store.product_by_barcode("x", STORE) is None
    assert store.search_products("shakar 2", STORE)[0]["sale_price"] == 15000
    store.close()


# --- haqiqiy broker (lokal Mosquitto) -----------------------------------------

MOSQUITTO = shutil.which("mosquitto")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def broker(tmp_path: Path):
    if MOSQUITTO is None:
        pytest.skip("mosquitto o'rnatilmagan")
    port = _free_port()
    conf = tmp_path / "mosquitto.conf"
    conf.write_text(f"listener {port} 127.0.0.1\nallow_anonymous true\npersistence false\n")
    proc = subprocess.Popen(  # noqa: S603 - sinov uchun o'rnatilgan mosquitto
        [MOSQUITTO, "-c", str(conf)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(0.5)
    yield port
    proc.terminate()
    proc.wait(timeout=5)


def _device(key: bytes, device_id: str, store: LocalStore, port: int) -> MqttSync:
    return MqttSync(
        key,
        device_id=device_id,
        apply_op=store.apply_op,
        host="127.0.0.1",
        port=port,
        tls=False,
    )


def _wait_until(predicate, timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_two_devices_share_sales_through_broker(broker):
    key = generate_store_key()
    store_a, store_b = LocalStore(), LocalStore()
    for store in (store_a, store_b):
        store.apply_pull(
            {
                "products": [
                    {"id": PRODUCT, "name": "Shakar", "unit": "kg", "sale_price": 14500, "barcodes": []}
                ],
                "movements": [
                    {"id": "m1", "store_id": STORE, "product_id": PRODUCT, "qty": "10", "kind": "receipt"}
                ],
                "cursors": {},
                "has_more": False,
            }
        )
    dev_a = _device(key, "dev-a", store_a, broker)
    dev_b = _device(key, "dev-b", store_b, broker)
    dev_a.start()
    dev_b.start()
    try:
        op = dev_a.publish("sale", STORE, {"items": [{"product_id": PRODUCT, "qty": "3"}]})
        store_a.apply_op(op)  # o'z operatsiyasini mahalliy qo'llash
        assert _wait_until(lambda: store_b.balance(STORE, PRODUCT) == Decimal(7))
        assert store_a.balance(STORE, PRODUCT) == Decimal(7)  # o'z xabari qaytganda dublikat bo'lmaydi
        time.sleep(0.5)
        assert store_a.balance(STORE, PRODUCT) == Decimal(7)
        assert store_b.balance(STORE, PRODUCT) == Decimal(7)
    finally:
        dev_a.stop()
        dev_b.stop()
        store_a.close()
        store_b.close()


def test_device_with_other_key_sees_nothing(broker):
    key, intruder_key = generate_store_key(), generate_store_key()
    store_a, store_x = LocalStore(), LocalStore()
    store_x.apply_pull(
        {
            "products": [{"id": PRODUCT, "name": "Shakar", "unit": "kg", "sale_price": 1, "barcodes": []}],
            "movements": [
                {"id": "m1", "store_id": STORE, "product_id": PRODUCT, "qty": "10", "kind": "receipt"}
            ],
            "cursors": {},
            "has_more": False,
        }
    )
    dev_a = _device(key, "dev-a", store_a, broker)
    spy = _device(intruder_key, "spy", store_x, broker)
    dev_a.start()
    spy.start()
    try:
        dev_a.publish("sale", STORE, {"items": [{"product_id": PRODUCT, "qty": "4"}]})
        time.sleep(1.0)
        assert store_x.balance(STORE, PRODUCT) == Decimal(10)
    finally:
        dev_a.stop()
        spy.stop()
        store_a.close()
        store_x.close()
