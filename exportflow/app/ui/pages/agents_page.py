"""Sales agents and performance page."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QFileDialog, QTabWidget, QVBoxLayout, QWidget
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.controllers.app_context import AppContext
from app.models import SalesAgent
from app.services import audit_service, report_service
from app.ui.dialogs.form_dialog import Field, FormDialog
from app.ui.i18n import t
from app.ui.pages.base_page import BasePage
from app.ui.widgets.common import PageHeader, button
from app.ui.widgets.detail_panel import DetailPanel
from app.ui.widgets.table import Column, DataTable


class AgentsPage(BasePage):
    """Agent register plus the manager/agent performance tables."""

    permission = "agent.view"
    topics = ("lead", "buyer", "contract")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        self.header = PageHeader()
        root.addWidget(self.header)
        if ctx.can("agent.edit"):
            self.header.add_action(button(t("agent.new"), self.on_new, "Primary"))
        self.header.add_action(button(t("common.export"), self.on_export, "Ghost"))
        self.header.add_action(button(t("common.refresh"), self.refresh, "Ghost"))

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.agents_table = DataTable(self._agent_columns())
        self.agents_table.selection_changed.connect(self._on_agent_selected)
        self.agents_table.row_activated.connect(lambda row: self.open_editor(row))
        self.manager_table = DataTable(self._manager_columns())
        self.agent_perf_table = DataTable(self._agent_perf_columns())

        self.tabs.addTab(self.agents_table, t("agent.tab_agents"))
        self.tabs.addTab(self.manager_table, t("report.manager_performance"))
        self.tabs.addTab(self.agent_perf_table, t("report.agent_performance"))

        self.detail = DetailPanel()
        self.detail.setVisible(False)
        self.detail.setMaximumHeight(250)
        root.addWidget(self.detail)

        self.retranslate()

    # ------------------------------------------------------------- columns
    def _agent_columns(self) -> list[Column]:
        return [
            Column("name", t("common.name"), stretch=True),
            Column("country", t("common.country"), width=120),
            Column("market", t("agent.market"), width=180),
            Column("email", t("common.email"), width=200),
            Column("phone", t("common.phone"), width=150),
            Column(
                "commission_percent", t("agent.commission"), kind="percent", decimals=1, width=120
            ),
            Column("commission_status", t("agent.commission_status"), kind="status", width=130),
        ]

    def _manager_columns(self) -> list[Column]:
        return [
            Column("manager", t("common.manager"), stretch=True),
            Column("leads", t("nav.leads"), kind="number", decimals=0, width=80),
            Column("rfqs", t("nav.rfq"), kind="number", decimals=0, width=80),
            Column("quotations", t("nav.quotations"), kind="number", decimals=0, width=100),
            Column("samples", t("buyer.tab_samples"), kind="number", decimals=0, width=90),
            Column("won", t("enum.lead_status.closed_won"), kind="number", decimals=0, width=70),
            Column("lost", t("enum.lead_status.closed_lost"), kind="number", decimals=0, width=70),
            Column(
                "conversion",
                t("report.quotation_conversion"),
                kind="percent",
                decimals=1,
                width=120,
            ),
            Column("expected", t("lead.expected_value"), kind="money", width=130),
            Column("won_value", t("workspace.revenue_actual"), kind="money", width=130),
            Column("avg_cycle", t("common.date"), kind="number", decimals=1, width=110),
        ]

    def _agent_perf_columns(self) -> list[Column]:
        return [
            Column("name", t("common.agent"), stretch=True),
            Column("country", t("common.country"), width=120),
            Column("buyers", t("agent.buyers"), kind="number", decimals=0, width=90),
            Column("leads", t("nav.leads"), kind="number", decimals=0, width=80),
            Column("won", t("enum.lead_status.closed_won"), kind="number", decimals=0, width=70),
            Column("lost", t("enum.lead_status.closed_lost"), kind="number", decimals=0, width=70),
            Column("won_value", t("workspace.revenue_actual"), kind="money", width=130),
            Column(
                "commission_percent", t("agent.commission"), kind="percent", decimals=1, width=110
            ),
            Column("commission_value", t("common.amount"), kind="money", width=130),
        ]

    # --------------------------------------------------------------- data
    def refresh(self) -> None:
        """Reload the agent list and both performance tables."""

        def _load(session: Session) -> tuple[list, list, list]:
            agents = [
                {
                    "id": row.id,
                    "name": row.name,
                    "country": row.country or "",
                    "market": row.market or "",
                    "email": row.email or "",
                    "phone": row.phone or "",
                    "commission_percent": row.commission_percent,
                    "commission_terms": row.commission_terms or "",
                    "commission_status": row.commission_status,
                    "notes": row.notes or "",
                }
                for row in session.scalars(
                    select(SalesAgent)
                    .where(SalesAgent.is_archived.is_(False))
                    .order_by(SalesAgent.name)
                ).all()
            ]
            managers = report_service.build(session, "manager_performance")["rows"]
            performance = report_service.build(session, "agent_performance")["rows"]
            return agents, managers, performance

        try:
            agents, managers, performance = self.ctx.read(_load)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.agents_table.set_rows(agents)
        self.manager_table.set_rows(managers)
        self.agent_perf_table.set_rows(performance)

    def retranslate(self) -> None:
        """Re-apply captions."""
        self.header.set_texts(t("agent.title"))
        self.tabs.setTabText(0, t("agent.tab_agents"))
        self.tabs.setTabText(1, t("report.manager_performance"))
        self.tabs.setTabText(2, t("report.agent_performance"))
        self.agents_table.set_columns(self._agent_columns())
        self.manager_table.set_columns(self._manager_columns())
        self.agent_perf_table.set_columns(self._agent_perf_columns())
        if self._loaded:
            self.refresh()

    # ------------------------------------------------------------ actions
    def _on_agent_selected(self, row: dict | None) -> None:
        if row is None:
            self.detail.set_empty()
            return
        self.detail.clear_tabs()
        self.detail.clear_actions()
        self.detail.set_header(row["name"], row["market"], "", row["commission_status"])
        if self.ctx.can("agent.edit"):
            self.detail.add_action(t("common.edit"), lambda: self.open_editor(row), "Primary")
        self.detail.add_fields_tab(
            t("common.details"),
            [
                (t("common.country"), row["country"]),
                (t("agent.market"), row["market"]),
                (t("common.email"), row["email"]),
                (t("common.phone"), row["phone"]),
                (t("agent.commission"), f"{row['commission_percent']}%"),
                (t("agent.commission_terms"), row["commission_terms"]),
                (t("common.notes"), row["notes"]),
            ],
        )
        self.detail.setVisible(True)

    def on_new(self) -> None:
        """Create a new sales agent."""
        self.open_editor(None)

    def open_editor(self, row: dict | None) -> None:
        """Show the agent editor."""
        if not self.ctx.can("agent.edit"):
            return
        values: dict[str, Any] = row.copy() if row else {"commission_status": "active"}
        fields = [
            Field("name", t("common.name"), required=True),
            Field("country", t("common.country")),
            Field("market", t("agent.market")),
            Field("email", t("common.email")),
            Field("phone", t("common.phone")),
            Field("commission_percent", t("agent.commission"), "float", decimals=2, maximum=100),
            Field("commission_terms", t("agent.commission_terms"), "textarea", height=60),
            Field(
                "commission_status",
                t("agent.commission_status"),
                "combo",
                [("active", "Active"), ("on_hold", "On hold"), ("closed", "Closed")],
                with_empty=False,
            ),
            Field("notes", t("common.notes"), "textarea", height=60),
        ]

        def _save(collected: dict[str, Any]) -> int:
            def _run(session: Session) -> int:
                agent = session.get(SalesAgent, row["id"]) if row else SalesAgent(name="")
                if row is None:
                    session.add(agent)
                for key in (
                    "name",
                    "country",
                    "market",
                    "email",
                    "phone",
                    "commission_percent",
                    "commission_terms",
                    "commission_status",
                    "notes",
                ):
                    if key in collected:
                        setattr(agent, key, collected[key])
                session.flush()
                audit_service.record(
                    session,
                    action="update" if row else "create",
                    entity_type="sales_agent",
                    entity_id=agent.id,
                    summary=f"Sales agent {agent.name}",
                    user_id=self.ctx.user.id,
                    username=self.ctx.user.username,
                )
                return agent.id

            return self.ctx.run(_run)

        dialog = FormDialog(t("agent.new"), fields, values, _save, self, width=620)
        if dialog.exec():
            self.info(t("common.saved"))
            self.refresh()

    def on_export(self) -> None:
        """Export the currently visible performance table."""
        code = ("agent_performance", "manager_performance", "agent_performance")[
            self.tabs.currentIndex()
        ]
        path, _ = QFileDialog.getSaveFileName(
            self, t("common.export"), f"{code}.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            written = self.ctx.run(
                lambda s: report_service.export(s, self.ctx.user, code, "xlsx", target=path)
            )
            self.info(t("common.exported", path=written))
        except Exception as exc:
            self.handle_error(exc)
