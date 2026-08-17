"""Email history and follow-up page."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget
from sqlalchemy.orm import Session

from app.controllers.app_context import AppContext
from app.services import email_service, task_service
from app.ui.dialogs.email_dialog import open_email_composer
from app.ui.i18n import t, te
from app.ui.pages.base_page import BasePage
from app.ui.widgets.common import PageHeader, banner, button
from app.ui.widgets.detail_panel import DetailPanel
from app.ui.widgets.table import Column, DataTable
from app.utils.formatting import fmt_datetime


class EmailPage(BasePage):
    """Three tabs: sent history, buyers awaiting a reply and open tasks."""

    permission = "email.view"
    topics = ("email", "task", "quotation")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        self.header = PageHeader()
        root.addWidget(self.header)
        if ctx.can("email.send"):
            self.header.add_action(button(t("email.new"), self.on_new, "Primary"))
        self.header.add_action(button(t("common.refresh"), self.refresh, "Ghost"))

        states = {state["kind"]: state for state in ctx.integration_states()}
        self.demo_banner = banner(t("email.provider_demo"), "info")
        self.demo_banner.setVisible(states.get("email", {}).get("is_demo", True))
        root.addWidget(self.demo_banner)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.history_table = DataTable(self._history_columns())
        self.history_table.selection_changed.connect(self._on_history_selected)
        self.history_table.row_activated.connect(self._open_message)
        self.waiting_table = DataTable(self._waiting_columns())
        self.waiting_table.row_activated.connect(self._reply_to)
        self.tasks_table = DataTable(self._task_columns())
        self.tasks_table.row_activated.connect(self._complete_task)

        self.tabs.addTab(self.history_table, t("email.history"))
        self.tabs.addTab(self.waiting_table, t("email.awaiting_reply"))
        self.tabs.addTab(self.tasks_table, t("workspace.my_tasks"))

        self.detail = DetailPanel()
        self.detail.setVisible(False)
        root.addWidget(self.detail)
        self.detail.setMaximumHeight(260)

        self.retranslate()

    # ------------------------------------------------------------- columns
    def _history_columns(self) -> list[Column]:
        return [
            Column("sent_at", t("common.date"), kind="datetime", width=140),
            Column("buyer", t("common.buyer"), width=190),
            Column("to_address", t("email.to"), width=200),
            Column("subject", t("email.subject"), stretch=True),
            Column("status", t("common.status"), kind="status", group="email_status", width=120),
            Column("provider", t("settings.provider"), width=120),
        ]

    def _waiting_columns(self) -> list[Column]:
        return [
            Column("sent_at", t("common.date"), kind="datetime", width=140),
            Column("buyer", t("common.buyer"), width=200),
            Column("subject", t("email.subject"), stretch=True),
            Column("days_waiting", t("email.days_waiting"), kind="number", decimals=0, width=120),
        ]

    def _task_columns(self) -> list[Column]:
        return [
            Column("due_date", t("common.due_date"), kind="date", width=110),
            Column("title", t("common.name"), stretch=True),
            Column("assignee", t("common.assignee"), width=150),
            Column("priority", t("common.priority"), kind="status", group="priority", width=110),
            Column("status", t("common.status"), kind="status", group="task_status", width=110),
        ]

    # --------------------------------------------------------------- data
    def refresh(self) -> None:
        """Reload all three tabs."""

        def _load(session: Session) -> tuple[list, list, list]:
            return (
                email_service.list_messages(session),
                email_service.awaiting_reply(session),
                task_service.list_tasks(session, status="open"),
            )

        try:
            history, waiting, tasks = self.ctx.read(_load)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.history_table.set_rows(history)
        self.waiting_table.set_rows(waiting)
        self.tasks_table.set_rows(tasks)

    def retranslate(self) -> None:
        """Re-apply captions."""
        self.header.set_texts(t("email.title"))
        self.tabs.setTabText(0, t("email.history"))
        self.tabs.setTabText(1, t("email.awaiting_reply"))
        self.tabs.setTabText(2, t("workspace.my_tasks"))
        self.history_table.set_columns(self._history_columns())
        self.waiting_table.set_columns(self._waiting_columns())
        self.tasks_table.set_columns(self._task_columns())
        if self._loaded:
            self.refresh()

    # ------------------------------------------------------------ actions
    def on_new(self) -> None:
        """Compose a new message."""
        if open_email_composer(self, self.ctx):
            self.ctx.notify("email")

    def _on_history_selected(self, row: dict | None) -> None:
        if row is None:
            self.detail.set_empty()
            return
        self.detail.clear_tabs()
        self.detail.clear_actions()
        self.detail.set_header(row["subject"], row["to_address"], "email_status", row["status"])
        if self.ctx.can("email.send"):
            self.detail.add_action(t("email.mark_replied"), lambda: self._mark_replied(row["id"]))
            self.detail.add_action(t("email.new"), lambda: self._reply_to(row), "Primary")
        self.detail.add_fields_tab(
            t("common.details"),
            [
                (t("common.buyer"), row["buyer"]),
                (t("email.to"), row["to_address"]),
                (t("common.date"), fmt_datetime(row["sent_at"])),
                (t("common.status"), te("email_status", row["status"])),
                (t("settings.provider"), row["provider"]),
                (t("common.notes"), row["error_message"]),
            ],
        )
        self.detail.add_list_tab(t("email.body"), (row["body"] or "").splitlines())
        self.detail.setVisible(True)

    def _open_message(self, row: dict) -> None:
        self._on_history_selected(row)

    def _reply_to(self, row: dict) -> None:
        if not self.ctx.can("email.send"):
            return
        if open_email_composer(
            self, self.ctx, buyer_id=row.get("buyer_id"), lead_id=row.get("lead_id")
        ):
            self.ctx.notify("email")

    def _mark_replied(self, message_id: int) -> None:
        try:
            self.ctx.run(lambda s: email_service.mark_reply_received(s, self.ctx.user, message_id))
            self.ctx.notify("email")
        except Exception as exc:
            self.handle_error(exc)

    def _complete_task(self, row: dict) -> None:
        try:
            self.ctx.run(lambda s: task_service.complete_task(s, self.ctx.user, row["id"]))
            self.ctx.notify("task")
        except Exception as exc:
            self.handle_error(exc)

    def on_export(self) -> None:
        """Not applicable on this page."""
        return None

    def load_rows(self, filters: dict[str, Any]) -> list[dict]:  # pragma: no cover - unused
        """Kept for interface symmetry with :class:`RecordPage`."""
        return []
