"""Foydalanuvchilar oynasi (faqat do'kon egasi): ro'yxat, kassir qo'shish, faollashtirish/o'chirish."""

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import (
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

ROLE_NAMES = {u.ROLE_OWNER: "Egasi", u.ROLE_CASHIER: "Kassir"}


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
        self.error.setStyleSheet("color: #b91c1c;")

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


class UsersDialog(QDialog):
    """`submit(op)` — operatsiyani qo'llash va yuborish (PosWindow._emit)."""

    def __init__(
        self,
        local: LocalStore,
        store_id: str,
        device_id: str,
        submit: Callable[[dict[str, Any]], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Foydalanuvchilar")
        self.local = local
        self.store_id = store_id
        self.device_id = device_id
        self.submit = submit
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Ism", "Login", "Rol", "Holat"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.message = QLabel("")
        self.message.setStyleSheet("color: #b91c1c;")

        self.btn_add = QPushButton("Kassir qo'shish")
        self.btn_toggle = QPushButton("Faollashtirish / o'chirish")
        self.btn_add.clicked.connect(self._add)
        self.btn_toggle.clicked.connect(self._toggle)
        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_add)
        buttons.addWidget(self.btn_toggle)
        buttons.addStretch(1)
        close = QPushButton("Yopish")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(self.message)
        layout.addLayout(buttons)
        self.resize(640, 420)
        self._reload()

    def _reload(self) -> None:
        rows = self.local.list_users(self.store_id)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            cells = [
                row["name"],
                row["login"],
                ROLE_NAMES.get(row["role"], row["role"]),
                "faol" if row["active"] else "o'chirilgan",
            ]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(str(text))
                item.setData(0x0100, row["id"])  # Qt.UserRole: foydalanuvchi id'si
                self.table.setItem(r, c, item)

    def _selected_user_id(self) -> str | None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return None if item is None else str(item.data(0x0100))

    def _add(self) -> None:
        dialog = AddCashierDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, login, password = dialog.values()
        try:
            op = u.add_cashier(self.local, self.store_id, self.device_id, name, login, password)
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
            op = u.set_active(self.local, self.store_id, self.device_id, user_id, not bool(current["active"]))
        except u.UserError as exc:
            self.message.setText(str(exc))
            return
        self.submit(op)
        self.message.setText("")
        self._reload()
