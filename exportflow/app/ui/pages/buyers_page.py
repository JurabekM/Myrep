"""Buyer CRM page."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QFileDialog, QWidget
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.controllers.app_context import AppContext
from app.models import SalesAgent
from app.services import (
    audit_service,
    auth_service,
    buyer_service,
    checklist_service,
    document_service,
    email_service,
    import_service,
    lead_service,
    logistics_service,
    quotation_service,
    task_service,
)
from app.ui.dialogs.form_dialog import Field, FormDialog
from app.ui.i18n import t, te
from app.ui.pages.base_page import RecordPage
from app.ui.widgets.common import button
from app.ui.widgets.table import Column, FilterSpec
from app.utils.enums import BUYER_TYPES, LEAD_SOURCES, RISK_LEVELS
from app.utils.errors import ValidationError
from app.utils.formatting import fmt_date, fmt_datetime, fmt_money


class BuyersPage(RecordPage):
    """Buyer register with a tabbed 360° detail panel."""

    permission = "buyer.view"
    title_key = "buyer.title"
    topics = ("buyer", "lead", "quotation")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        self._managers: list[tuple[int, str]] = []
        self._agents: list[tuple[int, str]] = []
        super().__init__(ctx, parent)
        if ctx.can("buyer.edit"):
            self.header.add_action(button(t("buyer.new"), self.on_new, "Primary"))
            self.header.add_action(button(t("common.import"), self._import_excel, "Ghost"))
        self.header.add_action(button(t("common.export"), self.on_export, "Ghost"))

    def columns(self) -> list[Column]:
        """Column layout of the buyer table."""
        return [
            Column("company_name", t("buyer.company"), stretch=True),
            Column("country", t("common.country"), width=110),
            Column("contact_person", t("buyer.contact_person"), width=150),
            Column("email", t("common.email"), width=190),
            Column("buyer_type", t("buyer.type"), kind="status", group="buyer_type", width=110),
            Column("source", t("common.source"), kind="status", group="lead_source", width=110),
            Column("manager", t("common.manager"), width=130),
            Column("leads", t("nav.leads"), kind="number", decimals=0, width=60),
            Column("quotations", t("nav.quotations"), kind="number", decimals=0, width=80),
            Column("risk_level", t("buyer.risk"), kind="status", group="risk_level", width=90),
            Column("status", t("common.status"), kind="status", group="buyer_status", width=100),
        ]

    def filter_specs(self) -> list[FilterSpec]:
        """Filters for the buyer table."""
        return [
            FilterSpec("country", t("common.country"), "combo", [], width=130),
            FilterSpec("buyer_type", t("buyer.type"), "enum", BUYER_TYPES, "buyer_type", 130),
            FilterSpec("source", t("common.source"), "enum", LEAD_SOURCES, "lead_source", 130),
            FilterSpec("manager_id", t("common.manager"), "combo", [], width=140),
            FilterSpec("risk_level", t("buyer.risk"), "enum", RISK_LEVELS, "risk_level", 110),
            FilterSpec("archived", t("common.show_archived"), "check"),
        ]

    # --------------------------------------------------------------- data
    def refresh(self) -> None:
        """Reload reference lists and the buyer table."""

        def _load(session: Session) -> tuple[list, list, list]:
            managers = [
                (user["id"], user["full_name"] or user["username"])
                for user in auth_service.list_users(session)
            ]
            countries = [(name, name) for name in buyer_service.distinct_countries(session)]
            agents = [
                (row.id, row.name)
                for row in session.scalars(
                    select(SalesAgent)
                    .where(SalesAgent.is_archived.is_(False))
                    .order_by(SalesAgent.name)
                ).all()
            ]
            return managers, countries, agents

        self._managers, countries, self._agents = self.ctx.read(_load)
        self.filter_bar.set_options("manager_id", self._managers, t("common.manager"))
        self.filter_bar.set_options("country", countries, t("common.country"))
        super().refresh()

    def load_rows(self, filters: dict[str, Any]) -> list[dict]:
        """Fetch buyers matching the filter bar."""

        def _load(session: Session) -> list[dict]:
            return buyer_service.search_buyers(
                session,
                text=filters.get("text", ""),
                country=filters.get("country"),
                buyer_type=filters.get("buyer_type"),
                source=filters.get("source"),
                manager_id=filters.get("manager_id"),
                risk_level=filters.get("risk_level"),
                include_archived=bool(filters.get("archived")),
            )

        return self.ctx.read(_load)

    # ------------------------------------------------------------- detail
    def fill_detail(self, row: dict) -> None:
        """Populate the 360° buyer panel."""
        buyer_id = row["id"]

        def _load(session: Session) -> dict:
            data = buyer_service.buyer_dict(session, buyer_id)
            data["leads"] = lead_service.search_leads(session, buyer_id=None)
            data["leads"] = [lead for lead in data["leads"] if lead["buyer_id"] == buyer_id]
            data["quotations"] = quotation_service.list_quotations(session, buyer_id=buyer_id)
            data["rfqs"] = quotation_service.list_rfqs(session, buyer_id=buyer_id)
            data["emails"] = email_service.list_messages(session, buyer_id=buyer_id)
            data["shipments"] = logistics_service.list_shipments(session, buyer_id=buyer_id)
            data["documents"] = document_service.list_documents(session, buyer_id=buyer_id)
            data["tasks"] = task_service.list_tasks(session, entity_type=None, status="open")
            data["tasks"] = [task for task in data["tasks"] if task["buyer_id"] == buyer_id]
            data["checklists"] = checklist_service.list_checklists(
                session, scope="buyer", entity_id=buyer_id
            )
            data["timeline"] = audit_service.timeline(session, "buyer", buyer_id, 60)
            return data

        data = self.ctx.read(_load)
        self.detail.set_header(
            data["company_name"],
            f"{data['country']} · {te('buyer_type', data['buyer_type'])}",
            "buyer_status",
            data["status"],
        )
        if self.ctx.can("buyer.edit"):
            self.detail.add_action(t("common.edit"), lambda: self.open_editor(buyer_id), "Primary")
        if self.ctx.can("lead.edit"):
            self.detail.add_action(t("lead.new"), lambda: self._new_lead(buyer_id))
        if self.ctx.can("email.send"):
            self.detail.add_action(t("email.new"), lambda: self._new_email(buyer_id))

        self.detail.add_fields_tab(
            t("buyer.tab_profile"),
            [
                (t("buyer.contact_person"), data.get("contact_person")),
                (t("buyer.position"), data.get("position")),
                (t("common.email"), data.get("email")),
                (t("common.phone"), data.get("phone")),
                (t("common.website"), data.get("website")),
                (t("buyer.linkedin"), data.get("linkedin")),
                (t("buyer.address"), data.get("address")),
                (t("buyer.interested"), data.get("interested_categories")),
                (t("buyer.annual_potential"), fmt_money(data.get("annual_potential"))),
                (t("buyer.target_market"), data.get("target_market")),
                (t("common.source"), te("lead_source", data.get("source"))),
                (t("buyer.risk"), te("risk_level", data.get("risk_level"))),
                (t("common.language"), (data.get("language") or "").upper()),
                (t("common.tags"), data.get("tags")),
                (t("common.notes"), data.get("notes")),
            ],
        )
        self.detail.add_list_tab(
            t("buyer.contacts"),
            [
                f"{'★ ' if c['is_primary'] else ''}{c['full_name']} · {c['position']} · "
                f"{c['email']} · {c['phone']}"
                for c in data.get("contacts", [])
            ],
        )
        self.detail.add_list_tab(
            t("nav.leads"),
            [
                f"{lead['title']} · {te('lead_status', lead['status'])} · "
                f"{fmt_money(lead['expected_value'], lead['currency'])}"
                for lead in data["leads"]
            ],
        )
        self.detail.add_list_tab(
            t("buyer.tab_quotations"),
            [f"RFQ {r['number']} · {te('rfq_status', r['status'])}" for r in data["rfqs"]]
            + [
                f"{q['number']} · {te('quotation_status', q['status'])} · "
                f"{fmt_money(q['grand_total'], q['currency'])}"
                for q in data["quotations"]
            ],
        )
        self.detail.add_list_tab(
            t("buyer.tab_conversations"),
            [
                f"{fmt_date(m['sent_at'])} · {m['subject']} · {te('email_status', m['status'])}"
                for m in data["emails"]
            ],
        )
        self.detail.add_list_tab(
            t("buyer.tab_logistics"),
            [
                f"{s['number']} · {s['destination']} · {te('shipment_status', s['status'])}"
                for s in data["shipments"]
            ],
        )
        self.detail.add_list_tab(
            t("buyer.tab_documents"),
            [f"{d['title']} · {te('certificate_type', d['doc_type'])}" for d in data["documents"]],
        )
        self.detail.add_list_tab(
            t("buyer.tab_checklist"),
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
            t("buyer.tab_activity"),
            [f"{fmt_datetime(item['happened_at'])} · {item['title']}" for item in data["timeline"]],
        )

    def on_row_activated(self, row: dict) -> None:
        """Open the editor on double click."""
        if self.ctx.can("buyer.edit"):
            self.open_editor(row["id"])

    # ------------------------------------------------------------ actions
    def on_new(self) -> None:
        """Create a new buyer."""
        if self.ctx.can("buyer.edit"):
            self.open_editor(None)

    def open_editor(self, buyer_id: int | None) -> None:
        """Show the buyer editor with duplicate detection."""
        values: dict[str, Any] = {
            "buyer_type": "importer",
            "risk_level": "medium",
            "language": "en",
            "source": "manual",
            "status": "active",
        }
        if buyer_id:
            values = self.ctx.read(lambda s: buyer_service.buyer_dict(s, buyer_id))

        fields = [
            Field("company_name", t("buyer.company"), required=True),
            Field("contact_person", t("buyer.contact_person")),
            Field("position", t("buyer.position")),
            Field("country", t("common.country"), required=True),
            Field("city", t("common.city")),
            Field("address", t("buyer.address"), "textarea", height=60),
            Field("email", t("common.email")),
            Field("phone", t("common.phone")),
            Field("website", t("common.website")),
            Field("linkedin", t("buyer.linkedin")),
            Field(
                "buyer_type", t("buyer.type"), "enum", BUYER_TYPES, "buyer_type", with_empty=False
            ),
            Field("interested_categories", t("buyer.interested")),
            Field("annual_potential", t("buyer.annual_potential"), "money"),
            Field("target_market", t("buyer.target_market")),
            Field(
                "language",
                t("common.language"),
                "combo",
                [("en", "English"), ("ru", "Русский"), ("uz", "O‘zbekcha")],
                with_empty=False,
            ),
            Field(
                "source", t("common.source"), "enum", LEAD_SOURCES, "lead_source", with_empty=False
            ),
            Field("manager_id", t("common.manager"), "combo", self._managers),
            Field("agent_id", t("common.agent"), "combo", self._agents),
            Field(
                "risk_level", t("buyer.risk"), "enum", RISK_LEVELS, "risk_level", with_empty=False
            ),
            Field("tags", t("common.tags")),
            Field("notes", t("common.notes"), "textarea", height=70),
        ]

        state = {"allow_duplicate": False}

        def _save(collected: dict[str, Any]) -> int:
            payload = dict(collected)
            payload["id"] = buyer_id
            try:
                return self.ctx.run(
                    lambda s: buyer_service.save_buyer(
                        s, self.ctx.user, payload, allow_duplicate=state["allow_duplicate"]
                    ).id
                )
            except ValidationError as exc:
                matches = exc.params.get("matches") or []
                if exc.key != "error.buyer_duplicate" or not matches:
                    raise
                text = "\n".join(
                    f"• {m['company_name']} ({m['country']}) — {', '.join(m['reasons'])}"
                    for m in matches
                )
                if not self.confirm(
                    t("buyer.duplicate_question", matches=text), t("buyer.duplicate_found")
                ):
                    raise
                state["allow_duplicate"] = True
                return self.ctx.run(
                    lambda s: buyer_service.save_buyer(
                        s, self.ctx.user, payload, allow_duplicate=True
                    ).id
                )

        dialog = FormDialog(
            t("buyer.new") if not buyer_id else values.get("company_name", ""),
            fields,
            values,
            _save,
            self,
        )
        if dialog.exec():
            self.ctx.notify("buyer")
            self.info(t("common.saved"))

    def _new_lead(self, buyer_id: int) -> None:
        from app.ui.pages.leads_page import open_lead_editor

        if open_lead_editor(self, self.ctx, None, buyer_id):
            self.ctx.notify("lead")

    def _new_email(self, buyer_id: int) -> None:
        from app.ui.dialogs.email_dialog import open_email_composer

        if open_email_composer(self, self.ctx, buyer_id=buyer_id):
            self.ctx.notify("email")

    def _import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, t("common.import"), "", "Excel (*.xlsx *.xlsm)")
        if not path:
            return
        try:
            result = self.ctx.run(lambda s: import_service.import_buyers(s, self.ctx.user, path))
            self.ctx.notify("buyer")
            self.info(f"+{result['created']} / ={result['duplicates']} / −{result['skipped']}")
        except Exception as exc:
            self.handle_error(exc)

    def on_export(self) -> None:
        """Export the buyer register."""
        path, _ = QFileDialog.getSaveFileName(
            self, t("common.export"), "buyers.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            written = self.ctx.run(lambda s: import_service.export_buyers(s, self.ctx.user, path))
            self.info(t("common.exported", path=written))
        except Exception as exc:
            self.handle_error(exc)
