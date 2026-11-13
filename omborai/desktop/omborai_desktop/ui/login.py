"""Serversiz kirish oqimi: do'kon yaratish yoki juftlash, so'ng foydalanuvchi login/parol bilan kiradi.

Hamma ma'lumot lokal bazada. Yangi foydalanuvchi va do'kon MQTT operatsiyasi sifatida navbatga qo'yiladi
va ulanganda boshqa qurilmalarga yuboriladi.
"""

import uuid
from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import auth
from ..offline.store import LocalStore
from ..security import has_store_key, save_store_key
from ..sync import ops as o
from ..sync.crypto import generate_store_key
from .dialogs import LoginDialog

ERROR_STYLE = "color: #b91c1c;"


class StartDialog(QDialog):
    """Birinchi ishga tushirish: yangi do'kon yoki mavjud do'konga qo'shilish."""

    NEW, JOIN = "new", "join"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.choice: str | None = None
        self.setWindowTitle("OmborAI — boshlash")
        new_btn = QPushButton("Yangi do'kon yaratish")
        join_btn = QPushButton("Mavjud do'konga qo'shilish (juftlash kodi)")
        new_btn.clicked.connect(lambda: self._pick(self.NEW))
        join_btn.clicked.connect(lambda: self._pick(self.JOIN))
        layout = QVBoxLayout(self)
        layout.addWidget(new_btn)
        layout.addWidget(join_btn)
        self.setMinimumWidth(360)

    def _pick(self, choice: str) -> None:
        self.choice = choice
        self.accept()


class CreateStoreDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Yangi do'kon")
        self.store_name = QLineEdit()
        self.owner_name = QLineEdit()
        self.login = QLineEdit()
        self.login.setPlaceholderText("masalan: egasi")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password2 = QLineEdit()
        self.password2.setEchoMode(QLineEdit.EchoMode.Password)
        self.error = QLabel("")
        self.error.setStyleSheet(ERROR_STYLE)

        form = QFormLayout()
        form.addRow("Do'kon nomi", self.store_name)
        form.addRow("Egasi ismi", self.owner_name)
        form.addRow("Login", self.login)
        form.addRow("Parol (kamida 8 belgi)", self.password)
        form.addRow("Parolni takrorlang", self.password2)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Yaratish")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Bekor qilish")
        buttons.accepted.connect(self._check)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addWidget(buttons)
        self.setMinimumWidth(400)

    def _check(self) -> None:
        if not all(f.text().strip() for f in (self.store_name, self.owner_name, self.login)):
            self.error.setText("Hamma maydonlarni to'ldiring")
        elif len(self.password.text()) < 8:
            self.error.setText("Parol kamida 8 belgi bo'lsin")
        elif self.password.text() != self.password2.text():
            self.error.setText("Parollar bir xil emas")
        else:
            self.accept()


class JoinDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Do'konga qo'shilish")
        self.code = QLineEdit()
        self.code.setPlaceholderText("<do'kon ID>:<kalit>")
        self.error = QLabel("")
        self.error.setStyleSheet(ERROR_STYLE)
        form = QFormLayout()
        form.addRow("Juftlash kodi", self.code)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Qo'shilish")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Bekor qilish")
        buttons.accepted.connect(self._check)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addWidget(buttons)
        self.setMinimumWidth(400)

    def _check(self) -> None:
        try:
            auth.parse_pairing_code(self.code.text())
        except ValueError as exc:
            self.error.setText(str(exc))
            return
        self.accept()


def create_store(local: LocalStore, store_name: str, owner_name: str, login: str, password: str) -> None:
    """Yangi do'kon yaratadi: kalit, do'kon nomi va egasi hisobi navbatga qo'yiladi."""
    store_id = str(uuid.uuid4())
    key = generate_store_key()
    save_store_key(key)
    device = local.device_id()
    salt, pw_hash = auth.hash_password(password)
    ops: list[dict[str, Any]] = [
        o.new_op(o.STORE, store_id, {"name": store_name}, device_id=device),
        o.new_op(
            o.USER,
            store_id,
            {
                "id": str(uuid.uuid4()),
                "login": auth.normalize_login(login),
                "name": owner_name,
                "role": "owner",
                "salt": salt,
                "pw_hash": pw_hash,
                "active": True,
            },
            device_id=device,
        ),
    ]
    local.set_state("store_id", store_id)
    local.set_state("store_name", store_name)
    for op in ops:
        local.apply_op(op)
        local.enqueue(op)


def join_store(local: LocalStore, code: str) -> None:
    """Juftlash kodi bo'yicha do'konga qo'shiladi. Ma'lumot MQTT snapshot orqali keladi."""
    store_id, key_hex = auth.parse_pairing_code(code)
    save_store_key(bytes.fromhex(key_hex))
    local.set_state("store_id", store_id)


def pairing_code(local: LocalStore) -> str | None:
    """Boshqa qurilmaga berish uchun juftlash kodi (kalit saqlangan bo'lsa)."""
    from ..security import get_or_create_store_key

    store_id = local.get_state("store_id")
    if not store_id or not has_store_key():
        return None
    return auth.make_pairing_code(store_id, get_or_create_store_key().hex())


def _login_once(local: LocalStore, dialog: LoginDialog) -> dict[str, Any] | None:
    store_id = local.get_state("store_id")
    login, password = dialog.credentials()
    user = local.find_user(store_id, login) if store_id else None
    if user is None:
        dialog.error.setText(
            "Foydalanuvchi topilmadi. Do'kon ma'lumoti hali kelmagan bo'lishi mumkin "
            "(internet va MQTT'ni tekshiring)."
            if store_id
            else "Avval do'kon yarating yoki unga qo'shiling"
        )
        return None
    if not auth.verify_password(password, user["salt"], user["pw_hash"]):
        dialog.error.setText("Login yoki parol noto'g'ri")
        return None
    return user


def run_login(local: LocalStore, parent: QWidget | None = None) -> dict[str, Any] | None:
    """Kirish oqimi. Muvaffaqiyatli bo'lsa foydalanuvchi lug'atini, bekor qilinsa None qaytaradi."""
    if local.get_state("store_id") is None or not has_store_key():
        start = StartDialog(parent)
        if start.exec() != QDialog.DialogCode.Accepted:
            return None
        if start.choice == StartDialog.NEW:
            create_dialog = CreateStoreDialog(parent)
            if create_dialog.exec() != QDialog.DialogCode.Accepted:
                return None
            create_store(
                local,
                create_dialog.store_name.text().strip(),
                create_dialog.owner_name.text().strip(),
                create_dialog.login.text().strip(),
                create_dialog.password.text(),
            )
            return _login_as_new_owner(local, create_dialog)
        join_dialog = JoinDialog(parent)
        if join_dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        join_store(local, join_dialog.code.text())

    dialog = LoginDialog(parent, default_email="")
    while dialog.exec() == QDialog.DialogCode.Accepted:
        user = _login_once(local, dialog)
        if user is not None:
            local.set_state("session_user", user["id"])
            return user
    return None


def _login_as_new_owner(local: LocalStore, create_dialog: CreateStoreDialog) -> dict[str, Any] | None:
    """Yangi do'konda egasi darhol kiradi (parol shu yerda kiritilgan)."""
    user = local.find_user(local.get_state("store_id") or "", create_dialog.login.text())
    if user is None:
        return None
    local.set_state("session_user", user["id"])
    return user
