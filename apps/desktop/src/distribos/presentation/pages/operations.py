"""Ombor, moliya va tashrif sahifalari."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from distribos.app_context import AppContext
from distribos.application import queries
from distribos.application.command_service import CommandRejected, build_payload
from distribos.domain.ids import uuid7_str
from distribos.persistence.models import MovementType
from distribos.presentation.pages.base import BasePage
from distribos.presentation.status import money, quantity
from distribos.presentation.theme import PALETTE
from distribos.presentation.widgets import (
    DataTable,
    ghost_button,
    primary_button,
)
from distribos.sync.event_store import NewEvent

#: Foydalanuvchi ko'radigan nomlar.
MOVEMENT_LABELS: dict[str, str] = {
    MovementType.RECEIPT: "Kirim",
    MovementType.SALE: "Sotuv",
    MovementType.RETURN_IN: "Qaytarib olindi",
    MovementType.RETURN_OUT: "Qaytarib berildi",
    MovementType.TRANSFER_OUT: "Chiqib ketdi (transfer)",
    MovementType.TRANSFER_IN: "Kirib keldi (transfer)",
    MovementType.WRITE_OFF: "Hisobdan chiqarish",
    MovementType.ADJUSTMENT: "Tuzatish",
    MovementType.RESERVATION: "Rezerv",
    MovementType.RELEASE: "Rezervdan chiqarish",
}


class InventoryPage(BasePage):
    """Qoldiq, harakatlar va omborlar."""

    live = True

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, "Ombor",
            "Qoldiq harakatlardan hisoblanadi — u hech qachon qo'lda "
            "qayta yozilmaydi.",
        )
        self._receipt = primary_button("Kirim/chiqim qo'shish")
        self._receipt.clicked.connect(self._on_movement)
        self.header.add_action(self._receipt)

        self._warehouse = ghost_button("Yangi ombor")
        self._warehouse.clicked.connect(self._on_new_warehouse)
        self.header.add_action(self._warehouse)

        tabs = QTabWidget()
        self.stock_table = DataTable(
            ["Ombor", "SKU", "Mahsulot", "Qoldiq", "Rezerv", "Mavjud", "Minimal"],
            placeholder="Mahsulot bo'yicha qidirish…",
        )
        self.movement_table = DataTable(
            ["Sana", "Ombor", "SKU", "Mahsulot", "Amal", "Miqdor"],
            placeholder="Harakatlar bo'yicha qidirish…",
        )
        tabs.addTab(self.stock_table, "Qoldiq")
        tabs.addTab(self.movement_table, "Harakatlar")
        self.add(tabs, 1)

    def refresh(self) -> None:
        with self.context.database.session() as session:
            stock = queries.list_stock(session)
            movements = queries.list_movements(session)

        self.stock_table.set_rows([
            (row.warehouse_name, row.product_sku, row.product_name,
             quantity(row.quantity), quantity(row.reserved),
             quantity(row.available), quantity(row.min_stock))
            for row in stock
        ])
        for index, row in enumerate(stock):
            if row.below_minimum:
                self.stock_table.set_row_tone(index, "warning")

        self.movement_table.set_rows([
            (occurred.strftime("%d.%m.%Y %H:%M"), warehouse, sku, name,
             MOVEMENT_LABELS.get(movement_type, movement_type), quantity(amount))
            for occurred, warehouse, sku, name, movement_type, amount in movements
        ])

        low = sum(1 for row in stock if row.below_minimum)
        subtitle = f"{len(stock)} ta pozitsiya"
        if low:
            subtitle += f" · {low} tasida qoldiq kam"
        self.header.set_subtitle(subtitle)

    @Slot()
    def _on_new_warehouse(self) -> None:
        from distribos.persistence.models import Warehouse

        dialog = WarehouseDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        code, name = dialog.values()
        try:
            with self.context.database.unit_of_work() as session:
                session.add(Warehouse(id=uuid7_str(), code=code, name=name))
        except Exception as exc:
            self.report_error(exc, "Ombor qo'shish")
            return
        self.refresh()

    @Slot()
    def _on_movement(self) -> None:
        with self.context.database.session() as session:
            warehouses = queries.list_warehouses(session)
            products = queries.list_products(session)

        if not warehouses:
            self.warn("Avval ombor qo'shing.", "Ombor yo'q")
            return
        if not products:
            self.warn("Avval mahsulot qo'shing.", "Mahsulot yo'q")
            return

        dialog = MovementDialog(self, warehouses, products)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.values()

        try:
            with self.context.database.unit_of_work() as session:
                self.context.command.submit(session, NewEvent(
                    "INVENTORY_MOVED", "Inventory", data["product_id"],
                    build_payload(movement_id=uuid7_str(), occurred_at=_now_iso(), **data),
                ))
        except CommandRejected as exc:
            self.warn(str(exc), "Saqlanmadi")
            return
        except Exception as exc:
            self.report_error(exc, "Ombor harakati")
            return
        self.refresh()


class FinancePage(BasePage):
    """Kassa, to'lovlar va qarzdorlik."""

    live = True

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, "Kassa va to'lovlar",
            "To'lov o'chirilmaydi — xato bo'lsa teskari yozuv yaratiladi.",
        )
        self._payment = primary_button("To'lov qabul qilish")
        self._payment.clicked.connect(self._on_payment)
        self.header.add_action(self._payment)

        self._reverse = ghost_button("To'lovni bekor qilish")
        self._reverse.clicked.connect(self._on_reverse)
        self.header.add_action(self._reverse)

        tabs = QTabWidget()
        self.payments_table = DataTable(
            ["Raqam", "Sana", "Yo'nalish", "Mijoz", "Summa", "Usul", "Holat"],
            placeholder="Raqam yoki mijoz bo'yicha qidirish…",
        )
        self.debt_table = DataTable(
            ["Kod", "Mijoz", "Telefon", "Kredit limiti", "Qarzdorlik", "Holat"],
            placeholder="Mijoz bo'yicha qidirish…",
        )
        tabs.addTab(self.payments_table, "To'lovlar")
        tabs.addTab(self.debt_table, "Qarzdorlik")
        self.add(tabs, 1)

    def refresh(self) -> None:
        with self.context.database.session() as session:
            payments = queries.list_payments(session)
            customers = queries.list_customers(session)

        self.payments_table.set_rows([
            (row.number, row.occurred_at.strftime("%d.%m.%Y %H:%M"),
             "Kirim" if row.direction == "IN" else "Chiqim",
             row.customer_name, money(row.amount), row.method,
             "Bekor qilingan" if row.is_reversed else "Amalda")
            for row in payments
        ])
        for index, row in enumerate(payments):
            if row.is_reversed:
                self.payments_table.set_row_tone(index, "warning")

        debtors = [c for c in customers if c.debt != 0]
        self.debt_table.set_rows([
            (row.code, row.name, row.phone or "—",
             money(row.credit_limit) if row.credit_limit else "Cheklanmagan",
             money(row.debt),
             "Limit oshgan" if row.over_limit else ("Qarz bor" if row.debt > 0 else "Avans"))
            for row in debtors
        ])
        for index, debtor in enumerate(debtors):
            if debtor.over_limit:
                self.debt_table.set_row_tone(index, "error")

        total_debt = sum(c.debt for c in customers if c.debt > 0)
        self.header.set_subtitle(
            f"{len(payments)} ta to'lov · umumiy qarzdorlik {money(total_debt)}"
        )

    @Slot()
    def _on_payment(self) -> None:
        with self.context.database.session() as session:
            customers = queries.list_customers(session)
        if not customers:
            self.warn("Avval mijoz qo'shing.", "Mijoz yo'q")
            return

        dialog = PaymentDialog(self, customers)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.values()

        payment_id = uuid7_str()
        try:
            with self.context.database.unit_of_work() as session:
                self.context.command.submit(session, NewEvent(
                    "PAYMENT_RECORDED", "Payment", payment_id,
                    build_payload(
                        payment_id=payment_id,
                        number=f"T-{payment_id[-8:].upper()}",
                        occurred_at=_now_iso(), **data,
                    ),
                ))
        except CommandRejected as exc:
            self.warn(str(exc), "Saqlanmadi")
            return
        except Exception as exc:
            self.report_error(exc, "To'lov qabul qilish")
            return
        self.refresh()

    @Slot()
    def _on_reverse(self) -> None:
        from distribos.persistence.models import Payment

        selected = self.payments_table.selected_row()
        if selected is None:
            self.warn("Avval jadvaldan to'lovni tanlang.")
            return

        number = selected[0]
        with self.context.database.session() as session:
            payment = session.query(Payment).filter_by(number=number).one_or_none()
            if payment is None:
                self.warn("To'lov topilmadi.")
                return
            if payment.is_reversed:
                self.warn("Bu to'lov allaqachon bekor qilingan.")
                return
            payment_id, amount = payment.id, payment.amount

        if not self.confirm(
            f"{money(amount)} miqdoridagi to'lov bekor qilinsinmi?\n\n"
            "To'lov o'chirilmaydi — uning o'rniga teskari yozuv yaratiladi, "
            "ya'ni tarix saqlanib qoladi.",
            "To'lovni bekor qilish",
        ):
            return

        reversal_id = uuid7_str()
        try:
            with self.context.database.unit_of_work() as session:
                self.context.command.submit(session, NewEvent(
                    "PAYMENT_REVERSED", "Payment", reversal_id,
                    {"payment_id": reversal_id, "reverses_payment_id": payment_id,
                     "number": f"R-{reversal_id[-8:].upper()}", "amount": amount,
                     "occurred_at": _now_iso(), "reason": "Foydalanuvchi bekor qildi"},
                ))
        except CommandRejected as exc:
            self.warn(str(exc), "Bekor qilinmadi")
            return
        self.refresh()


class VisitsPage(BasePage):
    """Agent tashriflari."""

    live = True

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, "Tashriflar", "Savdo agentlarining mijozlarga tashriflari.",
        )
        self.table = DataTable(
            ["Sana", "Mijoz", "Natija", "Izoh"],
            placeholder="Mijoz bo'yicha qidirish…",
        )
        self.add(self.table, 1)

    def refresh(self) -> None:
        with self.context.database.session() as session:
            visits = queries.list_visits(session)
        self.table.set_rows([
            (started.strftime("%d.%m.%Y %H:%M") if started else "—",
             customer, outcome or "—", note or "")
            for started, customer, outcome, note in visits
        ])
        self.header.set_subtitle(f"{len(visits)} ta tashrif")


# --- dialoglar ------------------------------------------------------------


class WarehouseDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Yangi ombor")
        self.setMinimumWidth(360)

        self._code = QLineEdit()
        self._name = QLineEdit()

        form = QFormLayout()
        form.addRow("Kod *", self._code)
        form.addRow("Nomi *", self._name)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @Slot()
    def _on_accept(self) -> None:
        if not self._code.text().strip() or not self._name.text().strip():
            QMessageBox.warning(self, "To'ldirilmagan", "Kod va nom majburiy.")
            return
        self.accept()

    def values(self) -> tuple[str, str]:
        return self._code.text().strip(), self._name.text().strip()


class MovementDialog(QDialog):
    def __init__(
        self, parent: QWidget, warehouses: Sequence[tuple[str, str, str]],
        products: Sequence[queries.ProductRow],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ombor harakati")
        self.setMinimumWidth(460)

        self._warehouse = QComboBox()
        for warehouse_id, code, name in warehouses:
            self._warehouse.addItem(f"{code} — {name}", warehouse_id)

        self._product = QComboBox()
        for product in products:
            self._product.addItem(f"{product.sku} — {product.name}", product.id)

        self._type = QComboBox()
        for key in (MovementType.RECEIPT, MovementType.WRITE_OFF,
                    MovementType.ADJUSTMENT, MovementType.RETURN_IN,
                    MovementType.TRANSFER_IN, MovementType.TRANSFER_OUT):
            self._type.addItem(MOVEMENT_LABELS[key], key)

        self._quantity = QDoubleSpinBox()
        self._quantity.setRange(-1_000_000, 1_000_000)
        self._quantity.setDecimals(3)
        self._quantity.setValue(1)

        self._note = QLineEdit()

        form = QFormLayout()
        form.addRow("Ombor", self._warehouse)
        form.addRow("Mahsulot", self._product)
        form.addRow("Amal", self._type)
        form.addRow("Miqdor", self._quantity)
        form.addRow("Izoh", self._note)

        hint = QLabel(
            "«Tuzatish» amalida miqdor manfiy bo'lishi mumkin. Qolgan "
            "amallarda musbat son kiriting."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {PALETTE.text_muted};")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)

    @Slot()
    def _on_accept(self) -> None:
        if self._quantity.value() == 0:
            QMessageBox.warning(self, "Noto'g'ri miqdor", "Miqdor 0 bo'lishi mumkin emas.")
            return
        if self._type.currentData() != MovementType.ADJUSTMENT and self._quantity.value() < 0:
            QMessageBox.warning(
                self, "Noto'g'ri miqdor",
                "Manfiy miqdor faqat «Tuzatish» amalida ishlatiladi.",
            )
            return
        self.accept()

    def values(self) -> dict[str, Any]:
        return {
            "warehouse_id": self._warehouse.currentData(),
            "product_id": self._product.currentData(),
            "movement_type": self._type.currentData(),
            "quantity": str(Decimal(str(self._quantity.value()))),
            "note": self._note.text().strip() or None,
        }


class PaymentDialog(QDialog):
    def __init__(self, parent: QWidget, customers: Sequence[queries.CustomerRow]) -> None:
        super().__init__(parent)
        self.setWindowTitle("To'lov")
        self.setMinimumWidth(420)

        self._direction = QComboBox()
        self._direction.addItem("Kirim (mijozdan)", "IN")
        self._direction.addItem("Chiqim", "OUT")

        self._customer = QComboBox()
        for customer in customers:
            label = f"{customer.name} ({customer.code})"
            if customer.debt > 0:
                label += f" — qarz {money(customer.debt)}"
            self._customer.addItem(label, customer.id)

        self._amount = QDoubleSpinBox()
        self._amount.setRange(0.01, 999_999_999)
        self._amount.setDecimals(2)
        self._amount.setGroupSeparatorShown(True)

        self._method = QComboBox()
        self._method.addItems(["cash", "card", "transfer"])

        self._note = QTextEdit()
        self._note.setMaximumHeight(70)

        form = QFormLayout()
        form.addRow("Yo'nalish", self._direction)
        form.addRow("Mijoz", self._customer)
        form.addRow("Summa (so'm)", self._amount)
        form.addRow("Usul", self._method)
        form.addRow("Izoh", self._note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> dict[str, Any]:
        return {
            "direction": self._direction.currentData(),
            "customer_id": self._customer.currentData(),
            "amount": int(self._amount.value() * 100),
            "method": self._method.currentText(),
            "note": self._note.toPlainText().strip() or None,
        }


def _now_iso() -> str:
    import datetime as dt

    return dt.datetime.now(dt.UTC).isoformat()
