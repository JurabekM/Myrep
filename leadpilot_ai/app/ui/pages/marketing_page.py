"""Marketing Source Analysis worksheet with ROI drill-down."""

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
from app.services import analytics_service, company_service
from app.services.analytics_service import PeriodFilter
from app.ui.i18n import tr
from app.ui.pages.base_page import BasePage
from app.ui.styles import theme
from app.ui.widgets.common import (
    DataTable,
    FilterChip,
    MetricTile,
    Panel,
    colored_item,
    combo,
    numeric_item,
    show_error,
    show_info,
)
from app.ui.widgets.labels import channel_items, channel_label, status_label
from app.utils.dates import fmt_date
from app.utils.formatting import fmt_money, fmt_number, fmt_percent, pretty_phone

COLUMNS = [
    "common.source",
    "common.campaign",
    "mkt.leads",
    "mkt.answered",
    "mkt.bookings",
    "mkt.arrivals",
    "mkt.sales",
    "common.revenue",
    "mkt.cost",
    "mkt.cpl",
    "mkt.cpb",
    "mkt.cps",
    "mkt.roas",
    "mkt.conversion",
]

DRILL_COLUMNS = [
    "common.name",
    "common.phone",
    "common.channel",
    "common.status",
    "common.revenue",
    "common.created",
]


class MarketingPage(BasePage):
    """Attribution worksheet: which ad source actually produces revenue."""

    title_key = "mkt.title"
    subtitle_key = "app.subtitle"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self._rows: list[analytics_service.MarketingRow] = []
        self._build()

    def _build(self) -> None:
        """Assemble the toolbar, table and drill-down."""
        self.export_button = QPushButton(tr("common.export_excel"))
        self.export_button.setIcon(theme.icon("fa6s.file-excel", theme.SUCCESS))
        self.export_button.clicked.connect(self._export)
        self.header().addWidget(self.export_button)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.tile_leads = MetricTile(tr("mkt.leads"), "0", theme.TEXT)
        self.tile_sales = MetricTile(tr("mkt.sales"), "0", theme.SUCCESS)
        self.tile_revenue = MetricTile(tr("common.revenue"), "0", theme.SUCCESS)
        self.tile_cost = MetricTile(tr("mkt.cost"), "0", theme.WARNING)
        self.tile_roas = MetricTile(tr("mkt.roas"), "0", theme.ACCENT)
        self.tile_cpl = MetricTile(tr("mkt.cpl"), "0", theme.INFO)
        for tile in (
            self.tile_leads,
            self.tile_sales,
            self.tile_revenue,
            self.tile_cost,
            self.tile_roas,
            self.tile_cpl,
        ):
            metrics.addWidget(tile)
        metrics.addStretch(1)
        self.body().addLayout(metrics)

        filters = Panel(padding=10, spacing=8)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-3))
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

        self.channel_box = combo(channel_items())
        self.channel_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.channel_box)

        branches = company_service.list_branches()
        self.branch_box = combo([(tr("common.all"), None)] + [(b.name, b.id) for b in branches])
        self.branch_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.branch_box)

        services = company_service.list_services()
        self.service_box = combo([(tr("common.all"), None)] + [(s.name, s.id) for s in services])
        self.service_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.service_box)

        self.chip_campaign = FilterChip(tr("mkt.group_campaign"), checked=True)
        self.chip_campaign.clicked.connect(self.reload)
        row.addWidget(self.chip_campaign)
        row.addStretch(1)
        filters.body().addLayout(row)
        self.body().addWidget(filters)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        table_panel = Panel(padding=8, spacing=6)
        self.table = DataTable([tr(key) for key in COLUMNS], stretch_column=1)
        self.table.setColumnWidth(0, 170)
        self.table.setColumnWidth(1, 190)
        self.table.itemSelectionChanged.connect(self._drill_down)
        table_panel.body().addWidget(self.table, 1)
        splitter.addWidget(table_panel)

        drill_panel = Panel(padding=8, spacing=6)
        self.drill_title = QLabel(tr("mkt.drilldown"))
        self.drill_title.setObjectName("SectionTitle")
        drill_panel.body().addWidget(self.drill_title)
        self.drill_table = DataTable([tr(key) for key in DRILL_COLUMNS], stretch_column=0)
        self.drill_table.doubleClicked.connect(self._open_lead)
        drill_panel.body().addWidget(self.drill_table, 1)
        splitter.addWidget(drill_panel)
        splitter.setSizes([420, 260])
        self.body().addWidget(splitter, 1)

    # ------------------------------------------------------------------ #
    def _current_filter(self) -> PeriodFilter:
        """Build the analytics filter."""
        channel = self.channel_box.currentData()
        return PeriodFilter(
            date_from=self.date_from.date().toPython(),
            date_to=self.date_to.date().toPython(),
            channels=[channel] if channel else [],
            branch_ids=[self.branch_box.currentData()] if self.branch_box.currentData() else [],
            service_ids=[self.service_box.currentData()] if self.service_box.currentData() else [],
        )

    def reload(self) -> None:
        """Recompute the attribution worksheet."""
        flt = self._current_filter()
        try:
            self._rows = analytics_service.marketing_rows(
                flt, group_by_campaign=self.chip_campaign.isChecked()
            )
        except Exception as exc:
            self.handle_error(exc)
            return

        rows = []
        ids = []
        totals = {"leads": 0, "sales": 0, "revenue": 0.0, "cost": 0.0}
        for index, row in enumerate(self._rows):
            ids.append(index)
            totals["leads"] += row.leads
            totals["sales"] += row.sales
            totals["revenue"] += row.revenue
            totals["cost"] += row.cost
            rows.append(
                [
                    row.source_name,
                    row.campaign_name or "—",
                    numeric_item(row.leads, fmt_number(row.leads)),
                    numeric_item(row.answered, fmt_number(row.answered)),
                    numeric_item(row.bookings, fmt_number(row.bookings)),
                    numeric_item(row.arrivals, fmt_number(row.arrivals)),
                    numeric_item(row.sales, fmt_number(row.sales)),
                    numeric_item(row.revenue, fmt_money(row.revenue)),
                    numeric_item(row.cost, fmt_money(row.cost)),
                    numeric_item(row.cpl, fmt_money(row.cpl)),
                    numeric_item(row.cpb, fmt_money(row.cpb)),
                    numeric_item(row.cps, fmt_money(row.cps)),
                    colored_item(
                        f"{row.roas:.2f}",
                        theme.SUCCESS if row.roas >= 1 else theme.DANGER,
                        bold=True,
                        sort_value=row.roas,
                    ),
                    colored_item(
                        fmt_percent(row.conversion),
                        theme.SUCCESS if row.conversion >= 10 else theme.TEXT_MUTED,
                        sort_value=row.conversion,
                    ),
                ]
            )
        self.table.fill(rows, ids=ids)

        self.tile_leads.set_value(fmt_number(totals["leads"]))
        self.tile_sales.set_value(fmt_number(totals["sales"]))
        self.tile_revenue.set_value(fmt_money(totals["revenue"]))
        self.tile_cost.set_value(fmt_money(totals["cost"]))
        self.tile_roas.set_value(f"{analytics_service.roas(totals['revenue'], totals['cost']):.2f}")
        self.tile_cpl.set_value(
            fmt_money(analytics_service.cost_per_lead(totals["cost"], totals["leads"]))
        )
        self.drill_table.setRowCount(0)

    def _drill_down(self) -> None:
        """Show the leads behind the selected attribution row."""
        index = self.table.selected_id()
        if index is None or index >= len(self._rows):
            return
        row = self._rows[index]
        try:
            leads = analytics_service.leads_of_source(
                self._current_filter(), source_id=row.source_id, campaign_id=row.campaign_id
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.drill_title.setText(f"{tr('mkt.drilldown')}: {row.source_name} / {row.campaign_name}")
        rows = []
        ids = []
        for lead in leads:
            ids.append(lead.id)
            rows.append(
                [
                    lead.display_name,
                    pretty_phone(lead.phone),
                    channel_label(lead.channel),
                    status_label(lead.status),
                    fmt_money(lead.revenue) if lead.revenue else "—",
                    fmt_date(lead.created_at),
                ]
            )
        self.drill_table.fill(rows, ids=ids)

    def _open_lead(self) -> None:
        """Open the selected lead in the inbox."""
        lead_id = self.drill_table.selected_id()
        if lead_id is not None:
            self.context.open_lead_requested.emit(lead_id)

    def _export(self) -> None:
        """Export the attribution table to Excel."""
        if not self.require(Perm.REPORT_EXPORT):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("common.export_excel"), "marketing_roi.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        headers = [tr(key) for key in COLUMNS]
        rows = [
            [
                row.source_name,
                row.campaign_name,
                row.leads,
                row.answered,
                row.bookings,
                row.arrivals,
                row.sales,
                row.revenue,
                row.cost,
                round(row.cpl, 2),
                round(row.cpb, 2),
                round(row.cps, 2),
                round(row.roas, 2),
                round(row.conversion, 2),
            ]
            for row in self._rows
        ]
        try:
            excel_export.export_generic(path, "Marketing ROI", headers, rows)
        except Exception as exc:
            show_error(self, tr("err.export_failed", detail=str(exc)))
            return
        show_info(self, tr("rep.saved_to", path=path))

    def retranslate(self) -> None:
        """Reapply translated captions."""
        super().retranslate()
        self.export_button.setText(tr("common.export_excel"))
        self.chip_campaign.setText(tr("mkt.group_campaign"))
        self.drill_title.setText(tr("mkt.drilldown"))
        self.table.set_headers([tr(key) for key in COLUMNS])
        self.drill_table.set_headers([tr(key) for key in DRILL_COLUMNS])
        self.reload()
