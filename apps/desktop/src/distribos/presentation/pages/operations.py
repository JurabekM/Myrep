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
from distribos.i18n import tr
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


def movement_labels() -> dict[str, str]:
    """Foydalanuvchi ko'radigan nomlar.

    Funksiya sifatida: modul darajasidagi doimiy `tr()`ni import
    vaqtida (til o'rnatilishidan OLDIN) muzlatib qo'yardi.
    """
    return {
        MovementType.RECEIPT: tr("Kirim"),
        MovementType.SALE: tr("Sotuv"),
        MovementType.RETURN_IN: tr("Qaytarib olindi"),
        MovementType.RETURN_OUT: tr("Qaytarib berildi"),
        MovementType.TRANSFER_OUT: tr("Chiqib ketdi (transfer)"),
        MovementType.TRANSFER_IN: tr("Kirib keldi (transfer)"),
        MovementType.WRITE_OFF: tr("Hisobdan chiqarish"),
        MovementType.ADJUSTMENT: tr("Tuzatish"),
        MovementType.RESERVATION: tr("Rezerv"),
        MovementType.RELEASE: tr("Rezervdan chiqarish"),
    }


class InventoryPage(BasePage):
    """Qoldiq, harakatlar va omborlar."""

    live = True

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, tr("Ombor"),
            tr(
                "Qoldiq harakatlardan hisoblanadi — u hech qachon qo'lda "
                "qayta yozilmaydi."
            ),
        )
        self._receipt = primary_button(tr("Kirim/chiqim qo'shish"))
        self._receipt.clicked.connect(self._on_movement)
        self.header.add_action(self._receipt)

        self._warehouse = ghost_button(tr("Yangi ombor"))
        self._warehouse.clicked.connect(self._on_new_warehouse)
        self.header.add_action(self._warehouse)

        tabs = QTabWidget()
        self.stock_table = DataTable(
            [tr("Ombor"), tr("SKU"), tr("Mahsulot"), tr("Qoldiq"), tr("Rezerv"),
             tr("Mavjud"), tr("Minimal")],
            placeholder=tr("Mahsulot bo'yicha qidirish…"),
        )
        self.movement_table = DataTable(
            [tr("Sana"), tr("Ombor"), tr("SKU"), tr("Mahsulot"), tr("Amal"), tr("Miqdor")],
            placeholder=tr("Harakatlar bo'yicha qidirish…"),
        )
        tabs.addTab(self.stock_table, tr("Qoldiq"))
        tabs.addTab(self.movement_table, tr("Harakatlar"))
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

        labels = movement_labels()
        self.movement_table.set_rows([
            (occurred.strftime("%d.%m.%Y %H:%M"), warehouse, sku, name,
             labels.get(movement_type, movement_type), quantity(amount))
            for occurred, warehouse, sku, name, movement_type, amount in movements
        ])

        low = sum(1 for row in stock if row.below_minimum)
        subtitle = tr("{n} ta pozitsiya").format(n=len(stock))
        if low:
            subtitle += tr(" · {n} tasida qoldiq kam").format(n=low)
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
            self.report_error(exc, tr("Ombor qo'shish"))
            return
        self.refresh()

    @Slot()
    def _on_movement(self) -> None:
        with self.context.database.session() as session:
            warehouses = queries.list_warehouses(session)
            products = queries.list_products(session)

        if not warehouses:
            self.warn(tr("Avval ombor qo'shing."), tr("Ombor yo'q"))
            return
        if not products:
            self.warn(tr("Avval mahsulot qo'shing."), tr("Mahsulot yo'q"))
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
            self.warn(str(exc), tr("Saqlanmadi"))
            return
        except Exception as exc:
            self.report_error(exc, tr("Ombor harakati"))
            return
        self.refresh()


class FinancePage(BasePage):
    """Kassa, to'lovlar va qarzdorlik."""

    live = True

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, tr("Kassa va to'lovlar"),
            tr("To'lov o'chirilmaydi — xato bo'lsa teskari yozuv yaratiladi."),
        )
        self._payment = primary_button(tr("To'lov qabul qilish"))
        self._payment.clicked.connect(self._on_payment)
        self.header.add_action(self._payment)

        self._reverse = ghost_button(tr("To'lovni bekor qilish"))
        self._reverse.clicked.connect(self._on_reverse)
        self.header.add_action(self._reverse)

        tabs = QTabWidget()
        self.payments_table = DataTable(
            [tr("Raqam"), tr("Sana"), tr("Yo'nalish"), tr("Mijoz"), tr("Summa"),
             tr("Usul"), tr("Holat")],
            placeholder=tr("Raqam yoki mijoz bo'yicha qidirish…"),
        )
        self.debt_table = DataTable(
            [tr("Kod"), tr("Mijoz"), tr("Telefon"), tr("Kredit limiti"),
             tr("Qarzdorlik"), tr("Holat")],
            placeholder=tr("Mijoz bo'yicha qidirish…"),
        )
        tabs.addTab(self.payments_table, tr("To'lovlar"))
        tabs.addTab(self.debt_table, tr("Qarzdorlik"))
        self.add(tabs, 1)

    def refresh(self) -> None:
        with self.context.database.session() as session:
            payments = queries.list_payments(session)
            customers = queries.list_customers(session)

        self.payments_table.set_rows([
            (row.number, row.occurred_at.strftime("%d.%m.%Y %H:%M"),
             tr("Kirim") if row.direction == "IN" else tr("Chiqim"),
             row.customer_name, money(row.amount), row.method,
             tr("Bekor qilingan") if row.is_reversed else tr("Amalda"))
            for row in payments
        ])
        for index, row in enumerate(payments):
            if row.is_reversed:
                self.payments_table.set_row_tone(index, "warning")

        debtors = [c for c in customers if c.debt != 0]
        self.debt_table.set_rows([
            (row.code, row.name, row.phone or "—",
             money(row.credit_limit) if row.credit_limit else tr("Cheklanmagan"),
             money(row.debt),
             tr("Limit oshgan") if row.over_limit
             else (tr("Qarz bor") if row.debt > 0 else tr("Avans")))
            for row in debtors
        ])
        for index, debtor in enumerate(debtors):
            if debtor.over_limit:
                self.debt_table.set_row_tone(index, "error")

        total_debt = sum(c.debt for c in customers if c.debt > 0)
        self.header.set_subtitle(
            tr("{n} ta to'lov · umumiy qarzdorlik {debt}").format(
                n=len(payments), debt=money(total_debt)
            )
        )

    @Slot()
    def _on_payment(self) -> None:
        with self.context.database.session() as session:
            customers = queries.list_customers(session)
        if not customers:
            self.warn(tr("Avval mijoz qo'shing."), tr("Mijoz yo'q"))
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
            context, tr("Tashriflar"), tr("Savdo agentlarining mijozlarga tashriflari."),
        )
        self.table = DataTable(
            [tr("Sana"), tr("Mijoz"), tr("Natija"), tr("Izoh")],
            placeholder=tr("Mijoz bo'yicha qidirish…"),
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
        self.header.set_subtitle(tr("{n} ta tashrif").format(n=len(visits)))


# --- dialoglar ------------------------------------------------------------


class WarehouseDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Yangi ombor"))
        self.setMinimumWidth(360)

        self._code = QLineEdit()
        self._name = QLineEdit()

        form = QFormLayout()
        form.addRow(tr("Kod *"), self._code)
        form.addRow(tr("Nomi *"), self._name)

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
            QMessageBox.warning(self, tr("To'ldirilmagan"), tr("Kod va nom majburiy."))
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
        self.setWindowTitle(tr("Ombor harakati"))
        self.setMinimumWidth(460)

        self._warehouse = QComboBox()
        for warehouse_id, code, name in warehouses:
            self._warehouse.addItem(f"{code} — {name}", warehouse_id)

        self._product = QComboBox()
        for product in products:
            self._product.addItem(f"{product.sku} — {product.name}", product.id)

        labels = movement_labels()
        self._type = QComboBox()
        for key in (MovementType.RECEIPT, MovementType.WRITE_OFF,
                    MovementType.ADJUSTMENT, MovementType.RETURN_IN,
                    MovementType.TRANSFER_IN, MovementType.TRANSFER_OUT):
            self._type.addItem(labels[key], key)

        self._quantity = QDoubleSpinBox()
        self._quantity.setRange(-1_000_000, 1_000_000)
        self._quantity.setDecimals(3)
        self._quantity.setValue(1)

        self._note = QLineEdit()

        form = QFormLayout()
        form.addRow(tr("Ombor"), self._warehouse)
        form.addRow(tr("Mahsulot"), self._product)
        form.addRow(tr("Amal"), self._type)
        form.addRow(tr("Miqdor"), self._quantity)
        form.addRow(tr("Izoh"), self._note)

        hint = QLabel(tr(
            "«Tuzatish» amalida miqdor manfiy bo'lishi mumkin. Qolgan "
            "amallarda musbat son kiriting."
        ))
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
            QMessageBox.warning(
                self, tr("Noto'g'ri miqdor"), tr("Miqdor 0 bo'lishi mumkin emas.")
            )
            return
        if self._type.currentData() != MovementType.ADJUSTMENT and self._quantity.value() < 0:
            QMessageBox.warning(
                self, tr("Noto'g'ri miqdor"),
                tr("Manfiy miqdor faqat «Tuzatish» amalida ishlatiladi."),
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
        self.setWindowTitle(tr("To'lov"))
        self.setMinimumWidth(420)

        self._direction = QComboBox()
        self._direction.addItem(tr("Kirim (mijozdan)"), "IN")
        self._direction.addItem(tr("Chiqim"), "OUT")

        self._customer = QComboBox()
        for customer in customers:
            label = f"{customer.name} ({customer.code})"
            if customer.debt > 0:
                label += tr(" — qarz {debt}").format(debt=money(customer.debt))
            self._customer.addItem(label, customer.id)

        self._amount = QDoubleSpinBox()
        self._amount.setRange(0.01, 999_999_999)
        self._amount.setDecimals(2)
        self._amount.setGroupSeparatorShown(True)

        self._method = QComboBox()
        # DIQQAT: to'lov usuli KODLARI (bazaga yoziladi), tarjima qilinmaydi.
        self._method.addItems(["cash", "card", "transfer"])

        self._note = QTextEdit()
        self._note.setMaximumHeight(70)

        form = QFormLayout()
        form.addRow(tr("Yo'nalish"), self._direction)
        form.addRow(tr("Mijoz"), self._customer)
        form.addRow(tr("Summa (so'm)"), self._amount)
        form.addRow(tr("Usul"), self._method)
        form.addRow(tr("Izoh"), self._note)

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
