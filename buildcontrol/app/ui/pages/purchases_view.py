"""Purchase requests, supplier quotes and orders (reused by page and tab)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSplitter, QWidget

from app.models.enums import OrderStatus, PurchaseStatus, Unit
from app.reports.pdf_reports import export_purchase_order
from app.services import counterparty_service, estimate_service, project_service, purchase_service
from app.services.permissions import Perm
from app.ui.dialogs.base_dialog import confirm, show_info
from app.ui.dialogs.form_dialog import (
    CHECK,
    COMBO,
    DATE,
    FILE,
    INT,
    MONEY,
    NUMBER,
    TEXT,
    TEXTAREA,
    Field,
    FormDialog,
)
from app.ui.pages.base_page import BasePage
from app.ui.styles.theme import COLORS, SPACING_SM
from app.ui.widgets.common import Card, button
from app.ui.widgets.table import (
    BADGE,
    Col,
    DataTable,
    make_combo,
)
from app.ui.widgets.table import (
    DATE as C_DATE,
)
from app.ui.widgets.table import (
    MONEY as C_MONEY,
)
from app.ui.widgets.table import (
    NUMBER as C_NUMBER,
)
from app.utils.files import open_path
from app.utils.formatting import fmt_money
from app.utils.i18n import tr
from app.utils.labels import options, order_status_label, purchase_status_label, unit_label

_STATUS_KIND = {
    PurchaseStatus.DRAFT.value: "neutral",
    PurchaseStatus.SUBMITTED.value: "warning",
    PurchaseStatus.APPROVED.value: "success",
    PurchaseStatus.REJECTED.value: "danger",
    PurchaseStatus.ORDERED.value: "accent",
    PurchaseStatus.PARTIAL.value: "info",
    PurchaseStatus.COMPLETED.value: "success",
}


class PurchasesView(BasePage):
    """Two-pane purchasing workspace: requests on top, quotes below."""

    permission = Perm.PURCHASE_VIEW

    def __init__(
        self,
        project_id: int | None = None,
        parent: QWidget | None = None,
        show_header: bool = True,
    ) -> None:
        super().__init__(
            tr("nav_purchases"),
            "",
            parent,
            show_header=show_header,
            compact=not show_header,
        )
        self.project_id = project_id

        self.new_btn = button(tr("new_request"), "add", "Primary")
        self.new_btn.clicked.connect(self._create_request)
        self.new_btn.setEnabled(self.can(Perm.PURCHASE_EDIT))
        self.header.add_action(self.new_btn)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        self.table = DataTable(self._request_columns())
        self.table.selection_changed.connect(self._on_request_selected)
        self.table.row_activated.connect(lambda _row: self._edit_request())
        self.status_filter = make_combo(options(PurchaseStatus, include_all=True))
        self.status_filter.currentIndexChanged.connect(self.refresh)
        self.table.add_filter(self.status_filter)
        if project_id is None:
            self.project_filter = make_combo(project_service.project_choices())
            self.project_filter.currentIndexChanged.connect(self.refresh)
            self.table.add_filter(self.project_filter)
        else:
            self.project_filter = None
        if not show_header:
            # Embedded as a project tab: the create button moves into the toolbar.
            self.table.add_action(self.new_btn)

        self.edit_btn = button(tr("edit"), "edit")
        self.edit_btn.clicked.connect(self._edit_request)
        self.submit_btn = button(tr("submit_for_approval"), "up")
        self.submit_btn.clicked.connect(lambda: self._set_status(PurchaseStatus.SUBMITTED.value))
        self.approve_btn = button(tr("approve"), "approve", "Success")
        self.approve_btn.clicked.connect(lambda: self._set_status(PurchaseStatus.APPROVED.value))
        self.reject_btn = button(tr("reject"), "reject", "Danger")
        self.reject_btn.clicked.connect(lambda: self._set_status(PurchaseStatus.REJECTED.value))
        for widget in (self.edit_btn, self.submit_btn, self.approve_btn, self.reject_btn):
            self.table.add_action(widget)
        splitter.addWidget(self.table)

        splitter.addWidget(self._build_quotes_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        self.root.addWidget(splitter, 1)
        self._on_request_selected(None)

    # -- construction --------------------------------------------------------- #
    def _request_columns(self) -> list[Col]:
        columns = [
            Col("number", "№", width=90),
            Col("title", tr("product_service"), stretch=True),
        ]
        if self.project_id is None:
            columns.append(Col("project", tr("project"), width=180))
        columns += [
            Col(
                "estimate_item",
                tr("estimate_item"),
                width=180,
                formatter=lambda r: r["estimate_item"]
                or (tr("off_estimate") if r["off_estimate"] else "—"),
                color=lambda r: COLORS.warning if r["off_estimate"] else None,
            ),
            Col("quantity", tr("quantity"), C_NUMBER, width=90),
            Col("unit", tr("unit"), width=80, formatter=lambda r: unit_label(r["unit"])),
            Col("est_total", tr("est_price"), C_MONEY, width=140),
            Col("selected_supplier", tr("supplier"), width=160),
            Col("selected_total", tr("total_value"), C_MONEY, width=140),
            Col("needed_date", tr("needed_date"), C_DATE, width=110),
            Col(
                "status",
                tr("status"),
                BADGE,
                width=150,
                badge=lambda r: (
                    purchase_status_label(r["status"]),
                    _STATUS_KIND.get(r["status"], "neutral"),
                ),
            ),
        ]
        return columns

    def _build_quotes_panel(self) -> QWidget:
        card = Card(tr("quotes"))
        self.best_label = QLabel("—")
        self.best_label.setObjectName("Hint")
        card.body().addWidget(self.best_label)

        self.quotes_table = DataTable(
            [
                Col("supplier_name", tr("supplier"), stretch=True),
                Col("contact", tr("contact"), width=150),
                Col("unit_price", tr("unit_price"), C_MONEY, width=140),
                Col("delivery_cost", tr("delivery_cost"), C_MONEY, width=140),
                Col("total_value", tr("total_value"), C_MONEY, width=150),
                Col("delivery_days", tr("delivery_days"), C_NUMBER, width=110),
                Col("payment_terms", tr("payment_terms"), width=150),
                Col(
                    "mark",
                    "",
                    BADGE,
                    width=130,
                    badge=lambda r: (r["mark"], r["mark_kind"]),
                ),
            ],
            searchable=False,
            paginated=False,
        )
        card.body().addWidget(self.quotes_table, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(SPACING_SM)
        self.add_quote_btn = button(tr("add_quote"), "add")
        self.add_quote_btn.clicked.connect(self._add_quote)
        self.edit_quote_btn = button(tr("edit"), "edit")
        self.edit_quote_btn.clicked.connect(self._edit_quote)
        self.select_quote_btn = button(tr("select_quote"), "approve", "Success")
        self.select_quote_btn.clicked.connect(self._select_quote)
        self.delete_quote_btn = button(tr("delete"), "delete", "Ghost")
        self.delete_quote_btn.clicked.connect(self._delete_quote)
        self.order_btn = button(tr("create_order"), "money", "Primary")
        self.order_btn.clicked.connect(self._create_order)
        self.order_pdf_btn = button(tr("export_pdf"), "pdf")
        self.order_pdf_btn.clicked.connect(self._export_order)
        for widget in (
            self.add_quote_btn,
            self.edit_quote_btn,
            self.select_quote_btn,
            self.delete_quote_btn,
        ):
            buttons.addWidget(widget)
        buttons.addStretch(1)
        buttons.addWidget(self.order_btn)
        buttons.addWidget(self.order_pdf_btn)
        card.body().addLayout(buttons)
        return card

    # -- data ----------------------------------------------------------------- #
    def refresh(self) -> None:
        """Reload requests and the quote panel."""
        project_id = self.project_id
        if project_id is None and self.project_filter is not None:
            project_id = self.project_filter.currentData() or None
        rows = purchase_service.list_requests(
            project_id=project_id, status=self.status_filter.currentData() or ""
        )
        self.table.set_rows(rows)
        self._on_request_selected(self.table.current_row())

    def _selected_request(self) -> dict | None:
        return self.table.current_row()

    def _on_request_selected(self, row: dict | None) -> None:
        may_edit = self.can(Perm.PURCHASE_EDIT)
        may_approve = self.can(Perm.PURCHASE_APPROVE)
        has = row is not None
        self.edit_btn.setEnabled(has and may_edit)
        self.submit_btn.setEnabled(has and may_edit and row["status"] == PurchaseStatus.DRAFT.value)
        self.approve_btn.setEnabled(
            has and may_approve and row["status"] == PurchaseStatus.SUBMITTED.value
        )
        self.reject_btn.setEnabled(
            has and may_approve and row["status"] == PurchaseStatus.SUBMITTED.value
        )
        self.add_quote_btn.setEnabled(has and may_edit)
        self.order_btn.setEnabled(has and may_approve)
        for widget in (self.edit_quote_btn, self.select_quote_btn, self.delete_quote_btn):
            widget.setEnabled(has and may_edit)
        self.order_pdf_btn.setEnabled(has)
        if not has:
            self.quotes_table.set_rows([])
            self.best_label.setText("—")
            return
        quotes = purchase_service.list_quotes(row["id"])
        rows = []
        for quote in quotes:
            if quote.is_selected:
                mark, kind = tr("select_quote"), "success"
            elif quote.is_best:
                mark, kind = tr("best_offer"), "accent"
            elif quote.is_cheapest:
                mark, kind = tr("best_price"), "info"
            elif quote.is_fastest:
                mark, kind = tr("fastest"), "warning"
            else:
                mark, kind = "", "neutral"
            rows.append(
                {
                    "id": quote.id,
                    "supplier_name": quote.supplier_name,
                    "contact": quote.contact,
                    "unit_price": quote.unit_price,
                    "delivery_cost": quote.delivery_cost,
                    "total_value": quote.total_value,
                    "delivery_days": quote.delivery_days,
                    "payment_terms": quote.payment_terms,
                    "file_path": quote.file_path,
                    "supplier_id": quote.supplier_id,
                    "is_selected": quote.is_selected,
                    "mark": mark,
                    "mark_kind": kind,
                }
            )
        self.quotes_table.set_rows(rows)
        best = next((q for q in quotes if q.is_best), None)
        if best is not None:
            self.best_label.setText(
                f"{tr('best_offer')}: {best.supplier_name} · {fmt_money(best.total_value)} · "
                f"{best.delivery_days} {tr('delivery_days').lower()}"
            )
        else:
            self.best_label.setText(tr("no_data"))

    # -- request actions ------------------------------------------------------ #
    def _request_fields(self, project_id: int | None) -> list[Field]:
        items = estimate_service.item_choices(project_id) if project_id else [("", "—")]
        projects = project_service.project_choices(include_all=False)
        fields = []
        if self.project_id is None:
            fields.append(
                Field("project_id", tr("project"), COMBO, required=True, options=projects)
            )
        fields += [
            Field("title", tr("product_service"), TEXT, required=True, span=2),
            Field("off_estimate", tr("off_estimate"), CHECK),
            Field(
                "estimate_item_id",
                tr("estimate_item"),
                COMBO,
                options=items,
                visible_if=lambda v: not v.get("off_estimate"),
                span=2,
            ),
            Field("quantity", tr("quantity"), NUMBER, required=True, decimals=2),
            Field("unit", tr("unit"), COMBO, options=options(Unit)),
            Field("est_price", tr("est_price"), MONEY),
            Field("needed_date", tr("needed_date"), DATE),
            Field("delivery_address", tr("delivery_address"), TEXT, span=2),
            Field(
                "responsible_id",
                tr("responsible"),
                COMBO,
                options=project_service.user_choices(),
            ),
            Field("status", tr("status"), COMBO, options=options(PurchaseStatus)),
            Field("note", tr("note"), TEXTAREA, span=2),
        ]
        return fields

    def _create_request(self) -> None:
        project_id = self.project_id
        dialog = FormDialog(
            tr("new_request"),
            self._request_fields(project_id),
            {"status": PurchaseStatus.DRAFT.value, "unit": Unit.PIECE.value},
            parent=self,
        )
        if not dialog.exec():
            return
        values = dialog.values()
        values.setdefault("project_id", project_id)
        self._save_request(values, None)

    def _edit_request(self) -> None:
        row = self._selected_request()
        if row is None:
            return
        dialog = FormDialog(
            tr("purchase_request"),
            self._request_fields(row["project_id"]),
            row,
            row["number"],
            parent=self,
        )
        if not dialog.exec():
            return
        values = dialog.values()
        values.setdefault("project_id", row["project_id"])
        self._save_request(values, row["id"])

    def _save_request(self, values: dict, request_id: int | None) -> None:
        values["project_id"] = values.get("project_id") or self.project_id
        values["estimate_item_id"] = values.get("estimate_item_id") or None
        values["responsible_id"] = values.get("responsible_id") or None
        try:
            purchase_service.save_request(values, self.actor, request_id)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    def _set_status(self, status: str) -> None:
        row = self._selected_request()
        if row is None:
            return
        try:
            purchase_service.set_request_status(row["id"], status, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    # -- quote actions -------------------------------------------------------- #
    def _quote_fields(self) -> list[Field]:
        return [
            Field(
                "supplier_id",
                tr("supplier"),
                COMBO,
                options=counterparty_service.counterparty_choices("supplier"),
                span=2,
            ),
            Field("supplier_name", tr("company_name"), TEXT, span=2),
            Field("contact", tr("contact"), TEXT),
            Field("unit_price", tr("unit_price"), MONEY, required=True),
            Field("delivery_cost", tr("delivery_cost"), MONEY),
            Field("delivery_days", tr("delivery_days"), INT, maximum=999),
            Field("payment_terms", tr("payment_terms"), TEXT),
            Field("file_path", tr("quote_file"), FILE, span=2),
        ]

    def _add_quote(self) -> None:
        row = self._selected_request()
        if row is None:
            return
        dialog = FormDialog(tr("add_quote"), self._quote_fields(), {}, row["title"], parent=self)
        if not dialog.exec():
            return
        self._save_quote(row["id"], dialog.values(), None)

    def _edit_quote(self) -> None:
        request = self._selected_request()
        quote = self.quotes_table.current_row()
        if request is None or quote is None:
            return
        dialog = FormDialog(tr("edit"), self._quote_fields(), quote, request["title"], parent=self)
        if not dialog.exec():
            return
        self._save_quote(request["id"], dialog.values(), quote["id"])

    def _save_quote(self, request_id: int, values: dict, quote_id: int | None) -> None:
        values["supplier_id"] = values.get("supplier_id") or None
        if not values.get("supplier_name") and values.get("supplier_id"):
            values["supplier_name"] = ""
        try:
            purchase_service.save_quote(request_id, values, self.actor, quote_id)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    def _select_quote(self) -> None:
        quote = self.quotes_table.current_row()
        if quote is None:
            self.notify(tr("select_row_first"), "warning")
            return
        try:
            purchase_service.select_quote(quote["id"], self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.refresh()

    def _delete_quote(self) -> None:
        quote = self.quotes_table.current_row()
        if quote is None or not confirm(self, tr("confirm_question"), tr("delete")):
            return
        try:
            purchase_service.delete_quote(quote["id"], self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.refresh()

    def _create_order(self) -> None:
        row = self._selected_request()
        if row is None:
            return
        try:
            order_id = purchase_service.create_order(row["id"], self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()
        self._offer_pdf(order_id)

    def _export_order(self) -> None:
        row = self._selected_request()
        if row is None:
            return
        orders = [o for o in purchase_service.list_orders() if o["request_id"] == row["id"]]
        if not orders:
            self.notify(tr("no_data"), "warning")
            return
        self._offer_pdf(orders[-1]["id"])

    def _offer_pdf(self, order_id: int) -> None:
        try:
            path = export_purchase_order(order_id)
        except Exception as exc:
            self.handle(exc)
            return
        show_info(self, f"{tr('report_saved')}:\n{path}")
        open_path(path)


class OrdersView(BasePage):
    """Read-only register of the issued purchase orders."""

    permission = Perm.PURCHASE_VIEW

    def __init__(self, project_id: int | None = None, parent: QWidget | None = None) -> None:
        super().__init__(tr("purchase_order"), "", parent, show_header=False, compact=True)
        self.project_id = project_id
        self.table = DataTable(
            [
                Col("order_no", tr("order_no"), width=110),
                Col("order_date", tr("date"), C_DATE, width=110),
                Col("title", tr("product_service"), stretch=True),
                Col("supplier", tr("supplier"), width=180),
                Col("quantity", tr("quantity"), C_NUMBER, width=90),
                Col("total_amount", tr("amount"), C_MONEY, width=150),
                Col(
                    "status",
                    tr("status"),
                    BADGE,
                    width=140,
                    badge=lambda r: (order_status_label(r["status"]), _order_kind(r["status"])),
                ),
            ]
        )
        self.pdf_btn = button(tr("export_pdf"), "pdf")
        self.pdf_btn.clicked.connect(self._export)
        self.table.add_action(self.pdf_btn)
        self.delivered_btn = button(tr("approve"), "approve", "Success")
        self.delivered_btn.clicked.connect(self._mark_delivered)
        self.delivered_btn.setEnabled(self.can(Perm.PURCHASE_EDIT))
        self.table.add_action(self.delivered_btn)
        self.root.addWidget(self.table, 1)

    def refresh(self) -> None:
        """Reload the order register."""
        self.table.set_rows(purchase_service.list_orders(self.project_id))

    def _export(self) -> None:
        row = self.table.current_row()
        if row is None:
            return
        try:
            path = export_purchase_order(row["id"])
        except Exception as exc:
            self.handle(exc)
            return
        show_info(self, f"{tr('report_saved')}:\n{path}")
        open_path(path)

    def _mark_delivered(self) -> None:
        row = self.table.current_row()
        if row is None:
            return
        try:
            purchase_service.set_order_status(row["id"], OrderStatus.DELIVERED.value, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()


def _order_kind(status: str) -> str:
    return {
        OrderStatus.NEW.value: "neutral",
        OrderStatus.SENT.value: "info",
        OrderStatus.DELIVERED.value: "success",
        OrderStatus.CANCELLED.value: "danger",
    }.get(status, "neutral")
