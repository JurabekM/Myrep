"""Juftlash bilan qo'shilgan qurilma: do'kon ma'lumoti (snapshot) kelguncha login oynasi ochilmaydi (K1).

Ilgari login MQTT ishga tushishidan oldin kutardi, snapshot esa so'ralmasdi: qurilma do'konga kira olmasdi.
"""

import os
import uuid
from typing import Any

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog

from omborai_desktop import auth
from omborai_desktop.offline.store import LocalStore
from omborai_desktop.sync import ops as o
from omborai_desktop.ui import bootstrap as bs
from omborai_desktop.ui import login as lg
from omborai_desktop.ui.dialogs import LoginDialog
from omborai_desktop.ui.tasks import SyncRunner

STORE_ID = str(uuid.uuid4())
OWNER_LOGIN = "egasi"
OWNER_PASSWORD = "parol-12345"


class FakeMqtt:
    """MqttSync o'rnida: ulanish, yuborish va so'rovni kuzatadi."""

    def __init__(self) -> None:
        self.connected = False
        self.start_calls = 0
        self.sent: list[dict[str, Any]] = []
        self.on_request = None

    def start(self, timeout: float = 10.0) -> None:
        self.start_calls += 1
        self.connected = True

    def stop(self) -> None:
        self.connected = False

    def send(self, op: dict[str, Any]) -> None:
        if not self.connected:
            raise ConnectionError("broker yo'q")
        self.sent.append(op)


class FlakyMqtt(FakeMqtt):
    """Birinchi ulanish muvaffaqiyatsiz bo'ladi (broker vaqtincha yo'q)."""

    def start(self, timeout: float = 10.0) -> None:
        self.start_calls += 1
        if self.start_calls == 1:
            raise ConnectionError("broker yo'q")
        self.connected = True


def _owner_user_op(device: str = "d-owner") -> dict[str, Any]:
    salt, digest = auth.hash_password(OWNER_PASSWORD)
    return o.new_op(
        o.USER,
        STORE_ID,
        {
            "id": str(uuid.uuid4()),
            "login": OWNER_LOGIN,
            "name": "Egasi",
            "role": "owner",
            "salt": salt,
            "pw_hash": digest,
            "active": True,
        },
        device_id=device,
    )


@pytest.fixture
def no_keyring(monkeypatch):
    """Haqiqiy OS keyring'ga yozmaslik; OMBORAI_STORE_KEY bo'lsa has_store_key() True."""
    monkeypatch.setattr(lg, "save_store_key", lambda key: None)
    monkeypatch.setenv("OMBORAI_STORE_KEY", "00" * 32)


@pytest.fixture
def scripted(monkeypatch):
    """Boshlash/juftlash dialoglari avtomatik javob beradi; kirish urinishlari sanaladi."""
    state = {"code": auth.make_pairing_code(STORE_ID, os.urandom(32).hex()), "login_attempts": 0}

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


def test_joined_device_logs_in_after_snapshot_arrives(qtbot, no_keyring, scripted):
    local = LocalStore()
    peer = FakeMqtt()
    # Boshqa qurilma (egasi) snapshot'ni yuboradi: bu login oynasidan oldin kutiladi
    QTimer.singleShot(100, lambda: local.apply_op(_owner_user_op()))

    def bootstrap() -> bool:
        return bs.wait_for_store(
            local, peer, runner=SyncRunner(), poll_interval_ms=20, request_interval_ms=10_000
        )

    user = lg.run_login(local, bootstrap=bootstrap)

    assert user is not None and user["login"] == OWNER_LOGIN
    assert peer.start_calls == 1
    assert scripted["login_attempts"] == 1


def test_cancelled_bootstrap_never_shows_login(qtbot, no_keyring, scripted):
    local = LocalStore()
    assert lg.run_login(local, bootstrap=lambda: False) is None
    assert scripted["login_attempts"] == 0


def test_bootstrap_runs_again_when_store_has_no_users(qtbot, no_keyring, scripted):
    """Juftlash yarim qolgan (snapshot kelmagan) bo'lsa, keyingi ishga tushirishda yana kutiladi."""
    local = LocalStore()
    local.set_state("store_id", STORE_ID)
    local.set_state("device_id", str(uuid.uuid4()))
    calls: list[bool] = []

    def bootstrap() -> bool:
        calls.append(True)
        return False

    assert lg.run_login(local, bootstrap=bootstrap) is None
    assert calls == [True]


def test_bootstrap_skipped_when_store_already_has_users(qtbot, no_keyring, scripted):
    local = LocalStore()
    local.apply_op(_owner_user_op())
    local.set_state("store_id", STORE_ID)
    calls: list[bool] = []

    user = lg.run_login(local, bootstrap=lambda: calls.append(True) or False)

    assert user is not None and user["login"] == OWNER_LOGIN
    assert calls == []


def test_wait_requests_snapshot_while_waiting(qtbot):
    local = LocalStore()
    local.set_state("store_id", STORE_ID)
    local.set_state("device_id", str(uuid.uuid4()))
    peer = FakeMqtt()
    QTimer.singleShot(200, lambda: local.apply_op(_owner_user_op()))

    ok = bs.wait_for_store(local, peer, runner=SyncRunner(), poll_interval_ms=20, request_interval_ms=20)

    assert ok is True
    requests = [op for op in peer.sent if op["type"] == o.SNAPSHOT_REQUEST]
    assert len(requests) >= 2
    assert all(op["store_id"] == STORE_ID for op in requests)


def test_wait_retries_after_connection_failure(qtbot):
    local = LocalStore()
    local.set_state("store_id", STORE_ID)
    local.set_state("device_id", str(uuid.uuid4()))
    peer = FlakyMqtt()
    QTimer.singleShot(300, lambda: local.apply_op(_owner_user_op()))

    ok = bs.wait_for_store(
        local,
        peer,
        runner=SyncRunner(),
        poll_interval_ms=20,
        request_interval_ms=10_000,
        retry_interval_ms=20,
    )

    assert ok is True
    assert peer.start_calls == 2


def test_wait_cancel_returns_false(qtbot):
    local = LocalStore()
    local.set_state("store_id", STORE_ID)
    local.set_state("device_id", str(uuid.uuid4()))
    QTimer.singleShot(100, lambda: QApplication.activeModalWidget().reject())

    ok = bs.wait_for_store(
        local, FakeMqtt(), runner=SyncRunner(), poll_interval_ms=20, request_interval_ms=10_000
    )

    assert ok is False
