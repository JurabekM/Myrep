"""Operator quality worksheet with a per-operator profile drawer."""

from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QWidget,
)

from app.controllers.app_context import AppContext
from app.models.enums import Permission as Perm
from app.reports import excel_export
from app.services import analytics_service
from app.services.analytics_service import PeriodFilter
from app.ui.i18n import tr
from app.ui.pages.base_page import BasePage
from app.ui.styles import theme
from app.ui.widgets.common import (
    DataTable,
    MetricTile,
    Panel,
    SearchBox,
    colored_item,
    numeric_item,
    show_error,
    show_info,
)
from app.utils.formatting import fmt_duration, fmt_money, fmt_number, fmt_percent

COLUMNS = [
    "common.operator",
    "mkt.leads",
    "ops.first_response",
    "ops.avg_response",
    "ops.closed",
    "mkt.bookings",
    "mkt.arrivals",
    "mkt.sales",
    "common.revenue",
    "mkt.conversion",
    "ops.missed",
    "ops.call_quality",
    "ops.ai_usage",
    "ops.sentiment",
]


class OperatorsPage(BasePage):
    """Filterable operator KPI table (not a chart dashboard)."""

    title_key = "ops.title"
    subtitle_key = "app.subtitle"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self._rows: list[analytics_service.OperatorRow] = []
        self._build()

    def _build(self) -> None:
        """Assemble the toolbar, table and profile panel."""
        self.export_button = QPushButton(tr("common.export_excel"))
        self.export_button.setIcon(theme.icon("fa6s.file-excel", theme.SUCCESS))
        self.export_button.clicked.connect(self._export)
        self.header().addWidget(self.export_button)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.tile_operators = MetricTile(tr("common.operator"), "0", theme.TEXT)
        self.tile_leads = MetricTile(tr("mkt.leads"), "0", theme.INFO)
        self.tile_sales = MetricTile(tr("mkt.sales"), "0", theme.SUCCESS)
        self.tile_response = MetricTile(tr("ops.first_response"), "—", theme.WARNING)
        self.tile_missed = MetricTile(tr("ops.missed"), "0", theme.DANGER)
        for tile in (
            self.tile_operators,
            self.tile_leads,
            self.tile_sales,
            self.tile_response,
            self.tile_missed,
        ):
            metrics.addWidget(tile)
        metrics.addStretch(1)
        self.body().addLayout(metrics)

        filters = Panel(padding=10, spacing=8)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.search_box = SearchBox(tr("common.search"))
        self.search_box.textChanged.connect(self._apply_search)
        row.addWidget(self.search_box, 2)
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.dateChanged.connect(self.reload)
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.dateChanged.connect(self.reload)
        row.addWidget(QLabel(tr("common.from")))
        row.addWidget(self.date_from)
        row.addWidget(QLabel(tr("common.to")))
        row.addWidget(self.date_to)
        row.addStretch(1)
        filters.body().addLayout(row)
        self.body().addWidget(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        table_panel = Panel(padding=8, spacing=6)
        self.table = DataTable([tr(key) for key in COLUMNS], stretch_column=0)
        self.table.itemSelectionChanged.connect(self._show_profile)
        table_panel.body().addWidget(self.table, 1)
        splitter.addWidget(table_panel)

        profile = Panel(padding=12, spacing=8)
        self.profile_title = QLabel(tr("ops.profile"))
        self.profile_title.setObjectName("SectionTitle")
        profile.body().addWidget(self.profile_title)
        self.profile_body = QLabel("—")
        self.profile_body.setWordWrap(True)
        self.profile_body.setTextFormat(Qt.TextFormat.RichText)
        self.profile_body.setAlignment(Qt.AlignmentFlag.AlignTop)
        profile.body().addWidget(self.profile_body, 1)
        profile.setMinimumWidth(300)
        splitter.addWidget(profile)
        splitter.setSizes([900, 320])
        self.body().addWidget(splitter, 1)

    # ------------------------------------------------------------------ #
    def _current_filter(self) -> PeriodFilter:
        """Build the analytics period filter."""
        return PeriodFilter(
            date_from=self.date_from.date().toPython(),
            date_to=self.date_to.date().toPython(),
        )

    def reload(self) -> None:
        """Recompute the operator KPI table."""
        try:
            self._rows = analytics_service.operator_rows(self._current_filter())
        except Exception as exc:
            self.handle_error(exc)
            return
        self._apply_search()

    def _apply_search(self) -> None:
        """Filter the already computed rows by name."""
        needle = self.search_box.text().strip().lower()
        rows_data = [r for r in self._rows if not needle or needle in r.full_name.lower()]

        rows = []
        ids = []
        total_leads = total_sales = total_missed = 0
        responses = []
        for row in rows_data:
            ids.append(row.user_id)
            total_leads += row.leads
            total_sales += row.sales
            total_missed += row.missed_followups
            if row.first_response_avg_sec:
                responses.append(row.first_response_avg_sec)
            rows.append(
                [
                    row.full_name,
                    numeric_item(row.leads, fmt_number(row.leads)),
                    fmt_duration(row.first_response_avg_sec),
                    fmt_duration(row.response_avg_sec),
                    numeric_item(row.closed, fmt_number(row.closed)),
                    numeric_item(row.bookings, fmt_number(row.bookings)),
                    numeric_item(row.arrivals, fmt_number(row.arrivals)),
                    numeric_item(row.sales, fmt_number(row.sales)),
                    numeric_item(row.revenue, fmt_money(row.revenue)),
                    colored_item(
                        fmt_percent(row.conversion),
                        theme.SUCCESS if row.conversion >= 15 else theme.TEXT_MUTED,
                        bold=True,
                        sort_value=row.conversion,
                    ),
                    colored_item(
                        fmt_number(row.missed_followups),
                        theme.DANGER if row.missed_followups else theme.TEXT_MUTED,
                        sort_value=row.missed_followups,
                    ),
                    numeric_item(row.call_quality, f"{row.call_quality:.0f}"),
                    numeric_item(row.ai_usage, fmt_percent(row.ai_usage)),
                    numeric_item(row.positive_sentiment, fmt_percent(row.positive_sentiment)),
                ]
            )
        self.table.fill(rows, ids=ids)
        self.tile_operators.set_value(str(len(rows_data)))
        self.tile_leads.set_value(fmt_number(total_leads))
        self.tile_sales.set_value(fmt_number(total_sales))
        self.tile_response.set_value(
            fmt_duration(int(sum(responses) / len(responses))) if responses else "—"
        )
        self.tile_missed.set_value(fmt_number(total_missed))

    def _show_profile(self) -> None:
        """Render the detail card of the selected operator."""
        user_id = self.table.selected_id()
        row = next((r for r in self._rows if r.user_id == user_id), None)
        if row is None:
            return
        muted = theme.TEXT_MUTED
        self.profile_body.setText(
            f"<b style='font-size:15px'>{row.full_name}</b><br><br>"
            f"<span style='color:{muted}'>{tr('mkt.leads')}:</span> {fmt_number(row.leads)}<br>"
            f"<span style='color:{muted}'>{tr('ops.first_response')}:</span> "
            f"{fmt_duration(row.first_response_avg_sec)}<br>"
            f"<span style='color:{muted}'>{tr('ops.closed')}:</span> {fmt_number(row.closed)}<br>"
            f"<span style='color:{muted}'>{tr('mkt.bookings')}:</span> {fmt_number(row.bookings)}<br>"
            f"<span style='color:{muted}'>{tr('mkt.arrivals')}:</span> {fmt_number(row.arrivals)}<br>"
            f"<span style='color:{muted}'>{tr('mkt.sales')}:</span> {fmt_number(row.sales)}<br>"
            f"<span style='color:{muted}'>{tr('common.revenue')}:</span> {fmt_money(row.revenue)}<br>"
            f"<span style='color:{muted}'>{tr('mkt.conversion')}:</span> "
            f"{fmt_percent(row.conversion)}<br>"
            f"<span style='color:{muted}'>{tr('ops.missed')}:</span> "
            f"<span style='color:{theme.DANGER if row.missed_followups else muted}'>"
            f"{fmt_number(row.missed_followups)}</span><br>"
            f"<span style='color:{muted}'>{tr('ops.call_quality')}:</span> {row.call_quality:.0f}/100<br>"
            f"<span style='color:{muted}'>{tr('ops.ai_usage')}:</span> {fmt_percent(row.ai_usage)}<br>"
            f"<span style='color:{muted}'>{tr('ops.sentiment')}:</span> "
            f"{fmt_percent(row.positive_sentiment)}"
        )

    def _export(self) -> None:
        """Export the operator table to Excel."""
        if not self.require(Perm.REPORT_EXPORT):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("common.export_excel"), "operators.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        headers = [tr(key) for key in COLUMNS]
        rows = [
            [
                row.full_name,
                row.leads,
                row.first_response_avg_sec,
                row.response_avg_sec,
                row.closed,
                row.bookings,
                row.arrivals,
                row.sales,
                row.revenue,
                round(row.conversion, 2),
                row.missed_followups,
                round(row.call_quality, 1),
                round(row.ai_usage, 1),
                round(row.positive_sentiment, 1),
            ]
            for row in self._rows
        ]
        try:
            excel_export.export_generic(path, "Operators", headers, rows)
        except Exception as exc:
            show_error(self, tr("err.export_failed", detail=str(exc)))
            return
        show_info(self, tr("rep.saved_to", path=path))

    def retranslate(self) -> None:
        """Reapply translated captions."""
        super().retranslate()
        self.export_button.setText(tr("common.export_excel"))
        self.profile_title.setText(tr("ops.profile"))
        self.table.set_headers([tr(key) for key in COLUMNS])
        self.reload()
