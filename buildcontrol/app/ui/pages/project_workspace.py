"""Single project workspace with the ten operational tabs."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QTabWidget, QVBoxLayout, QWidget

from app.models.enums import CounterpartyKind, ProjectStatus
from app.services import project_service
from app.services.permissions import Perm
from app.ui.pages.counterparties_view import CounterpartiesView
from app.ui.pages.expenses_view import ExpensesView
from app.ui.pages.project_tabs.activity_tab import ActivityTab
from app.ui.pages.project_tabs.documents_tab import DocumentsTab
from app.ui.pages.project_tabs.estimate_tab import EstimateTab
from app.ui.pages.project_tabs.overview_tab import OverviewTab
from app.ui.pages.project_tabs.project_reports_tab import ProjectReportsTab
from app.ui.pages.project_tabs.stages_tab import StagesTab
from app.ui.pages.purchases_view import PurchasesView
from app.ui.pages.warehouse_view import WarehouseView
from app.ui.styles.theme import SPACING, SPACING_LG, SPACING_SM
from app.ui.widgets.common import Badge, button
from app.utils.formatting import fmt_date, fmt_money
from app.utils.i18n import tr
from app.utils.labels import project_status_label, project_type_label

_STATUS_KIND = {
    ProjectStatus.PLANNED.value: "info",
    ProjectStatus.ACTIVE.value: "success",
    ProjectStatus.SUSPENDED.value: "warning",
    ProjectStatus.COMPLETED.value: "accent",
    ProjectStatus.ARCHIVED.value: "neutral",
}


class ProjectWorkspace(QWidget):
    """Header with the project passport plus the tabbed working area."""

    permission = Perm.PROJECT_VIEW

    def __init__(self, project_id: int, on_back, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project_id = project_id
        self._on_back = on_back
        self.project = project_service.get_project(project_id)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING, SPACING_LG, SPACING)
        layout.setSpacing(SPACING_SM)
        layout.addLayout(self._build_header())

        self.tabs = QTabWidget()
        self.tab_widgets: list[QWidget] = []
        self._add_tab(OverviewTab(project_id, self._goto_tab), "tab_overview")
        self._add_tab(EstimateTab(project_id), "tab_estimate")
        self._add_tab(PurchasesView(project_id, show_header=False), "tab_purchases")
        self._add_tab(WarehouseView(project_id, show_header=False), "tab_warehouse")
        self._add_tab(StagesTab(project_id), "tab_stages")
        self._add_tab(
            CounterpartiesView(
                CounterpartyKind.CONTRACTOR.value, show_header=False, locked_kind=True
            ),
            "tab_contractors",
        )
        self._add_tab(ExpensesView(project_id, show_header=False), "tab_expenses")
        self._add_tab(DocumentsTab(project_id), "tab_documents")
        self._add_tab(ProjectReportsTab(project_id), "tab_reports")
        self._add_tab(ActivityTab(project_id), "tab_activity")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs, 1)

    # -- construction ------------------------------------------------------------ #
    def _add_tab(self, widget: QWidget, label_key: str) -> None:
        self.tabs.addTab(widget, tr(label_key))
        self.tab_widgets.append(widget)

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(SPACING)

        back = button(tr("back_to_projects"), "back", "Ghost")
        back.clicked.connect(lambda: self._on_back())
        row.addWidget(back)

        info = QVBoxLayout()
        info.setSpacing(2)
        title = QLabel(f"{self.project['code']} · {self.project['name']}")
        title.setObjectName("PageTitle")
        info.addWidget(title)
        meta = QLabel(self._meta_text())
        meta.setObjectName("PageSubtitle")
        info.addWidget(meta)
        row.addLayout(info)
        row.addStretch(1)

        self.status_badge = Badge(
            project_status_label(self.project["status"]),
            _STATUS_KIND.get(self.project["status"], "neutral"),
        )
        self.status_badge.setMinimumWidth(130)
        self.status_badge.setMinimumHeight(26)
        row.addWidget(self.status_badge)
        return row

    def _meta_text(self) -> str:
        project = self.project
        parts = [
            f"{tr('client')}: {project.get('client') or '—'}",
            f"{tr('address')}: {project.get('address') or '—'}",
            f"{tr('project_type')}: {project_type_label(project.get('project_type'))}",
            f"{tr('manager')}: {project.get('manager_name') or '—'}",
            f"{fmt_date(project.get('start_date'))} — {fmt_date(project.get('end_date'))}",
            f"{tr('budget')}: {fmt_money(project.get('planned_budget'))}",
        ]
        return "   ·   ".join(parts)

    # -- behaviour ---------------------------------------------------------------- #
    def _goto_tab(self, label_key: str) -> None:
        """Jump to a tab from an overview shortcut."""
        target = tr(label_key)
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == target:
                self.tabs.setCurrentIndex(index)
                return

    def _on_tab_changed(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()

    def refresh(self) -> None:
        """Refresh the visible tab."""
        self._on_tab_changed(self.tabs.currentIndex())
