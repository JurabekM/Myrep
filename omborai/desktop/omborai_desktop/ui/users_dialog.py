"""Foydalanuvchilar va qurilmalar oynasi (faqat egasi qurilmasi): hisoblar, qurilmalar, juftlash kodi."""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import users as u
from ..offline.store import LocalStore
from ..sync import ops as o

ROLE_NAMES = {u.ROLE_OWNER: "Egasi", u.ROLE_CASHIER: "Kassir"}
ROLE_ID = 0x0100  # Qt.UserRole


class AddCashierDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Kassir qo'shish")
        self.name = QLineEdit()
        self.login = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password2 = QLineEdit()
        self.password2.setEchoMode(QLineEdit.EchoMode.Password)
        self.error = QLabel("")
        self.error.setStyleSheet("color: #F87171;")

        form = QFormLayout()
        form.addRow("Ism", self.name)
        form.addRow("Login", self.login)
        form.addRow(f"Parol (kamida {u.MIN_PASSWORD} belgi)", self.password)
        form.addRow("Parolni takrorlang", self.password2)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Qo'shish")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Bekor qilish")
        buttons.accepted.connect(self._check)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addWidget(buttons)
        self.setMinimumWidth(380)

    def _check(self) -> None:
        if self.password.text() != self.password2.text():
            self.error.setText("Parollar bir xil emas")
            return
        self.accept()

    def values(self) -> tuple[str, str, str]:
        return self.name.text(), self.login.text(), self.password.text()


class PairingDialog(QDialog):
    """Juftlash kodi: faqat egasi ko'radi. Kod — sir (do'kon kaliti va egasi ishonchi)."""

    def __init__(self, code: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Juftlash kodi")
        self.code_label = QLabel(code)
        self.code_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.code_label.setWordWrap(True)
        warning = QLabel("Bu kod do'kon kalitini o'z ichiga oladi. Uni faqat ishonchli qurilmaga yuboring.")
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #F87171;")
        copy_button = QPushButton("Nusxalash")
        copy_button.clicked.connect(lambda: QApplication.clipboard().setText(code))
        close = QPushButton("Yopish")
        close.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addWidget(copy_button)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout = QVBoxLayout(self)
        layout.addWidget(self.code_label)
        layout.addWidget(warning)
        layout.addLayout(buttons)
        self.setMinimumWidth(520)


class UsersDialog(QDialog):
    """`submit(op)` — operatsiyani qo'llash va yuborish (PosWindow._emit). `pairing()` — juftlash kodi."""

    def __init__(
        self,
        local: LocalStore,
        submit: Callable[[dict[str, Any]], bool],
        pairing: Callable[[], str | None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Foydalanuvchilar va qurilmalar")
        self.local = local
        self.submit = submit
        self.pairing = pairing
        self.store_id = local.get_state("store_id") or ""

        self.users_table = self._table(["Ism", "Login", "Rol", "Holat"])
        self.devices_table = self._table(["Qurilma", "Rol", "Holat", "ID"])
        self.message = QLabel("")
        self.message.setStyleSheet("color: #F87171;")

        self.btn_add = QPushButton("Kassir qo'shish")
        self.btn_toggle = QPushButton("Faollashtirish / o'chirish")
        self.btn_add.clicked.connect(self._add)
        self.btn_toggle.clicked.connect(self._toggle)
        self.btn_block = QPushButton("Qurilmani bloklash / faollashtirish")
        self.btn_role = QPushButton("Egasi / kassir qilish")
        self.btn_block.clicked.connect(self._toggle_device)
        self.btn_role.clicked.connect(self._toggle_device_role)
        self.btn_pairing = QPushButton("Juftlash kodi")
        self.btn_pairing.clicked.connect(self._show_pairing)
        self.btn_pairing.setEnabled(pairing is not None)

        users_buttons = QHBoxLayout()
        users_buttons.addWidget(self.btn_add)
        users_buttons.addWidget(self.btn_toggle)
        users_buttons.addStretch(1)
        devices_buttons = QHBoxLayout()
        devices_buttons.addWidget(self.btn_block)
        devices_buttons.addWidget(self.btn_role)
        devices_buttons.addStretch(1)
        devices_buttons.addWidget(self.btn_pairing)

        close = QPushButton("Yopish")
        close.clicked.connect(self.accept)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(close)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Foydalanuvchilar (login/parol hisoblari)"))
        layout.addWidget(self.users_table)
        layout.addLayout(users_buttons)
        layout.addWidget(QLabel("Qurilmalar (ruxsatlar qurilma darajasida)"))
        layout.addWidget(self.devices_table)
        layout.addLayout(devices_buttons)
        layout.addWidget(self.message)
        layout.addLayout(footer)
        self.resize(760, 560)
        self._reload()

    @staticmethod
    def _table(headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return table

    def _reload(self) -> None:
        rows = self.local.list_users(self.store_id)
        self.users_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            cells = [
                row["name"],
                row["login"],
                ROLE_NAMES.get(row["role"], row["role"]),
                "faol" if row["active"] else "o'chirilgan",
            ]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(str(text))
                item.setData(ROLE_ID, row["id"])
                self.users_table.setItem(r, c, item)

        devices = self.local.list_devices(self.store_id)
        self.devices_table.setRowCount(len(devices))
        for r, device in enumerate(devices):
            cells = [
                device["label"] or "—",
                ROLE_NAMES.get(device["role"], device["role"]),
                "faol" if device["active"] else "bloklangan",
                device["device_id"][:8],
            ]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(str(text))
                item.setData(ROLE_ID, device["device_id"])
                self.devices_table.setItem(r, c, item)

    def _selected_user_id(self) -> str | None:
        row = self.users_table.currentRow()
        item = self.users_table.item(row, 0) if row >= 0 else None
        return None if item is None else str(item.data(ROLE_ID))

    def _selected_device_id(self) -> str | None:
        row = self.devices_table.currentRow()
        item = self.devices_table.item(row, 0) if row >= 0 else None
        return None if item is None else str(item.data(ROLE_ID))

    def _add(self) -> None:
        dialog = AddCashierDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, login, password = dialog.values()
        try:
            op = u.add_cashier(self.local, name, login, password)
        except u.UserError as exc:
            self.message.setText(str(exc))
            return
        self.submit(op)
        self.message.setText("")
        self._reload()

    def _toggle(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            self.message.setText("Avval foydalanuvchini tanlang")
            return
        current = self.local.get_user(user_id)
        if current is None:
            return
        try:
            op = u.set_active(self.local, user_id, not bool(current["active"]))
        except u.UserError as exc:
            self.message.setText(str(exc))
            return
        self.submit(op)
        self.message.setText("")
        self._reload()

    def _device_op(self, device_id: str, **changes: Any) -> dict[str, Any] | None:
        device = self.local.device_row(device_id)
        if device is None:
            self.message.setText("Qurilma topilmadi")
            return None
        if device["role"] == o.ROLE_OWNER:
            self.message.setText("Egasi qurilmasini o'zgartirib bo'lmaydi")
            return None
        payload = {
            "device_id": device["device_id"],
            "public_key": device["public_key"],
            "role": device["role"],
            "label": device["label"],
            "active": device["active"],
            **changes,
        }
        return self.local.new_op(o.DEVICE, payload)

    def _toggle_device(self) -> None:
        device_id = self._selected_device_id()
        if device_id is None:
            self.message.setText("Avval qurilmani tanlang")
            return
        device = self.local.device_row(device_id)
        if device is None:
            return
        op = self._device_op(device_id, active=not device["active"])
        if op is None:
            return
        self.submit(op)
        self.message.setText("")
        self._reload()

    def _toggle_device_role(self) -> None:
        device_id = self._selected_device_id()
        if device_id is None:
            self.message.setText("Avval qurilmani tanlang")
            return
        device = self.local.device_row(device_id)
        if device is None:
            return
        new_role = o.ROLE_OWNER if device["role"] == o.ROLE_CASHIER else o.ROLE_CASHIER
        op = self._device_op(device_id, role=new_role)
        if op is None:
            return
        self.submit(op)
        self.message.setText("")
        self._reload()

    def _show_pairing(self) -> None:
        code = self.pairing() if self.pairing is not None else None
        if not code:
            self.message.setText("Juftlash kodi faqat egasi qurilmasida ko'rinadi")
            return
        PairingDialog(code, self).exec()
