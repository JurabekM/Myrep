import uuid
from decimal import Decimal
from typing import Any

import httpx
import pytest
from PySide6.QtWidgets import QDialog

from omborai_desktop.api import ApiError
from omborai_desktop.config import DesktopConfig
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
    def __init__(self, *, shift: dict | None = None, sale_error: Exception | None = None) -> None:
        self.shift = shift or {"id": str(uuid.uuid4()), "store_id": STORE_ID}
        self.sale_error = sale_error
        self.sales_posted: list[dict[str, Any]] = []

    def stores(self):
        return [{"id": STORE_ID, "name": "Test do'kon"}]

    def current_shift(self, store_id):
        return self.shift

    def product_by_barcode(self, code, store_id):
        return SUT if code == SUT["barcodes"][0] else None

    def search_products(self, query, store_id):
        return [SUT] if "sut" in query.lower() else []

    def create_sale(self, payload):
        self.sales_posted.append(payload)
        if self.sale_error is not None:
            raise self.sale_error
        return {
            "id": payload["id"],
            "number": 1042,
            "created_at": "2026-10-10T14:32:00",
            "subtotal": 24000,
            "discount": 0,
            "total": 24000,
            "items": [
                {
                    "product_name": "Sut 1 L",
                    "qty": "2",
                    "unit": "dona",
                    "unit_price": 12000,
                    "line_total": 24000,
                }
            ],
            "payments": [{"method": "cash", "amount": 24000}],
        }


@pytest.fixture
def no_blocking_dialogs(monkeypatch):
    """Modal dialoglar testda bloklamasin: javobni oldindan belgilaymiz."""
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


def _window(qtbot, api):
    window = mw.PosWindow(api, DesktopConfig(), runner=SyncRunner())
    qtbot.addWidget(window)
    window.start()
    return window


def test_start_loads_store_and_open_shift(qtbot):
    api = FakeApi()
    window = _window(qtbot, api)
    assert window.store["id"] == STORE_ID
    assert window.shift is not None
    assert "ochiq" in window.shift_label.text()


def test_barcode_scan_adds_product_and_quantity_edit_updates_total(qtbot):
    window = _window(qtbot, FakeApi())
    window.search.setText("4780012300123")
    window._on_search_submitted()  # noqa: SLF001 - Enter bosilgan holat
    window.search.setText("4780012300123")
    window._on_search_submitted()  # noqa: SLF001

    assert len(window.cart.lines) == 1
    assert window.cart.lines[0].qty == Decimal(2)
    assert window.cart.total == 24000

    window.table.item(0, 1).setText("3")
    assert window.cart.total == 36000


def test_unknown_barcode_is_reported_not_added(qtbot):
    window = _window(qtbot, FakeApi())
    window.search.setText("9999999999999")
    window._on_search_submitted()  # noqa: SLF001
    assert window.cart.is_empty


def test_successful_payment_posts_sale_once_and_clears_cart(qtbot, no_blocking_dialogs):
    api = FakeApi()
    window = _window(qtbot, api)
    window.search.setText("4780012300123")
    window._on_search_submitted()  # noqa: SLF001
    window.search.setText("4780012300123")
    window._on_search_submitted()  # noqa: SLF001

    window.pay()

    assert len(api.sales_posted) == 1
    posted = api.sales_posted[0]
    assert posted["payments"] == [{"method": "cash", "amount": 24000}]
    assert "unit_price" not in str(posted)
    assert window.cart.is_empty
    assert window._pending is None  # noqa: SLF001
    assert len(no_blocking_dialogs) == 1
    assert "Chek #1042" in no_blocking_dialogs[0]


def test_server_rejection_keeps_cart_and_drops_pending(qtbot, monkeypatch, no_blocking_dialogs):
    api = FakeApi(sale_error=ApiError(409, "Qoldiq yetarli emas"))
    window = _window(qtbot, api)
    window.search.setText("4780012300123")
    window._on_search_submitted()  # noqa: SLF001

    window.pay()

    assert not window.cart.is_empty
    assert window._pending is None  # noqa: SLF001


def test_network_failure_queues_sale_offline_with_same_id(qtbot, no_blocking_dialogs):
    class Offline(FakeApi):
        def create_sale(self, payload):
            self.sales_posted.append(payload)
            raise httpx.ConnectError("uzildi")

    api = Offline()
    window = _window(qtbot, api)
    window.search.setText("4780012300123")
    window._on_search_submitted()  # noqa: SLF001

    window.pay()

    assert window._pending is None  # noqa: SLF001
    assert window.cart.is_empty
    queued = window.local.pending_ops()
    assert len(queued) == 1
    assert queued[0].op_id == api.sales_posted[0]["id"]
    assert window.local.pending_count() == 1


def test_offline_sale_is_pushed_by_sync_and_leaves_outbox(qtbot, no_blocking_dialogs):
    class Recovering(FakeApi):
        def __init__(self):
            super().__init__()
            self.online = False

        def create_sale(self, payload):
            if not self.online:
                raise httpx.ConnectError("uzildi")
            return super().create_sale(payload)

        def sync_push(self, body):
            return {
                "results": [
                    {"op_id": op["op_id"], "status": "applied", "duplicate": False} for op in body["ops"]
                ]
            }

        def sync_pull(self, store_id, cursors, limit=200):
            return {"products": [], "movements": [], "sales": [], "cursors": cursors, "has_more": False}

    api = Recovering()
    window = _window(qtbot, api)
    window.search.setText("4780012300123")
    window._on_search_submitted()  # noqa: SLF001
    window.pay()
    assert window.local.pending_count() == 1

    api.online = True
    window.sync_now()

    assert window.local.pending_count() == 0
    assert "navbatda" not in window.sync_label.text()


def test_offline_search_uses_local_cache(qtbot):
    class Down(FakeApi):
        def search_products(self, query, store_id):
            raise httpx.ConnectError("yo'q")

    window = _window(qtbot, Down())
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
