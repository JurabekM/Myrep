"""Juftlash va bootstrap (K1, K5): egasi tasdig'i va snapshot kelguncha login oynasi ochilmaydi.

Ssenariy: yangi qurilma kodni kiritadi -> join_request -> egasi tasdiqlaydi -> snapshot -> login.
"""

import os
from typing import Any

import pytest
from helpers import OWNER_LOGIN, OWNER_PASSWORD, STORE_ID, Device, add_user_op, device_op, make_owner
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog

from omborai_desktop import auth
from omborai_desktop.offline.store import APPLIED
from omborai_desktop.sync import ops as o
from omborai_desktop.ui import bootstrap as bs
from omborai_desktop.ui import login as lg
from omborai_desktop.ui.dialogs import LoginDialog
from omborai_desktop.ui.tasks import SyncRunner


class FakeMqtt:
    """MqttSync o'rnida: ulanish, yuborish va so'rovlarni kuzatadi."""

    def __init__(self) -> None:
        self.connected = False
        self.start_calls = 0
        self.sent: list[dict[str, Any]] = []
        self.on_request = None
        self.on_join_request = None

    def start(self, timeout: float = 10.0) -> None:
        self.start_calls += 1
        self.connected = True

    def stop(self) -> None:
        self.connected = False

    def send(self, op: dict[str, Any]) -> None:
        if not self.connected:
            raise ConnectionError("broker yo'q")
        self.sent.append(op)

    def types(self) -> list[str]:
        return [op["type"] for op in self.sent]


class FlakyMqtt(FakeMqtt):
    """Birinchi ulanish muvaffaqiyatsiz (broker vaqtincha yo'q)."""

    def start(self, timeout: float = 10.0) -> None:
        self.start_calls += 1
        if self.start_calls == 1:
            raise ConnectionError("broker yo'q")
        self.connected = True


@pytest.fixture
def no_keyring(monkeypatch):
    monkeypatch.setattr(lg, "save_store_key", lambda key: None)
    monkeypatch.setenv("OMBORAI_STORE_KEY", "00" * 32)


@pytest.fixture
def scripted(monkeypatch, request):
    """Boshlash/juftlash/kirish dialoglari avtomatik javob beradi."""
    owner = make_owner(1)
    state = {
        "code": auth.make_pairing_code(
            STORE_ID, owner.id, owner.identity.public_key_hex, os.urandom(32).hex()
        ),
        "login_attempts": 0,
        "owner": owner,
    }

    def start_exec(self):
        self.choice = lg.StartDialog.JOIN
        return QDialog.DialogCode.Accepted

    def join_exec(self):
        self.code.setText(state["code"])
        return QDialog.DialogCode.Accepted

    def login_exec(self):
        state["login_attempts"] += 1
        return QDialog.DialogCode.Accepted if state["login_attempts"] <= 3 else QDialog.DialogCode.Rejected

    monkeypatch.setattr(lg.StartDialog, "exec", start_exec)
    monkeypatch.setattr(lg.JoinDialog, "exec", join_exec)
    monkeypatch.setattr(LoginDialog, "exec", login_exec)
    monkeypatch.setattr(LoginDialog, "credentials", lambda self: (OWNER_LOGIN, OWNER_PASSWORD))
    return state


def _owner_snapshot_and_approval(owner: Device, newcomer: Device):
    """Egasi tasdiqlaydi (device op) va snapshot yuboradi — tarmoqdan kelgandek."""
    approval = device_op(owner, newcomer)
    owner.local.apply_op(approval)
    snapshot = owner.op(o.SNAPSHOT, owner.local.snapshot_payload(STORE_ID))
    return approval, snapshot


def test_joined_device_logs_in_only_after_owner_approval_and_snapshot(qtbot, no_keyring, scripted):
    """K1: join -> tasdiq -> snapshot -> login. Login oynasi snapshot'dan oldin ochilmaydi."""
    owner = scripted["owner"]
    owner.local.apply_op(add_user_op(owner))
    newcomer = Device(2)
    approval, snapshot = _owner_snapshot_and_approval(owner, newcomer)
    peer = FakeMqtt()
    seen: dict[str, Any] = {}

    def deliver_approval():
        seen["join_before_approval"] = "join_request" in peer.types()
        newcomer.local.apply_op(approval)

    QTimer.singleShot(150, deliver_approval)
    QTimer.singleShot(300, lambda: newcomer.local.apply_op(snapshot))

    def bootstrap() -> bool:
        return bs.wait_for_store(
            newcomer.local,
            peer,
            runner=SyncRunner(),
            poll_interval_ms=20,
            request_interval_ms=50,
            retry_interval_ms=20,
        )

    user = lg.run_login(newcomer.local, bootstrap=bootstrap)

    assert seen.get("join_before_approval") is True  # tasdiqdan oldin so'rov yuborilgan
    assert user is not None and user["login"] == OWNER_LOGIN
    assert scripted["login_attempts"] == 1
    assert peer.start_calls == 1
    assert newcomer.local.is_bootstrapped()


def test_cancelled_bootstrap_never_shows_login(qtbot, no_keyring, scripted):
    local = Device(3).local
    assert lg.run_login(local, bootstrap=lambda: False) is None
    assert scripted["login_attempts"] == 0


def test_bootstrap_runs_again_when_store_is_not_ready(qtbot, no_keyring, scripted):
    """Juftlash yarim qolgan: keyingi ishga tushirishda yana kutiladi."""
    owner = scripted["owner"]
    newcomer = Device(4)
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    calls: list[bool] = []

    def bootstrap() -> bool:
        calls.append(True)
        return False

    assert lg.run_login(newcomer.local, bootstrap=bootstrap) is None
    assert calls == [True]


def test_bootstrap_skipped_for_owner_device(qtbot, no_keyring, scripted):
    owner = scripted["owner"]
    owner.local.apply_op(add_user_op(owner))
    calls: list[bool] = []
    user = lg.run_login(owner.local, bootstrap=lambda: calls.append(True) or False)
    assert user is not None and user["login"] == OWNER_LOGIN
    assert calls == []


def test_wait_sends_join_request_then_snapshot_request(qtbot):
    owner = make_owner(1)
    newcomer = Device(5)
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    approval, snapshot = _owner_snapshot_and_approval(owner, newcomer)
    peer = FakeMqtt()
    QTimer.singleShot(150, lambda: newcomer.local.apply_op(approval))
    QTimer.singleShot(300, lambda: newcomer.local.apply_op(snapshot))

    ok = bs.wait_for_store(
        newcomer.local,
        peer,
        runner=SyncRunner(),
        poll_interval_ms=20,
        request_interval_ms=40,
        retry_interval_ms=20,
    )

    assert ok is True
    types = peer.types()
    assert types[0] == o.JOIN_REQUEST
    assert o.SNAPSHOT_REQUEST in types
    assert types.index(o.SNAPSHOT_REQUEST) > types.index(o.JOIN_REQUEST)


def test_wait_retries_after_connection_failure(qtbot):
    owner = make_owner(1)
    newcomer = Device(6)
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    approval, snapshot = _owner_snapshot_and_approval(owner, newcomer)
    peer = FlakyMqtt()
    QTimer.singleShot(200, lambda: newcomer.local.apply_op(approval))
    QTimer.singleShot(350, lambda: newcomer.local.apply_op(snapshot))

    ok = bs.wait_for_store(
        newcomer.local,
        peer,
        runner=SyncRunner(),
        poll_interval_ms=20,
        request_interval_ms=10_000,
        retry_interval_ms=20,
    )

    assert ok is True
    assert peer.start_calls == 2


def test_wait_cancel_returns_false(qtbot):
    owner = make_owner(1)
    newcomer = Device(7)
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    QTimer.singleShot(100, lambda: QApplication.activeModalWidget().reject())

    ok = bs.wait_for_store(
        newcomer.local, FakeMqtt(), runner=SyncRunner(), poll_interval_ms=20, request_interval_ms=10_000
    )

    assert ok is False


def test_owner_approval_makes_new_device_active(qtbot):
    owner = make_owner(1)
    newcomer = Device(8)
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    approval = device_op(owner, newcomer)
    assert owner.local.apply_op(approval) == APPLIED
    assert newcomer.local.apply_op(approval) == APPLIED
    assert bs._is_approved(newcomer.local)
