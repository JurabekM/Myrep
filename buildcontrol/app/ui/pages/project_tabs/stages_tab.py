"""Work stages: Gantt timeline, stage table and the daily site log."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QWidget

from app.models.enums import StageStatus
from app.services import estimate_service, project_service, stage_service
from app.services.permissions import Perm
from app.ui.dialogs.base_dialog import confirm
from app.ui.dialogs.form_dialog import (
    COMBO,
    DATE,
    FILE,
    INT,
    PERCENT,
    TEXT,
    TEXTAREA,
    Field,
    FormDialog,
)
from app.ui.pages.base_page import BasePage
from app.ui.styles.theme import COLORS
from app.ui.widgets.common import Card, button
from app.ui.widgets.gantt import GanttPanel
from app.ui.widgets.table import (
    BADGE,
    PROGRESS,
    Col,
    DataTable,
    make_combo,
)
from app.ui.widgets.table import (
    DATE as C_DATE,
)
from app.utils.i18n import tr
from app.utils.labels import options, stage_status_label

_KIND = {
    StageStatus.NOT_STARTED.value: "neutral",
    StageStatus.IN_PROGRESS.value: "accent",
    StageStatus.REVIEW.value: "info",
    StageStatus.DELAYED.value: "danger",
    StageStatus.DONE.value: "success",
    StageStatus.BLOCKED.value: "warning",
}


class StagesTab(BasePage):
    """Schedule of one project."""

    permission = Perm.STAGE_VIEW

    def __init__(self, project_id: int, parent: QWidget | None = None) -> None:
        super().__init__("", "", parent, show_header=False, compact=True)
        self.project_id = project_id

        self.gantt = GanttPanel()
        self.gantt.chart.stage_clicked.connect(self._select_stage)
        gantt_card = Card(tr("timeline"))
        gantt_card.body().addWidget(self.gantt)
        self.root.addWidget(gantt_card, 0)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_stage_table())
        splitter.addWidget(self._build_log_table())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        self.root.addWidget(splitter, 1)

    # -- construction --------------------------------------------------------------- #
    def _build_stage_table(self) -> QWidget:
        card = Card(tr("stages"))
        self.table = DataTable(
            [
                Col("name", tr("stage"), stretch=True),
                Col("section", tr("linked_section"), width=170),
                Col("plan_start", tr("plan_start"), C_DATE, width=110),
                Col("plan_end", tr("plan_end"), C_DATE, width=110),
                Col("actual_start", tr("actual_start"), C_DATE, width=110),
                Col("actual_end", tr("actual_end"), C_DATE, width=110),
                Col("progress_percent", tr("percent_done"), PROGRESS, width=110),
                Col("responsible", tr("responsible"), width=150),
                Col(
                    "status",
                    tr("status"),
                    BADGE,
                    width=140,
                    badge=lambda r: (
                        stage_status_label(r["status"]),
                        _KIND.get(r["status"], "neutral"),
                    ),
                ),
            ]
        )
        self.table.set_row_color(
            lambda r: COLORS.danger if r["status"] == StageStatus.DELAYED.value else None
        )
        self.status_filter = make_combo(options(StageStatus, include_all=True))
        self.status_filter.currentIndexChanged.connect(self.refresh)
        self.table.add_filter(self.status_filter)

        self.new_btn = button(tr("new_stage"), "add", "Primary")
        self.new_btn.clicked.connect(self._create_stage)
        self.edit_btn = button(tr("edit"), "edit")
        self.edit_btn.clicked.connect(self._edit_stage)
        self.up_btn = button("", "up", "Ghost", tr("move_up"))
        self.up_btn.setFixedWidth(34)
        self.up_btn.clicked.connect(lambda: self._move(-1))
        self.down_btn = button("", "down", "Ghost", tr("move_down"))
        self.down_btn.setFixedWidth(34)
        self.down_btn.clicked.connect(lambda: self._move(1))
        self.del_btn = button(tr("archive"), "archive", "Ghost")
        self.del_btn.clicked.connect(self._delete_stage)
        for widget in (self.new_btn, self.edit_btn, self.up_btn, self.down_btn, self.del_btn):
            self.table.add_action(widget)
            widget.setEnabled(self.can(Perm.STAGE_EDIT))
        self.table.selection_changed.connect(lambda _row: self._reload_logs())
        self.table.row_activated.connect(lambda _row: self._edit_stage())
        card.body().addWidget(self.table, 1)
        return card

    def _build_log_table(self) -> QWidget:
        card = Card(tr("site_log"))
        self.log_table = DataTable(
            [
                Col("log_date", tr("date"), C_DATE, width=110),
                Col("stage", tr("stage"), width=180),
                Col("work_done", tr("work_done"), stretch=True),
                Col("progress_percent", tr("percent_done"), PROGRESS, width=110),
                Col("workers_count", tr("workers_count"), width=120),
                Col(
                    "issue",
                    tr("issue"),
                    width=200,
                    color=lambda r: COLORS.warning if r["issue"] else None,
                ),
                Col("author", tr("author"), width=140),
            ],
            paginated=False,
        )
        self.new_log_btn = button(tr("new_log"), "add", "Primary")
        self.new_log_btn.clicked.connect(self._create_log)
        self.edit_log_btn = button(tr("edit"), "edit")
        self.edit_log_btn.clicked.connect(self._edit_log)
        self.del_log_btn = button(tr("delete"), "delete", "Ghost")
        self.del_log_btn.clicked.connect(self._delete_log)
        for widget in (self.new_log_btn, self.edit_log_btn, self.del_log_btn):
            self.log_table.add_action(widget)
            widget.setEnabled(self.can(Perm.STAGE_EDIT))
        card.body().addWidget(self.log_table, 1)
        return card

    # -- data ---------------------------------------------------------------------- #
    def refresh(self) -> None:
        """Reload stages, timeline and logs."""
        rows = stage_service.list_stages(
            self.project_id, status=self.status_filter.currentData() or ""
        )
        self.table.set_rows(rows)
        self.gantt.set_rows(stage_service.stage_gantt_rows(self.project_id))
        self._reload_logs()

    def _reload_logs(self) -> None:
        self.log_table.set_rows(stage_service.list_logs(self.project_id))

    def _select_stage(self, stage_id: int) -> None:
        for index, row in enumerate(self.table.model.page_rows()):
            if row["id"] == stage_id:
                self.table.view.selectRow(index)
                return

    # -- stage actions -------------------------------------------------------------- #
    def _stage_fields(self) -> list[Field]:
        return [
            Field("name", tr("stage"), TEXT, required=True, span=2),
            Field(
                "section_id",
                tr("linked_section"),
                COMBO,
                options=estimate_service.section_choices(self.project_id),
                span=2,
            ),
            Field("plan_start", tr("plan_start"), DATE, default=date.today()),
            Field("plan_end", tr("plan_end"), DATE, default=date.today() + timedelta(days=14)),
            Field("actual_start", tr("actual_start"), DATE),
            Field("actual_end", tr("actual_end"), DATE),
            Field("progress_percent", tr("percent_done"), PERCENT),
            Field("status", tr("status"), COMBO, options=options(StageStatus)),
            Field(
                "responsible_id",
                tr("responsible"),
                COMBO,
                options=project_service.user_choices(),
            ),
            Field("dependencies", tr("dependencies"), TEXT, hint="1,2,3"),
            Field("note", tr("note"), TEXTAREA, span=2),
        ]

    def _create_stage(self) -> None:
        dialog = FormDialog(
            tr("new_stage"),
            self._stage_fields(),
            {"status": StageStatus.NOT_STARTED.value},
            parent=self,
        )
        if not dialog.exec():
            return
        self._save_stage(dialog.values(), None)

    def _edit_stage(self) -> None:
        row = self.table.current_row()
        if row is None:
            return
        dialog = FormDialog(tr("stage"), self._stage_fields(), row, row["name"], parent=self)
        if not dialog.exec():
            return
        self._save_stage(dialog.values(), row["id"])

    def _save_stage(self, values: dict, stage_id: int | None) -> None:
        values["project_id"] = self.project_id
        values["section_id"] = values.get("section_id") or None
        values["responsible_id"] = values.get("responsible_id") or None
        try:
            stage_service.save_stage(values, self.actor, stage_id)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    def _move(self, direction: int) -> None:
        row = self.table.current_row()
        if row is None:
            return
        try:
            stage_service.move_stage(row["id"], direction, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.refresh()

    def _delete_stage(self) -> None:
        row = self.table.current_row()
        if row is None or not confirm(self, tr("confirm_question"), tr("archive")):
            return
        try:
            stage_service.delete_stage(row["id"], self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.refresh()

    # -- log actions ------------------------------------------------------------------ #
    def _log_fields(self) -> list[Field]:
        return [
            Field("log_date", tr("date"), DATE, default=date.today()),
            Field(
                "stage_id",
                tr("stage"),
                COMBO,
                options=stage_service.stage_choices(self.project_id),
            ),
            Field("work_done", tr("work_done"), TEXTAREA, required=True, span=2),
            Field("progress_percent", tr("percent_done"), PERCENT),
            Field("workers_count", tr("workers_count"), INT, maximum=10_000),
            Field("issue", tr("issue"), TEXTAREA, span=2),
            Field("photo_path", tr("photo"), FILE, span=2),
        ]

    def _create_log(self) -> None:
        selected = self.table.current_row()
        dialog = FormDialog(
            tr("new_log"),
            self._log_fields(),
            {"stage_id": selected["id"] if selected else ""},
            parent=self,
        )
        if not dialog.exec():
            return
        self._save_log(dialog.values(), None)

    def _edit_log(self) -> None:
        row = self.log_table.current_row()
        if row is None:
            return
        dialog = FormDialog(tr("site_log"), self._log_fields(), row, parent=self)
        if not dialog.exec():
            return
        self._save_log(dialog.values(), row["id"])

    def _save_log(self, values: dict, log_id: int | None) -> None:
        values["project_id"] = self.project_id
        values["stage_id"] = values.get("stage_id") or None
        try:
            stage_service.save_log(values, self.actor, log_id)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    def _delete_log(self) -> None:
        row = self.log_table.current_row()
        if row is None or not confirm(self, tr("confirm_question"), tr("delete")):
            return
        try:
            stage_service.delete_log(row["id"], self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self._reload_logs()
