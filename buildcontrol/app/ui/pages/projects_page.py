"""Projects register and the entry point into a project workspace."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QStackedWidget, QWidget

from app.models.enums import ProjectStatus, ProjectType
from app.services import project_service
from app.services.permissions import Perm
from app.ui.dialogs.base_dialog import confirm
from app.ui.dialogs.form_dialog import COMBO, DATE, MONEY, TEXT, TEXTAREA, Field, FormDialog
from app.ui.pages.base_page import BasePage
from app.ui.pages.project_workspace import ProjectWorkspace
from app.ui.styles.theme import COLORS
from app.ui.widgets.common import button
from app.ui.widgets.table import BADGE, Col, DataTable, make_combo
from app.ui.widgets.table import DATE as C_DATE
from app.ui.widgets.table import MONEY as C_MONEY
from app.utils.formatting import fmt_money
from app.utils.i18n import tr
from app.utils.labels import (
    options,
    project_status_label,
    project_type_label,
)

_STATUS_KIND = {
    ProjectStatus.PLANNED.value: "info",
    ProjectStatus.ACTIVE.value: "success",
    ProjectStatus.SUSPENDED.value: "warning",
    ProjectStatus.COMPLETED.value: "accent",
    ProjectStatus.ARCHIVED.value: "neutral",
}


def project_fields(managers: list[tuple], for_edit: bool = False) -> list[Field]:
    """Return the form specification of a project card."""
    return [
        Field("name", tr("project_name"), TEXT, required=True, span=2),
        Field("client", tr("client"), TEXT),
        Field("address", tr("address"), TEXT),
        Field("project_type", tr("project_type"), COMBO, options=options(ProjectType)),
        Field("status", tr("status"), COMBO, options=options(ProjectStatus)),
        Field("start_date", tr("start_date"), DATE),
        Field("end_date", tr("end_date"), DATE),
        Field("manager_id", tr("manager"), COMBO, options=managers),
        Field(
            "planned_budget",
            tr("planned_budget"),
            MONEY,
            required=not for_edit,
            maximum=1e15,
        ),
        Field("notes", tr("notes"), TEXTAREA, span=2),
    ]


class ProjectListPage(BasePage):
    """Filterable register of every project."""

    permission = Perm.PROJECT_VIEW

    def __init__(self, on_open, parent: QWidget | None = None) -> None:
        super().__init__(tr("projects"), tr("app_subtitle"), parent)
        self._on_open = on_open

        self.new_btn = button(tr("new_project"), "add", "Primary")
        self.new_btn.clicked.connect(self._create)
        self.new_btn.setEnabled(self.can(Perm.PROJECT_EDIT))
        self.header.add_action(self.new_btn)

        self.table = DataTable(self._columns())
        self.table.set_row_color(self._row_color)
        self.table.row_activated.connect(lambda row: self._on_open(row["id"]))

        self.status_filter = make_combo(options(ProjectStatus, include_all=True))
        self.status_filter.currentIndexChanged.connect(self.refresh)
        self.table.add_filter(self.status_filter)

        self.type_filter = make_combo(options(ProjectType, include_all=True))
        self.type_filter.currentIndexChanged.connect(self.refresh)
        self.table.add_filter(self.type_filter)

        self.archived_box = QCheckBox(tr("show_archived"))
        self.archived_box.stateChanged.connect(self.refresh)
        self.table.add_filter(self.archived_box)

        self.open_btn = button(tr("open_project"), "open", "Primary")
        self.open_btn.clicked.connect(self._open_selected)
        self.edit_btn = button(tr("edit"), "edit")
        self.edit_btn.clicked.connect(self._edit_selected)
        self.archive_btn = button(tr("archive"), "archive", "Ghost")
        self.archive_btn.clicked.connect(self._archive_selected)
        for widget in (self.open_btn, self.edit_btn, self.archive_btn):
            self.table.add_action(widget)
        self.table.selection_changed.connect(self._update_actions)

        self.root.addWidget(self.table, 1)
        self._update_actions(None)

    # -- table ---------------------------------------------------------------- #
    def _columns(self) -> list[Col]:
        return [
            Col("code", tr("code"), width=90),
            Col("name", tr("project_name"), stretch=True),
            Col("client", tr("client"), width=160),
            Col(
                "project_type",
                tr("project_type"),
                width=130,
                formatter=lambda r: project_type_label(r["project_type"]),
            ),
            Col("start_date", tr("start_date"), C_DATE, width=100),
            Col("end_date", tr("end_date"), C_DATE, width=100),
            Col("manager", tr("manager"), width=150),
            Col("planned_budget", tr("planned_budget"), C_MONEY, width=150),
            Col(
                "actual",
                tr("actual_cost"),
                C_MONEY,
                width=150,
                color=lambda r: (
                    COLORS.danger
                    if r["planned_budget"] and r["actual"] > r["planned_budget"]
                    else None
                ),
            ),
            Col(
                "status",
                tr("status"),
                BADGE,
                width=130,
                badge=lambda r: (
                    project_status_label(r["status"]),
                    _STATUS_KIND.get(r["status"], "neutral"),
                ),
            ),
        ]

    def _row_color(self, row: dict) -> str | None:
        if row.get("is_archived"):
            return COLORS.text_faint
        return None

    # -- data ----------------------------------------------------------------- #
    def refresh(self) -> None:
        """Reload the project list applying the current filters."""
        status = self.status_filter.currentData() or ""
        type_filter = self.type_filter.currentData() or ""
        rows = []
        for project in project_service.list_projects(
            status=status, include_archived=self.archived_box.isChecked()
        ):
            if type_filter and project.project_type != type_filter:
                continue
            rows.append(
                {
                    "id": project.id,
                    "code": project.code,
                    "name": project.name,
                    "client": project.client,
                    "address": project.address,
                    "project_type": project.project_type,
                    "start_date": project.start_date,
                    "end_date": project.end_date,
                    "manager": project.manager,
                    "planned_budget": project.planned_budget,
                    "actual": project.actual,
                    "status": project.status,
                    "is_archived": project.is_archived,
                }
            )
        self.table.set_rows(rows)
        self.header.set_subtitle(self._summary_text())
        self._update_actions(self.table.current_row())

    def _summary_text(self) -> str:
        summary = project_service.portfolio_summary()
        return (
            f"{tr('projects')}: {summary['count']}  ·  {tr('enum.project_status.active')}: "
            f"{summary['active']}  ·  {tr('budget')}: {fmt_money(summary['budget'])}  ·  "
            f"{tr('actual_cost')}: {fmt_money(summary['actual'])}  ·  "
            f"{tr('over_budget')}: {summary['over_budget']}"
        )

    # -- actions -------------------------------------------------------------- #
    def _update_actions(self, row: dict | None) -> None:
        has_row = row is not None
        may_edit = self.can(Perm.PROJECT_EDIT)
        self.open_btn.setEnabled(has_row)
        self.edit_btn.setEnabled(has_row and may_edit)
        self.archive_btn.setEnabled(has_row and self.can(Perm.PROJECT_ARCHIVE))
        if has_row:
            self.archive_btn.setText(tr("restore") if row.get("is_archived") else tr("archive"))

    def _open_selected(self) -> None:
        row = self.table.current_row()
        if row:
            self._on_open(row["id"])

    def _create(self) -> None:
        managers = project_service.user_choices()
        dialog = FormDialog(
            tr("new_project"),
            project_fields(managers),
            {"status": ProjectStatus.PLANNED.value},
            parent=self,
        )
        if not dialog.exec():
            return
        values = dialog.values()
        values["manager_id"] = values["manager_id"] or None
        try:
            project_id = project_service.save_project(values, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()
        self._on_open(project_id)

    def _edit_selected(self) -> None:
        row = self.table.current_row()
        if row is None:
            return
        data = project_service.get_project(row["id"])
        managers = project_service.user_choices()
        dialog = FormDialog(
            tr("edit"), project_fields(managers, for_edit=True), data, data["name"], parent=self
        )
        if not dialog.exec():
            return
        values = dialog.values()
        values["manager_id"] = values["manager_id"] or None
        try:
            project_service.save_project(values, self.actor, row["id"])
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    def _archive_selected(self) -> None:
        row = self.table.current_row()
        if row is None:
            return
        restoring = bool(row.get("is_archived"))
        if not restoring and not confirm(self, tr("archive_project_q"), tr("archive")):
            return
        try:
            project_service.archive_project(row["id"], self.actor, not restoring)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()


class ProjectsPage(QStackedWidget):
    """Switches between the project register and a single project workspace."""

    permission = Perm.PROJECT_VIEW

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.list_page = ProjectListPage(self.open_project)
        self.addWidget(self.list_page)
        self.workspace: ProjectWorkspace | None = None

    def open_project(self, project_id: int) -> None:
        """Open the workspace of ``project_id``."""
        if self.workspace is not None:
            self.removeWidget(self.workspace)
            self.workspace.deleteLater()
        self.workspace = ProjectWorkspace(project_id, self.show_list)
        self.addWidget(self.workspace)
        self.setCurrentWidget(self.workspace)

    def show_list(self) -> None:
        """Return to the project register."""
        self.setCurrentWidget(self.list_page)
        self.list_page.refresh()

    def refresh(self) -> None:
        """Refresh whichever view is currently visible."""
        widget = self.currentWidget()
        if hasattr(widget, "refresh"):
            widget.refresh()
