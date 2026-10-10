"""Tovar katalogi: ro'yxat, qo'shish, tahrirlash, o'chirish. Har bir o'zgarish MQTT operatsiyasi."""

import uuid
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..money import format_som
from .dialogs import parse_som

UNITS = ["dona", "kg", "litr", "metr", "quti", "paket"]
BARCODE_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-")


def parse_barcodes(text: str) -> list[str] | None:
    """'4780012300017, 4780012300024' -> ro'yxat. Noto'g'ri bo'lsa None."""
    codes = [part.strip() for part in text.split(",") if part.strip()]
    for code in codes:
        if not (4 <= len(code) <= 64 and set(code) <= BARCODE_CHARS):
            return None
    if len(set(codes)) != len(codes):
        return None
    return codes


class ProductFormDialog(QDialog):
    def __init__(self, product: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tovarni tahrirlash" if product else "Yangi tovar")
        self._product = product or {}
        self.name = QLineEdit(self._product.get("name", ""))
        self.unit = QComboBox()
        self.unit.addItems(UNITS)
        if self._product.get("unit") in UNITS:
            self.unit.setCurrentText(self._product["unit"])
        self.sale_price = QLineEdit(str(self._product.get("sale_price", 0)))
        self.cost_price = QLineEdit(str(self._product.get("cost_price", 0)))
        self.min_stock = QLineEdit(str(self._product.get("min_stock", "0")))
        self.barcodes = QLineEdit(", ".join(self._product.get("barcodes", [])))
        self.barcodes.setPlaceholderText("4780012300017, 4780012300024")
        self.error = QLabel("")
        self.error.setStyleSheet("color: #b91c1c;")

        form = QFormLayout()
        form.addRow("Nomi", self.name)
        form.addRow("Birlik", self.unit)
        form.addRow("Sotuv narxi (so'm)", self.sale_price)
        form.addRow("Tannarx (so'm)", self.cost_price)
        form.addRow("Minimal qoldiq", self.min_stock)
        form.addRow("Shtrix-kodlar", self.barcodes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Saqlash")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Bekor qilish")
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addWidget(buttons)
        self.setMinimumWidth(420)
        self._result: dict[str, Any] | None = None

    def _validate(self) -> None:
        name = self.name.text().strip()
        if len(name) < 2:
            self.error.setText("Nomi kamida 2 belgi bo'lishi kerak")
            return
        sale = parse_som(self.sale_price.text())
        cost = parse_som(self.cost_price.text())
        if sale is None or cost is None:
            self.error.setText("Narxlar butun son bo'lishi kerak")
            return
        try:
            min_stock = Decimal(self.min_stock.text().replace(",", "."))
        except InvalidOperation:
            self.error.setText("Minimal qoldiq raqam bo'lishi kerak")
            return
        if min_stock < 0:
            self.error.setText("Minimal qoldiq manfiy bo'lishi mumkin emas")
            return
        codes = parse_barcodes(self.barcodes.text())
        if codes is None:
            self.error.setText("Shtrix-kodlar noto'g'ri yoki takrorlangan (4–64 belgi, harf/raqam/-)")
            return
        self._result = {
            "id": self._product.get("id") or str(uuid.uuid4()),
            "name": name,
            "unit": self.unit.currentText(),
            "sale_price": sale,
            "cost_price": cost,
            "min_stock": str(min_stock),
            "barcodes": codes,
            "deleted": False,
        }
        self.accept()

    @property
    def result_product(self) -> dict[str, Any] | None:
        return self._result


class ProductsDialog(QDialog):
    """Katalog oynasi. Amallar callback'lar orqali bajariladi (ilova MQTT operatsiyasini yuboradi)."""

    def __init__(
        self,
        provider: Callable[[], list[dict[str, Any]]],
        on_save: Callable[[dict[str, Any]], None],
        on_delete: Callable[[dict[str, Any]], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tovarlar katalogi")
        self._provider = provider
        self._on_save = on_save
        self._on_delete = on_delete
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Tovar", "Narx", "Shtrix-kod", "Minimal"])
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Qidirish")
        self.search.textChanged.connect(lambda _t: self.refresh())

        self.btn_new = QPushButton("Yangi tovar")
        self.btn_new.clicked.connect(self._new)
        self.btn_edit = QPushButton("Tahrirlash")
        self.btn_edit.clicked.connect(self._edit)
        self.btn_delete = QPushButton("O'chirish")
        self.btn_delete.clicked.connect(self._delete)
        self.table.doubleClicked.connect(lambda _i: self._edit())

        row = QHBoxLayout()
        row.addWidget(self.btn_new)
        row.addWidget(self.btn_edit)
        row.addWidget(self.btn_delete)
        close = QPushButton("Yopish")
        close.clicked.connect(self.accept)
        row.addStretch(1)
        row.addWidget(close)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Tahrirlash uchun ikki marta bosing."))
        layout.addLayout(row)
        self.resize(760, 480)
        self.refresh()

    def refresh(self) -> None:
        self._products = self._provider()
        needle = self.search.text().strip().lower()
        shown = [p for p in self._products if not needle or needle in p["name"].lower()]
        self.table.setRowCount(len(shown))
        for row, product in enumerate(shown):
            cells = [
                QTableWidgetItem(product["name"]),
                QTableWidgetItem(format_som(product["sale_price"])),
                QTableWidgetItem(", ".join(product["barcodes"])),
                QTableWidgetItem(f"{product['min_stock']} {product['unit']}"),
            ]
            cells[0].setData(Qt.ItemDataRole.UserRole, product["id"])
            for col, cell in enumerate(cells):
                self.table.setItem(row, col, cell)

    def _selected(self) -> dict[str, Any] | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        cell = self.table.item(row, 0)
        if cell is None:
            return None
        product_id = cell.data(Qt.ItemDataRole.UserRole)
        return next((p for p in self._products if p["id"] == product_id), None)

    def _new(self) -> None:
        dialog = ProductFormDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_product:
            self._on_save(dialog.result_product)
            self.refresh()

    def _edit(self) -> None:
        product = self._selected()
        if product is None:
            return
        dialog = ProductFormDialog(product, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_product:
            self._on_save(dialog.result_product)
            self.refresh()

    def _delete(self) -> None:
        product = self._selected()
        if product is None:
            return
        answer = QMessageBox.question(self, "O'chirish", f"«{product['name']}» o'chirilsinmi?")
        if answer == QMessageBox.StandardButton.Yes:
            self._on_delete(product)
            self.refresh()
