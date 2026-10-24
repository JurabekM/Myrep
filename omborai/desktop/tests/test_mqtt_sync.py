import shutil
import socket
import subprocess
import threading
import time
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

from omborai_desktop.offline.store import LocalStore
from omborai_desktop.sync import ops as o
from omborai_desktop.sync.crypto import DecryptionError, generate_store_key, open_envelope, seal, topic_for
from omborai_desktop.sync.mqtt_sync import MqttSync

STORE = str(uuid.uuid4())
PRODUCT = str(uuid.uuid4())


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
        open_envelope(key, raw, topic + "x")
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
    # Sinov uchun o'rnatilgan mosquitto (foydalanuvchi kiritmasi emas)
    proc = subprocess.Popen(  # noqa: S603
        [MOSQUITTO, "-c", str(conf)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(0.5)
    yield port
    proc.terminate()
    proc.wait(timeout=5)


def _device(key: bytes, device_id: str, store: LocalStore, port: int, **kw) -> MqttSync:
    return MqttSync(
        key, device_id=device_id, apply_op=store.apply_op, host="127.0.0.1", port=port, tls=False, **kw
    )


def _wait_until(predicate, timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def _catalog_op(device: str) -> dict:
    return o.new_op(
        o.PRODUCT,
        STORE,
        {"id": PRODUCT, "name": "Shakar", "unit": "kg", "sale_price": 14500, "barcodes": []},
        device_id=device,
    )


def _receipt_op(device: str, qty: str) -> dict:
    return o.new_op(
        o.MOVEMENT, STORE, {"product_id": PRODUCT, "kind": "receipt", "qty": qty}, device_id=device
    )


def test_two_devices_share_sales_through_broker(broker):
    key = generate_store_key()
    store_a, store_b = LocalStore(), LocalStore()
    dev_a = _device(key, "dev-a", store_a, broker)
    dev_b = _device(key, "dev-b", store_b, broker)
    dev_a.start()
    dev_b.start()
    try:
        for op in (_catalog_op("dev-a"), _receipt_op("dev-a", "10")):
            store_a.apply_op(op)
            dev_a.send(op)
        assert _wait_until(lambda: store_b.balance(STORE, PRODUCT) == Decimal(10))

        shift = o.new_op(
            o.SHIFT_OPEN, STORE, {"shift_id": "sh1", "opening_cash": 0}, device_id="dev-a", op_id="sh1"
        )
        store_a.apply_op(shift)
        dev_a.send(shift)
        assert _wait_until(lambda: store_b.open_shift(STORE) is not None)

        sale_id = str(uuid.uuid4())
        sale = o.new_op(
            o.SALE,
            STORE,
            {
                "id": sale_id,
                "shift_id": "sh1",
                "number": "dev-a-1",
                "created_at": "t",
                "total": 43500,
                "items": [{"product_id": PRODUCT, "qty": "3"}],
                "payments": [],
            },
            device_id="dev-a",
            op_id=sale_id,
        )
        store_a.apply_op(sale)
        dev_a.send(sale)
        assert _wait_until(lambda: store_b.balance(STORE, PRODUCT) == Decimal(7))
        time.sleep(0.5)
        assert store_a.balance(STORE, PRODUCT) == Decimal(7)  # o'z xabari qaytganda ikki marta hisoblanmaydi
        assert store_b.balance(STORE, PRODUCT) == Decimal(7)
    finally:
        dev_a.stop()
        dev_b.stop()
        store_a.close()
        store_b.close()


def test_device_with_other_key_sees_nothing(broker):
    key, intruder_key = generate_store_key(), generate_store_key()
    store_a, store_x = LocalStore(), LocalStore()
    dev_a = _device(key, "dev-a", store_a, broker)
    spy = _device(intruder_key, "spy", store_x, broker)
    dev_a.start()
    spy.start()
    try:
        dev_a.send(_catalog_op("dev-a"))
        dev_a.send(_receipt_op("dev-a", "10"))
        time.sleep(1.0)
        assert store_x.balance(STORE, PRODUCT) == Decimal(0)
        assert store_x.applied_count() == 0
    finally:
        dev_a.stop()
        spy.stop()
        store_a.close()
        store_x.close()


def test_new_device_bootstraps_from_peer_snapshot(broker):
    key = generate_store_key()
    store_a, store_new = LocalStore(), LocalStore()
    store_a.apply_op(_catalog_op("dev-a"))
    store_a.apply_op(_receipt_op("dev-a", "6"))

    def answer(request):
        # Javob bu yerda alohida oqimda yuboriladi (paho callback ichida kutish deadlock beradi)
        snap = o.new_op(o.SNAPSHOT, STORE, store_a.snapshot_payload(STORE), device_id="dev-a")
        threading.Thread(target=dev_a.send, args=(snap,), daemon=True).start()

    dev_a = _device(key, "dev-a", store_a, broker, on_request=answer)
    dev_new = _device(key, "dev-new", store_new, broker)
    dev_a.start()
    dev_new.start()
    try:
        dev_new.send(o.new_op(o.SNAPSHOT_REQUEST, STORE, {}, device_id="dev-new"))
        assert _wait_until(lambda: store_new.balance(STORE, PRODUCT) == Decimal(6))
        assert store_new.get_product(PRODUCT, STORE)["name"] == "Shakar"
    finally:
        dev_a.stop()
        dev_new.stop()
        store_a.close()
        store_new.close()
