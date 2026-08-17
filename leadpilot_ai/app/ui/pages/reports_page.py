"""Reports page: 12 report types exportable to PDF and Excel."""

from __future__ import annotations

import logging

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QWidget,
)

from app.config import load_config
from app.controllers.app_context import AppContext
from app.models.enums import Permission as Perm
from app.reports import excel_export, pdf_export, report_builder
from app.services import auth_service, company_service
from app.services.analytics_service import PeriodFilter
from app.ui.i18n import tr
from app.ui.pages.base_page import BasePage
from app.ui.styles import theme
from app.ui.widgets.common import (
    DataTable,
    Panel,
    combo,
    show_error,
    show_info,
)
from app.ui.widgets.labels import channel_items, status_items

logger = logging.getLogger(__name__)


class ReportsPage(BasePage):
    """Pick a report, filter it, preview it and export it."""

    title_key = "rep.title"
    subtitle_key = "app.subtitle"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self._sections: list[report_builder.ReportSection] = []
        self._build()

    def _build(self) -> None:
        """Assemble the report picker, filters and preview."""
        self.generate_button = QPushButton(tr("rep.generate"))
        self.generate_button.setObjectName("Primary")
        self.generate_button.clicked.connect(self.generate)
        self.header().addWidget(self.generate_button)

        self.pdf_button = QPushButton(tr("common.export_pdf"))
        self.pdf_button.setIcon(theme.icon("fa6s.file-pdf", theme.DANGER))
        self.pdf_button.clicked.connect(self._export_pdf)
        self.header().addWidget(self.pdf_button)

        self.excel_button = QPushButton(tr("common.export_excel"))
        self.excel_button.setIcon(theme.icon("fa6s.file-excel", theme.SUCCESS))
        self.excel_button.clicked.connect(self._export_excel)
        self.header().addWidget(self.excel_button)

        filters = Panel(padding=10, spacing=8)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        row.addWidget(QLabel(tr("common.from")))
        row.addWidget(self.date_from)
        row.addWidget(QLabel(tr("common.to")))
        row.addWidget(self.date_to)

        self.channel_box = combo(channel_items())
        row.addWidget(self.channel_box)
        self.status_box = combo(status_items())
        row.addWidget(self.status_box)

        operators = auth_service.list_operators()
        self.owner_box = combo(
            [(tr("common.all"), None)] + [(u.full_name, u.id) for u in operators]
        )
        row.addWidget(self.owner_box)

        sources = company_service.list_sources()
        self.source_box = combo([(tr("common.all"), None)] + [(s.name, s.id) for s in sources])
        row.addWidget(self.source_box)

        campaigns = company_service.list_campaigns()
        self.campaign_box = combo([(tr("common.all"), None)] + [(c.name, c.id) for c in campaigns])
        row.addWidget(self.campaign_box)

        branches = company_service.list_branches()
        self.branch_box = combo([(tr("common.all"), None)] + [(b.name, b.id) for b in branches])
        row.addWidget(self.branch_box)

        services = company_service.list_services()
        self.service_box = combo([(tr("common.all"), None)] + [(s.name, s.id) for s in services])
        row.addWidget(self.service_box)
        row.addStretch(1)
        filters.body().addLayout(row)
        self.body().addWidget(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        picker = Panel(padding=8, spacing=6)
        self.picker_title = QLabel(tr("rep.title"))
        self.picker_title.setObjectName("SectionTitle")
        picker.body().addWidget(self.picker_title)
        self.report_list = QListWidget()
        for spec in report_builder.REPORTS:
            item = QListWidgetItem(tr(spec.title_key))
            item.setData(Qt.ItemDataRole.UserRole, spec.key)
            self.report_list.addItem(item)
        self.report_list.setCurrentRow(0)
        self.report_list.currentItemChanged.connect(lambda *_: self.generate())
        picker.body().addWidget(self.report_list, 1)
        picker.setMaximumWidth(300)
        splitter.addWidget(picker)

        preview = Panel(padding=8, spacing=6)
        self.preview_title = QLabel("—")
        self.preview_title.setObjectName("SectionTitle")
        preview.body().addWidget(self.preview_title)
        self.preview_table = DataTable([""], stretch_column=0)
        preview.body().addWidget(self.preview_table, 1)
        self.section_hint = QLabel("")
        self.section_hint.setObjectName("Muted")
        preview.body().addWidget(self.section_hint)
        splitter.addWidget(preview)
        splitter.setSizes([280, 940])
        self.body().addWidget(splitter, 1)

    # ------------------------------------------------------------------ #
    def _current_filter(self) -> PeriodFilter:
        """Build the shared analytics filter from the toolbar."""
        channel = self.channel_box.currentData()
        status = self.status_box.currentData()
        return PeriodFilter(
            date_from=self.date_from.date().toPython(),
            date_to=self.date_to.date().toPython(),
            channels=[channel] if channel else [],
            statuses=[status] if status else [],
            owner_ids=[self.owner_box.currentData()] if self.owner_box.currentData() else [],
            source_ids=[self.source_box.currentData()] if self.source_box.currentData() else [],
            campaign_ids=(
                [self.campaign_box.currentData()] if self.campaign_box.currentData() else []
            ),
            branch_ids=[self.branch_box.currentData()] if self.branch_box.currentData() else [],
            service_ids=[self.service_box.currentData()] if self.service_box.currentData() else [],
        )

    def _current_key(self) -> str:
        """Key of the selected report."""
        item = self.report_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else "leads_registry"

    def generate(self) -> None:
        """Build the selected report and show the first section as a preview."""
        key = self._current_key()
        try:
            self._sections = report_builder.build(key, self._current_filter())
        except Exception as exc:
            self.handle_error(exc)
            return
        self.preview_title.setText(report_builder.report_title(key))
        if not self._sections:
            self.preview_table.set_headers([tr("common.empty")])
            self.preview_table.setRowCount(0)
            return
        section = self._sections[0]
        self.preview_table.set_headers(list(section.headers))
        self.preview_table.fill(section.rows)
        if len(self._sections) > 1:
            names = ", ".join(s.title for s in self._sections[1:])
            self.section_hint.setText(f"+ {names}")
        else:
            self.section_hint.setText("")

    def reload(self) -> None:
        """Regenerate the current report."""
        self.generate()

    def _export_pdf(self) -> None:
        """Export the report to PDF."""
        if not self.require(Perm.REPORT_EXPORT):
            return
        if not self._sections:
            self.generate()
        key = self._current_key()
        default = str(load_config().exports_dir / f"{key}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, tr("common.export_pdf"), default, "PDF (*.pdf)")
        if not path:
            return
        company = company_service.get_company()
        try:
            pdf_export.build_report(
                path,
                report_builder.report_title(key),
                [(s.title, s.headers, s.rows) for s in self._sections],
                subtitle=(
                    f"{self.date_from.date().toString('dd.MM.yyyy')} — "
                    f"{self.date_to.date().toString('dd.MM.yyyy')}"
                ),
                company=company.name if company else "",
            )
        except Exception as exc:
            logger.exception("PDF export failed")
            show_error(self, tr("err.export_failed", detail=str(exc)))
            return
        show_info(self, tr("rep.saved_to", path=path))

    def _export_excel(self) -> None:
        """Export the report to Excel."""
        if not self.require(Perm.REPORT_EXPORT):
            return
        if not self._sections:
            self.generate()
        key = self._current_key()
        default = str(load_config().exports_dir / f"{key}.xlsx")
        path, _ = QFileDialog.getSaveFileName(
            self, tr("common.export_excel"), default, "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            excel_export.export_table(path, [(s.title, s.headers, s.rows) for s in self._sections])
        except Exception as exc:
            logger.exception("Excel export failed")
            show_error(self, tr("err.export_failed", detail=str(exc)))
            return
        show_info(self, tr("rep.saved_to", path=path))

    def retranslate(self) -> None:
        """Reapply translated captions."""
        super().retranslate()
        self.generate_button.setText(tr("rep.generate"))
        self.pdf_button.setText(tr("common.export_pdf"))
        self.excel_button.setText(tr("common.export_excel"))
        self.picker_title.setText(tr("rep.title"))
        for index, spec in enumerate(report_builder.REPORTS):
            item = self.report_list.item(index)
            if item is not None:
                item.setText(tr(spec.title_key))
        self.generate()
