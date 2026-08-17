"""Reports page: filters on the left, live preview on the right."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import REPORTS_DIR
from app.reports import excel_reports, pdf_reports
from app.services import project_service, report_service
from app.services.permissions import Perm
from app.services.report_service import REPORT_TYPES, ReportData, ReportFilters
from app.ui.dialogs.base_dialog import show_info
from app.ui.pages.base_page import BasePage
from app.ui.styles.theme import SPACING, SPACING_SM
from app.ui.widgets.common import Card, button, field_label
from app.ui.widgets.table import Col, DataTable
from app.utils.files import open_path
from app.utils.formatting import fmt_money
from app.utils.i18n import tr


class ReportsPage(BasePage):
    """Builds, previews and exports every report."""

    permission = Perm.REPORT_VIEW

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("reports"), "", parent)
        self._data: ReportData | None = None

        body = QHBoxLayout()
        body.setSpacing(SPACING)
        self.root.addLayout(body, 1)

        body.addWidget(self._build_sidebar(), 0)
        body.addWidget(self._build_preview(), 1)

        self.report_list.setCurrentRow(0)

    # -- construction ----------------------------------------------------------- #
    def _build_sidebar(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setFixedWidth(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(SPACING, SPACING, SPACING, SPACING)
        layout.setSpacing(SPACING_SM)

        layout.addWidget(field_label(tr("report_type")))
        self.report_list = QListWidget()
        self.report_list.setFrameShape(QFrame.Shape.NoFrame)
        for key, title_key, _needs_project in REPORT_TYPES:
            item = QListWidgetItem(tr(title_key))
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.report_list.addItem(item)
        self.report_list.currentRowChanged.connect(self._on_report_changed)
        layout.addWidget(self.report_list, 1)

        layout.addWidget(field_label(tr("project")))
        self.project_box = QComboBox()
        for value, label in project_service.project_choices():
            self.project_box.addItem(label, value)
        layout.addWidget(self.project_box)

        layout.addWidget(field_label(tr("date_from")))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setDate(QDate.currentDate().addMonths(-6))
        layout.addWidget(self.date_from)

        layout.addWidget(field_label(tr("date_to")))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setDate(QDate.currentDate().addDays(30))
        layout.addWidget(self.date_to)

        layout.addWidget(field_label(tr("status")))
        self.status_box = QComboBox()
        layout.addWidget(self.status_box)

        self.generate_btn = button(tr("generate"), "refresh", "Primary")
        self.generate_btn.clicked.connect(self.refresh)
        layout.addWidget(self.generate_btn)

        buttons = QHBoxLayout()
        self.pdf_btn = button(tr("export_pdf"), "pdf")
        self.pdf_btn.clicked.connect(self._export_pdf)
        self.excel_btn = button(tr("export_excel"), "excel")
        self.excel_btn.clicked.connect(self._export_excel)
        buttons.addWidget(self.pdf_btn)
        buttons.addWidget(self.excel_btn)
        layout.addLayout(buttons)

        self.folder_btn = button(tr("open_folder"), "open", "Ghost")
        self.folder_btn.clicked.connect(lambda: open_path(REPORTS_DIR))
        layout.addWidget(self.folder_btn)
        return panel

    def _build_preview(self) -> QWidget:
        self.preview_card = Card(tr("reports"))
        self.table = DataTable([Col("name", tr("name"), stretch=True)], searchable=True)
        self.preview_card.body().addWidget(self.table, 1)
        return self.preview_card

    # -- behaviour --------------------------------------------------------------- #
    def _current_key(self) -> str:
        item = self.report_list.currentItem()
        return str(item.data(Qt.ItemDataRole.UserRole)) if item else "estimate"

    def _on_report_changed(self) -> None:
        key = self._current_key()
        needs_project = next((n for k, _t, n in REPORT_TYPES if k == key), False)
        self.project_box.setEnabled(True)
        if needs_project and not self.project_box.currentData():
            for index in range(self.project_box.count()):
                if self.project_box.itemData(index):
                    self.project_box.setCurrentIndex(index)
                    break
        self.status_box.clear()
        for value, label in report_service.status_options(key):
            self.status_box.addItem(label, value)
        self.refresh()

    def _filters(self) -> ReportFilters:
        def to_date(widget: QDateEdit) -> date:
            qdate = widget.date()
            return date(qdate.year(), qdate.month(), qdate.day())

        project_id = self.project_box.currentData()
        return ReportFilters(
            project_id=int(project_id) if project_id else None,
            date_from=to_date(self.date_from),
            date_to=to_date(self.date_to),
            status=str(self.status_box.currentData() or ""),
        )

    def refresh(self) -> None:
        """Rebuild the currently selected report."""
        key = self._current_key()
        filters = self._filters()
        needs_project = next((n for k, _t, n in REPORT_TYPES if k == key), False)
        if needs_project and not filters.project_id:
            self.header.set_subtitle(tr("select_row_first"))
            return
        try:
            data = report_service.build(key, filters)
        except Exception as exc:
            self.handle(exc)
            return
        self._data = data
        self._render(data)

    def _render(self, data: ReportData) -> None:
        columns = [
            Col(c.key, c.title, _kind(c.kind), stretch=(c.width or 1) >= 2.0) for c in data.columns
        ]
        new_table = DataTable(columns)
        new_table.set_rows(data.rows)
        layout = self.preview_card.body()
        previous = self.table
        layout.replaceWidget(previous, new_table)
        # Detach immediately: deleteLater alone would leave the old table visible
        # until the next event loop pass, stacking previews on top of each other.
        previous.setParent(None)
        previous.deleteLater()
        self.table = new_table

        titles = {c.key: c.title for c in data.columns}
        subtitle = data.subtitle
        if data.totals:
            subtitle += "   " + "   ".join(
                f"{titles.get(key, key)}: {fmt_money(value)}" for key, value in data.totals.items()
            )
        self.header.set_subtitle(f"{data.title} · {len(data.rows)} {tr('rows')}   {subtitle}")

    # -- export ------------------------------------------------------------------ #
    def _export_pdf(self) -> None:
        if self._data is None:
            return
        try:
            path = pdf_reports.render_report(self._data)
        except Exception as exc:
            self.handle(exc)
            return
        show_info(self, f"{tr('report_saved')}:\n{path}")
        open_path(path)

    def _export_excel(self) -> None:
        if self._data is None:
            return
        try:
            path = excel_reports.render_report(self._data)
        except Exception as exc:
            self.handle(exc)
            return
        show_info(self, f"{tr('report_saved')}:\n{path}")
        open_path(path)


def _kind(report_kind: str) -> str:
    from app.ui.widgets import table as table_widget

    return {
        "money": table_widget.MONEY,
        "number": table_widget.NUMBER,
        "percent": table_widget.PERCENT,
        "date": table_widget.DATE,
    }.get(report_kind, table_widget.TEXT)
