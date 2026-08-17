"""Tasks / follow-up worksheet with the automation rule engine trigger."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QMenu, QPushButton, QWidget

from app.controllers.app_context import AppContext
from app.models.enums import Permission as Perm
from app.models.enums import TaskStatus
from app.services import auth_service, task_service
from app.ui.dialogs.misc_dialogs import TaskDialog
from app.ui.i18n import tr
from app.ui.pages.base_page import BasePage
from app.ui.styles import theme
from app.ui.widgets.common import (
    DataTable,
    FilterChip,
    MetricTile,
    Panel,
    SearchBox,
    colored_item,
    combo,
    show_info,
)
from app.ui.widgets.labels import (
    priority_color,
    priority_label,
    task_status_items,
    task_status_label,
    task_type_items,
    task_type_label,
)
from app.utils.dates import fmt_datetime, now

COLUMNS = [
    "common.title",
    "common.type",
    "common.name",
    "tasks.assignee",
    "tasks.due",
    "common.priority",
    "common.status",
]

STATUS_COLORS = {
    TaskStatus.OPEN: theme.INFO,
    TaskStatus.IN_PROGRESS: theme.ACCENT,
    TaskStatus.DONE: theme.SUCCESS,
    TaskStatus.CANCELLED: theme.TEXT_DISABLED,
    TaskStatus.OVERDUE: theme.DANGER,
}


class TasksPage(BasePage):
    """Follow-up worksheet."""

    title_key = "tasks.title"
    subtitle_key = "app.subtitle"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self._build()
        context.tasks_updated.connect(self.reload)

    def _build(self) -> None:
        """Assemble the toolbar and the table."""
        self.new_button = QPushButton(tr("tasks.new"))
        self.new_button.setObjectName("Primary")
        self.new_button.setIcon(theme.icon("fa6s.plus", "#FFFFFF"))
        self.new_button.clicked.connect(self._create)
        self.header().addWidget(self.new_button)

        self.rules_button = QPushButton(tr("tasks.run_rules"))
        self.rules_button.clicked.connect(self._run_rules)
        self.header().addWidget(self.rules_button)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.tile_open = MetricTile(tr("tstatus.open"), "0", theme.INFO)
        self.tile_overdue = MetricTile(tr("tstatus.overdue"), "0", theme.DANGER)
        self.tile_today = MetricTile(tr("common.today"), "0", theme.WARNING)
        self.tile_done = MetricTile(tr("tstatus.done"), "0", theme.SUCCESS)
        for tile in (self.tile_open, self.tile_overdue, self.tile_today, self.tile_done):
            metrics.addWidget(tile)
        metrics.addStretch(1)
        self.body().addLayout(metrics)

        filters = Panel(padding=10, spacing=8)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.search_box = SearchBox(tr("common.search"))
        self.search_box.textChanged.connect(self.reload)
        row.addWidget(self.search_box, 2)

        self.status_box = combo(task_status_items())
        self.status_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.status_box)

        self.type_box = combo(task_type_items())
        self.type_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.type_box)

        operators = auth_service.list_operators()
        self.assignee_box = combo(
            [(tr("common.all"), None)] + [(u.full_name, u.id) for u in operators]
        )
        self.assignee_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.assignee_box)

        self.chip_mine = FilterChip(tr("tasks.my"))
        self.chip_mine.clicked.connect(self.reload)
        row.addWidget(self.chip_mine)
        self.chip_overdue = FilterChip(tr("tasks.overdue"))
        self.chip_overdue.clicked.connect(self.reload)
        row.addWidget(self.chip_overdue)
        row.addStretch(1)
        filters.body().addLayout(row)
        self.body().addWidget(filters)

        panel = Panel(padding=8, spacing=6)
        self.table = DataTable([tr(key) for key in COLUMNS], stretch_column=0)
        self.table.doubleClicked.connect(self._edit)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_menu)
        panel.body().addWidget(self.table, 1)
        self.body().addWidget(panel, 1)

    # ------------------------------------------------------------------ #
    def reload(self) -> None:
        """Reload the task table."""
        status = self.status_box.currentData()
        task_type = self.type_box.currentData()
        statuses = [status] if status else None
        if self.chip_overdue.isChecked():
            statuses = [TaskStatus.OVERDUE]
        try:
            tasks = task_service.list_tasks(
                actor=self.user,
                statuses=statuses,
                task_types=[task_type] if task_type else None,
                assignee_id=self.assignee_box.currentData(),
                search=self.search_box.text(),
                only_mine=self.chip_mine.isChecked(),
            )
        except Exception as exc:
            self.handle_error(exc)
            return

        rows = []
        ids = []
        counters = {"open": 0, "overdue": 0, "today": 0, "done": 0}
        current = now()
        for task in tasks:
            ids.append(task.id)
            if task.status in (TaskStatus.OPEN, TaskStatus.IN_PROGRESS):
                counters["open"] += 1
            if task.status == TaskStatus.OVERDUE:
                counters["overdue"] += 1
            if task.status == TaskStatus.DONE:
                counters["done"] += 1
            if task.due_at and task.due_at.date() == current.date():
                counters["today"] += 1
            rows.append(
                [
                    task.title,
                    task_type_label(task.task_type),
                    task.lead.display_name if task.lead else "—",
                    task.assignee.full_name if task.assignee else "—",
                    fmt_datetime(task.due_at),
                    colored_item(priority_label(task.priority), priority_color(task.priority)),
                    colored_item(
                        task_status_label(task.status),
                        STATUS_COLORS.get(task.status, theme.TEXT_MUTED),
                        bold=True,
                    ),
                ]
            )
        self.table.fill(rows, ids=ids)
        self.tile_open.set_value(str(counters["open"]))
        self.tile_overdue.set_value(str(counters["overdue"]))
        self.tile_today.set_value(str(counters["today"]))
        self.tile_done.set_value(str(counters["done"]))

    def _create(self) -> None:
        """Create a task."""
        if not self.require(Perm.TASK_MANAGE):
            return
        dialog = TaskDialog(self.user, parent=self)
        if dialog.exec():
            self.reload()

    def _edit(self) -> None:
        """Edit the selected task."""
        task_id = self.table.selected_id()
        if task_id is None:
            return
        tasks = {t.id: t for t in task_service.list_tasks(actor=self.user, limit=1000)}
        task = tasks.get(task_id)
        if task is None:
            return
        dialog = TaskDialog(self.user, task=task, parent=self)
        if dialog.exec():
            self.reload()

    def _show_menu(self, position) -> None:
        """Row context menu."""
        task_id = self.table.selected_id()
        if task_id is None:
            return
        menu = QMenu(self)
        menu.addAction(tr("tasks.complete"), lambda: self._complete(task_id))
        menu.addAction(tr("common.edit"), self._edit)
        menu.addSeparator()
        menu.addAction(
            tr("tstatus.in_progress"), lambda: self._set_status(task_id, TaskStatus.IN_PROGRESS)
        )
        menu.addAction(
            tr("tstatus.cancelled"), lambda: self._set_status(task_id, TaskStatus.CANCELLED)
        )
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _complete(self, task_id: int) -> None:
        """Mark a task as done."""
        try:
            task_service.complete_task(task_id, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.reload()

    def _set_status(self, task_id: int, status: str) -> None:
        """Change a task status."""
        try:
            task_service.update_task(task_id, actor=self.user, status=status)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.reload()

    def _run_rules(self) -> None:
        """Run the automation rules on demand."""
        try:
            counters = task_service.run_rules()
        except Exception as exc:
            self.handle_error(exc)
            return
        show_info(
            self,
            " · ".join(f"{key}: {value}" for key, value in counters.items()),
        )
        self.reload()
        self.context.notifications_updated.emit()

    def retranslate(self) -> None:
        """Reapply translated captions."""
        super().retranslate()
        self.new_button.setText(tr("tasks.new"))
        self.rules_button.setText(tr("tasks.run_rules"))
        self.chip_mine.setText(tr("tasks.my"))
        self.chip_overdue.setText(tr("tasks.overdue"))
        self.table.set_headers([tr(key) for key in COLUMNS])
        self.tile_open.set_label(tr("tstatus.open"))
        self.tile_overdue.set_label(tr("tstatus.overdue"))
        self.tile_today.set_label(tr("common.today"))
        self.tile_done.set_label(tr("tstatus.done"))
        self.reload()
