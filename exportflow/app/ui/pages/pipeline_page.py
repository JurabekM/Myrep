"""Kanban pipeline workspace with drag-and-drop stage changes."""

from __future__ import annotations

import json

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.controllers.app_context import AppContext
from app.services import auth_service, buyer_service, lead_service
from app.ui.i18n import t, te
from app.ui.pages.base_page import BasePage
from app.ui.pages.leads_page import change_lead_stage, open_lead_editor
from app.ui.styles.theme import COLORS, status_colors
from app.ui.widgets.common import PageHeader, button
from app.ui.widgets.table import FilterBar, FilterSpec
from app.utils.enums import LEAD_SOURCES, PIPELINE_STAGES
from app.utils.formatting import fmt_date, fmt_money

MIME_TYPE = "application/x-exportflow-lead"


class LeadCard(QFrame):
    """Draggable deal card."""

    activated = Signal(int)

    def __init__(self, lead: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("KanbanCard")
        self.lead = lead
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        accent = status_colors(lead.get("temperature"))[0]
        self.setStyleSheet(f"QFrame#KanbanCard {{ border-left-color: {accent}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 9)
        layout.setSpacing(3)

        title = QLabel(lead["title"])
        title.setObjectName("KanbanTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        meta = QLabel(
            f"{lead.get('buyer', '')} · {lead.get('country', '')}\n"
            f"{lead.get('product', '') or '—'}"
        )
        meta.setObjectName("KanbanMeta")
        meta.setWordWrap(True)
        layout.addWidget(meta)

        value = QLabel(fmt_money(lead.get("expected_value"), lead.get("currency") or "USD"))
        value.setStyleSheet(f"color: {COLORS['success']}; font-weight: 700;")
        layout.addWidget(value)

        footer_text = f"{lead.get('manager') or '—'}"
        if lead.get("next_follow_up"):
            footer_text += f" · {fmt_date(lead['next_follow_up'])}"
        footer = QLabel(footer_text)
        footer.setObjectName("KanbanMeta")
        if lead.get("overdue"):
            footer.setStyleSheet(f"color: {COLORS['danger']}; font-weight: 600;")
        layout.addWidget(footer)

        if lead.get("next_step"):
            step = QLabel("→ " + lead["next_step"])
            step.setObjectName("KanbanMeta")
            step.setWordWrap(True)
            layout.addWidget(step)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Start a drag operation carrying the lead id."""
        if event.button() != Qt.MouseButton.LeftButton:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_TYPE, json.dumps({"id": self.lead["id"]}).encode("utf-8"))
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.exec(Qt.DropAction.MoveAction)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Open the lead editor."""
        self.activated.emit(self.lead["id"])


class StageColumn(QWidget):
    """One kanban column accepting dropped cards."""

    lead_dropped = Signal(int, str)
    lead_activated = Signal(int)

    def __init__(self, stage: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("KanbanColumn")
        self.stage = stage
        self.setAcceptDrops(True)
        self.setMinimumWidth(232)
        self.setMaximumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.header = QLabel(te("lead_status", stage))
        self.header.setObjectName("KanbanHeader")
        fg = status_colors(stage)[0]
        self.header.setStyleSheet(f"color: {fg}; font-weight: 700;")
        layout.addWidget(self.header)

        self.summary = QLabel("")
        self.summary.setObjectName("KanbanMeta")
        layout.addWidget(self.summary)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cards_host = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch(1)
        scroll.setWidget(self.cards_host)
        layout.addWidget(scroll, 1)

    def set_leads(self, leads: list[dict]) -> None:
        """Replace every card in the column."""
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        total = sum(lead.get("expected_value") or 0 for lead in leads)
        self.summary.setText(
            t("pipeline.deals", count=len(leads), value=fmt_money(total))
            if leads
            else t("pipeline.no_deals")
        )
        for lead in leads:
            card = LeadCard(lead)
            card.activated.connect(self.lead_activated.emit)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    def retranslate(self) -> None:
        """Re-apply the stage caption."""
        self.header.setText(te("lead_status", self.stage))

    # ------------------------------------------------------------ drag&drop
    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Accept lead drags."""
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()
            self.setStyleSheet(
                f"QWidget#KanbanColumn {{ border-color: {COLORS['accent']}; background-color: #16233A; }}"
            )

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Reset the highlight."""
        self.setStyleSheet("")

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Emit the stage change request."""
        self.setStyleSheet("")
        if not event.mimeData().hasFormat(MIME_TYPE):
            return
        payload = json.loads(bytes(event.mimeData().data(MIME_TYPE)).decode("utf-8"))
        event.acceptProposedAction()
        self.lead_dropped.emit(int(payload["id"]), self.stage)


class PipelinePage(BasePage):
    """Kanban board over the open export deals."""

    permission = "lead.view"
    topics = ("lead", "quotation", "contract")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        self.header = PageHeader()
        root.addWidget(self.header)
        if ctx.can("lead.edit"):
            self.header.add_action(button(t("lead.new"), self.on_new, "Primary"))
        self.header.add_action(button(t("common.refresh"), self.refresh, "Ghost"))

        self.filter_bar = FilterBar(
            [
                FilterSpec("country", t("common.country"), "combo", [], width=130),
                FilterSpec("source", t("common.source"), "enum", LEAD_SOURCES, "lead_source", 130),
                FilterSpec("manager_id", t("common.manager"), "combo", [], width=150),
            ]
        )
        self.filter_bar.changed.connect(self.refresh)
        root.addWidget(self.filter_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        board = QWidget()
        self.board_layout = QHBoxLayout(board)
        self.board_layout.setContentsMargins(0, 0, 0, 0)
        self.board_layout.setSpacing(10)
        scroll.setWidget(board)
        root.addWidget(scroll, 1)

        self.columns: dict[str, StageColumn] = {}
        for stage in PIPELINE_STAGES:
            column = StageColumn(stage)
            column.lead_dropped.connect(self._on_drop)
            column.lead_activated.connect(self._open_lead)
            self.board_layout.addWidget(column)
            self.columns[stage] = column

        self.retranslate()

    # --------------------------------------------------------------- data
    def refresh(self) -> None:
        """Reload the board."""
        filters = self.filter_bar.values()

        def _load(session: Session) -> tuple[dict, list, list]:
            board = lead_service.pipeline_board(
                session,
                text=filters.get("text", ""),
                country=filters.get("country"),
                source=filters.get("source"),
                manager_id=filters.get("manager_id"),
            )
            managers = [
                (user["id"], user["full_name"] or user["username"])
                for user in auth_service.list_users(session)
            ]
            countries = [(name, name) for name in buyer_service.distinct_countries(session)]
            return board, managers, countries

        try:
            board, managers, countries = self.ctx.read(_load)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.filter_bar.set_options("manager_id", managers, t("common.manager"))
        self.filter_bar.set_options("country", countries, t("common.country"))
        for stage, column in self.columns.items():
            column.set_leads(board.get(stage, []))

    def retranslate(self) -> None:
        """Re-apply captions."""
        self.header.set_texts(t("pipeline.title"), t("pipeline.subtitle"))
        for column in self.columns.values():
            column.retranslate()
        if self._loaded:
            self.refresh()

    # ------------------------------------------------------------ actions
    def _on_drop(self, lead_id: int, stage: str) -> None:
        if not self.ctx.can("lead.edit"):
            self.ctx.show_toast(t("error.permission_denied"), "warning")
            return
        try:
            if change_lead_stage(self, self.ctx, lead_id, stage):
                self.info(te("lead_status", stage))
        except Exception as exc:
            self.handle_error(exc)
        self.refresh()

    def _open_lead(self, lead_id: int) -> None:
        if self.ctx.can("lead.edit") and open_lead_editor(self, self.ctx, lead_id):
            self.ctx.notify("lead")

    def on_new(self) -> None:
        """Create a new deal."""
        if self.ctx.can("lead.edit") and open_lead_editor(self, self.ctx, None):
            self.ctx.notify("lead")

    def on_export(self) -> None:
        """Export the pipeline report."""
        from app.services import report_service

        try:
            path = self.ctx.run(
                lambda s: report_service.export(s, self.ctx.user, "pipeline_by_country", "xlsx")
            )
            self.info(t("common.exported", path=path))
        except Exception as exc:
            self.handle_error(exc)
