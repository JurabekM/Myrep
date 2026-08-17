"""Quotation workflow page and its line-item editor."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.config import SUPPORTED_CURRENCIES
from app.controllers.app_context import AppContext
from app.reports import build_quotation_pdf, export_excel
from app.services import auth_service, buyer_service, product_service, quotation_service
from app.ui.i18n import t, te
from app.ui.pages.base_page import RecordPage
from app.ui.widgets.common import (
    banner,
    button,
    combo,
    combo_value,
    date_edit,
    date_value,
    line_edit,
    section_title,
    spin,
    text_area,
)
from app.ui.widgets.items_editor import ItemColumn, ItemsEditor
from app.ui.widgets.table import Column, FilterSpec
from app.utils.enums import INCOTERMS, PAYMENT_TERMS, QUOTATION_STATUSES, UNITS
from app.utils.errors import ExportFlowError
from app.utils.formatting import fmt_date, fmt_money, today


def show_error(parent: QWidget, exc: Exception) -> None:
    """Show a translated error message from a non-page widget."""
    from PySide6.QtWidgets import QMessageBox

    if isinstance(exc, ExportFlowError):
        params = {k: v for k, v in exc.params.items() if isinstance(v, (str, int, float))}
        message = t(exc.key, **params)
    else:
        message = f"{t('error.generic')}\n\n{type(exc).__name__}: {exc}"
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(t("app.title"))
    box.setText(message)
    box.exec()


class QuotationEditor(QDialog):
    """Full quotation editor with live totals and validation warnings."""

    def __init__(
        self,
        ctx: AppContext,
        quotation_id: int | None,
        parent: QWidget | None = None,
        lead_id: int | None = None,
        buyer_id: int | None = None,
        rfq_id: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.quotation_id = quotation_id
        self.saved_id: int | None = None
        self.setModal(True)
        self.setWindowTitle(t("quotation.new") if not quotation_id else t("quotation.title"))
        self.resize(1080, 760)

        def _reference(session: Session) -> dict:
            return {
                "buyers": [
                    (row["id"], f"{row['company_name']} ({row['country']})")
                    for row in buyer_service.search_buyers(session)
                ],
                "products": [
                    (row["id"], f"{row['sku']} — {row['name']}")
                    for row in product_service.search_products(session, lang=ctx.language())
                ],
                "managers": [
                    (user["id"], user["full_name"] or user["username"])
                    for user in auth_service.list_users(session)
                ],
            }

        self.reference = ctx.read(_reference)
        self.data: dict[str, Any] = {
            "currency": "USD",
            "incoterm": "FOB",
            "language": "en",
            "issue_date": today(),
            "buyer_id": buyer_id,
            "lead_id": lead_id,
            "rfq_id": rfq_id,
            "status": "draft",
            "items": [],
        }
        if quotation_id:
            self.data = ctx.read(lambda s: quotation_service.quotation_dict(s, quotation_id))

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)

        title = QLabel(self.data.get("number") or t("quotation.new"))
        title.setObjectName("PageTitle")
        root.addWidget(title)

        self.warning_banner = banner("", "warning")
        self.warning_banner.setVisible(False)
        root.addWidget(self.warning_banner)

        columns_row = QHBoxLayout()
        columns_row.setSpacing(18)
        left = QFormLayout()
        right = QFormLayout()
        left.setSpacing(8)
        right.setSpacing(8)

        self.buyer_combo = combo(self.reference["buyers"], self.data.get("buyer_id"), False)
        self.manager_combo = combo(self.reference["managers"], self.data.get("manager_id"), True)
        self.language_combo = combo(
            [("en", "English"), ("ru", "Русский"), ("uz", "O‘zbekcha")],
            self.data.get("language"),
            False,
        )
        self.currency_combo = combo(
            [(c, c) for c in SUPPORTED_CURRENCIES], self.data.get("currency"), False
        )
        self.issue_date = date_edit(self.data.get("issue_date"))
        self.valid_until = date_edit(self.data.get("valid_until"))
        left.addRow(t("common.buyer"), self.buyer_combo)
        left.addRow(t("common.manager"), self.manager_combo)
        left.addRow(t("common.language"), self.language_combo)
        left.addRow(t("common.currency"), self.currency_combo)
        left.addRow(t("quotation.issue_date"), self.issue_date)
        left.addRow(t("quotation.valid_until"), self.valid_until)

        self.incoterm_combo = combo([(i, i) for i in INCOTERMS], self.data.get("incoterm"), False)
        self.loading_port = line_edit("", self.data.get("loading_port") or "")
        self.destination = line_edit("", self.data.get("destination") or "")
        self.payment_terms = combo(
            [(p, p) for p in PAYMENT_TERMS], self.data.get("payment_terms"), True
        )
        self.payment_terms.setEditable(True)
        if self.data.get("payment_terms"):
            self.payment_terms.setCurrentText(self.data["payment_terms"])
        self.delivery_terms = line_edit("", self.data.get("delivery_terms") or "")
        self.lead_time = spin(0, 999, self.data.get("lead_time_days") or 0, 0)
        right.addRow(t("common.incoterm"), self.incoterm_combo)
        right.addRow(t("quotation.loading_port"), self.loading_port)
        right.addRow(t("common.destination"), self.destination)
        right.addRow(t("quotation.payment_terms"), self.payment_terms)
        right.addRow(t("quotation.delivery_terms"), self.delivery_terms)
        right.addRow(t("quotation.lead_time"), self.lead_time)

        columns_row.addLayout(left, 1)
        columns_row.addLayout(right, 1)
        root.addLayout(columns_row)

        root.addWidget(section_title(t("quotation.items")))
        self.items_editor = ItemsEditor(
            [
                ItemColumn("description", t("common.description"), "text", width=280),
                ItemColumn("hs_code", t("product.hs_code"), "text", width=90),
                ItemColumn("quantity", t("common.quantity"), "number", width=90, decimals=2),
                ItemColumn("unit", t("common.unit"), "combo", 80, [(u, u) for u in UNITS]),
                ItemColumn("unit_price", t("price.unit_price"), "money", width=100, decimals=4),
                ItemColumn("cost_price", t("quotation.cost_price"), "money", width=100, decimals=4),
                ItemColumn("moq", t("product.moq"), "number", width=80, decimals=0),
                ItemColumn("packaging", t("quotation.packaging"), "text", width=160),
            ],
            self.data.get("items", []),
            on_add=self._pick_price_line,
        )
        self.items_editor.changed.connect(self._recalculate)
        root.addWidget(self.items_editor, 1)

        totals_row = QHBoxLayout()
        totals_row.setSpacing(12)
        self.freight = spin(0, 1e9, self.data.get("freight_cost") or 0)
        self.insurance = spin(0, 1e9, self.data.get("insurance_cost") or 0)
        self.discount = spin(0, 1e9, self.data.get("discount") or 0)
        for widget in (self.freight, self.insurance, self.discount):
            widget.valueChanged.connect(self._recalculate)
        totals_row.addWidget(QLabel(t("quotation.freight")))
        totals_row.addWidget(self.freight)
        totals_row.addWidget(QLabel(t("quotation.insurance")))
        totals_row.addWidget(self.insurance)
        totals_row.addWidget(QLabel(t("quotation.discount")))
        totals_row.addWidget(self.discount)
        totals_row.addStretch(1)
        self.totals_label = QLabel("")
        self.totals_label.setObjectName("SectionTitle")
        totals_row.addWidget(self.totals_label)
        root.addLayout(totals_row)

        texts_row = QHBoxLayout()
        texts_row.setSpacing(12)
        self.intro = text_area(t("quotation.intro"), self.data.get("intro_text") or "", 70)
        self.remarks = text_area(t("quotation.remarks"), self.data.get("remarks") or "", 70)
        self.packaging = text_area(t("quotation.packaging"), self.data.get("packaging") or "", 70)
        texts_row.addWidget(self.intro)
        texts_row.addWidget(self.packaging)
        texts_row.addWidget(self.remarks)
        root.addLayout(texts_row)

        self.certificate_refs = line_edit(
            t("quotation.certificate_refs"), self.data.get("certificate_refs") or ""
        )
        root.addWidget(self.certificate_refs)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(button(t("common.cancel"), self.reject, "Ghost"))
        buttons.addWidget(button(t("common.save"), self._save, "Primary"))
        root.addLayout(buttons)

        self._recalculate()

    # ------------------------------------------------------------- helpers
    def _collect(self) -> dict[str, Any]:
        return {
            "id": self.quotation_id,
            "buyer_id": combo_value(self.buyer_combo),
            "lead_id": self.data.get("lead_id"),
            "rfq_id": self.data.get("rfq_id"),
            "manager_id": combo_value(self.manager_combo),
            "language": combo_value(self.language_combo),
            "currency": combo_value(self.currency_combo),
            "issue_date": date_value(self.issue_date) or today(),
            "valid_until": date_value(self.valid_until),
            "incoterm": combo_value(self.incoterm_combo),
            "loading_port": self.loading_port.text().strip(),
            "destination": self.destination.text().strip(),
            "payment_terms": self.payment_terms.currentText().strip(),
            "delivery_terms": self.delivery_terms.text().strip(),
            "lead_time_days": int(self.lead_time.value()) or None,
            "freight_cost": self.freight.value(),
            "insurance_cost": self.insurance.value(),
            "discount": self.discount.value(),
            "intro_text": self.intro.toPlainText().strip(),
            "remarks": self.remarks.toPlainText().strip(),
            "packaging": self.packaging.toPlainText().strip(),
            "certificate_refs": self.certificate_refs.text().strip(),
        }

    def _recalculate(self) -> None:
        items = self.items_editor.rows()
        totals = quotation_service.compute_totals(
            items, self.freight.value(), self.insurance.value(), self.discount.value()
        )
        currency = combo_value(self.currency_combo) or "USD"
        self.totals_label.setText(
            f"{t('quotation.subtotal')}: {fmt_money(totals['subtotal'], currency)}   ·   "
            f"{t('quotation.grand_total')}: {fmt_money(totals['grand_total'], currency)}   ·   "
            f"{t('quotation.margin')}: {totals['margin_percent']:.1f}%"
        )
        self.items_editor.set_summary(t("common.rows", count=len(items)))
        warnings = self.ctx.read(
            lambda s: quotation_service.validate_quotation(s, self._collect(), items)
        )
        if warnings:
            self.warning_banner.setText(
                t("quotation.warnings") + ": " + "; ".join(t(code) for code in warnings)
            )
            self.warning_banner.setVisible(True)
        else:
            self.warning_banner.setVisible(False)

    def _pick_price_line(self) -> dict | None:
        """Add a line built from an approved, still valid price."""
        labels = [label for _pid, label in self.reference["products"]]
        if not labels:
            return None
        choice, ok = QInputDialog.getItem(
            self, t("common.product"), t("common.product"), labels, 0, False
        )
        if not ok:
            return None
        product_id = self.reference["products"][labels.index(choice)][0]
        prices = self.ctx.read(
            lambda s: [
                {
                    "id": price.id,
                    "label": f"{price.custom_incoterm or price.incoterm} · "
                    f"{price.unit_price:,.2f} {price.currency} · {price.origin_point or ''}",
                }
                for price in product_service.valid_prices_for_product(s, product_id)
            ]
        )
        if not prices:
            self.ctx.show_toast(t("price.only_approved"), "warning")
            return None
        price_labels = [price["label"] for price in prices]
        price_choice, ok = QInputDialog.getItem(
            self, t("quotation.add_from_price"), t("common.price"), price_labels, 0, False
        )
        if not ok:
            return None
        price_id = prices[price_labels.index(price_choice)]["id"]
        quantity, ok = QInputDialog.getDouble(
            self, t("common.quantity"), t("common.quantity"), 1000, 0, 1e9, 2
        )
        if not ok:
            return None
        return self.ctx.read(
            lambda s: quotation_service.suggest_line_from_price(s, product_id, price_id, quantity)
        )

    def _save(self) -> None:
        values = self._collect()
        items = self.items_editor.rows()
        try:
            self.saved_id = self.ctx.run(
                lambda s: quotation_service.save_quotation(s, self.ctx.user, values, items).id
            )
        except Exception as exc:
            show_error(self, exc)
            return
        self.accept()


def open_quotation_editor(
    parent: QWidget,
    ctx: AppContext,
    quotation_id: int | None,
    lead_id: int | None = None,
    buyer_id: int | None = None,
    rfq_id: int | None = None,
) -> bool:
    """Convenience wrapper used from several pages."""
    dialog = QuotationEditor(ctx, quotation_id, parent, lead_id, buyer_id, rfq_id)
    return bool(dialog.exec())


class QuotationsPage(RecordPage):
    """Quotation register with the approval and sending workflow."""

    permission = "quotation.view"
    title_key = "quotation.title"
    topics = ("quotation", "lead", "buyer")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        if ctx.can("quotation.edit"):
            self.header.add_action(button(t("quotation.new"), self.on_new, "Primary"))
        self.header.add_action(button(t("common.export"), self.on_export, "Ghost"))

    def columns(self) -> list[Column]:
        """Column layout of the quotation table."""
        return [
            Column("number", t("quotation.number"), width=120),
            Column("buyer", t("common.buyer"), stretch=True),
            Column("country", t("common.country"), width=100),
            Column("issue_date", t("quotation.issue_date"), kind="date", width=115),
            Column("valid_until", t("quotation.valid_until"), kind="date", width=150),
            Column("incoterm", t("common.incoterm"), width=80),
            Column("destination", t("common.destination"), width=150),
            Column("grand_total", t("quotation.grand_total"), kind="money", width=130),
            Column(
                "status", t("common.status"), kind="status", group="quotation_status", width=140
            ),
            Column("manager", t("common.manager"), width=130),
        ]

    def filter_specs(self) -> list[FilterSpec]:
        """Filters for the quotation table."""
        return [
            FilterSpec(
                "status", t("common.status"), "enum", QUOTATION_STATUSES, "quotation_status", 150
            ),
            FilterSpec(
                "incoterm", t("common.incoterm"), "combo", [(i, i) for i in INCOTERMS], width=110
            ),
            FilterSpec(
                "currency",
                t("common.currency"),
                "combo",
                [(c, c) for c in SUPPORTED_CURRENCIES],
                width=100,
            ),
            FilterSpec("date_from", t("common.date_from"), "date", width=120),
            FilterSpec("date_to", t("common.date_to"), "date", width=120),
        ]

    def load_rows(self, filters: dict[str, Any]) -> list[dict]:
        """Fetch quotations matching the filter bar."""

        def _load(session: Session) -> list[dict]:
            return quotation_service.list_quotations(
                session,
                text=filters.get("text", ""),
                status=filters.get("status"),
                incoterm=filters.get("incoterm"),
                currency=filters.get("currency"),
                date_from=filters.get("date_from"),
                date_to=filters.get("date_to"),
            )

        return self.ctx.read(_load)

    # ------------------------------------------------------------- detail
    def fill_detail(self, row: dict) -> None:
        """Populate the quotation detail panel with workflow actions."""
        data = self.ctx.read(lambda s: quotation_service.quotation_dict(s, row["id"]))
        self.detail.set_header(
            data["number"],
            f"{data['buyer']} · {fmt_money(data['grand_total'], data['currency'])}",
            "quotation_status",
            data["status"],
        )
        can_edit = self.ctx.can("quotation.edit")
        if can_edit:
            self.detail.add_action(t("common.edit"), lambda: self.open_editor(row["id"]), "Primary")
        if can_edit and data["status"] in ("draft", "review_required"):
            self.detail.add_action(t("quotation.submit_review"), lambda: self._submit(row["id"]))
        if self.ctx.can("quotation.approve") and data["status"] in ("draft", "review_required"):
            self.detail.add_action(
                t("quotation.approve"), lambda: self._approve(row["id"]), "Success"
            )
        if self.ctx.can("quotation.send") and data["status"] == "approved":
            self.detail.add_action(
                t("quotation.mark_sent"), lambda: self._mark_sent(row["id"]), "Success"
            )
        if can_edit:
            self.detail.add_action(t("quotation.set_status"), lambda: self._set_status(row["id"]))
            self.detail.add_action(t("common.copy"), lambda: self._duplicate(row["id"]))
        self.detail.add_action(t("quotation.export_pdf"), lambda: self._export_pdf(row["id"]))
        if self.ctx.can("email.send"):
            self.detail.add_action(t("quotation.email_draft"), lambda: self._email(data))

        self.detail.add_fields_tab(
            t("common.details"),
            [
                (t("common.buyer"), data["buyer"]),
                (t("quotation.issue_date"), fmt_date(data["issue_date"])),
                (t("quotation.valid_until"), fmt_date(data["valid_until"])),
                (t("common.incoterm"), data["incoterm"]),
                (t("quotation.loading_port"), data["loading_port"]),
                (t("common.destination"), data["destination"]),
                (t("quotation.payment_terms"), data["payment_terms"]),
                (t("quotation.lead_time"), data["lead_time_days"]),
                (t("quotation.subtotal"), fmt_money(data["subtotal"], data["currency"])),
                (t("quotation.freight"), fmt_money(data["freight_cost"], data["currency"])),
                (t("quotation.insurance"), fmt_money(data["insurance_cost"], data["currency"])),
                (t("quotation.discount"), fmt_money(data["discount"], data["currency"])),
                (t("quotation.grand_total"), fmt_money(data["grand_total"], data["currency"])),
                (t("quotation.certificate_refs"), data["certificate_refs"]),
                (t("quotation.remarks"), data["remarks"]),
            ],
        )
        self.detail.add_list_tab(
            t("quotation.items"),
            [
                f"{item['description']} · {item['quantity']:g} {item['unit']} × "
                f"{fmt_money(item['unit_price'], data['currency'])} = "
                f"{fmt_money(item['line_total'], data['currency'])}"
                for item in data["items"]
            ],
        )
        self.detail.add_list_tab(
            t("quotation.versions"),
            [
                f"rev.{v['revision']} · {te('quotation_status', v['status'])} · "
                f"{fmt_money(v['grand_total'], data['currency'])} · {v['comment']}"
                for v in data["versions"]
            ],
        )

    def on_row_activated(self, row: dict) -> None:
        """Open the editor on double click."""
        if self.ctx.can("quotation.edit"):
            self.open_editor(row["id"])

    # ------------------------------------------------------------ actions
    def on_new(self) -> None:
        """Create a new quotation."""
        if self.ctx.can("quotation.edit") and open_quotation_editor(self, self.ctx, None):
            self.ctx.notify("quotation")

    def open_editor(self, quotation_id: int) -> None:
        """Edit an existing quotation."""
        if open_quotation_editor(self, self.ctx, quotation_id):
            self.ctx.notify("quotation")
            self.info(t("common.saved"))

    def _submit(self, quotation_id: int) -> None:
        try:
            self.ctx.run(
                lambda s: quotation_service.submit_for_review(s, self.ctx.user, quotation_id)
            )
            self.ctx.notify("quotation")
        except Exception as exc:
            self.handle_error(exc)

    def _approve(self, quotation_id: int) -> None:
        try:
            self.ctx.run(
                lambda s: quotation_service.approve_quotation(s, self.ctx.user, quotation_id)
            )
            self.ctx.notify("quotation")
            self.info(t("quotation.approve"))
        except Exception as exc:
            self.handle_error(exc)

    def _mark_sent(self, quotation_id: int) -> None:
        try:
            self.ctx.run(lambda s: quotation_service.mark_sent(s, self.ctx.user, quotation_id))
            self.ctx.notify("quotation")
            self.info(t("quotation.mark_sent"))
        except Exception as exc:
            self.handle_error(exc)

    def _set_status(self, quotation_id: int) -> None:
        options = [(status, te("quotation_status", status)) for status in QUOTATION_STATUSES]
        labels = [label for _value, label in options]
        choice, ok = QInputDialog.getItem(
            self, t("quotation.set_status"), t("common.status"), labels, 0, False
        )
        if not ok:
            return
        target = options[labels.index(choice)][0]
        try:
            self.ctx.run(
                lambda s: quotation_service.set_status(s, self.ctx.user, quotation_id, target)
            )
            self.ctx.notify("quotation")
        except Exception as exc:
            self.handle_error(exc)

    def _duplicate(self, quotation_id: int) -> None:
        try:
            new_id = self.ctx.run(
                lambda s: quotation_service.duplicate_quotation(s, self.ctx.user, quotation_id).id
            )
            self.ctx.notify("quotation")
            self.table.select_id(new_id)
        except Exception as exc:
            self.handle_error(exc)

    def _export_pdf(self, quotation_id: int) -> None:
        data = self.ctx.read(lambda s: quotation_service.quotation_dict(s, quotation_id))
        path, _ = QFileDialog.getSaveFileName(
            self, t("quotation.export_pdf"), f"{data['number']}.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            company = self.ctx.company()
            written = build_quotation_pdf(path, data, company)

            def _store(session: Session) -> None:
                quotation = quotation_service.get_quotation(session, quotation_id)
                quotation.last_pdf_path = written

            self.ctx.run(_store)
            self.info(t("common.exported", path=written))
        except Exception as exc:
            self.handle_error(exc)

    def _email(self, data: dict) -> None:
        from app.ui.dialogs.email_dialog import open_email_composer

        if open_email_composer(
            self,
            self.ctx,
            buyer_id=data["buyer_id"],
            quotation_id=data["id"],
            lead_id=data.get("lead_id"),
        ):
            self.ctx.notify("email")

    def on_export(self) -> None:
        """Export the quotation register (or one quotation) to Excel."""
        row = self.table.current_row()
        if row is None:
            rows = self.table.model.rows
            path, _ = QFileDialog.getSaveFileName(
                self, t("common.export"), "quotations.xlsx", "Excel (*.xlsx)"
            )
            if not path:
                return
            columns = [(column.key, column.title) for column in self.columns()]
            self.info(
                t("common.exported", path=export_excel(path, t("quotation.title"), columns, rows))
            )
            return
        data = self.ctx.read(lambda s: quotation_service.quotation_dict(s, row["id"]))
        path, _ = QFileDialog.getSaveFileName(
            self, t("quotation.export_excel"), f"{data['number']}.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        columns = [
            ("description", t("common.description")),
            ("hs_code", t("product.hs_code")),
            ("quantity", t("common.quantity")),
            ("unit", t("common.unit")),
            ("unit_price", t("price.unit_price")),
            ("line_total", t("common.amount")),
        ]
        meta = {
            t("quotation.number"): data["number"],
            t("common.buyer"): data["buyer"],
            t("common.incoterm"): data["incoterm"],
            t("quotation.grand_total"): f"{data['grand_total']:,.2f} {data['currency']}",
        }
        written = export_excel(path, data["number"], columns, data["items"], meta=meta)
        self.info(t("common.exported", path=written))
