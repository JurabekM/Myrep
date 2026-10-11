"""Kassa oynasi (PosWindow) GUI testlari: har bir tugma bosilib tekshiriladi (qoida: tugma ishlasin yoki o'chiq)."""

from decimal import Decimal

import pytest
from helpers import STORE_ID, Device, bootstrapped_pair, make_owner, movement_op, product_op, shift_open_op
from PySide6.QtWidgets import QDialog

from omborai_desktop.config import DesktopConfig
from omborai_desktop.offline.store import APPLIED, REJECTED
from omborai_desktop.sync import crypto
from omborai_desktop.sync import ops as o
from omborai_desktop.ui import main_window as mw
from omborai_desktop.ui.tasks import SyncRunner

PID = "00000000-0000-0000-0000-00000000abcd"


class FakeMqtt:
    def __init__(self, connected: bool = True) -> None:
        self.connected = connected
        self.sent: list[dict] = []
        self.on_request = None
        self.on_join_request = None

    def start(self, timeout: float = 10.0) -> None:
        self.connected = True

    def stop(self) -> None:
        self.connected = False

    def send(self, op: dict) -> None:
        if not self.connected:
            raise ConnectionError("broker yo'q")
        self.sent.append(op)

    def types(self) -> list[str]:
        return [op["type"] for op in self.sent]


@pytest.fixture
def ui(monkeypatch):
    """Dialoglar va xabarlar soxtalashtirilgan: testda modal oyna ochilmaydi, javoblar yozib olinadi."""
    log = {
        "warn": [],
        "info": [],
        "payment": 0,
        "receipt": 0,
        "products": 0,
        "users": 0,
        "open_cash": None,
        "close_cash": None,
        "ask_join": [],
        "join_answer": o.ROLE_CASHIER,
    }

    class FakePayment:
        method = "cash"
        change = 0

        def __init__(self, total, parent=None):
            self.total = total

        def exec(self):
            log["payment"] += 1
            return QDialog.DialogCode.Accepted

    class FakeReceipt:
        print_requested = False

        def __init__(self, text, *, can_print, parent=None):
            pass

        def exec(self):
            log["receipt"] += 1
            return QDialog.DialogCode.Rejected

    class FakeOpenShift:
        def __init__(self, parent=None):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def opening_cash(self):
            return 5000

    class FakeCloseShift:
        def __init__(self, parent=None):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def closing_cash(self):
            return 5000

    class FakeProducts:
        def __init__(self, **kwargs):
            pass

        def exec(self):
            log["products"] += 1
            return QDialog.DialogCode.Rejected

    class FakeUsers:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            log["users"] += 1
            return QDialog.DialogCode.Rejected

    monkeypatch.setattr(mw, "PaymentDialog", FakePayment)
    monkeypatch.setattr(mw, "ReceiptDialog", FakeReceipt)
    monkeypatch.setattr(mw, "OpenShiftDialog", FakeOpenShift)
    monkeypatch.setattr(mw, "CloseShiftDialog", FakeCloseShift)
    monkeypatch.setattr(mw, "ProductsDialog", FakeProducts)
    monkeypatch.setattr(mw, "UsersDialog", FakeUsers)
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda _p, title, text, *a, **k: log["warn"].append(text))
    monkeypatch.setattr(mw.QMessageBox, "information", lambda *a, **k: log["info"].append(a))

    def ask_join(self, label):
        log["ask_join"].append(label)
        return log["join_answer"]

    monkeypatch.setattr(mw.PosWindow, "_ask_join", ask_join)
    return log


def _window(local, user_role: str, mqtt=None, user_login: str = "u"):
    user = {"id": f"user-{user_role}", "login": user_login, "role": user_role}
    win = mw.PosWindow(DesktopConfig(), user=user, runner=SyncRunner(), local=local, mqtt=mqtt or FakeMqtt())
    win._load_saved_store()
    return win


def _stock(owner: Device, qty: str = "10") -> None:
    owner.local.apply_op(product_op(owner, PID, 1000))
    owner.local.apply_op(movement_op(owner, PID, qty))


def test_owner_window_enables_manage_buttons(qtbot, ui):
    owner = make_owner(1)
    win = _window(owner.local, o.ROLE_OWNER)
    qtbot.addWidget(win)
    assert win.btn_refund.isEnabled() and win.btn_products.isEnabled() and win.btn_users.isEnabled()
    assert win.btn_refund.toolTip() == ""


def test_cashier_window_disables_manage_buttons_with_reason(qtbot, ui):
    owner, cashier = bootstrapped_pair()
    win = _window(cashier.local, o.ROLE_CASHIER)
    qtbot.addWidget(win)
    for button in (win.btn_refund, win.btn_products, win.btn_users):
        assert not button.isEnabled()
        assert "egasi" in button.toolTip().lower()


def test_disabled_buttons_do_nothing_when_clicked(qtbot, ui):
    owner, cashier = bootstrapped_pair()
    win = _window(cashier.local, o.ROLE_CASHIER)
    qtbot.addWidget(win)
    win.btn_products.click()
    win.btn_users.click()
    win.btn_refund.click()
    assert ui["products"] == 0 and ui["users"] == 0 and ui["warn"] == []


def test_owner_buttons_open_their_dialogs(qtbot, ui):
    owner = make_owner(1)
    win = _window(owner.local, o.ROLE_OWNER)
    qtbot.addWidget(win)
    win.btn_products.click()
    win.btn_users.click()
    assert ui["products"] == 1 and ui["users"] == 1


def test_shift_button_opens_and_closes_shift_on_this_device(qtbot, ui):
    owner, cashier = bootstrapped_pair()
    win = _window(cashier.local, o.ROLE_CASHIER)
    qtbot.addWidget(win)
    assert win.shift_label.text().endswith("yopiq</span>")
    win.btn_shift.click()  # ochish
    assert cashier.local.open_shift_for_device(cashier.id) is not None
    assert win.btn_shift.text() == "Smenani yopish"
    win.btn_shift.click()  # yopish
    assert cashier.local.open_shift_for_device(cashier.id) is None


def test_sale_is_signed_applied_and_sent(qtbot, ui):
    owner, cashier = bootstrapped_pair()
    _stock(owner)
    for d in (cashier,):
        d.local.apply_op(product_op(owner, PID, 1000))
        d.local.apply_op(movement_op(owner, PID, "10"))
    mqtt = FakeMqtt()
    win = _window(cashier.local, o.ROLE_CASHIER, mqtt=mqtt)
    qtbot.addWidget(win)
    assert win.open_shift(0) is None
    win.cart.add(cashier.local.get_product(PID, STORE_ID))
    win.cart.set_qty(PID, Decimal(2))
    win._refresh_cart()
    win.pay()
    sale_ops = [op for op in mqtt.sent if op["type"] == o.SALE]
    assert len(sale_ops) == 1 and ui["payment"] == 1
    assert crypto.verify_op(sale_ops[0], cashier.identity.public_key_hex)
    assert cashier.local.balance(STORE_ID, PID) == Decimal(8)


def test_sale_without_shift_is_blocked(qtbot, ui):
    owner, cashier = bootstrapped_pair()
    cashier.local.apply_op(product_op(owner, PID, 1000))
    win = _window(cashier.local, o.ROLE_CASHIER)
    qtbot.addWidget(win)
    win.cart.add(cashier.local.get_product(PID, STORE_ID))
    win.pay()
    assert ui["payment"] == 0 and any("smena" in w.lower() for w in ui["warn"])


def test_owner_refund_button_refunds_completed_sale(qtbot, ui):
    owner, cashier = bootstrapped_pair()
    _stock(owner)
    shift = shift_open_op(cashier)
    owner.local.apply_op(shift)
    from helpers import sale_op

    sale = sale_op(cashier, PID, "3", 1000, shift_id=shift["op_id"])
    owner.local.apply_op(sale)
    win = _window(owner.local, o.ROLE_OWNER)
    qtbot.addWidget(win)
    assert win.refund_sale(sale["op_id"]) is True
    assert owner.local.get_sale(sale["op_id"])["status"] == "refunded"
    assert owner.local.balance(STORE_ID, PID) == Decimal(10)


def test_cashier_cannot_refund_even_when_called_directly(qtbot, ui):
    owner, cashier = bootstrapped_pair()
    _stock(owner)
    from helpers import sale_op

    sale = sale_op(cashier, PID, "1", 1000)
    owner.local.apply_op(sale)
    win = _window(cashier.local, o.ROLE_CASHIER)
    qtbot.addWidget(win)
    assert win.refund_sale(sale["op_id"]) is False
    assert any("egasi" in w.lower() for w in ui["warn"])


def test_rejected_local_change_is_not_sent(qtbot, ui):
    owner, cashier = bootstrapped_pair()
    mqtt = FakeMqtt()
    win = _window(cashier.local, o.ROLE_CASHIER, mqtt=mqtt)
    qtbot.addWidget(win)
    win.save_product(
        {
            "id": PID,
            "name": "Hile",
            "unit": "dona",
            "sale_price": 1,
            "cost_price": 0,
            "min_stock": "0",
            "barcodes": [],
            "deleted": False,
        }
    )
    assert mqtt.sent == []
    assert cashier.local.get_product(PID, STORE_ID) is None
    assert ui["warn"]


def test_join_request_prompt_approves_cashier_and_is_asked_once(qtbot, ui):
    owner = make_owner(1)
    newcomer = Device(3)
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    request = newcomer.local.join_request("Kassa-2")
    mqtt = FakeMqtt()
    win = _window(owner.local, o.ROLE_OWNER, mqtt=mqtt, user_login="egasi")
    qtbot.addWidget(win)
    win._on_join_requested(request)
    win._on_join_requested(request)  # takror so'rov: dialog qayta chiqmasin
    assert ui["ask_join"] == ["Kassa-2"]
    device = owner.local.device_row(newcomer.id)
    assert device is not None and device["active"] and device["role"] == o.ROLE_CASHIER
    assert o.DEVICE in mqtt.types()


def test_join_request_rejected_by_owner_changes_nothing(qtbot, ui):
    owner = make_owner(1)
    newcomer = Device(4)
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    ui["join_answer"] = None
    mqtt = FakeMqtt()
    win = _window(owner.local, o.ROLE_OWNER, mqtt=mqtt, user_login="egasi")
    qtbot.addWidget(win)
    win._on_join_requested(newcomer.local.join_request("Begona"))
    assert owner.local.device_row(newcomer.id) is None
    assert mqtt.sent == []


def test_join_request_ignored_by_cashier_window(qtbot, ui):
    owner, cashier = bootstrapped_pair()
    newcomer = Device(5)
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    win = _window(cashier.local, o.ROLE_CASHIER)
    qtbot.addWidget(win)
    win._on_join_requested(newcomer.local.join_request("x"))
    assert ui["ask_join"] == []


def test_snapshot_request_is_answered_only_by_owner_device(qtbot, ui):
    owner, cashier = bootstrapped_pair()
    newcomer = Device(6)
    owner_mqtt = FakeMqtt()
    owner_win = _window(owner.local, o.ROLE_OWNER, mqtt=owner_mqtt, user_login="egasi")
    qtbot.addWidget(owner_win)
    # Yangi qurilma egasi tomonidan tasdiqlangan bo'lishi kerak (roster'da faol)
    from helpers import device_op

    owner.local.apply_op(device_op(owner, newcomer))
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    request = newcomer.local.new_op(o.SNAPSHOT_REQUEST, {})
    owner_win._on_snapshot_requested(request)
    assert o.SNAPSHOT in owner_mqtt.types()

    cashier_mqtt = FakeMqtt()
    cashier_win = _window(cashier.local, o.ROLE_CASHIER, mqtt=cashier_mqtt)
    qtbot.addWidget(cashier_win)
    cashier_win._on_snapshot_requested(request)
    assert cashier_mqtt.sent == []


def test_sync_label_shows_pending_outbox(qtbot, ui):
    owner = make_owner(1)
    win = _window(owner.local, o.ROLE_OWNER, mqtt=FakeMqtt(connected=False))
    qtbot.addWidget(win)
    owner.local.enqueue(product_op(owner, PID, 100))
    win._update_sync_label()
    assert "navbatda" in win.sync_label.text() and "MQTT uzilgan" in win.sync_label.text()


def test_apply_result_constants_match_protocol():
    assert APPLIED == "applied" and REJECTED == "rejected"
