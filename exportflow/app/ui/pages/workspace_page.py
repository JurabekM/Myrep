"""Workspace: the operational start page (not a classic dashboard).

It is a work queue: metrics that navigate, plus the concrete tasks, alerts and
follow-ups the signed-in user has to act on today.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QSplitter, QVBoxLayout, QWidget
from sqlalchemy.orm import Session

from app.controllers.app_context import AppContext
from app.services import (
    audit_service,
    document_service,
    lead_service,
    logistics_service,
    report_service,
    task_service,
)
from app.ui.i18n import t
from app.ui.pages.base_page import BasePage
from app.ui.widgets.common import PageHeader, StatCard, button, section_title
from app.ui.widgets.table import Column, DataTable
from app.utils.formatting import fmt_date, fmt_money

#: Metric key -> (translation key, accent colour, navigation target)
METRICS = (
    ("open_leads", "workspace.open_leads", "accent", "leads"),
    ("pipeline_value", "workspace.pipeline_value", "success", "pipeline"),
    ("overdue_follow_ups", "workspace.overdue_follow_ups", "danger", "leads"),
    ("quotations_sent", "workspace.quotations_sent", "warning", "quotations"),
    ("expiring_certificates", "workspace.expiring_certificates", "warning", "certificates"),
    ("delayed_shipments", "workspace.delayed_shipments", "danger", "shipments"),
    ("overdue_checklists", "workspace.overdue_checklists", "danger", "checklists"),
    ("revenue_actual", "workspace.revenue_actual", "success", "reports"),
)


class WorkspacePage(BasePage):
    """Metric strip plus three working lists."""

    topics = ("*",)
    navigate = Signal(str)

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        self.header = PageHeader()
        root.addWidget(self.header)
        self.header.add_action(button(t("common.refresh"), self.refresh, "Ghost"))

        grid_host = QWidget()
        self.grid = QGridLayout(grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(10)
        self.cards: dict[str, StatCard] = {}
        for index, (key, label_key, accent, target) in enumerate(METRICS):
            card = StatCard(t(label_key), "0", accent)
            card.clicked.connect(lambda page=target: self.navigate.emit(page))
            self.grid.addWidget(card, index // 4, index % 4)
            self.cards[key] = card
        root.addWidget(grid_host)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        tasks_host = QWidget()
        tasks_layout = QVBoxLayout(tasks_host)
        tasks_layout.setContentsMargins(0, 0, 8, 0)
        tasks_layout.setSpacing(6)
        self.tasks_title = section_title(t("workspace.my_tasks"))
        tasks_layout.addWidget(self.tasks_title)
        self.tasks_table = DataTable(self._task_columns())
        self.tasks_table.row_activated.connect(self._complete_task)
        tasks_layout.addWidget(self.tasks_table, 1)
        splitter.addWidget(tasks_host)

        follow_host = QWidget()
        follow_layout = QVBoxLayout(follow_host)
        follow_layout.setContentsMargins(8, 0, 8, 0)
        follow_layout.setSpacing(6)
        self.follow_title = section_title(t("workspace.follow_ups"))
        follow_layout.addWidget(self.follow_title)
        self.follow_table = DataTable(self._follow_columns())
        self.follow_table.row_activated.connect(lambda _row: self.navigate.emit("leads"))
        follow_layout.addWidget(self.follow_table, 1)
        splitter.addWidget(follow_host)

        alerts_host = QWidget()
        alerts_layout = QVBoxLayout(alerts_host)
        alerts_layout.setContentsMargins(8, 0, 0, 0)
        alerts_layout.setSpacing(6)
        self.alerts_title = section_title(t("workspace.alerts"))
        alerts_layout.addWidget(self.alerts_title)
        self.alerts_table = DataTable(self._alert_columns())
        alerts_layout.addWidget(self.alerts_table, 1)
        self.activity_title = section_title(t("workspace.recent_activity"))
        alerts_layout.addWidget(self.activity_title)
        self.activity_table = DataTable(self._activity_columns())
        alerts_layout.addWidget(self.activity_table, 1)
        splitter.addWidget(alerts_host)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)
        root.addWidget(splitter, 1)

        self.retranslate()

    # ------------------------------------------------------------- columns
    def _task_columns(self) -> list[Column]:
        return [
            Column("due_date", t("common.due_date"), kind="date", width=100),
            Column("title", t("common.name"), stretch=True),
            Column("priority", t("common.priority"), kind="status", group="priority", width=100),
        ]

    def _follow_columns(self) -> list[Column]:
        return [
            Column("next_follow_up", t("lead.next_follow_up"), kind="date", width=110),
            Column("title", t("lead.name"), stretch=True),
            Column("buyer", t("common.buyer"), width=150),
            Column("status", t("common.stage"), kind="status", group="lead_status", width=140),
        ]

    def _alert_columns(self) -> list[Column]:
        return [
            Column("kind", t("common.type"), width=120),
            Column("title", t("common.description"), stretch=True),
            Column("due", t("common.date"), width=110),
        ]

    def _activity_columns(self) -> list[Column]:
        return [
            Column("at", t("common.date"), kind="datetime", width=140),
            Column("summary", t("common.description"), stretch=True),
        ]

    # --------------------------------------------------------------- data
    def refresh(self) -> None:
        """Reload metrics and all working lists."""

        def _load(session: Session) -> dict:
            counters = report_service.dashboard_counters(session)
            tasks = task_service.list_tasks(
                session, assignee_id=self.ctx.user.id, status="open", limit=60
            )
            if not tasks:
                tasks = task_service.list_tasks(session, status="open", limit=60)
            follow_ups = [
                lead
                for lead in lead_service.search_leads(session, include_closed=False)
                if lead["next_follow_up"]
            ][:60]
            alerts = []
            for alert in document_service.expiry_alerts(session):
                alerts.append(
                    {
                        "kind": t("nav.certificates"),
                        "title": f"{alert['name']} · {alert['days_left']} d",
                        "due": fmt_date(alert["expiry_date"]),
                    }
                )
            for delay in logistics_service.delay_alerts(session):
                alerts.append(
                    {
                        "kind": t("nav.shipments"),
                        "title": f"{delay['number']} · {delay['kind'].upper()} +{delay['days']} d",
                        "due": fmt_date(delay["planned"]),
                    }
                )
            activity = audit_service.search(session, limit=40)
            return {
                "counters": counters,
                "tasks": tasks,
                "follow_ups": follow_ups,
                "alerts": alerts,
                "activity": activity,
            }

        try:
            data = self.ctx.read(_load)
        except Exception as exc:
            self.handle_error(exc)
            return

        counters = data["counters"]
        for key, card in self.cards.items():
            value = counters.get(key, 0)
            if key in ("pipeline_value", "revenue_actual"):
                card.set_value(fmt_money(value))
            else:
                card.set_value(str(value))
        self.tasks_table.set_rows(data["tasks"])
        self.follow_table.set_rows(data["follow_ups"])
        self.alerts_table.set_rows(data["alerts"])
        self.activity_table.set_rows(data["activity"])

    def retranslate(self) -> None:
        """Re-apply captions."""
        self.header.set_texts(t("workspace.title"), t("workspace.subtitle"))
        for key, label_key, _accent, _target in METRICS:
            self.cards[key].set_label(t(label_key))
        self.tasks_title.setText(t("workspace.my_tasks"))
        self.follow_title.setText(t("workspace.follow_ups"))
        self.alerts_title.setText(t("workspace.alerts"))
        self.activity_title.setText(t("workspace.recent_activity"))
        self.tasks_table.set_columns(self._task_columns())
        self.follow_table.set_columns(self._follow_columns())
        self.alerts_table.set_columns(self._alert_columns())
        self.activity_table.set_columns(self._activity_columns())
        if self._loaded:
            self.refresh()

    # ------------------------------------------------------------ actions
    def _complete_task(self, row: dict) -> None:
        if not self.confirm(t("workspace.complete_task")):
            return
        try:
            self.ctx.run(lambda s: task_service.complete_task(s, self.ctx.user, row["id"]))
            self.ctx.notify("task")
        except Exception as exc:
            self.handle_error(exc)
