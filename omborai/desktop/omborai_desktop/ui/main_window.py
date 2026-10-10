"""Kassa (POS) oynasi. Barcha tarmoq chaqiruvlari fon oqimida; savdo idempotent yuboriladi."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from PySide6.QtCore import Qt, QTimer
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

from ..api import ApiClient, ApiError
from ..cart import Cart
from ..config import DesktopConfig
from ..escpos import build_receipt_bytes, send_to_network_printer
from ..money import format_qty, format_som
from ..offline.store import LocalStore
from ..receipt import render_receipt
from .dialogs import CloseShiftDialog, OpenShiftDialog, PaymentDialog, ReceiptDialog, RefundDialog, parse_som
from .tasks import BackgroundRunner

ROLE_PRODUCT_ID = Qt.ItemDataRole.UserRole


class PosWindow(QMainWindow):
    def __init__(
        self,
        api: ApiClient,
        config: DesktopConfig,
        runner: Any | None = None,
        local: LocalStore | None = None,
        mqtt: Any | None = None,
        refresh_interval_ms: int = 15_000,
    ) -> None:
        super().__init__()
        self.api = api
        self.config = config
        self.runner = runner or BackgroundRunner(self)
        self.local = local or LocalStore()
        self.mqtt = mqtt  # MqttSync: savdo faqat MQTT orqali (docs/sync-mqtt.md)
        self.store: dict[str, Any] | None = None
        self.shift: dict[str, Any] | None = None
        self.cart = Cart()
        self._pending: dict[str, Any] | None = None  # serverga yuborilayotgan savdo (bir vaqtda bitta)
        self._filling_table = False
        self._flushing = False
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
        self.btn_shift = QPushButton("Smena")
        self.btn_shift.clicked.connect(self._on_shift_clicked)
        self.sync_label = QLabel("Sinxron: —")
        self.btn_refund = QPushButton("Qaytarish")
        self.btn_refund.clicked.connect(self._on_refund_clicked)

        top = QHBoxLayout()
        top.addWidget(self.store_label)
        top.addSpacing(24)
        top.addWidget(self.shift_label)
        top.addStretch(1)
        top.addWidget(self.sync_label)
        top.addWidget(self.btn_refund)
        top.addWidget(self.btn_shift)

        # Chap: skaner va qidiruv
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

        # O'ng: savat
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

    def _build_shortcuts(self) -> None:
        self._bind_shortcut("F2", self.search.setFocus)
        self._bind_shortcut("F12", self.pay)
        self._bind_shortcut("Delete", self._remove_selected, parent=self.table)
        self._bind_shortcut("Escape", self.search.clear, parent=self.search)

    def _bind_shortcut(self, key: str, action: Callable[[], None], parent: QWidget | None = None) -> None:
        shortcut = QShortcut(QKeySequence(key), parent or self)
        shortcut.activated.connect(action)

    # --- yordamchilar ------------------------------------------------------

    @property
    def store_id(self) -> str:
        if self.store is None:
            raise RuntimeError("Do'kon tanlanmagan")
        return str(self.store["id"])

    def _status(self, text: str) -> None:
        self.statusBar().showMessage(text, 8000)

    def _on_error(self, exc: Exception) -> None:
        if isinstance(exc, ApiError):
            QMessageBox.warning(self, "Xatolik", exc.message)
        elif isinstance(exc, httpx.HTTPError):
            self._status("Serverga ulanib bo'lmadi. Internet yoki server holatini tekshiring.")
        else:
            QMessageBox.critical(self, "Kutilmagan xatolik", str(exc))

    # --- boshlash: do'kon va smena -----------------------------------------

    def start(self) -> None:
        if self.mqtt is not None:
            self.runner.run(self.mqtt.start, self._on_mqtt_started, self._on_mqtt_failed)
        self._sync_timer.start()
        self.runner.run(self.api.stores, self._on_stores_loaded, self._on_error)

    def _on_mqtt_started(self, _result: Any) -> None:
        self._refresh_sync_state()

    def _on_mqtt_failed(self, exc: Exception) -> None:
        self._update_sync_label(ok=False)
        self._status(f"MQTT ulanmadi: {exc}")

    def _on_stores_loaded(self, stores: list[dict[str, Any]]) -> None:
        if not stores:
            QMessageBox.warning(self, "Do'kon yo'q", "Hisobingizga biriktirilgan do'kon topilmadi.")
            return
        self.store = stores[0]
        self.store_label.setText(f"Do'kon: <b>{self.store['name']}</b>")
        self._load_shift()

    def _load_shift(self) -> None:
        self.runner.run(lambda: self.api.current_shift(self.store_id), self._on_shift_loaded, self._on_error)

    def _on_shift_loaded(self, shift: dict[str, Any] | None) -> None:
        self.shift = shift
        self._show_shift_state()
        self._refresh_sync_state()
        if shift is None:
            self._open_shift_dialog()

    def _show_shift_state(self) -> None:
        if self.shift is None:
            self.shift_label.setText("Smena: <span style='color:#b91c1c'>yopiq</span>")
            self.btn_shift.setText("Smena ochish")
        else:
            self.shift_label.setText("Smena: <span style='color:#15803d'>ochiq</span>")
            self.btn_shift.setText("Smenani yopish")

    def _on_shift_clicked(self) -> None:
        if self.shift is None:
            self._open_shift_dialog()
        else:
            self._close_shift_dialog()

    def _open_shift_dialog(self) -> None:
        dialog = OpenShiftDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        cash = dialog.opening_cash()
        self.runner.run(
            lambda: self.api.open_shift(self.store_id, cash),
            self._on_shift_loaded,
            self._on_error,
        )

    def _close_shift_dialog(self) -> None:
        dialog = CloseShiftDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        shift_id, cash = str(self.shift["id"]), dialog.closing_cash()  # type: ignore[index]

        def on_closed(summary: dict[str, Any]) -> None:
            self.shift = None
            self._show_shift_state()
            methods = ", ".join(f"{k}: {format_som(v)}" for k, v in summary["by_method"].items()) or "—"
            QMessageBox.information(
                self,
                "Smena yopildi",
                f"Savdolar: {summary['sales_count']} ta, {format_som(summary['total_sales'])} so'm\n"
                f"Qaytarishlar: {summary['refunds_count']} ta, {format_som(summary['total_refunds'])} so'm\n"
                f"To'lov turlari: {methods}\n"
                f"Kutilgan naqd: {format_som(summary['expected_cash'])} so'm\n"
                f"Haqiqiy naqd: {format_som(cash)} so'm\n"
                f"Farq: {format_som(summary['difference'] or 0)} so'm",
            )

        self.runner.run(lambda: self.api.close_shift(shift_id, cash), on_closed, self._on_error)

    # --- qidiruv va savat ----------------------------------------------------

    def _on_search_submitted(self) -> None:
        text = self.search.text().strip()
        if not text:
            return
        if text.isdigit() and len(text) >= 4:  # skaner odatda raqamli kod yuboradi
            self.runner.run(
                lambda: self.api.product_by_barcode(text, self.store_id),
                lambda product: self._on_barcode_found(text, product),
                lambda exc: self._lookup_offline(text, exc, barcode=True),
            )
        else:
            self.runner.run(
                lambda: self.api.search_products(text, self.store_id),
                self._on_search_results,
                lambda exc: self._lookup_offline(text, exc, barcode=False),
            )

    def _lookup_offline(self, text: str, exc: Exception, *, barcode: bool) -> None:
        """Server bilan aloqa bo'lmasa, mahalliy keshdan qidiriladi."""
        if not isinstance(exc, httpx.HTTPError):
            self._on_error(exc)
            return
        self._status("Offline qidiruv (mahalliy kesh)")
        if barcode:
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

    # --- to'lov va savdo ---------------------------------------------------

    def pay(self) -> None:
        if self._pending is not None:
            self._status("Oldingi savdo yuborilmoqda, kuting")
            return
        if self.cart.is_empty:
            self._status("Savat bo'sh")
            return
        if self.shift is None:
            QMessageBox.warning(self, "Smena", "Avval smenani oching.")
            return
        dialog = PaymentDialog(self.cart.total, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        payload = self.cart.to_sale_payload(self.store_id, [(dialog.method, self.cart.total)])
        payload["number"] = self.local.next_receipt_number()
        payload["created_at"] = datetime.now(UTC).isoformat()
        self._pending = {"payload": payload, "change": dialog.change}
        self._send_sale(self._pending)

    def _send_sale(self, pending: dict[str, Any]) -> None:
        payload = pending["payload"]
        if self.mqtt is None or not self.mqtt.connected:
            self._queue_offline(pending)
            return
        self.btn_pay.setEnabled(False)
        self._status("Savdo yuborilmoqda...")
        mqtt = self.mqtt
        self.runner.run(
            lambda: mqtt.publish("sale", self.store_id, payload, op_id=payload["id"]),
            lambda op: self._on_sale_published(op, pending),
            lambda exc: self._on_sale_publish_failed(exc, pending),
        )

    def _on_sale_published(self, op: dict[str, Any], pending: dict[str, Any]) -> None:
        self.local.apply_op(op)  # o'z savdomizni mahalliy qoldiqqa darhol qo'llaymiz
        self._finish_sale(pending)

    def _on_sale_publish_failed(self, exc: Exception, pending: dict[str, Any]) -> None:
        # Yuborilganmi-yo'qmi noma'lum bo'lsa ham navbatga qo'yamiz: qayta yuborishda qabul qiluvchilar
        # op_id bo'yicha dublikatni rad etadi, shuning uchun ikki marta hisoblanmaydi
        self._queue_offline(pending)

    def _finish_sale(self, pending: dict[str, Any]) -> None:
        self._pending = None
        self.btn_pay.setEnabled(True)
        payload = pending["payload"]
        store_name = self.store["name"] if self.store else self.config.store_name_fallback
        text = render_receipt(payload, store_name, width=self.config.receipt_width, change=pending["change"])
        self.cart.clear()
        self._refresh_cart()
        self._update_sync_label()
        self._status(f"Chek #{payload['number']} saqlandi")
        dialog = ReceiptDialog(text, can_print=bool(self.config.printer_host), parent=self)
        dialog.exec()
        if dialog.print_requested:
            self._print(text)

    def _queue_offline(self, pending: dict[str, Any]) -> None:
        self._pending = None
        self.btn_pay.setEnabled(True)
        self.local.enqueue_sale(self.store_id, pending["payload"], datetime.now(UTC).isoformat())
        self._finish_sale_without_receipt(pending)

    def _finish_sale_without_receipt(self, pending: dict[str, Any]) -> None:
        self.cart.clear()
        self._refresh_cart()
        self._update_sync_label()
        self._status(f"Navbatga qo'yildi (aloqa tiklanganda yuboriladi): {self.local.pending_count()} ta")

    # --- sinxronizatsiya (MQTT) -----------------------------------------------

    def _refresh_sync_state(self) -> None:
        if self.mqtt is None:
            self._update_sync_label(ok=None)
            return
        connected = bool(self.mqtt.connected)
        self._update_sync_label(ok=connected)
        if connected:
            self._flush_outbox()

    def _flush_outbox(self) -> None:
        if self._flushing or self.mqtt is None or not self.mqtt.connected:
            return
        ops = self.local.pending_ops(limit=50)
        if not ops:
            return
        self._flushing = True
        mqtt = self.mqtt

        def publish_all() -> list[dict[str, Any]]:
            return [mqtt.publish("sale", op.store_id, op.payload, op_id=op.op_id) for op in ops]

        self.runner.run(publish_all, self._on_outbox_flushed, self._on_outbox_flush_failed)

    def _on_outbox_flushed(self, published: list[dict[str, Any]]) -> None:
        for op in published:
            self.local.apply_op(op)
            self.local.drop_outbox(op["op_id"])
        self._flushing = False
        self._update_sync_label(ok=True)

    def _on_outbox_flush_failed(self, exc: Exception) -> None:
        self._flushing = False
        self._update_sync_label(ok=False)

    def _update_sync_label(self, ok: bool | None = None) -> None:
        pending = self.local.pending_count()
        if self.mqtt is None or ok is None:
            state = "—"
        elif ok:
            state = "<span style='color:#15803d'>MQTT ulangan</span>"
        else:
            state = "<span style='color:#b91c1c'>MQTT uzilgan</span>"
        parts = [f"Sinxron: {state}"]
        if pending:
            parts.append(f"navbatda <b>{pending}</b>")
        self.sync_label.setText("  ·  ".join(parts))

    def _print(self, text: str) -> None:
        host = self.config.printer_host
        if not host:
            return
        data = build_receipt_bytes(text)
        self.runner.run(
            lambda: send_to_network_printer(host, data),
            lambda _r: self._status("Chek chop etildi"),
            lambda exc: self._on_print_failed(exc),
        )

    def _on_print_failed(self, exc: Exception) -> None:
        QMessageBox.warning(self, "Printer", f"Chop etib bo'lmadi: {exc}")

    # --- qaytarish ---------------------------------------------------------

    def _on_refund_clicked(self) -> None:
        self.runner.run(lambda: self.api.list_sales(self.store_id), self._open_refund_dialog, self._on_error)

    def _open_refund_dialog(self, sales: list[dict[str, Any]]) -> None:
        dialog = RefundDialog(sales, self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.sale_id is None:
            return
        sale_id = dialog.sale_id

        def on_refunded(sale: dict[str, Any]) -> None:
            self._status(f"Chek #{sale['number']} qaytarildi")
            self.runner.run(
                lambda: self.api.current_shift(self.store_id), self._on_shift_loaded, self._on_error
            )

        self.runner.run(lambda: self.api.refund_sale(sale_id), on_refunded, self._on_error)


__all__ = ["PosWindow"]
