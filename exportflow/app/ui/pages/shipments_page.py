"""Logistics and shipment page."""

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
from app.reports import build_shipping_document
from app.services import (
    buyer_service,
    contract_service,
    lead_service,
    logistics_service,
    quotation_service,
)
from app.ui.dialogs.form_dialog import Field, FormDialog
from app.ui.i18n import t, te
from app.ui.pages.base_page import RecordPage
from app.ui.pages.quotations_page import show_error
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
from app.utils.enums import (
    CONTAINER_TYPES,
    CUSTOMS_STATUSES,
    INCOTERMS,
    SHIPMENT_STATUSES,
    SHIPMENT_TRANSITIONS,
    UNITS,
)
from app.utils.formatting import fmt_date, fmt_money, fmt_number


class ShipmentEditor(QDialog):
    """Shipment editor with item lines and cost tracking."""

    def __init__(
        self, ctx: AppContext, shipment_id: int | None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.shipment_id = shipment_id
        self.setModal(True)
        self.setWindowTitle(t("shipment.new") if not shipment_id else t("shipment.title"))
        self.resize(1020, 760)

        def _reference(session: Session) -> dict:
            return {
                "buyers": [
                    (row["id"], f"{row['company_name']} ({row['country']})")
                    for row in buyer_service.search_buyers(session)
                ],
                "leads": [(row["id"], row["title"]) for row in lead_service.search_leads(session)],
                "contracts": [
                    (row["id"], f"{row['number']} — {row['buyer']}")
                    for row in contract_service.list_contracts(session)
                ],
                "quotations": [
                    (row["id"], f"{row['number']} — {row['buyer']}")
                    for row in quotation_service.list_quotations(session)
                ],
            }

        self.reference = ctx.read(_reference)
        self.data: dict[str, Any] = {
            "incoterm": "FOB",
            "currency": "USD",
            "status": "planning",
            "customs_status": "not_started",
            "items": [],
        }
        if shipment_id:
            self.data = ctx.read(lambda s: logistics_service.shipment_dict(s, shipment_id))

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)
        heading = QLabel(self.data.get("number") or t("shipment.new"))
        heading.setObjectName("PageTitle")
        root.addWidget(heading)

        form_row = QHBoxLayout()
        left = QFormLayout()
        middle = QFormLayout()
        right = QFormLayout()
        for layout in (left, middle, right):
            layout.setSpacing(8)

        self.buyer = combo(self.reference["buyers"], self.data.get("buyer_id"), False)
        self.lead = combo(self.reference["leads"], self.data.get("lead_id"), True)
        self.contract = combo(self.reference["contracts"], self.data.get("contract_id"), True)
        self.quotation = combo(self.reference["quotations"], self.data.get("quotation_id"), True)
        left.addRow(t("common.buyer"), self.buyer)
        left.addRow(t("nav.leads"), self.lead)
        left.addRow(t("nav.contracts"), self.contract)
        left.addRow(t("nav.quotations"), self.quotation)

        self.incoterm = combo([(i, i) for i in INCOTERMS], self.data.get("incoterm"), False)
        self.origin = line_edit("", self.data.get("origin") or "")
        self.loading_port = line_edit("", self.data.get("loading_port") or "")
        self.destination = line_edit("", self.data.get("destination") or "")
        self.container = combo(
            [(c, c) for c in CONTAINER_TYPES], self.data.get("container_type"), True
        )
        middle.addRow(t("common.incoterm"), self.incoterm)
        middle.addRow(t("shipment.origin"), self.origin)
        middle.addRow(t("shipment.loading_port"), self.loading_port)
        middle.addRow(t("common.destination"), self.destination)
        middle.addRow(t("shipment.container"), self.container)

        self.forwarder = line_edit("", self.data.get("forwarder") or "")
        self.carrier = line_edit("", self.data.get("carrier") or "")
        self.tracking = line_edit("", self.data.get("tracking_reference") or "")
        self.etd = date_edit(self.data.get("etd"))
        self.eta = date_edit(self.data.get("eta"))
        self.customs = combo(
            [(c, te("customs_status", c)) for c in CUSTOMS_STATUSES],
            self.data.get("customs_status"),
            False,
        )
        right.addRow(t("shipment.forwarder"), self.forwarder)
        right.addRow(t("shipment.carrier"), self.carrier)
        right.addRow(t("shipment.tracking"), self.tracking)
        right.addRow(t("shipment.etd"), self.etd)
        right.addRow(t("shipment.eta"), self.eta)
        right.addRow(t("shipment.customs"), self.customs)

        form_row.addLayout(left, 1)
        form_row.addLayout(middle, 1)
        form_row.addLayout(right, 1)
        root.addLayout(form_row)

        items_header = QHBoxLayout()
        items_header.addWidget(section_title(t("shipment.items")))
        items_header.addStretch(1)
        items_header.addWidget(
            button(t("shipment.from_quotation"), self._fill_from_quotation, "Ghost")
        )
        root.addLayout(items_header)

        self.items_editor = ItemsEditor(
            [
                ItemColumn("description", t("common.description"), "text", width=250),
                ItemColumn("hs_code", t("product.hs_code"), "text", width=90),
                ItemColumn("quantity", t("common.quantity"), "number", width=90),
                ItemColumn("unit", t("common.unit"), "combo", 70, [(u, u) for u in UNITS]),
                ItemColumn("unit_price", t("price.unit_price"), "money", width=100, decimals=4),
                ItemColumn("packages", t("shipment.packages"), "number", width=90),
                ItemColumn("net_weight", t("shipment.net_weight"), "number", width=100),
                ItemColumn("gross_weight", t("shipment.gross_weight"), "number", width=100),
            ],
            self.data.get("items", []),
        )
        root.addWidget(self.items_editor, 1)

        costs = QHBoxLayout()
        costs.setSpacing(10)
        self.currency = combo(
            [(c, c) for c in SUPPORTED_CURRENCIES], self.data.get("currency"), False
        )
        self.planned_freight = spin(0, 1e9, self.data.get("planned_freight_cost") or 0)
        self.freight = spin(0, 1e9, self.data.get("freight_cost") or 0)
        self.planned_insurance = spin(0, 1e9, self.data.get("planned_insurance_cost") or 0)
        self.insurance = spin(0, 1e9, self.data.get("insurance_cost") or 0)
        self.other_cost = spin(0, 1e9, self.data.get("other_cost") or 0)
        costs.addWidget(QLabel(t("common.currency")))
        costs.addWidget(self.currency)
        costs.addWidget(QLabel(t("shipment.planned_cost")))
        costs.addWidget(self.planned_freight)
        costs.addWidget(QLabel(t("shipment.freight_cost")))
        costs.addWidget(self.freight)
        costs.addWidget(QLabel(t("shipment.insurance_cost")))
        costs.addWidget(self.insurance)
        costs.addWidget(self.planned_insurance)
        costs.addWidget(self.other_cost)
        costs.addStretch(1)
        root.addLayout(costs)

        self.notes = text_area(t("common.notes"), self.data.get("notes") or "", 60)
        root.addWidget(self.notes)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(button(t("common.cancel"), self.reject, "Ghost"))
        buttons.addWidget(button(t("common.save"), self._save, "Primary"))
        root.addLayout(buttons)

    def _fill_from_quotation(self) -> None:
        quotation_id = combo_value(self.quotation)
        if not quotation_id:
            self.ctx.show_toast(t("error.validation"), "warning")
            return
        items = self.ctx.read(
            lambda s: logistics_service.build_items_from_quotation(s, quotation_id)
        )
        self.items_editor.set_rows(items)

    def _save(self) -> None:
        values = {
            "id": self.shipment_id,
            "buyer_id": combo_value(self.buyer),
            "lead_id": combo_value(self.lead),
            "contract_id": combo_value(self.contract),
            "quotation_id": combo_value(self.quotation),
            "incoterm": combo_value(self.incoterm),
            "origin": self.origin.text().strip(),
            "loading_port": self.loading_port.text().strip(),
            "destination": self.destination.text().strip(),
            "container_type": combo_value(self.container),
            "forwarder": self.forwarder.text().strip(),
            "carrier": self.carrier.text().strip(),
            "tracking_reference": self.tracking.text().strip(),
            "etd": date_value(self.etd),
            "eta": date_value(self.eta),
            "customs_status": combo_value(self.customs),
            "currency": combo_value(self.currency),
            "planned_freight_cost": self.planned_freight.value(),
            "freight_cost": self.freight.value(),
            "planned_insurance_cost": self.planned_insurance.value(),
            "insurance_cost": self.insurance.value(),
            "other_cost": self.other_cost.value(),
            "notes": self.notes.toPlainText().strip(),
        }
        try:
            self.ctx.run(
                lambda s: logistics_service.save_shipment(
                    s, self.ctx.user, values, self.items_editor.rows()
                )
            )
        except Exception as exc:
            show_error(self, exc)
            return
        self.accept()


class ShipmentsPage(RecordPage):
    """Shipment register with status transitions and shipping documents."""

    permission = "shipment.view"
    title_key = "shipment.title"
    topics = ("shipment", "contract", "lead")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        if ctx.can("shipment.edit"):
            self.header.add_action(button(t("shipment.new"), self.on_new, "Primary"))
        self.header.add_action(button(t("common.export"), self.on_export, "Ghost"))

    def columns(self) -> list[Column]:
        """Column layout of the shipment table."""
        return [
            Column("number", t("shipment.number"), width=120),
            Column("buyer", t("common.buyer"), stretch=True),
            Column("incoterm", t("common.incoterm"), width=80),
            Column("loading_port", t("shipment.loading_port"), width=160),
            Column("destination", t("common.destination"), width=160),
            Column("etd", t("shipment.etd"), kind="date", width=100),
            Column("eta", t("shipment.eta"), kind="date", width=100),
            Column("status", t("common.status"), kind="status", group="shipment_status", width=140),
            Column(
                "customs_status",
                t("shipment.customs"),
                kind="status",
                group="customs_status",
                width=160,
            ),
            Column("actual_cost", t("shipment.actual_cost"), kind="money", width=120),
        ]

    def filter_specs(self) -> list[FilterSpec]:
        """Filters for the shipment table."""
        return [
            FilterSpec(
                "status", t("common.status"), "enum", SHIPMENT_STATUSES, "shipment_status", 150
            ),
            FilterSpec(
                "incoterm", t("common.incoterm"), "combo", [(i, i) for i in INCOTERMS], width=110
            ),
        ]

    def load_rows(self, filters: dict[str, Any]) -> list[dict]:
        """Fetch shipments matching the filter bar."""
        return self.ctx.read(
            lambda s: logistics_service.list_shipments(
                s,
                text=filters.get("text", ""),
                status=filters.get("status"),
                incoterm=filters.get("incoterm"),
            )
        )

    # ------------------------------------------------------------- detail
    def fill_detail(self, row: dict) -> None:
        """Populate the shipment detail panel."""
        data = self.ctx.read(lambda s: logistics_service.shipment_dict(s, row["id"]))
        self.detail.set_header(
            data["number"],
            f"{data['buyer']} · {data['destination'] or ''}",
            "shipment_status",
            data["status"],
        )
        if self.ctx.can("shipment.edit"):
            self.detail.add_action(t("common.edit"), lambda: self.open_editor(row["id"]), "Primary")
            self.detail.add_action(t("shipment.change_status"), lambda: self._change_status(row))
            self.detail.add_action(
                t("shipment.add_quote"), lambda: self._add_freight_quote(row["id"])
            )
        self.detail.add_action(
            t("shipment.invoice"), lambda: self._document(data, "commercial_invoice")
        )
        self.detail.add_action(
            t("shipment.packing_list"), lambda: self._document(data, "packing_list")
        )
        if self.ctx.can("contract.edit") and data["status"] == "delivered":
            self.detail.add_action(
                t("shipment.record_revenue"), lambda: self._record_revenue(data), "Success"
            )

        if row.get("delayed"):
            self.detail.add_tab(t("shipment.delayed"), banner(t("shipment.delayed"), "error"))

        self.detail.add_fields_tab(
            t("common.details"),
            [
                (t("common.buyer"), data["buyer"]),
                (t("common.incoterm"), data["incoterm"]),
                (t("shipment.origin"), data["origin"]),
                (t("shipment.loading_port"), data["loading_port"]),
                (t("common.destination"), data["destination"]),
                (t("shipment.container"), data["container_type"]),
                (t("shipment.forwarder"), data["forwarder"]),
                (t("shipment.carrier"), data["carrier"]),
                (t("shipment.tracking"), data["tracking_reference"]),
                (t("shipment.etd"), fmt_date(data["etd"])),
                (t("shipment.eta"), fmt_date(data["eta"])),
                (t("shipment.actual_departure"), fmt_date(data["actual_departure"])),
                (t("shipment.actual_arrival"), fmt_date(data["actual_arrival"])),
                (t("shipment.customs"), te("customs_status", data["customs_status"])),
                (t("shipment.packages"), fmt_number(data["package_count"], 0)),
                (t("shipment.net_weight"), fmt_number(data["net_weight"])),
                (t("shipment.gross_weight"), fmt_number(data["gross_weight"])),
                (t("shipment.planned_cost"), fmt_money(data["planned_cost"], data["currency"])),
                (t("shipment.actual_cost"), fmt_money(data["actual_cost"], data["currency"])),
                (
                    t("shipment.cost_delta"),
                    fmt_money(data["actual_cost"] - data["planned_cost"], data["currency"]),
                ),
                (t("common.notes"), data["notes"]),
            ],
        )
        self.detail.add_list_tab(
            t("shipment.items"),
            [
                f"{item['description']} · {item['quantity']:g} {item['unit']} · "
                f"{item['packages']:g} pkg · {item['gross_weight']:,.1f} kg"
                for item in data["items"]
            ],
        )
        self.detail.add_list_tab(
            t("shipment.freight_quotes"),
            [
                f"{'★ ' if q['is_selected'] else ''}{q['forwarder']} · {q['mode']} · "
                f"{fmt_money(q['price'], q['currency'])} · {q['transit_days'] or '—'} d"
                for q in data["freight_quotes"]
            ],
        )

    def on_row_activated(self, row: dict) -> None:
        """Open the editor on double click."""
        if self.ctx.can("shipment.edit"):
            self.open_editor(row["id"])

    # ------------------------------------------------------------ actions
    def on_new(self) -> None:
        """Create a new shipment."""
        self.open_editor(None)

    def open_editor(self, shipment_id: int | None) -> None:
        """Show the shipment editor."""
        dialog = ShipmentEditor(self.ctx, shipment_id, self)
        if dialog.exec():
            self.ctx.notify("shipment")
            self.info(t("common.saved"))

    def _change_status(self, row: dict) -> None:
        allowed = SHIPMENT_TRANSITIONS.get(row["status"], ())
        if not allowed:
            self.ctx.show_toast(t("error.workflow"), "warning")
            return
        options = [(status, te("shipment_status", status)) for status in allowed]
        labels = [label for _value, label in options]
        choice, ok = QInputDialog.getItem(
            self, t("shipment.change_status"), t("common.status"), labels, 0, False
        )
        if not ok:
            return
        target = options[labels.index(choice)][0]
        try:
            self.ctx.run(
                lambda s: logistics_service.change_status(s, self.ctx.user, row["id"], target)
            )
            self.ctx.notify("shipment")
        except Exception as exc:
            self.handle_error(exc)

    def _add_freight_quote(self, shipment_id: int) -> None:
        fields = [
            Field("forwarder", t("shipment.forwarder"), required=True),
            Field(
                "mode",
                t("common.type"),
                "combo",
                [
                    ("sea", "Sea"),
                    ("rail", "Rail"),
                    ("road", "Road"),
                    ("air", "Air"),
                    ("multimodal", "Multimodal"),
                ],
                with_empty=False,
            ),
            Field("price", t("common.price"), "money", required=True),
            Field(
                "currency",
                t("common.currency"),
                "combo",
                [(c, c) for c in SUPPORTED_CURRENCIES],
                with_empty=False,
            ),
            Field("transit_days", t("product.lead_time"), "int", maximum=365),
            Field("valid_until", t("price.valid_to"), "date"),
            Field("notes", t("common.notes"), "textarea", height=60),
        ]

        def _save(values: dict[str, Any]) -> int:
            payload = dict(values)
            payload["shipment_id"] = shipment_id
            return self.ctx.run(
                lambda s: logistics_service.save_freight_quote(s, self.ctx.user, payload).id
            )

        dialog = FormDialog(
            t("shipment.add_quote"), fields, {"mode": "sea", "currency": "USD"}, _save, self, 560
        )
        if dialog.exec():
            quote_id = dialog.result_value
            if quote_id and self.confirm(t("shipment.select_quote")):
                self.ctx.run(
                    lambda s: logistics_service.select_freight_quote(s, self.ctx.user, quote_id)
                )
            self.ctx.notify("shipment")

    def _document(self, data: dict, kind: str) -> None:
        suffix = "invoice" if kind == "commercial_invoice" else "packing-list"
        path, _ = QFileDialog.getSaveFileName(
            self, t("shipment.invoice"), f"{data['number']}-{suffix}.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            written = build_shipping_document(path, data, self.ctx.company(), kind)
            self.info(t("common.exported", path=written))
        except Exception as exc:
            self.handle_error(exc)

    def _record_revenue(self, data: dict) -> None:
        fields = [
            Field("expected_amount", t("report.revenue_expected_vs_actual"), "money"),
            Field("actual_amount", t("workspace.revenue_actual"), "money", required=True),
            Field(
                "currency",
                t("common.currency"),
                "combo",
                [(c, c) for c in SUPPORTED_CURRENCIES],
                with_empty=False,
            ),
            Field("record_date", t("common.date"), "date"),
            Field("notes", t("common.notes"), "textarea", height=60),
        ]

        def _save(values: dict[str, Any]) -> int:
            payload = dict(values)
            payload.update(
                {
                    "shipment_id": data["id"],
                    "lead_id": data.get("lead_id"),
                    "contract_id": data.get("contract_id"),
                    "buyer_id": data.get("buyer_id"),
                    "kind": "shipment",
                }
            )
            return self.ctx.run(
                lambda s: contract_service.record_revenue(s, self.ctx.user, payload).id
            )

        dialog = FormDialog(
            t("shipment.record_revenue"),
            fields,
            {"currency": data.get("currency") or "USD"},
            _save,
            self,
            560,
        )
        if dialog.exec():
            self.ctx.notify("shipment")
            self.info(t("common.saved"))

    def on_export(self) -> None:
        """Export the shipment status report."""
        from app.services import report_service

        path, _ = QFileDialog.getSaveFileName(
            self, t("common.export"), "shipments.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            written = self.ctx.run(
                lambda s: report_service.export(
                    s, self.ctx.user, "shipment_status", "xlsx", target=path
                )
            )
            self.info(t("common.exported", path=written))
        except Exception as exc:
            self.handle_error(exc)
