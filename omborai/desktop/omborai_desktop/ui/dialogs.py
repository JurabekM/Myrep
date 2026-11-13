"""Kichik dialoglar: kirish, smena ochish/yopish, to'lov, chek ko'rinishi, chekni qaytarish."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..money import format_som
from ..receipt import METHOD_LABELS


def _int_field(value: int = 0) -> QLineEdit:
    edit = QLineEdit(str(value))
    edit.setPlaceholderText("0")
    edit.setAlignment(Qt.AlignmentFlag.AlignRight)
    return edit


def parse_som(text: str) -> int | None:
    """'14 500' yoki '14500' -> 14500. Noto'g'ri bo'lsa None."""
    cleaned = text.replace(" ", "").replace(",", "")
    if not cleaned.isdigit():
        return None
    return int(cleaned)


class LoginDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, default_email: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("OmborAI — kirish")
        self.email = QLineEdit(default_email)
        self.email.setPlaceholderText("login")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.error = QLabel("")
        self.error.setStyleSheet("color: #b91c1c;")

        form = QFormLayout()
        form.addRow("Login", self.email)
        form.addRow("Parol", self.password)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Kirish")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Bekor qilish")
        buttons.accepted.connect(self._accept_if_filled)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addWidget(buttons)
        self.setMinimumWidth(360)

    def _accept_if_filled(self) -> None:
        if not self.email.text().strip() or not self.password.text():
            self.error.setText("Login va parolni kiriting")
            return
        self.accept()

    def credentials(self) -> tuple[str, str]:
        return self.email.text().strip(), self.password.text()


class OpenShiftDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Smena ochish")
        self.cash = _int_field(0)
        form = QFormLayout()
        form.addRow("Kassadagi boshlang'ich naqd (so'm)", self.cash)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _validate(self) -> None:
        if parse_som(self.cash.text()) is not None:
            self.accept()

    def opening_cash(self) -> int:
        return parse_som(self.cash.text()) or 0


class CloseShiftDialog(QDialog):
    def __init__(self, expected_hint: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Smenani yopish")
        self.cash = _int_field(0)
        form = QFormLayout()
        form.addRow("Kassadagi haqiqiy naqd (so'm)", self.cash)
        if expected_hint:
            form.addRow("", QLabel(expected_hint))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _validate(self) -> None:
        if parse_som(self.cash.text()) is not None:
            self.accept()

    def closing_cash(self) -> int:
        return parse_som(self.cash.text()) or 0


class PaymentDialog(QDialog):
    """Bitta to'lov turi bilan to'lash. Naqd bo'lsa qaytimni hisoblaydi."""

    METHODS = ("cash", "card", "click", "payme")

    def __init__(self, total: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("To'lov")
        self._total = total
        self._method = "cash"

        self.total_label = QLabel(f"<b>{format_som(total)} so'm</b>")
        self.total_label.setStyleSheet("font-size: 22px;")

        self._group = QButtonGroup(self)
        method_row = QHBoxLayout()
        for method in self.METHODS:
            button = QPushButton(METHOD_LABELS[method])
            button.setCheckable(True)
            button.setMinimumHeight(48)
            button.setChecked(method == self._method)
            self._group.addButton(button)
            button.clicked.connect(lambda _checked=False, m=method: self._select(m))
            method_row.addWidget(button)

        self.received = _int_field(total)
        self.received.textChanged.connect(self._update_change)
        self.change_label = QLabel("")
        self.change_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        form = QFormLayout()
        form.addRow("Qabul qilindi (so'm)", self.received)
        form.addRow("Qaytim", self.change_label)

        self.error = QLabel("")
        self.error.setStyleSheet("color: #b91c1c;")
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("To'lash")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Bekor qilish")
        buttons.accepted.connect(self._confirm)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.total_label)
        layout.addLayout(method_row)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addWidget(buttons)
        self.setMinimumWidth(420)
        self._update_change()

    def _select(self, method: str) -> None:
        self._method = method
        self.received.setEnabled(method == "cash")
        if method != "cash":
            self.received.setText(str(self._total))
        self._update_change()

    def _update_change(self) -> None:
        received = parse_som(self.received.text()) or 0
        change = max(received - self._total, 0) if self._method == "cash" else 0
        self.change_label.setText(f"{format_som(change)} so'm")

    def _confirm(self) -> None:
        received = parse_som(self.received.text())
        if received is None or (self._method == "cash" and received < self._total):
            self.error.setText("Qabul qilingan summa jami summadan kam bo'lmasligi kerak")
            return
        self.accept()

    @property
    def method(self) -> str:
        return self._method

    @property
    def change(self) -> int:
        if self._method != "cash":
            return 0
        return max((parse_som(self.received.text()) or 0) - self._total, 0)


class ReceiptDialog(QDialog):
    def __init__(self, receipt_text: str, *, can_print: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chek")
        self.print_requested = False
        view = QPlainTextEdit(receipt_text)
        view.setReadOnly(True)
        view.setStyleSheet("font-family: monospace; font-size: 13px;")
        view.setMinimumWidth(380)

        buttons = QDialogButtonBox()
        if can_print:
            print_button = buttons.addButton("Chop etish", QDialogButtonBox.ButtonRole.AcceptRole)
            print_button.clicked.connect(self._on_print)
        close_button = buttons.addButton("Yopish", QDialogButtonBox.ButtonRole.RejectRole)
        close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(view)
        layout.addWidget(buttons)

    def _on_print(self) -> None:
        self.print_requested = True
        self.accept()


class RefundDialog(QDialog):
    def __init__(self, sales: list[dict], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chekni qaytarish")
        self.list = QListWidget()
        self._sales = {}
        for sale in sales:
            label = f"#{sale['number']}  ·  {format_som(sale['total'])} so'm  ·  {sale['status']}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, sale["id"])
            if sale["status"] != "completed":
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.list.addItem(item)
            self._sales[sale["id"]] = sale
        self.list.itemDoubleClicked.connect(lambda _i: self._accept_selected())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Qaytarish")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Bekor qilish")
        buttons.accepted.connect(self._accept_selected)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Qaytariladigan chekni tanlang:"))
        layout.addWidget(self.list)
        layout.addWidget(buttons)
        self.setMinimumWidth(380)
        self._selected: str | None = None

    def _accept_selected(self) -> None:
        item = self.list.currentItem()
        if item is None or not item.flags() & Qt.ItemFlag.ItemIsEnabled:
            return
        self._selected = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    @property
    def sale_id(self) -> str | None:
        return self._selected


__all__ = [
    "CloseShiftDialog",
    "LoginDialog",
    "OpenShiftDialog",
    "PaymentDialog",
    "ReceiptDialog",
    "RefundDialog",
    "parse_som",
]
