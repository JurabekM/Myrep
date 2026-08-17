"""RFQ intake page."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from sqlalchemy.orm import Session

from app.config import SUPPORTED_CURRENCIES
from app.controllers.app_context import AppContext
from app.services import buyer_service, lead_service, product_service, quotation_service
from app.ui.i18n import t, te
from app.ui.pages.base_page import RecordPage
from app.ui.pages.quotations_page import open_quotation_editor, show_error
from app.ui.widgets.common import (
    button,
    combo,
    combo_value,
    date_edit,
    date_value,
    line_edit,
    section_title,
    text_area,
)
from app.ui.widgets.items_editor import ItemColumn, ItemsEditor
from app.ui.widgets.table import Column, FilterSpec
from app.utils.enums import INCOTERMS, PAYMENT_TERMS, RFQ_STATUSES, UNITS
from app.utils.formatting import fmt_date, today


class RFQEditor(QDialog):
    """Editor for a buyer request with its requested item lines."""

    def __init__(self, ctx: AppContext, rfq_id: int | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.rfq_id = rfq_id
        self.setModal(True)
        self.setWindowTitle(t("rfq.new") if not rfq_id else t("rfq.title"))
        self.resize(940, 700)

        def _reference(session: Session) -> dict:
            return {
                "buyers": [
                    (row["id"], f"{row['company_name']} ({row['country']})")
                    for row in buyer_service.search_buyers(session)
                ],
                "leads": [(row["id"], row["title"]) for row in lead_service.search_leads(session)],
                "products": [
                    (row["id"], f"{row['sku']} — {row['name']}")
                    for row in product_service.search_products(session, lang=ctx.language())
                ],
            }

        self.reference = ctx.read(_reference)
        self.data: dict[str, Any] = {
            "received_at": today(),
            "currency": "USD",
            "status": "new",
            "items": [],
        }
        if rfq_id:
            self.data = ctx.read(lambda s: quotation_service.rfq_dict(s, rfq_id))

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)
        heading = QLabel(self.data.get("number") or t("rfq.new"))
        heading.setObjectName("PageTitle")
        root.addWidget(heading)

        form_row = QHBoxLayout()
        left = QFormLayout()
        right = QFormLayout()
        left.setSpacing(8)
        right.setSpacing(8)

        self.buyer_combo = combo(self.reference["buyers"], self.data.get("buyer_id"), False)
        self.lead_combo = combo(self.reference["leads"], self.data.get("lead_id"), True)
        self.received_at = date_edit(self.data.get("received_at") or today())
        self.deadline = date_edit(self.data.get("deadline"))
        self.currency = combo(
            [(c, c) for c in SUPPORTED_CURRENCIES], self.data.get("currency"), False
        )
        self.status = combo(
            [(status, te("rfq_status", status)) for status in RFQ_STATUSES],
            self.data.get("status"),
            False,
        )
        left.addRow(t("common.buyer"), self.buyer_combo)
        left.addRow(t("nav.leads"), self.lead_combo)
        left.addRow(t("rfq.received"), self.received_at)
        left.addRow(t("rfq.deadline"), self.deadline)
        left.addRow(t("common.currency"), self.currency)
        left.addRow(t("common.status"), self.status)

        self.incoterm = combo([(i, i) for i in INCOTERMS], self.data.get("target_incoterm"), True)
        self.destination = line_edit("", self.data.get("destination") or "")
        self.payment = combo(
            [(p, p) for p in PAYMENT_TERMS], self.data.get("payment_condition"), True
        )
        self.payment.setEditable(True)
        if self.data.get("payment_condition"):
            self.payment.setCurrentText(self.data["payment_condition"])
        self.certificates = line_edit("", self.data.get("certificate_requirements") or "")
        right.addRow(t("rfq.target_incoterm"), self.incoterm)
        right.addRow(t("common.destination"), self.destination)
        right.addRow(t("rfq.payment_condition"), self.payment)
        right.addRow(t("rfq.certificate_requirements"), self.certificates)

        form_row.addLayout(left, 1)
        form_row.addLayout(right, 1)
        root.addLayout(form_row)

        root.addWidget(section_title(t("rfq.items")))
        self.items_editor = ItemsEditor(
            [
                ItemColumn("description", t("common.description"), "text", width=300),
                ItemColumn("quantity", t("common.quantity"), "number", width=100),
                ItemColumn("unit", t("common.unit"), "combo", 80, [(u, u) for u in UNITS]),
                ItemColumn("target_price", t("rfq.target_price"), "money", width=110, decimals=4),
                ItemColumn("notes", t("common.notes"), "text", width=200),
            ],
            self.data.get("items", []),
        )
        root.addWidget(self.items_editor, 1)

        self.packaging = text_area(
            t("rfq.packaging_requirements"), self.data.get("packaging_requirements") or "", 60
        )
        self.notes = text_area(t("rfq.internal_notes"), self.data.get("internal_notes") or "", 60)
        text_row = QHBoxLayout()
        text_row.addWidget(self.packaging)
        text_row.addWidget(self.notes)
        root.addLayout(text_row)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(button(t("common.cancel"), self.reject, "Ghost"))
        buttons.addWidget(button(t("common.save"), self._save, "Primary"))
        root.addLayout(buttons)

    def _save(self) -> None:
        values = {
            "id": self.rfq_id,
            "buyer_id": combo_value(self.buyer_combo),
            "lead_id": combo_value(self.lead_combo),
            "received_at": date_value(self.received_at) or today(),
            "deadline": date_value(self.deadline),
            "currency": combo_value(self.currency),
            "status": combo_value(self.status),
            "target_incoterm": combo_value(self.incoterm),
            "destination": self.destination.text().strip(),
            "payment_condition": self.payment.currentText().strip(),
            "certificate_requirements": self.certificates.text().strip(),
            "packaging_requirements": self.packaging.toPlainText().strip(),
            "internal_notes": self.notes.toPlainText().strip(),
        }
        items = self.items_editor.rows()
        try:
            self.ctx.run(lambda s: quotation_service.save_rfq(s, self.ctx.user, values, items))
        except Exception as exc:
            show_error(self, exc)
            return
        self.accept()


class RFQPage(RecordPage):
    """Register of incoming buyer requests."""

    permission = "rfq.view"
    title_key = "rfq.title"
    topics = ("rfq", "buyer", "quotation")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        if ctx.can("rfq.edit"):
            self.header.add_action(button(t("rfq.new"), self.on_new, "Primary"))

    def columns(self) -> list[Column]:
        """Column layout of the RFQ table."""
        return [
            Column("number", t("rfq.number"), width=130),
            Column("buyer", t("common.buyer"), stretch=True),
            Column("received_at", t("rfq.received"), kind="date", width=110),
            Column("deadline", t("rfq.deadline"), kind="date", width=110),
            Column("target_incoterm", t("rfq.target_incoterm"), width=100),
            Column("destination", t("common.destination"), width=160),
            Column("items", t("rfq.items"), kind="number", decimals=0, width=70),
            Column("currency", t("common.currency"), width=80),
            Column("status", t("common.status"), kind="status", group="rfq_status", width=120),
        ]

    def filter_specs(self) -> list[FilterSpec]:
        """Filters for the RFQ table."""
        return [FilterSpec("status", t("common.status"), "enum", RFQ_STATUSES, "rfq_status", 140)]

    def load_rows(self, filters: dict[str, Any]) -> list[dict]:
        """Fetch RFQs matching the filter bar."""
        return self.ctx.read(
            lambda s: quotation_service.list_rfqs(
                s, text=filters.get("text", ""), status=filters.get("status")
            )
        )

    def fill_detail(self, row: dict) -> None:
        """Populate the RFQ detail panel."""
        data = self.ctx.read(lambda s: quotation_service.rfq_dict(s, row["id"]))
        self.detail.set_header(data["number"], row.get("buyer", ""), "rfq_status", data["status"])
        if self.ctx.can("rfq.edit"):
            self.detail.add_action(t("common.edit"), lambda: self.open_editor(row["id"]), "Primary")
        if self.ctx.can("quotation.edit"):
            self.detail.add_action(
                t("rfq.create_quotation"), lambda: self._create_quotation(data), "Success"
            )
        self.detail.add_fields_tab(
            t("common.details"),
            [
                (t("common.buyer"), row.get("buyer")),
                (t("rfq.received"), fmt_date(data["received_at"])),
                (t("rfq.deadline"), fmt_date(data["deadline"])),
                (t("rfq.target_incoterm"), data["target_incoterm"]),
                (t("common.destination"), data["destination"]),
                (t("rfq.payment_condition"), data["payment_condition"]),
                (t("rfq.certificate_requirements"), data["certificate_requirements"]),
                (t("rfq.packaging_requirements"), data["packaging_requirements"]),
                (t("rfq.internal_notes"), data["internal_notes"]),
            ],
        )
        self.detail.add_list_tab(
            t("rfq.items"),
            [
                f"{item['description']} · {item['quantity']:g} {item['unit']}"
                + (f" · target {item['target_price']:,.2f}" if item.get("target_price") else "")
                for item in data["items"]
            ],
        )

    def on_row_activated(self, row: dict) -> None:
        """Open the editor on double click."""
        if self.ctx.can("rfq.edit"):
            self.open_editor(row["id"])

    def on_new(self) -> None:
        """Create a new RFQ."""
        self.open_editor(None)

    def open_editor(self, rfq_id: int | None) -> None:
        """Show the RFQ editor."""
        dialog = RFQEditor(self.ctx, rfq_id, self)
        if dialog.exec():
            self.ctx.notify("rfq")
            self.info(t("common.saved"))

    def _create_quotation(self, rfq: dict) -> None:
        if open_quotation_editor(
            self,
            self.ctx,
            None,
            lead_id=rfq.get("lead_id"),
            buyer_id=rfq["buyer_id"],
            rfq_id=rfq["id"],
        ):
            self.ctx.notify("quotation")
