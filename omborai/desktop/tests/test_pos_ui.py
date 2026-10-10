import uuid
from decimal import Decimal
from typing import Any

import pytest
from PySide6.QtWidgets import QDialog

from omborai_desktop.config import DesktopConfig
from omborai_desktop.offline.store import LocalStore
from omborai_desktop.ui import main_window as mw
from omborai_desktop.ui.tasks import SyncRunner

STORE_ID = str(uuid.uuid4())
SUT_ID = str(uuid.uuid4())
SUT = {
    "id": SUT_ID,
    "name": "Sut 1 L",
    "unit": "dona",
    "sale_price": 12000,
    "stock_qty": "10.000",
    "barcodes": ["4780012300123"],
}


class FakeApi:
    """Faqat do'kon, smena, tovar qidiruvi va barcode uchun (savdo endi MQTT orqali)."""

    def __init__(self) -> None:
        self.shift: dict | None = {"id": str(uuid.uuid4()), "store_id": STORE_ID}

    def stores(self):
        return [{"id": STORE_ID, "name": "Test do'kon"}]

    def current_shift(self, store_id):
        return self.shift

    def product_by_barcode(self, code, store_id):
        return SUT if code == SUT["barcodes"][0] else None

    def search_products(self, query, store_id):
        return [SUT] if "sut" in query.lower() else []


class FakeMqtt:
    """MqttSync o'rnida: nashr qilingan operatsiyalarni yozib boradi."""

    def __init__(self) -> None:
        self.connected = True
        self.published: list[dict[str, Any]] = []
        self.fail_next = False

    def start(self, timeout: float = 10.0) -> None:
        return None

    def stop(self) -> None:
        return None

    def publish(self, op_type, store_id, payload, *, op_id=None):
        if not self.connected or self.fail_next:
            self.fail_next = False
            raise ConnectionError("broker yo'q")
        op = {"op_id": op_id or str(uuid.uuid4()), "type": op_type, "store_id": store_id, "payload": payload}
        self.published.append(op)
        return op


@pytest.fixture
def no_blocking_dialogs(monkeypatch):
    """Modal dialoglar testda bloklamasin."""
    shown: list[str] = []

    class FakeReceipt:
        print_requested = False

        def __init__(self, text, *, can_print, parent=None):
            shown.append(text)

        def exec(self):
            return QDialog.DialogCode.Rejected

    class FakePayment:
        method = "cash"
        change = 1000

        def __init__(self, total, parent=None):
            self.total = total

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(mw, "ReceiptDialog", FakeReceipt)
    monkeypatch.setattr(mw, "PaymentDialog", FakePayment)
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(mw.QMessageBox, "information", lambda *a, **k: None)
    return shown


def _window(qtbot, api=None, mqtt=None, local=None):
    window = mw.PosWindow(
        api or FakeApi(),
        DesktopConfig(),
        runner=SyncRunner(),
        local=local or LocalStore(),
        mqtt=mqtt or FakeMqtt(),
    )
    qtbot.addWidget(window)
    window.start()
    return window


def _scan_and_pay(window):
    window.search.setText("4780012300123")
    window._on_search_submitted()  # noqa: SLF001
    window.search.setText("4780012300123")
    window._on_search_submitted()  # noqa: SLF001
    window.pay()


def test_start_loads_store_and_open_shift(qtbot):
    window = _window(qtbot)
    assert window.store["id"] == STORE_ID
    assert window.shift is not None
    assert "ochiq" in window.shift_label.text()


def test_barcode_scan_adds_product_and_quantity_edit_updates_total(qtbot):
    window = _window(qtbot)
    window.search.setText("4780012300123")
    window._on_search_submitted()  # noqa: SLF001
    window.search.setText("4780012300123")
    window._on_search_submitted()  # noqa: SLF001

    assert len(window.cart.lines) == 1
    assert window.cart.lines[0].qty == Decimal(2)
    assert window.cart.total == 24000

    window.table.item(0, 1).setText("3")
    assert window.cart.total == 36000


def test_unknown_barcode_is_reported_not_added(qtbot):
    window = _window(qtbot)
    window.search.setText("9999999999999")
    window._on_search_submitted()  # noqa: SLF001
    assert window.cart.is_empty


def test_successful_payment_publishes_sale_over_mqtt_and_applies_locally(qtbot, no_blocking_dialogs):
    mqtt = FakeMqtt()
    local = LocalStore()
    window = _window(qtbot, mqtt=mqtt, local=local)
    _scan_and_pay(window)

    assert len(mqtt.published) == 1
    op = mqtt.published[0]
    assert op["type"] == "sale"
    assert op["payload"]["payments"] == [{"method": "cash", "amount": 24000}]
    assert op["payload"]["items"][0]["unit_price"] == 12000  # narx qurilmada hisoblanadi
    assert window.cart.is_empty
    assert window.local.pending_count() == 0
    assert len(no_blocking_dialogs) == 1
    assert "Chek #1" in no_blocking_dialogs[0]


def test_publish_failure_queues_sale_with_same_id_and_flushes_later(qtbot, no_blocking_dialogs):
    mqtt = FakeMqtt()
    mqtt.connected = False
    window = _window(qtbot, mqtt=mqtt)
    _scan_and_pay(window)

    assert window.cart.is_empty
    queued = window.local.pending_ops()
    assert len(queued) == 1
    sale_id = queued[0].op_id

    mqtt.connected = True
    window._refresh_sync_state()  # noqa: SLF001 - ulanish tiklandi
    assert [op["op_id"] for op in mqtt.published] == [sale_id]
    assert window.local.pending_count() == 0


def test_sale_is_not_double_applied_if_broker_ack_was_lost(qtbot, no_blocking_dialogs):
    class AckLost(FakeMqtt):
        def publish(self, op_type, store_id, payload, *, op_id=None):
            op = super().publish(op_type, store_id, payload, op_id=op_id)
            if len(self.published) == 1:
                raise ConnectionError("ack yetmadi")  # xabar yetib bordi, lekin javob kelmadi
            return op

    mqtt = AckLost()
    local = LocalStore()
    window = _window(qtbot, mqtt=mqtt, local=local)
    _scan_and_pay(window)
    assert window.local.pending_count() == 1

    window._refresh_sync_state()  # noqa: SLF001 - qayta yuborish
    # Bir xil op_id ikki marta nashr qilindi, lekin qo'llanish bir marta
    assert [op["op_id"] for op in mqtt.published] == [mqtt.published[0]["op_id"]] * 2
    assert window.local.balance(STORE_ID, SUT_ID) == Decimal(-2)
    local.close()


def test_offline_search_uses_local_cache(qtbot):
    class Down(FakeApi):
        def search_products(self, query, store_id):
            import httpx

            raise httpx.ConnectError("yo'q")

    window = _window(qtbot, api=Down())
    window.local.upsert_products(
        [
            {
                "id": SUT_ID,
                "name": "Sut 1 L",
                "unit": "dona",
                "sale_price": 12000,
                "barcodes": ["4780012300123"],
            }
        ]
    )
    window.search.setText("sut")
    window._on_search_submitted()  # noqa: SLF001
    assert window.results.count() == 1


def test_mqtt_status_label_reflects_connection(qtbot):
    mqtt = FakeMqtt()
    window = _window(qtbot, mqtt=mqtt)
    window._refresh_sync_state()  # noqa: SLF001
    assert "MQTT ulangan" in window.sync_label.text()
    mqtt.connected = False
    window._refresh_sync_state()  # noqa: SLF001
    assert "MQTT uzilgan" in window.sync_label.text()
