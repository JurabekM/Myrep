"""Savdo sahifalari — buyurtmalar, mijozlar, mahsulotlar."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from distribos.app_context import AppContext
from distribos.application import queries
from distribos.application.command_service import CommandRejected, build_payload
from distribos.domain.ids import uuid7_str
from distribos.domain.rules import DomainError, check_credit_limit, compute_order_totals
from distribos.presentation.pages.base import BasePage
from distribos.presentation.status import money, order_state, quantity

if TYPE_CHECKING:
    from distribos.persistence.models import OrderState
from distribos.presentation.theme import PALETTE
from distribos.presentation.widgets import (
    DataTable,
    ghost_button,
    primary_button,
)
from distribos.sync.event_store import NewEvent


class ProductsPage(BasePage):
    """Mahsulot katalogi."""

    live = True

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, "Mahsulotlar",
            "Katalog, narxlar va qoldiq. Qidirish uchun yozishni boshlang.",
        )
        self._new = primary_button("Yangi mahsulot")
        self._new.clicked.connect(self._on_new)
        self.header.add_action(self._new)

        self._price = ghost_button("Narxni o'zgartirish")
        self._price.clicked.connect(self._on_change_price)
        self.header.add_action(self._price)

        self.table = DataTable(
            ["SKU", "Nomi", "Birlik", "Ulgurji", "Chakana", "Agent", "Qoldiq", "Holat"],
            placeholder="SKU, nom yoki shtrix-kod bo'yicha qidirish…",
        )
        self.add(self.table, 1)

    def refresh(self) -> None:
        with self.context.database.session() as session:
            rows = queries.list_products(session)

        self.table.set_rows([
            (row.sku, row.name, row.unit, money(row.wholesale_price),
             money(row.retail_price), money(row.agent_price),
             quantity(row.stock),
             "Kam qoldi" if row.below_minimum else ("Faol" if row.is_active else "Faol emas"))
            for row in rows
        ])
        for index, row in enumerate(rows):
            if row.below_minimum:
                self.table.set_row_tone(index, "warning")
        self.header.set_subtitle(f"{len(rows)} ta mahsulot")

    @Slot()
    def _on_new(self) -> None:
        dialog = ProductDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.values()
        product_id = uuid7_str()
        try:
            with self.context.database.unit_of_work() as session:
                self.context.command.submit(session, NewEvent(
                    "PRODUCT_CREATED", "Product", product_id,
                    build_payload(product_id=product_id, **data),
                ))
        except (CommandRejected, DomainError) as exc:
            self.warn(str(exc), "Saqlanmadi")
            return
        except Exception as exc:
            self.report_error(exc, "Mahsulot qo'shish")
            return
        self.refresh()

    @Slot()
    def _on_change_price(self) -> None:
        selected = self.table.selected_row()
        if selected is None:
            self.warn("Avval jadvaldan mahsulotni tanlang.")
            return

        sku = selected[0]
        with self.context.database.session() as session:
            matches = queries.list_products(session, search=sku, limit=1)
        if not matches:
            self.warn("Mahsulot topilmadi.")
            return
        product = matches[0]

        dialog = PriceDialog(self, product)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        field, new_price = dialog.values()
        try:
            with self.context.database.unit_of_work() as session:
                self.context.command.submit(session, NewEvent(
                    "PRODUCT_PRICE_CHANGED", "Product", product.id,
                    {"product_id": product.id, "field": field, "new_price": new_price},
                ))
        except CommandRejected as exc:
            self.warn(str(exc), "Saqlanmadi")
            return
        self.refresh()


class CustomersPage(BasePage):
    """Mijozlar va qarzdorlik."""

    live = True

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, "Mijozlar", "Aloqa ma'lumotlari, narx toifasi va qarzdorlik.",
        )
        self._new = primary_button("Yangi mijoz")
        self._new.clicked.connect(self._on_new)
        self.header.add_action(self._new)

        self.table = DataTable(
            ["Kod", "Nomi", "Telefon", "Narx toifasi", "Kredit limiti",
             "Qarzdorlik", "Buyurtmalar"],
            placeholder="Nom, kod yoki telefon bo'yicha qidirish…",
        )
        self.add(self.table, 1)

    def refresh(self) -> None:
        with self.context.database.session() as session:
            rows = queries.list_customers(session)

        self.table.set_rows([
            (row.code, row.name, row.phone or "—", row.price_tier,
             money(row.credit_limit) if row.credit_limit else "Cheklanmagan",
             money(row.debt), row.order_count)
            for row in rows
        ])
        for index, row in enumerate(rows):
            if row.over_limit:
                self.table.set_row_tone(index, "error")
        self.header.set_subtitle(f"{len(rows)} ta mijoz")

    @Slot()
    def _on_new(self) -> None:
        dialog = CustomerDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.values()
        customer_id = uuid7_str()
        try:
            with self.context.database.unit_of_work() as session:
                self.context.command.submit(session, NewEvent(
                    "CUSTOMER_CREATED", "Customer", customer_id,
                    build_payload(customer_id=customer_id, **data),
                ))
        except CommandRejected as exc:
            self.warn(str(exc), "Saqlanmadi")
            return
        except Exception as exc:
            self.report_error(exc, "Mijoz qo'shish")
            return
        self.refresh()


class OrdersPage(BasePage):
    """Buyurtmalar ro'yxati va yaratish."""

    live = True

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, "Buyurtmalar",
            "Buyurtma yaratish, tasdiqlash va yetkazish holati.",
        )
        self._new = primary_button("Yangi buyurtma")
        self._new.clicked.connect(self._on_new)
        self.header.add_action(self._new)

        self._advance = ghost_button("Holatni o'zgartirish")
        self._advance.clicked.connect(self._on_advance)
        self.header.add_action(self._advance)

        self.table = DataTable(
            ["Raqam", "Mijoz", "Sana", "Holat", "Qatorlar", "Summa",
             "To'langan", "Sinxronizatsiya"],
            placeholder="Raqam yoki mijoz bo'yicha qidirish…",
        )
        self.add(self.table, 1)

    def refresh(self) -> None:
        from distribos.presentation.status import delivery_status

        with self.context.database.session() as session:
            rows = queries.list_orders(session)

        self.table.set_rows([
            (row.number, row.customer_name,
             row.ordered_at.strftime("%d.%m.%Y"),
             order_state(row.state), row.line_count, money(row.total),
             money(row.paid_total), delivery_status(row.delivery_state).text)
            for row in rows
        ])
        self.header.set_subtitle(f"{len(rows)} ta buyurtma")

    @Slot()
    def _on_new(self) -> None:
        with self.context.database.session() as session:
            customers = queries.list_customers(session)
            products = queries.list_products(session)

        if not customers:
            self.warn("Avval kamida bitta mijoz qo'shing.", "Mijoz yo'q")
            return
        if not products:
            self.warn("Avval kamida bitta mahsulot qo'shing.", "Mahsulot yo'q")
            return

        dialog = OrderDialog(self, customers, products)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        customer, lines = dialog.values()
        if not lines:
            self.warn("Buyurtmaga kamida bitta qator qo'shing.")
            return

        totals = compute_order_totals(lines)
        check = check_credit_limit(customer.debt, customer.credit_limit, totals.total)
        if not check.allowed:
            proceed = self.confirm(
                f"{check.reason}\n\n"
                f"Joriy qarz: {money(check.current_debt)}\n"
                f"Buyurtma: {money(totals.total)}\n"
                f"Jami bo'ladi: {money(check.projected_debt)}\n\n"
                "Baribir davom etasizmi?",
                "Kredit limiti oshib ketadi",
            )
            if not proceed:
                return

        order_id = uuid7_str()
        try:
            with self.context.database.unit_of_work() as session:
                self.context.command.submit(session, NewEvent(
                    "ORDER_CREATED", "Order", order_id,
                    {
                        "order_id": order_id,
                        "number": _next_order_number(self.context),
                        "customer_id": customer.id,
                        "ordered_at": _now_iso(),
                        "lines": lines,
                    },
                ))
        except CommandRejected as exc:
            self.warn(str(exc), "Saqlanmadi")
            return
        except Exception as exc:
            self.report_error(exc, "Buyurtma yaratish")
            return

        self.refresh()
        self.notify(
            "Buyurtma qurilmada saqlandi.\n\n"
            "Internet bo'lmasa ham u yo'qolmaydi — ulanish paydo bo'lishi "
            "bilan boshqa qurilmalarga avtomatik yuboriladi.",
            "Buyurtma yaratildi",
        )

    @Slot()
    def _on_advance(self) -> None:
        from distribos.domain.rules import ORDER_TRANSITIONS
        from distribos.persistence.models import Order, OrderState

        selected = self.table.selected_row()
        if selected is None:
            self.warn("Avval jadvaldan buyurtmani tanlang.")
            return

        number = selected[0]
        with self.context.database.session() as session:
            order = session.query(Order).filter_by(number=number).one_or_none()
            if order is None:
                self.warn("Buyurtma topilmadi.")
                return
            order_id, current = order.id, OrderState(order.state)

        allowed = sorted(ORDER_TRANSITIONS.get(current, frozenset()))
        if not allowed:
            self.warn(
                f"«{order_state(current)}» yakuniy holat — uni o'zgartirib "
                "bo'lmaydi.", "O'zgartirib bo'lmaydi",
            )
            return

        dialog = StateDialog(self, current, allowed)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        target = dialog.value()
        if target is None:
            # `_choice` bo'sh emas (`allowed` bo'sh bo'lsa yuqorida
            # qaytamiz) — bu holat amalda yuz bermaydi, lekin qat'iy
            # tekshiruv aniqroq xato beradi jimgina yiqilishdan ko'ra.
            self.warn("Yangi holat tanlanmadi.", "O'zgartirilmadi")
            return

        try:
            with self.context.database.unit_of_work() as session:
                self.context.command.submit(session, NewEvent(
                    "ORDER_STATE_CHANGED", "Order", order_id,
                    {"order_id": order_id, "from_state": current.value,
                     "to_state": target.value},
                ))
        except CommandRejected as exc:
            self.warn(str(exc), "O'zgartirilmadi")
            return
        self.refresh()


# --- dialoglar ------------------------------------------------------------


class ProductDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Yangi mahsulot")
        self.setMinimumWidth(440)

        form = QFormLayout()
        self._sku = QLineEdit()
        self._name = QLineEdit()
        self._barcode = QLineEdit()
        self._unit = QComboBox()
        self._unit.addItems(["dona", "kg", "litr", "quti", "metr", "to'plam"])
        self._wholesale = _money_input()
        self._retail = _money_input()
        self._agent = _money_input()
        self._min_stock = QDoubleSpinBox()
        self._min_stock.setRange(0, 1_000_000)
        self._min_stock.setDecimals(3)

        form.addRow("SKU *", self._sku)
        form.addRow("Nomi *", self._name)
        form.addRow("Shtrix-kod", self._barcode)
        form.addRow("O'lchov birligi", self._unit)
        form.addRow("Ulgurji narx (so'm)", self._wholesale)
        form.addRow("Chakana narx (so'm)", self._retail)
        form.addRow("Agent narxi (so'm)", self._agent)
        form.addRow("Minimal qoldiq", self._min_stock)

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
        if not self._sku.text().strip() or not self._name.text().strip():
            QMessageBox.warning(self, "To'ldirilmagan", "SKU va nom majburiy.")
            return
        self.accept()

    def values(self) -> dict[str, Any]:
        return {
            "sku": self._sku.text().strip(),
            "name": self._name.text().strip(),
            "barcode": self._barcode.text().strip() or None,
            "unit": self._unit.currentText(),
            "wholesale_price": int(self._wholesale.value() * 100),
            "retail_price": int(self._retail.value() * 100),
            "agent_price": int(self._agent.value() * 100),
            "min_stock": str(Decimal(str(self._min_stock.value()))),
        }


class PriceDialog(QDialog):
    _FIELDS = (
        ("Ulgurji narx", "wholesale_price"),
        ("Chakana narx", "retail_price"),
        ("Agent narxi", "agent_price"),
        ("Xarid narxi", "purchase_price"),
    )

    def __init__(self, parent: QWidget, product: queries.ProductRow) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Narx: {product.name}")
        self.setMinimumWidth(380)

        self._field = QComboBox()
        for label, key in self._FIELDS:
            self._field.addItem(label, key)

        self._price = _money_input()
        self._price.setValue(product.wholesale_price / 100)

        form = QFormLayout()
        form.addRow("Qaysi narx", self._field)
        form.addRow("Yangi qiymat (so'm)", self._price)

        note = QLabel(
            "Narx o'zgarishi barcha qurilmalarga yuboriladi. Mavjud "
            "buyurtmalardagi narx O'ZGARMAYDI."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {PALETTE.text_muted};")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, int]:
        return self._field.currentData(), int(self._price.value() * 100)


class CustomerDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Yangi mijoz")
        self.setMinimumWidth(440)

        self._code = QLineEdit()
        self._name = QLineEdit()
        self._phone = QLineEdit()
        self._kind = QComboBox()
        self._kind.addItem("Yuridik shaxs", "COMPANY")
        self._kind.addItem("Jismoniy shaxs", "INDIVIDUAL")
        self._tier = QComboBox()
        self._tier.addItems(["wholesale", "retail", "agent"])
        self._credit = _money_input()
        self._terms = QSpinBox()
        self._terms.setRange(0, 365)
        self._address = QTextEdit()
        self._address.setMaximumHeight(70)

        form = QFormLayout()
        form.addRow("Kod *", self._code)
        form.addRow("Nomi *", self._name)
        form.addRow("Turi", self._kind)
        form.addRow("Telefon", self._phone)
        form.addRow("Narx toifasi", self._tier)
        form.addRow("Kredit limiti (so'm)", self._credit)
        form.addRow("To'lov muddati (kun)", self._terms)
        form.addRow("Manzil", self._address)

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

    def values(self) -> dict[str, Any]:
        return {
            "code": self._code.text().strip(),
            "name": self._name.text().strip(),
            "kind": self._kind.currentData(),
            "phone": self._phone.text().strip() or None,
            "price_tier": self._tier.currentText(),
            "credit_limit": int(self._credit.value() * 100),
            "payment_term_days": self._terms.value(),
            "address": self._address.toPlainText().strip() or None,
        }


class OrderDialog(QDialog):
    """Buyurtma yaratish — mijoz + qatorlar."""

    def __init__(
        self, parent: QWidget,
        customers: Sequence[queries.CustomerRow], products: Sequence[queries.ProductRow],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Yangi buyurtma")
        self.setMinimumSize(720, 520)
        self._customers = customers
        self._products = products
        self._lines: list[dict[str, Any]] = []

        self._customer = QComboBox()
        for customer in customers:
            label = f"{customer.name} ({customer.code})"
            if customer.debt:
                label += f" — qarz {money(customer.debt)}"
            self._customer.addItem(label, customer)

        self._product = QComboBox()
        for product in products:
            self._product.addItem(f"{product.sku} — {product.name}", product)

        self._quantity = QDoubleSpinBox()
        self._quantity.setRange(0.001, 1_000_000)
        self._quantity.setDecimals(3)
        self._quantity.setValue(1)

        self._discount = QDoubleSpinBox()
        self._discount.setRange(0, 100)
        self._discount.setSuffix(" %")

        add = primary_button("Qatorni qo'shish")
        add.clicked.connect(self._on_add_line)

        top = QFormLayout()
        top.addRow("Mijoz", self._customer)

        line_row = QHBoxLayout()
        line_row.addWidget(self._product, 3)
        line_row.addWidget(self._quantity, 1)
        line_row.addWidget(self._discount, 1)
        line_row.addWidget(add)

        self.table = DataTable(
            ["Mahsulot", "Miqdor", "Narx", "Chegirma", "Summa"], searchable=False
        )

        self._total = QLabel("Jami: 0 UZS")
        self._total.setObjectName("CardValue")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(line_row)
        layout.addWidget(self.table, 1)
        layout.addWidget(self._total)
        layout.addWidget(buttons)

    @Slot()
    def _on_add_line(self) -> None:
        product = self._product.currentData()
        customer = self._customer.currentData()
        from distribos.domain.rules import resolve_unit_price

        try:
            unit_price = resolve_unit_price(
                {"retail_price": product.retail_price,
                 "wholesale_price": product.wholesale_price,
                 "agent_price": product.agent_price},
                customer.price_tier,
            )
        except DomainError as exc:
            QMessageBox.warning(self, "Narx yo'q", str(exc))
            return

        self._lines.append({
            "line_id": uuid7_str(),
            "product_id": product.id,
            "quantity": str(Decimal(str(self._quantity.value()))),
            "unit_price": unit_price,
            "discount_percent": str(Decimal(str(self._discount.value()))),
        })
        self._redraw()

    def _redraw(self) -> None:
        from distribos.domain.rules import line_total

        products = {p.id: p for p in self._products}
        rows = []
        for line in self._lines:
            product = products[line["product_id"]]
            total = line_total(line["quantity"], line["unit_price"],
                               line["discount_percent"])
            rows.append((
                product.name, line["quantity"], money(line["unit_price"]),
                f"{line['discount_percent']} %", money(total),
            ))
        self.table.set_rows(rows)
        totals = compute_order_totals(self._lines)
        self._total.setText(f"Jami: {money(totals.total)}")

    def values(self) -> tuple[Any, list[dict[str, Any]]]:
        return self._customer.currentData(), self._lines


class StateDialog(QDialog):
    def __init__(
        self, parent: QWidget, current: OrderState, allowed: Sequence[OrderState],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Buyurtma holati")
        self.setMinimumWidth(360)

        self._choice = QComboBox()
        for state in allowed:
            self._choice.addItem(order_state(state), state)

        form = QFormLayout()
        form.addRow("Joriy holat", QLabel(order_state(current)))
        form.addRow("Yangi holat", self._choice)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def value(self) -> OrderState | None:
        # `currentData()` PySide6 stublarida `Any` — biz `addItem()` da
        # o'zimiz `OrderState` qo'yganimiz uchun bu xavfsiz.
        return cast("OrderState | None", self._choice.currentData())


# --- yordamchilar ---------------------------------------------------------


def _money_input() -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(0, 999_999_999)
    box.setDecimals(2)
    box.setGroupSeparatorShown(True)
    return box


def _now_iso() -> str:
    import datetime as dt

    return dt.datetime.now(dt.UTC).isoformat()


def _next_order_number(context: AppContext) -> str:
    """Buyurtma raqami — qurilma prefiksi bilan.

    Prefiks SHART: ikki qurilma offline'da bir vaqtda buyurtma yaratsa,
    prefiksisiz ikkalasi ham «B-000123» bo'lib, sinxronizatsiyada
    to'qnashardi.
    """
    from sqlalchemy import func, select

    from distribos.persistence.models import Order

    prefix = context.device_id.hex()[:4].upper()
    with context.database.session() as session:
        count = session.execute(
            select(func.count()).select_from(Order).where(
                Order.number.like(f"{prefix}-%")
            )
        ).scalar_one()
    return f"{prefix}-{int(count) + 1:05d}"
