"""Report shortcuts scoped to a single project."""

from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from app.reports import excel_reports, pdf_reports
from app.services import report_service
from app.services.permissions import Perm
from app.services.report_service import REPORT_TYPES, ReportFilters
from app.ui.dialogs.base_dialog import show_info
from app.ui.pages.base_page import BasePage
from app.ui.styles.theme import SPACING
from app.ui.widgets.common import Card, button
from app.utils.files import open_path
from app.utils.i18n import tr


class ProjectReportsTab(BasePage):
    """One card per report with PDF and Excel export buttons."""

    permission = Perm.REPORT_VIEW

    def __init__(self, project_id: int, parent: QWidget | None = None) -> None:
        super().__init__("", "", parent, show_header=False, compact=True)
        self.project_id = project_id

        grid = QGridLayout()
        grid.setSpacing(SPACING)
        for index, (key, title_key, _needs_project) in enumerate(REPORT_TYPES):
            grid.addWidget(self._build_card(key, title_key), index // 3, index % 3)
        for column in range(3):
            grid.setColumnStretch(column, 1)
        self.root.addLayout(grid)
        self.root.addStretch(1)

    def _build_card(self, key: str, title_key: str) -> QWidget:
        card = Card(tr(title_key))
        hint = QLabel(tr("report_type"))
        hint.setObjectName("CardHint")
        card.body().addWidget(hint)
        pdf_btn = button(tr("export_pdf"), "pdf", "Primary")
        pdf_btn.clicked.connect(lambda _=False, k=key: self._export(k, "pdf"))
        excel_btn = button(tr("export_excel"), "excel")
        excel_btn.clicked.connect(lambda _=False, k=key: self._export(k, "excel"))
        card.body().addWidget(pdf_btn)
        card.body().addWidget(excel_btn)
        return card

    def _export(self, key: str, fmt: str) -> None:
        try:
            data = report_service.build(key, ReportFilters(project_id=self.project_id))
            path = (
                pdf_reports.render_report(data)
                if fmt == "pdf"
                else excel_reports.render_report(data)
            )
        except Exception as exc:
            self.handle(exc)
            return
        show_info(self, f"{tr('report_saved')}:\n{path}")
        open_path(path)

    def refresh(self) -> None:
        """Nothing to reload — the cards are static shortcuts."""
