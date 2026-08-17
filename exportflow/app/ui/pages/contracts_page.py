"""Export contracts page."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QFileDialog, QWidget
from sqlalchemy.orm import Session

from app.config import SUPPORTED_CURRENCIES
from app.controllers.app_context import AppContext
from app.services import buyer_service, contract_service, document_service, lead_service
from app.ui.dialogs.form_dialog import Field, FormDialog
from app.ui.i18n import t
from app.ui.pages.base_page import RecordPage
from app.ui.widgets.common import button
from app.ui.widgets.table import Column, FilterSpec
from app.utils.enums import CONTRACT_STATUSES, INCOTERMS, PAYMENT_TERMS
from app.utils.formatting import fmt_date, fmt_money


class ContractsPage(RecordPage):
    """Register of signed export contracts."""

    permission = "contract.view"
    title_key = "nav.contracts"
    topics = ("contract", "lead")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        self._buyers: list[tuple[int, str]] = []
        self._leads: list[tuple[int, str]] = []
        super().__init__(ctx, parent)
        if ctx.can("contract.edit"):
            self.header.add_action(button(t("common.new"), self.on_new, "Primary"))

    def columns(self) -> list[Column]:
        """Column layout of the contract table."""
        return [
            Column("number", t("rfq.number"), width=120),
            Column("buyer", t("common.buyer"), stretch=True),
            Column("sign_date", t("common.date"), kind="date", width=110),
            Column("valid_until", t("price.valid_to"), kind="date", width=110),
            Column("incoterm", t("common.incoterm"), width=90),
            Column("amount", t("common.amount"), kind="money", width=130),
            Column("payment_terms", t("quotation.payment_terms"), width=200),
            Column("status", t("common.status"), kind="status", group="contract_status", width=130),
        ]

    def filter_specs(self) -> list[FilterSpec]:
        """Filters for the contract table."""
        return [
            FilterSpec(
                "status", t("common.status"), "enum", CONTRACT_STATUSES, "contract_status", 150
            )
        ]

    def refresh(self) -> None:
        """Reload reference lists and the contract table."""

        def _load(session: Session) -> tuple[list, list]:
            buyers = [
                (row["id"], f"{row['company_name']} ({row['country']})")
                for row in buyer_service.search_buyers(session)
            ]
            leads = [(row["id"], row["title"]) for row in lead_service.search_leads(session)]
            return buyers, leads

        self._buyers, self._leads = self.ctx.read(_load)
        super().refresh()

    def load_rows(self, filters: dict[str, Any]) -> list[dict]:
        """Fetch contracts matching the filter bar."""
        return self.ctx.read(
            lambda s: contract_service.list_contracts(
                s, text=filters.get("text", ""), status=filters.get("status")
            )
        )

    def fill_detail(self, row: dict) -> None:
        """Populate the contract detail panel."""
        self.detail.set_header(
            row["number"],
            f"{row['buyer']} · {fmt_money(row['amount'], row['currency'])}",
            "contract_status",
            row["status"],
        )
        if self.ctx.can("contract.edit"):
            self.detail.add_action(t("common.edit"), lambda: self.open_editor(row), "Primary")
            self.detail.add_action(t("common.attach_file"), lambda: self._attach(row["id"]))
        self.detail.add_fields_tab(
            t("common.details"),
            [
                (t("common.buyer"), row["buyer"]),
                (t("common.date"), fmt_date(row["sign_date"])),
                (t("price.valid_to"), fmt_date(row["valid_until"])),
                (t("common.amount"), fmt_money(row["amount"], row["currency"])),
                (t("common.incoterm"), row["incoterm"]),
                (t("quotation.payment_terms"), row["payment_terms"]),
                (t("certificate.file"), row["file_path"]),
                (t("common.notes"), row["notes"]),
            ],
        )
        documents = self.ctx.read(
            lambda s: document_service.list_attachments(s, "contract", row["id"])
        )
        self.detail.add_list_tab(
            t("certificate.documents"), [doc["file_name"] for doc in documents]
        )

    def on_row_activated(self, row: dict) -> None:
        """Open the editor on double click."""
        if self.ctx.can("contract.edit"):
            self.open_editor(row)

    def on_new(self) -> None:
        """Create a new contract."""
        self.open_editor(None)

    def open_editor(self, row: dict | None) -> None:
        """Show the contract editor."""
        values: dict[str, Any] = row.copy() if row else {"currency": "USD", "status": "draft"}
        fields = [
            Field("buyer_id", t("common.buyer"), "combo", self._buyers, required=True),
            Field("lead_id", t("nav.leads"), "combo", self._leads),
            Field("number", t("rfq.number")),
            Field("sign_date", t("common.date"), "date"),
            Field("valid_until", t("price.valid_to"), "date"),
            Field("amount", t("common.amount"), "money", required=True),
            Field(
                "currency",
                t("common.currency"),
                "combo",
                [(c, c) for c in SUPPORTED_CURRENCIES],
                with_empty=False,
            ),
            Field("incoterm", t("common.incoterm"), "combo", [(i, i) for i in INCOTERMS]),
            Field(
                "payment_terms",
                t("quotation.payment_terms"),
                "combo",
                [(p, p) for p in PAYMENT_TERMS],
            ),
            Field("delivery_terms", t("quotation.delivery_terms")),
            Field(
                "status",
                t("common.status"),
                "enum",
                CONTRACT_STATUSES,
                "contract_status",
                with_empty=False,
            ),
            Field("notes", t("common.notes"), "textarea", height=70),
        ]

        def _save(collected: dict[str, Any]) -> int:
            payload = dict(collected)
            payload["id"] = row["id"] if row else None
            return self.ctx.run(
                lambda s: contract_service.save_contract(s, self.ctx.user, payload).id
            )

        dialog = FormDialog(t("nav.contracts"), fields, values, _save, self, width=640)
        if dialog.exec():
            self.ctx.notify("contract")
            self.info(t("common.saved"))

    def _attach(self, contract_id: int) -> None:
        path, _ = QFileDialog.getOpenFileName(self, t("common.attach_file"), "", "All files (*.*)")
        if not path:
            return
        try:
            self.ctx.run(
                lambda s: document_service.add_attachment(
                    s, self.ctx.user, "contract", contract_id, path
                )
            )
            self.ctx.notify("contract")
        except Exception as exc:
            self.handle_error(exc)
