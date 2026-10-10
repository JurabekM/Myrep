"""Kassa (POS) oynasi. Savdo, smena, qaytarish va katalog — hammasi MQTT operatsiyasi (docs/sync-mqtt.md).

Oqim: amal → operatsiya yaratiladi → lokal bazaga darhol qo'llanadi → broker'ga yuboriladi
(ulanmagan bo'lsa navbatga qo'yiladi va ulanganda yuboriladi).
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..cart import Cart
from ..config import DesktopConfig
from ..escpos import build_receipt_bytes, send_to_network_printer
from ..money import format_qty, format_som
from ..offline.store import LocalStore
from ..receipt import render_receipt
from ..sync import ops as o
from .dialogs import (
    CloseShiftDialog,
    OpenShiftDialog,
    PaymentDialog,
    ReceiptDialog,
    RefundDialog,
    parse_som,
)
from .products_dialog import ProductsDialog
from .tasks import BackgroundRunner

ROLE_PRODUCT_ID = Qt.ItemDataRole.UserRole
SNAPSHOT_REQUEST_INTERVAL_S = 60


class _Bridge(QObject):
    """MQTT oqimidan (paho) asosiy (UI) oqimiga o'tkazish uchun."""

    snapshot_requested = Signal(object)


class PosWindow(QMainWindow):
    def __init__(
        self,
        config: DesktopConfig,
        runner: Any | None = None,
        local: LocalStore | None = None,
        mqtt: Any | None = None,
        refresh_interval_ms: int = 15_000,
    ) -> None:
        super().__init__()
        self.config = config
        self.runner = runner or BackgroundRunner(self)
        self.local = local or LocalStore()
        self.mqtt = mqtt
        self.store: dict[str, Any] | None = None
        self.cart = Cart()
        self._pending: dict[str, Any] | None = None  # yuborilayotgan savdo (bir vaqtda bitta)
        self._filling_table = False
        self._flushing = False
        self._last_snapshot_request = 0.0
        self._bridge = _Bridge(self)
        self._bridge.snapshot_requested.connect(self._on_snapshot_requested)
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(refresh_interval_ms)
        self._sync_timer.timeout.connect(self._refresh_sync_state)
        self._build_ui()
        self._build_shortcuts()

    # --- UI qurish --------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowTitle("OmborAI — Kassa")
        self.resize(1200, 760)

        self.store_label = QLabel("Do'kon: —")
        self.shift_label = QLabel("Smena: —")
        self.shift_label.setStyleSheet("font-weight: bold;")
        self.sync_label = QLabel("Sinxron: —")
        self.btn_shift = QPushButton("Smena")
        self.btn_shift.clicked.connect(self._on_shift_clicked)
        self.btn_refund = QPushButton("Qaytarish")
        self.btn_refund.clicked.connect(self._on_refund_clicked)
        self.btn_products = QPushButton("Tovarlar")
        self.btn_products.clicked.connect(self._open_products)

        top = QHBoxLayout()
        top.addWidget(self.store_label)
        top.addSpacing(24)
        top.addWidget(self.shift_label)
        top.addStretch(1)
        top.addWidget(self.sync_label)
        top.addWidget(self.btn_products)
        top.addWidget(self.btn_refund)
        top.addWidget(self.btn_shift)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Shtrix-kod skanerlang yoki nom yozing (F2)")
        self.search.setMinimumHeight(48)
        self.search.returnPressed.connect(self._on_search_submitted)
        self.results = QListWidget()
        self.results.itemActivated.connect(self._on_result_activated)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self.search)
        left_layout.addWidget(QLabel("Natijalar (Enter yoki ikki marta bosing):"))
        left_layout.addWidget(self.results)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Tovar", "Miqdor", "Narx", "Summa"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.table.itemChanged.connect(self._on_qty_edited)

        self.subtotal_label = QLabel()
        self.discount_edit = QLineEdit("0")
        self.discount_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.discount_edit.editingFinished.connect(self._on_discount_changed)
        self.total_label = QLabel()
        self.total_label.setStyleSheet("font-size: 26px; font-weight: bold;")

        self.btn_remove = QPushButton("O'chirish (Del)")
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_clear = QPushButton("Savatni tozalash")
        self.btn_clear.clicked.connect(self._clear_cart)
        self.btn_pay = QPushButton("To'lash (F12)")
        self.btn_pay.setMinimumHeight(64)
        self.btn_pay.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.btn_pay.clicked.connect(self.pay)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.table, 1)
        totals = QHBoxLayout()
        totals.addWidget(QLabel("Jami:"))
        totals.addWidget(self.subtotal_label)
        totals.addSpacing(16)
        totals.addWidget(QLabel("Chegirma:"))
        totals.addWidget(self.discount_edit)
        right_layout.addLayout(totals)
        right_layout.addWidget(self.total_label)
        row = QHBoxLayout()
        row.addWidget(self.btn_remove)
        row.addWidget(self.btn_clear)
        right_layout.addLayout(row)
        right_layout.addWidget(QLabel("Fiskal chek: ishlab chiqish jarayonida"))
        right_layout.addWidget(self.btn_pay)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([430, 770])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Tayyor")
        self._refresh_cart()
        self._show_shift_state()

    def _build_shortcuts(self) -> None:
        self._bind_shortcut("F2", self.search.setFocus)
        self._bind_shortcut("F12", self.pay)
        self._bind_shortcut("Delete", self._remove_selected, parent=self.table)
        self._bind_shortcut("Escape", self.search.clear, parent=self.search)

    def _bind_shortcut(self, key: str, action: Callable[[], None], parent: QWidget | None = None) -> None:
        shortcut = QShortcut(QKeySequence(key), parent or self)
        shortcut.activated.connect(action)

    # --- yordamchilar -------------------------------------------------------

    @property
    def store_id(self) -> str:
        if self.store is None:
            raise RuntimeError("Do'kon tanlanmagan")
        return str(self.store["id"])

    def _status(self, text: str) -> None:
        self.statusBar().showMessage(text, 8000)

    def _warn(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def _emit(self, op: dict[str, Any]) -> None:
        """Operatsiyani lokal qo'llaydi va broker'ga yuboradi (yoki navbatga qo'yadi)."""
        self.local.apply_op(op)
        if self.mqtt is None or not self.mqtt.connected:
            self.local.enqueue(op)
            self._update_sync_label()
            return
        mqtt = self.mqtt

        def send() -> None:
            mqtt.send(op)

        self.runner.run(send, lambda _r: self._update_sync_label(), lambda _e: self._queue(op))

    def _queue(self, op: dict[str, Any]) -> None:
        self.local.enqueue(op)
        self._update_sync_label()

    def _new_op(self, op_type: str, payload: dict[str, Any], op_id: str | None = None) -> dict[str, Any]:
        return o.new_op(op_type, self.store_id, payload, device_id=self.local.device_id(), op_id=op_id)

    # --- boshlash ------------------------------------------------------------

    def start(self) -> None:
        if self.mqtt is not None:
            self.mqtt.on_request = self._bridge.snapshot_requested.emit
            self.runner.run(self.mqtt.start, self._on_mqtt_started, self._on_mqtt_failed)
        self._load_saved_store()
        self._sync_timer.start()

    def _load_saved_store(self) -> None:
        """Do'kon id'si bor bo'lsa ishlaydi. Nomi snapshot kelgach ham yangilanadi (joinlangan qurilma)."""
        store_id = self.local.get_state("store_id")
        if store_id:
            self.store = {"id": store_id, "name": self.local.store_name(store_id) or ""}
            self._refresh_store_label()
            self._show_shift_state()

    def _refresh_store_label(self) -> None:
        if self.store is None:
            return
        name = self.local.store_name(self.store["id"]) or self.store["name"]
        self.store["name"] = name
        self.store_label.setText(f"Do'kon: <b>{name or '…'}</b>")

    def _on_mqtt_started(self, _result: Any) -> None:
        self._refresh_sync_state()

    def _on_mqtt_failed(self, exc: Exception) -> None:
        self._update_sync_label()
        self._status(f"MQTT ulanmadi: {exc}")

    def _on_error(self, exc: Exception) -> None:
        self._warn("Xatolik", str(exc))

    # --- smena (MQTT) ----------------------------------------------------------

    def _show_shift_state(self) -> None:
        if self.store is None:
            return
        shift = self.local.open_shift(self.store_id)
        if shift is None:
            self.shift_label.setText("Smena: <span style='color:#b91c1c'>yopiq</span>")
            self.btn_shift.setText("Smena ochish")
        else:
            self.shift_label.setText("Smena: <span style='color:#15803d'>ochiq</span>")
            self.btn_shift.setText("Smenani yopish")

    def _on_shift_clicked(self) -> None:
        if self.store is None:
            return
        if self.local.open_shift(self.store_id) is None:
            open_dialog = OpenShiftDialog(self)
            if open_dialog.exec() == QDialog.DialogCode.Accepted:
                self.open_shift(open_dialog.opening_cash())
        else:
            close_dialog = CloseShiftDialog(parent=self)
            if close_dialog.exec() == QDialog.DialogCode.Accepted:
                self.close_shift(close_dialog.closing_cash())

    def open_shift(self, opening_cash: int) -> None:
        if self.local.open_shift(self.store_id) is not None:
            self._warn("Smena", "Smena allaqachon ochiq.")
            return
        shift_id = str(uuid.uuid4())
        self._emit(
            self._new_op(o.SHIFT_OPEN, {"shift_id": shift_id, "opening_cash": opening_cash}, op_id=shift_id)
        )
        self._show_shift_state()

    def close_shift(self, closing_cash: int) -> dict[str, Any] | None:
        shift = self.local.open_shift(self.store_id)
        if shift is None:
            self._warn("Smena", "Ochiq smena yo'q.")
            return None
        summary = self.local.shift_summary(shift["id"])
        expected = int(shift["opening_cash"]) + int(summary["by_method"].get("cash", 0))
        self._emit(
            self._new_op(
                o.SHIFT_CLOSE,
                {"shift_id": shift["id"], "closing_cash": closing_cash, "summary": summary},
            )
        )
        self._show_shift_state()
        methods = ", ".join(f"{k}: {format_som(v)}" for k, v in summary["by_method"].items()) or "—"
        QMessageBox.information(
            self,
            "Smena yopildi",
            f"Savdolar: {summary['sales_count']} ta, {format_som(summary['total_sales'])} so'm\n"
            f"Qaytarishlar: {summary['refunds_count']} ta, {format_som(summary['total_refunds'])} so'm\n"
            f"To'lov turlari: {methods}\n"
            f"Kutilgan naqd: {format_som(expected)} so'm\n"
            f"Haqiqiy naqd: {format_som(closing_cash)} so'm\n"
            f"Farq: {format_som(closing_cash - expected)} so'm",
        )
        return summary

    # --- qidiruv va savat ----------------------------------------------------

    def _on_search_submitted(self) -> None:
        if self.store is None:
            return
        text = self.search.text().strip()
        if not text:
            return
        if text.isdigit() and len(text) >= 4:  # skaner odatda raqamli kod yuboradi
            self._on_barcode_found(text, self.local.product_by_barcode(text, self.store_id))
        else:
            self._on_search_results(self.local.search_products(text, self.store_id))

    def _on_barcode_found(self, code: str, product: dict[str, Any] | None) -> None:
        if product is None:
            self._status(f"Tovar topilmadi: {code}")
        else:
            self._add_product(product)
        self.search.clear()
        self.search.setFocus()

    def _on_search_results(self, products: list[dict[str, Any]]) -> None:
        self.results.clear()
        for product in products:
            stock = format_qty(Decimal(product.get("stock_qty") or 0))
            price = format_som(product["sale_price"])
            item = QListWidgetItem(f"{product['name']}  ·  {price} so'm  ·  {stock} {product['unit']}")
            item.setData(ROLE_PRODUCT_ID, product)
            self.results.addItem(item)
        if len(products) == 1:
            self._add_product(products[0])
            self.search.clear()
        elif not products:
            self._status("Hech narsa topilmadi")

    def _on_result_activated(self, item: QListWidgetItem) -> None:
        self._add_product(item.data(ROLE_PRODUCT_ID))

    def _add_product(self, product: dict[str, Any]) -> None:
        if self._pending is not None:
            self._status("Oldingi savdo yuborilmoqda, kuting")
            return
        self.cart.add(product)
        self._refresh_cart()
        self._status(f"Qo'shildi: {product['name']}")

    def _refresh_cart(self) -> None:
        self._filling_table = True
        try:
            self.table.setRowCount(len(self.cart.lines))
            for row, line in enumerate(self.cart.lines):
                name = QTableWidgetItem(line.name)
                name.setData(ROLE_PRODUCT_ID, line.product_id)
                name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)
                qty = QTableWidgetItem(format_qty(line.qty))
                qty.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                price = QTableWidgetItem(format_som(line.unit_price))
                price.setFlags(price.flags() & ~Qt.ItemFlag.ItemIsEditable)
                total = QTableWidgetItem(format_som(line.line_total))
                total.setFlags(total.flags() & ~Qt.ItemFlag.ItemIsEditable)
                for col, cell in enumerate((name, qty, price, total)):
                    if col in (2, 3):
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(row, col, cell)
        finally:
            self._filling_table = False
        self.subtotal_label.setText(f"{format_som(self.cart.subtotal)} so'm")
        self.total_label.setText(f"Jami: {format_som(self.cart.total)} so'm")
        self.discount_edit.setText(str(self.cart.discount))

    def _product_id_at(self, row: int) -> str | None:
        cell = self.table.item(row, 0)
        return None if cell is None else cell.data(ROLE_PRODUCT_ID)

    def _on_qty_edited(self, item: QTableWidgetItem) -> None:
        if self._filling_table or item.column() != 1:
            return
        product_id = self._product_id_at(item.row())
        if product_id is None:
            return
        try:
            qty = Decimal(item.text().replace(",", "."))
        except InvalidOperation:
            self._status("Miqdor raqam bo'lishi kerak")
            self._refresh_cart()
            return
        if qty <= 0:
            self.cart.remove(product_id)
        else:
            self.cart.set_qty(product_id, qty)
        self._refresh_cart()

    def _remove_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or self._pending is not None:
            return
        product_id = self._product_id_at(row)
        if product_id is not None:
            self.cart.remove(product_id)
        self._refresh_cart()

    def _clear_cart(self) -> None:
        if self._pending is not None:
            return
        self.cart.clear()
        self._refresh_cart()

    def _on_discount_changed(self) -> None:
        amount = parse_som(self.discount_edit.text())
        if amount is None:
            self._status("Chegirma raqam bo'lishi kerak")
            self.discount_edit.setText(str(self.cart.discount))
            return
        try:
            self.cart.set_discount(amount)
        except ValueError as exc:
            self._status(str(exc))
        self._refresh_cart()

    # --- savdo (MQTT) ----------------------------------------------------------

    def pay(self) -> None:
        if self._pending is not None:
            self._status("Oldingi savdo yuborilmoqda, kuting")
            return
        if self.store is None or self.cart.is_empty:
            self._status("Savat bo'sh")
            return
        shift = self.local.open_shift(self.store_id)
        if shift is None:
            self._warn("Smena", "Avval smenani oching.")
            return
        short = self._insufficient_stock()
        if short:
            self._warn("Qoldiq yetarli emas", short)
            return
        dialog = PaymentDialog(self.cart.total, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        payload = self.cart.to_sale_payload(self.store_id, [(dialog.method, self.cart.total)], sale_id=None)
        payload["shift_id"] = shift["id"]
        payload["number"] = self.local.next_receipt_number()
        payload["created_at"] = datetime.now(UTC).isoformat()
        self._complete_sale(payload, dialog.change)

    def _insufficient_stock(self) -> str | None:
        for line in self.cart.lines:
            available = self.local.balance(self.store_id, line.product_id)
            if line.qty > available:
                return (
                    f"«{line.name}»: qoldiq {format_qty(available)} {line.unit}, "
                    f"so'ralgan {format_qty(line.qty)}"
                )
        return None

    def _complete_sale(self, payload: dict[str, Any], change: int) -> None:
        op = self._new_op(o.SALE, payload, op_id=payload["id"])
        self._emit(op)
        store_name = self.store["name"] if self.store else self.config.store_name_fallback
        text = render_receipt(payload, store_name, width=self.config.receipt_width, change=change)
        self.cart.clear()
        self._refresh_cart()
        self._status(f"Chek #{payload['number']} saqlandi")
        dialog = ReceiptDialog(text, can_print=bool(self.config.printer_host), parent=self)
        dialog.exec()
        if dialog.print_requested:
            self._print(text)

    def _print(self, text: str) -> None:
        host = self.config.printer_host
        if not host:
            return
        data = build_receipt_bytes(text)
        self.runner.run(
            lambda: send_to_network_printer(host, data),
            lambda _r: self._status("Chek chop etildi"),
            lambda exc: self._warn("Printer", f"Chop etib bo'lmadi: {exc}"),
        )

    # --- qaytarish (MQTT) -----------------------------------------------------

    def _on_refund_clicked(self) -> None:
        if self.store is None:
            return
        dialog = RefundDialog(self.local.sales(self.store_id), self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.sale_id is None:
            return
        self.refund_sale(dialog.sale_id)

    def refund_sale(self, sale_id: str) -> bool:
        sale = self.local.get_sale(sale_id)
        if sale is None or sale["status"] != "completed":
            self._warn("Qaytarish", "Bu chekni qaytarib bo'lmaydi.")
            return False
        # op_id = refund:<sale_id>: barcha qurilmalarda bir chek faqat bir marta qaytariladi
        self._emit(self._new_op(o.REFUND, {"sale_id": sale_id}, op_id=o.refund_op_id(sale_id)))
        self._status(f"Chek #{sale['number']} qaytarildi")
        return True

    # --- tovarlar katalogi (MQTT) -----------------------------------------------

    def _open_products(self) -> None:
        if self.store is None:
            return
        dialog = ProductsDialog(
            provider=self.local.all_products,
            on_save=self.save_product,
            on_delete=self.delete_product,
            parent=self,
        )
        dialog.exec()
        self._refresh_cart()

    def save_product(self, product: dict[str, Any]) -> None:
        self._emit(self._new_op(o.PRODUCT, product))

    def delete_product(self, product: dict[str, Any]) -> None:
        payload = {**product, "deleted": True}
        self._emit(self._new_op(o.PRODUCT, payload))

    # --- sinxronizatsiya ------------------------------------------------------

    def _refresh_sync_state(self) -> None:
        connected = bool(self.mqtt and self.mqtt.connected)
        self._refresh_store_label()
        self._update_sync_label()
        if not connected:
            return
        self._flush_outbox()
        if self.local.applied_count() == 0:
            self._request_snapshot()

    def _flush_outbox(self) -> None:
        if self._flushing or self.mqtt is None or not self.mqtt.connected:
            return
        pending = self.local.pending_ops(limit=50)
        if not pending:
            return
        self._flushing = True
        mqtt = self.mqtt

        def publish_all() -> list[str]:
            sent: list[str] = []
            for op in pending:
                mqtt.send(op)
                sent.append(op["op_id"])
            return sent

        self.runner.run(publish_all, self._on_outbox_flushed, self._on_outbox_flush_failed)

    def _on_outbox_flushed(self, sent: list[str]) -> None:
        for op_id in sent:
            self.local.drop_outbox(op_id)
        self._flushing = False
        self._update_sync_label()

    def _on_outbox_flush_failed(self, _exc: Exception) -> None:
        self._flushing = False
        self._update_sync_label()

    def _request_snapshot(self) -> None:
        """Yangi qurilma: boshqa qurilmalardan katalog va qoldiqni so'raydi (rate-limit bilan)."""
        now = datetime.now(UTC).timestamp()
        if now - self._last_snapshot_request < SNAPSHOT_REQUEST_INTERVAL_S or self.store is None:
            return
        self._last_snapshot_request = now
        request = self._new_op(o.SNAPSHOT_REQUEST, {})
        self._send_async(request)

    def _on_snapshot_requested(self, request: dict[str, Any]) -> None:
        """Boshqa qurilma so'radi: bizda ma'lumot bo'lsa, snapshot yuboramiz."""
        if self.store is None or request.get("store_id") != self.store_id or self.local.applied_count() == 0:
            return
        snapshot = self._new_op(o.SNAPSHOT, self.local.snapshot_payload(self.store_id))
        self._send_async(snapshot)

    def _send_async(self, op: dict[str, Any]) -> None:
        if self.mqtt is None or not self.mqtt.connected:
            return
        mqtt = self.mqtt
        self.runner.run(lambda: mqtt.send(op), lambda _r: None, lambda _e: None)

    def _update_sync_label(self) -> None:
        pending = self.local.pending_count()
        if self.mqtt is None:
            state = "—"
        elif self.mqtt.connected:
            state = "<span style='color:#15803d'>MQTT ulangan</span>"
        else:
            state = "<span style='color:#b91c1c'>MQTT uzilgan</span>"
        parts = [f"Sinxron: {state}"]
        if pending:
            parts.append(f"navbatda <b>{pending}</b>")
        self.sync_label.setText("  ·  ".join(parts))


__all__ = ["PosWindow"]
