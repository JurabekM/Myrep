"""Export lead CRM page."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QFileDialog, QInputDialog, QWidget
from sqlalchemy.orm import Session

from app.config import SUPPORTED_CURRENCIES
from app.controllers.app_context import AppContext
from app.services import (
    audit_service,
    auth_service,
    buyer_service,
    checklist_service,
    contract_service,
    import_service,
    lead_service,
    product_service,
    quotation_service,
    task_service,
)
from app.ui.dialogs.form_dialog import Field, FormDialog
from app.ui.i18n import t, te
from app.ui.pages.base_page import RecordPage
from app.ui.widgets.common import button
from app.ui.widgets.table import Column, FilterSpec
from app.utils.enums import (
    INCOTERMS,
    LEAD_SOURCES,
    LEAD_STATUSES,
    LEAD_TEMPERATURES,
    LOST_REASONS,
    PIPELINE_STAGES,
)
from app.utils.errors import ValidationError
from app.utils.formatting import fmt_date, fmt_datetime, fmt_money


def _reference_data(ctx: AppContext) -> dict[str, list[tuple[Any, str]]]:
    """Load the combo box sources shared by the lead editor."""

    def _load(session: Session) -> dict[str, list[tuple[Any, str]]]:
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

    return ctx.read(_load)


def open_lead_editor(
    parent: QWidget, ctx: AppContext, lead_id: int | None, buyer_id: int | None = None
) -> bool:
    """Open the lead editor dialog; returns True when something was saved."""
    reference = _reference_data(ctx)
    values: dict[str, Any] = {
        "status": "new",
        "temperature": "warm",
        "source": "manual",
        "currency": "USD",
        "probability": 20,
        "buyer_id": buyer_id,
    }
    if lead_id:
        values = ctx.read(lambda s: lead_service.lead_dict(s, lead_id))

    fields = [
        Field("title", t("lead.name"), required=True),
        Field("buyer_id", t("common.buyer"), "combo", reference["buyers"], required=True),
        Field("product_id", t("common.product"), "combo", reference["products"]),
        Field("country", t("common.country")),
        Field("source", t("common.source"), "enum", LEAD_SOURCES, "lead_source", with_empty=False),
        Field("source_detail", t("lead.source_detail")),
        Field("status", t("common.status"), "enum", LEAD_STATUSES, "lead_status", with_empty=False),
        Field(
            "temperature",
            t("lead.temperature"),
            "enum",
            LEAD_TEMPERATURES,
            "temperature",
            with_empty=False,
        ),
        Field("expected_value", t("lead.expected_value"), "money"),
        Field(
            "currency",
            t("common.currency"),
            "combo",
            [(c, c) for c in SUPPORTED_CURRENCIES],
            with_empty=False,
        ),
        Field("probability", t("lead.probability"), "int", maximum=100),
        Field("incoterm", t("common.incoterm"), "combo", [(i, i) for i in INCOTERMS]),
        Field("destination", t("common.destination")),
        Field("manager_id", t("common.manager"), "combo", reference["managers"]),
        Field("next_step", t("lead.next_step")),
        Field("next_follow_up", t("lead.next_follow_up"), "date"),
        Field("tags", t("common.tags")),
        Field("notes", t("common.notes"), "textarea", height=80),
    ]

    def _save(collected: dict[str, Any]) -> int:
        payload = dict(collected)
        payload["id"] = lead_id
        # Closing rules are enforced through change_status, not the plain editor.
        if lead_id:
            current = ctx.read(lambda s: lead_service.lead_dict(s, lead_id))
            if current["status"] != payload.get("status") and payload.get("status") in (
                "closed_won",
                "closed_lost",
            ):
                raise ValidationError("Use the stage action to close a deal", key="error.workflow")
        return ctx.run(lambda s: lead_service.save_lead(s, ctx.user, payload).id)

    dialog = FormDialog(
        t("lead.new") if not lead_id else values.get("title", ""), fields, values, _save, parent
    )
    return bool(dialog.exec())


class LeadsPage(RecordPage):
    """Filterable lead register with bulk actions."""

    permission = "lead.view"
    title_key = "lead.title"
    topics = ("lead", "buyer", "quotation")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        self._managers: list[tuple[int, str]] = []
        super().__init__(ctx, parent)
        if ctx.can("lead.edit"):
            self.header.add_action(button(t("lead.new"), self.on_new, "Primary"))
            self.header.add_action(button(t("lead.import"), self._import_leads, "Ghost"))
        if ctx.can("lead.assign"):
            self.header.add_action(button(t("lead.bulk_assign"), self._bulk_assign, "Ghost"))
        self.header.add_action(button(t("common.export"), self.on_export, "Ghost"))

    def columns(self) -> list[Column]:
        """Column layout of the lead table."""
        return [
            Column("title", t("lead.name"), stretch=True),
            Column("buyer", t("common.buyer"), width=170),
            Column("country", t("common.country"), width=100),
            Column("product", t("common.product"), width=160),
            Column("source", t("common.source"), kind="status", group="lead_source", width=110),
            Column("status", t("common.stage"), kind="status", group="lead_status", width=150),
            Column(
                "temperature", t("lead.temperature"), kind="status", group="temperature", width=90
            ),
            Column("expected_value", t("lead.expected_value"), kind="money", width=120),
            Column("next_follow_up", t("lead.next_follow_up"), kind="date", width=110),
            Column("manager", t("common.manager"), width=130),
        ]

    def filter_specs(self) -> list[FilterSpec]:
        """Filters for the lead table."""
        return [
            FilterSpec("country", t("common.country"), "combo", [], width=120),
            FilterSpec("source", t("common.source"), "enum", LEAD_SOURCES, "lead_source", 120),
            FilterSpec("status", t("common.stage"), "enum", LEAD_STATUSES, "lead_status", 150),
            FilterSpec(
                "temperature", t("lead.temperature"), "enum", LEAD_TEMPERATURES, "temperature", 110
            ),
            FilterSpec("manager_id", t("common.manager"), "combo", [], width=140),
            FilterSpec("overdue", t("lead.overdue_only"), "check"),
        ]

    # --------------------------------------------------------------- data
    def refresh(self) -> None:
        """Reload the filter sources and the lead table."""

        def _load(session: Session) -> tuple[list, list]:
            managers = [
                (user["id"], user["full_name"] or user["username"])
                for user in auth_service.list_users(session)
            ]
            countries = [(name, name) for name in buyer_service.distinct_countries(session)]
            return managers, countries

        self._managers, countries = self.ctx.read(_load)
        self.filter_bar.set_options("manager_id", self._managers, t("common.manager"))
        self.filter_bar.set_options("country", countries, t("common.country"))
        super().refresh()

    def load_rows(self, filters: dict[str, Any]) -> list[dict]:
        """Fetch leads matching the filter bar."""

        def _load(session: Session) -> list[dict]:
            return lead_service.search_leads(
                session,
                text=filters.get("text", ""),
                country=filters.get("country"),
                source=filters.get("source"),
                status=filters.get("status"),
                temperature=filters.get("temperature"),
                manager_id=filters.get("manager_id"),
                overdue_only=bool(filters.get("overdue")),
            )

        return self.ctx.read(_load)

    # ------------------------------------------------------------- detail
    def fill_detail(self, row: dict) -> None:
        """Populate the lead detail panel."""
        lead_id = row["id"]

        def _load(session: Session) -> dict:
            data = lead_service.lead_dict(session, lead_id)
            data["quotations"] = quotation_service.list_quotations(session)
            data["quotations"] = [q for q in data["quotations"] if q["lead_id"] == lead_id]
            data["checklists"] = checklist_service.list_checklists(
                session, scope="lead", entity_id=lead_id
            )
            data["tasks"] = [
                task
                for task in task_service.list_tasks(session, status="open")
                if task["lead_id"] == lead_id
            ]
            data["timeline"] = audit_service.timeline(session, "lead", lead_id, 60)
            return data

        data = self.ctx.read(_load)
        self.detail.set_header(
            data["title"],
            f"{row.get('buyer', '')} · {fmt_money(data['expected_value'], data['currency'])}",
            "lead_status",
            data["status"],
        )
        if self.ctx.can("lead.edit"):
            self.detail.add_action(t("common.edit"), lambda: self.open_editor(lead_id), "Primary")
            self.detail.add_action(t("lead.change_stage"), lambda: self._change_stage(lead_id))
        if self.ctx.can("quotation.edit"):
            self.detail.add_action(t("quotation.new"), lambda: self._new_quotation(data))

        self.detail.add_fields_tab(
            t("buyer.tab_profile"),
            [
                (t("common.buyer"), row.get("buyer")),
                (t("common.country"), data.get("country")),
                (t("common.product"), row.get("product")),
                (t("common.source"), te("lead_source", data.get("source"))),
                (t("lead.source_detail"), data.get("source_detail")),
                (t("lead.temperature"), te("temperature", data.get("temperature"))),
                (t("lead.expected_value"), fmt_money(data["expected_value"], data["currency"])),
                (t("lead.probability"), f"{data.get('probability')}%"),
                (t("common.incoterm"), data.get("incoterm")),
                (t("common.destination"), data.get("destination")),
                (t("lead.next_step"), data.get("next_step")),
                (t("lead.next_follow_up"), fmt_date(data.get("next_follow_up"))),
                (t("common.manager"), row.get("manager")),
                (t("lead.lost_reason"), te("lost_reason", data.get("lost_reason"))),
                (t("common.notes"), data.get("notes")),
            ],
        )
        self.detail.add_list_tab(
            t("nav.quotations"),
            [
                f"{q['number']} · {te('quotation_status', q['status'])} · "
                f"{fmt_money(q['grand_total'], q['currency'])}"
                for q in data["quotations"]
            ],
        )
        self.detail.add_list_tab(
            t("nav.checklists"),
            [
                f"{c['name']} · {c['completion']}% ({c['done']}/{c['total']})"
                for c in data["checklists"]
            ],
        )
        self.detail.add_list_tab(
            t("buyer.tab_tasks"),
            [f"{fmt_date(task['due_date'])} · {task['title']}" for task in data["tasks"]],
        )
        self.detail.add_list_tab(
            t("common.timeline"),
            [f"{fmt_datetime(item['happened_at'])} · {item['title']}" for item in data["timeline"]],
        )

    def on_row_activated(self, row: dict) -> None:
        """Open the editor on double click."""
        if self.ctx.can("lead.edit"):
            self.open_editor(row["id"])

    # ------------------------------------------------------------ actions
    def on_new(self) -> None:
        """Create a new lead."""
        if self.ctx.can("lead.edit") and open_lead_editor(self, self.ctx, None):
            self.ctx.notify("lead")
            self.info(t("common.saved"))

    def open_editor(self, lead_id: int | None) -> None:
        """Edit an existing lead."""
        if open_lead_editor(self, self.ctx, lead_id):
            self.ctx.notify("lead")
            self.info(t("common.saved"))

    def _change_stage(self, lead_id: int) -> None:
        """Move a lead to another stage, enforcing the closing rules."""
        stages = [(stage, te("lead_status", stage)) for stage in PIPELINE_STAGES]
        labels = [label for _value, label in stages]
        choice, ok = QInputDialog.getItem(
            self, t("lead.change_stage"), t("common.stage"), labels, 0, False
        )
        if not ok:
            return
        target = stages[labels.index(choice)][0]
        change_lead_stage(self, self.ctx, lead_id, target)

    def _new_quotation(self, lead: dict) -> None:
        from app.ui.pages.quotations_page import open_quotation_editor

        if open_quotation_editor(
            self, self.ctx, None, lead_id=lead["id"], buyer_id=lead["buyer_id"]
        ):
            self.ctx.notify("quotation")

    def _bulk_assign(self) -> None:
        rows = self.table.selected_rows()
        if not rows:
            return
        labels = [name for _id, name in self._managers]
        if not labels:
            return
        choice, ok = QInputDialog.getItem(
            self, t("lead.assign"), t("common.manager"), labels, 0, False
        )
        if not ok:
            return
        manager_id = self._managers[labels.index(choice)][0]
        ids = [row["id"] for row in rows]
        try:
            count = self.ctx.run(
                lambda s: lead_service.assign_leads(s, self.ctx.user, ids, manager_id)
            )
            self.ctx.notify("lead")
            self.info(t("common.rows", count=count))
        except Exception as exc:
            self.handle_error(exc)

    def _import_leads(self) -> None:
        try:
            result = self.ctx.run(
                lambda s: import_service.import_leads_from_provider(s, self.ctx.user)
            )
            self.ctx.notify("lead")
            self.info(t("lead.imported", leads=result["leads"], provider=result["provider"]))
        except Exception as exc:
            self.handle_error(exc)

    def on_export(self) -> None:
        """Export leads to Excel."""
        path, _ = QFileDialog.getSaveFileName(
            self, t("common.export"), "leads.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            written = self.ctx.run(lambda s: import_service.export_leads(s, self.ctx.user, path))
            self.info(t("common.exported", path=written))
        except Exception as exc:
            self.handle_error(exc)


def change_lead_stage(parent: QWidget, ctx: AppContext, lead_id: int, target: str) -> bool:
    """Apply a stage change, collecting the extra data the rules require.

    Losing a deal requires a reason; winning one requires a contract, which is
    offered to be created from the dialog.
    """
    from PySide6.QtWidgets import QMessageBox

    lost_reason = None
    lost_comment = None
    if target == "closed_lost":
        reasons = [(code, te("lost_reason", code)) for code in LOST_REASONS]
        labels = [label for _code, label in reasons]
        choice, ok = QInputDialog.getItem(
            parent, t("lead.lost_reason"), t("lead.lost_required"), labels, 0, False
        )
        if not ok:
            return False
        lost_reason = reasons[labels.index(choice)][0]
        lost_comment, _ = QInputDialog.getText(
            parent, t("lead.lost_comment"), t("lead.lost_comment")
        )

    try:
        ctx.run(
            lambda s: lead_service.change_status(
                s,
                ctx.user,
                lead_id,
                target,
                lost_reason=lost_reason,
                lost_comment=lost_comment,
            )
        )
    except ValidationError as exc:
        if exc.key == "error.contract_required" and ctx.can("contract.edit"):
            box = QMessageBox(parent)
            box.setIcon(QMessageBox.Icon.Question)
            box.setWindowTitle(t("common.confirm"))
            box.setText(f"{t('lead.won_required')}\n\n{t('lead.create_contract')}?")
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if box.exec() != QMessageBox.StandardButton.Yes:
                return False
            if not _create_contract_for_lead(parent, ctx, lead_id):
                return False
            ctx.run(lambda s: lead_service.change_status(s, ctx.user, lead_id, target))
        else:
            raise
    ctx.notify("lead")
    return True


def _create_contract_for_lead(parent: QWidget, ctx: AppContext, lead_id: int) -> bool:
    """Create a contract for the lead so the deal can be marked as won."""
    lead = ctx.read(lambda s: lead_service.lead_dict(s, lead_id))
    fields = [
        Field("number", t("rfq.number")),
        Field("sign_date", t("common.date"), "date"),
        Field("amount", t("common.amount"), "money", required=True),
        Field(
            "currency",
            t("common.currency"),
            "combo",
            [(c, c) for c in SUPPORTED_CURRENCIES],
            with_empty=False,
        ),
        Field("incoterm", t("common.incoterm"), "combo", [(i, i) for i in INCOTERMS]),
        Field("payment_terms", t("price.payment_terms")),
        Field("notes", t("common.notes"), "textarea", height=60),
    ]
    values = {
        "amount": lead.get("expected_value") or 0,
        "currency": lead.get("currency") or "USD",
        "incoterm": lead.get("incoterm"),
        "status": "signed",
    }

    def _save(collected: dict[str, Any]) -> int:
        payload = dict(collected)
        payload.update({"buyer_id": lead["buyer_id"], "lead_id": lead_id, "status": "signed"})
        return ctx.run(lambda s: contract_service.save_contract(s, ctx.user, payload).id)

    dialog = FormDialog(t("lead.create_contract"), fields, values, _save, parent, width=560)
    return bool(dialog.exec())
