import uuid
from decimal import Decimal
from typing import Any

import pytest
from PySide6.QtWidgets import QDialog

from omborai_desktop.config import DesktopConfig
from omborai_desktop.offline.store import LocalStore
from omborai_desktop.sync import ops as o
from omborai_desktop.ui import main_window as mw
from omborai_desktop.ui.tasks import SyncRunner

STORE_ID = str(uuid.uuid4())
SUT_ID = str(uuid.uuid4())


class FakeApi:
    def stores(self):
        return [{"id": STORE_ID, "name": "Test do'kon"}]


class FakeMqtt:
    def __init__(self) -> None:
        self.connected = True
        self.sent: list[dict[str, Any]] = []
        self.on_request = None

    def start(self, timeout: float = 10.0) -> None:
        return None

    def stop(self) -> None:
        return None

    def send(self, op: dict[str, Any]) -> None:
        if not self.connected:
            raise ConnectionError("broker yo'q")
        self.sent.append(op)


@pytest.fixture
def dialogs(monkeypatch):
    shown: list[str] = []
    warnings: list[str] = []

    class FakeReceipt:
        print_requested = False

        def __init__(self, text, *, can_print, parent=None):
            shown.append(text)

        def exec(self):
            return QDialog.DialogCode.Rejected

    class FakePayment:
        method = "cash"
        change = 0

        def __init__(self, total, parent=None):
            self.total = total

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(mw, "ReceiptDialog", FakeReceipt)
    monkeypatch.setattr(mw, "PaymentDialog", FakePayment)
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda _p, _t, text, *a, **k: warnings.append(text))
    monkeypatch.setattr(mw.QMessageBox, "information", lambda *a, **k: None)
    return shown, warnings


def _window(qtbot, local=None, mqtt=None):
    window = mw.PosWindow(
        FakeApi(), DesktopConfig(), runner=SyncRunner(), local=local or LocalStore(), mqtt=mqtt or FakeMqtt()
    )
    qtbot.addWidget(window)
    window.start()
    return window


def _seed_catalog(window, qty="10"):
    device = window.local.device_id()
    window.local.apply_op(
        o.new_op(
            o.PRODUCT,
            STORE_ID,
            {
                "id": SUT_ID,
                "name": "Sut 1 L",
                "unit": "dona",
                "sale_price": 12000,
                "barcodes": ["4780012300123"],
            },
            device_id=device,
        )
    )
    window.local.apply_op(
        o.new_op(
            o.MOVEMENT,
            STORE_ID,
            {
                "product_id": SUT_ID,
                "kind": "receipt",
                "qty": qty,
            },
            device_id=device,
        )
    )


def _scan(window, code="4780012300123", times=2):
    for _ in range(times):
        window.search.setText(code)
        window._on_search_submitted()  # noqa: SLF001


def test_store_is_loaded_and_remembered(qtbot):
    window = _window(qtbot)
    assert window.store["id"] == STORE_ID
    assert window.local.get_state("store_id") == STORE_ID


def test_sale_requires_open_shift(qtbot, dialogs):
    _, warnings = dialogs
    window = _window(qtbot)
    _seed_catalog(window)
    _scan(window)
    window.pay()
    assert warnings == ["Avval smenani oching."]
    assert not any(op["type"] == o.SALE for op in window.mqtt.sent)


def test_sale_publishes_priced_op_and_reduces_local_stock(qtbot, dialogs):
    window = _window(qtbot)
    _seed_catalog(window)
    window.open_shift(0)
    _scan(window)
    window.pay()

    sales = [op for op in window.mqtt.sent if op["type"] == o.SALE]
    assert len(sales) == 1
    payload = sales[0]["payload"]
    assert payload["items"][0]["unit_price"] == 12000
    assert payload["shift_id"] == window.local.open_shift(STORE_ID)["id"]
    assert window.local.balance(STORE_ID, SUT_ID) == Decimal(8)
    assert window.cart.is_empty


def test_insufficient_stock_blocks_sale_before_publishing(qtbot, dialogs):
    _, warnings = dialogs
    window = _window(qtbot)
    _seed_catalog(window, qty="1")
    window.open_shift(0)
    _scan(window, times=1)
    window.table.item(0, 1).setText("3")
    window.pay()
    assert warnings and warnings[0].startswith("«Sut 1 L»")
    assert not any(op["type"] == o.SALE for op in window.mqtt.sent)


def test_offline_sale_is_queued_then_published_on_reconnect(qtbot, dialogs):
    mqtt = FakeMqtt()
    mqtt.connected = False
    window = _window(qtbot, mqtt=mqtt)
    _seed_catalog(window)
    window.open_shift(0)
    _scan(window)
    window.pay()
    assert window.local.pending_count() >= 1
    queued_sales = [op for op in window.local.pending_ops() if op["type"] == o.SALE]
    assert len(queued_sales) == 1

    mqtt.connected = True
    window._refresh_sync_state()  # noqa: SLF001 - ulanish tiklandi
    assert [op["op_id"] for op in mqtt.sent if op["type"] == o.SALE] == [queued_sales[0]["op_id"]]
    assert window.local.pending_count() == 0


def test_refund_publishes_deterministic_op_once(qtbot, dialogs):
    window = _window(qtbot)
    _seed_catalog(window)
    window.open_shift(0)
    _scan(window)
    window.pay()
    sale_id = next(op["op_id"] for op in window.mqtt.sent if op["type"] == o.SALE)

    assert window.refund_sale(sale_id) is True
    refunds = [op for op in window.mqtt.sent if op["type"] == o.REFUND]
    assert refunds[0]["op_id"] == o.refund_op_id(sale_id)
    assert window.local.get_sale(sale_id)["status"] == "refunded"
    assert window.local.balance(STORE_ID, SUT_ID) == Decimal(10)
    assert window.refund_sale(sale_id) is False  # ikkinchi marta qaytarib bo'lmaydi


def test_shift_close_publishes_summary_and_clears_open_shift(qtbot, dialogs):
    window = _window(qtbot)
    _seed_catalog(window)
    window.open_shift(1000)
    _scan(window)
    window.pay()
    summary = window.close_shift(13000)
    assert summary["sales_count"] == 1
    assert window.local.open_shift(STORE_ID) is None
    closes = [op for op in window.mqtt.sent if op["type"] == o.SHIFT_CLOSE]
    assert closes[0]["payload"]["summary"]["by_method"] == {"cash": 24000}


def test_catalog_add_edit_delete_are_operations(qtbot, dialogs):
    window = _window(qtbot)
    new_id = str(uuid.uuid4())
    window.save_product(
        {
            "id": new_id,
            "name": "Choy",
            "unit": "quti",
            "sale_price": 22000,
            "cost_price": 15000,
            "min_stock": "2",
            "barcodes": ["4780012300031"],
            "deleted": False,
        }
    )
    assert window.local.get_product(new_id, STORE_ID)["name"] == "Choy"

    window.save_product(
        {
            "id": new_id,
            "name": "Choy premium",
            "unit": "quti",
            "sale_price": 25000,
            "cost_price": 15000,
            "min_stock": "2",
            "barcodes": ["4780012300031"],
            "deleted": False,
        }
    )
    assert window.local.get_product(new_id, STORE_ID)["sale_price"] == 25000

    window.delete_product(window.local.get_product(new_id, STORE_ID))
    assert window.local.get_product(new_id, STORE_ID) is None
    catalog_ops = [op["type"] for op in window.mqtt.sent if op["type"] != o.SNAPSHOT_REQUEST]
    assert catalog_ops == [o.PRODUCT, o.PRODUCT, o.PRODUCT]


def test_fresh_device_requests_snapshot_and_peer_answers(qtbot, dialogs):
    mqtt = FakeMqtt()
    window = _window(qtbot, mqtt=mqtt)
    window._refresh_sync_state()  # noqa: SLF001 - bo'sh qurilma
    requests = [op for op in mqtt.sent if op["type"] == o.SNAPSHOT_REQUEST]
    assert len(requests) == 1

    other = _window(qtbot, mqtt=FakeMqtt())
    _seed_catalog(other)
    other._on_snapshot_requested(requests[0])  # noqa: SLF001 - boshqa qurilma javob beradi
    snaps = [op for op in other.mqtt.sent if op["type"] == o.SNAPSHOT]
    assert len(snaps) == 1
    assert snaps[0]["payload"]["balances"] == {SUT_ID: "10"}
