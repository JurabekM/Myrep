"""Lead CRM worksheet: filtering, bulk actions, timeline and duplicate merge."""

from __future__ import annotations

import logging

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMenu,
    QPushButton,
    QSplitter,
    QWidget,
)

from app.controllers.app_context import AppContext
from app.models.enums import LeadStatus
from app.models.enums import Permission as Perm
from app.reports import excel_export
from app.repositories.lead_repository import LeadFilter
from app.services import analytics_service, auth_service, company_service, lead_service
from app.ui.dialogs.lead_dialog import LeadDialog, MergeLeadsDialog, StatusChangeDialog
from app.ui.i18n import tr
from app.ui.pages.base_page import BasePage
from app.ui.styles import theme
from app.ui.widgets.common import (
    DataTable,
    MetricTile,
    Pager,
    Panel,
    SearchBox,
    colored_item,
    combo,
    confirm,
    numeric_item,
    show_error,
    show_info,
)
from app.ui.widgets.labels import (
    channel_items,
    channel_label,
    intent_color,
    intent_items,
    intent_label,
    score_color,
    status_color,
    status_items,
    status_label,
)
from app.utils.dates import end_of_day, fmt_date, fmt_datetime, start_of_day
from app.utils.formatting import fmt_money, pretty_phone

logger = logging.getLogger(__name__)

COLUMNS = [
    "common.name",
    "common.phone",
    "common.channel",
    "common.status",
    "leads.intent",
    "common.score",
    "leads.owner",
    "common.source",
    "common.service",
    "common.revenue",
    "common.created",
]


class LeadsPage(BasePage):
    """Desktop CRM table with a detail drawer."""

    title_key = "leads.title"
    subtitle_key = "app.subtitle"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self._build()
        context.leads_updated.connect(self.reload)

    # ------------------------------------------------------------------ #
    def _build(self) -> None:
        """Assemble the toolbar, metrics, table and detail drawer."""
        self.new_button = QPushButton(tr("leads.new"))
        self.new_button.setObjectName("Primary")
        self.new_button.setIcon(theme.icon("fa6s.plus", "#FFFFFF"))
        self.new_button.clicked.connect(self.create_lead)
        self.header().addWidget(self.new_button)

        self.bulk_button = QPushButton(tr("leads.bulk"))
        self.bulk_button.clicked.connect(self._show_bulk_menu)
        self.header().addWidget(self.bulk_button)

        self.duplicates_button = QPushButton(tr("leads.duplicates"))
        self.duplicates_button.clicked.connect(self._show_duplicates)
        self.header().addWidget(self.duplicates_button)

        self.export_button = QPushButton(tr("common.export_excel"))
        self.export_button.setIcon(theme.icon("fa6s.file-excel", theme.SUCCESS))
        self.export_button.clicked.connect(self._export)
        self.header().addWidget(self.export_button)

        # Metrics strip
        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.tile_total = MetricTile(tr("mkt.leads"), "0", theme.TEXT)
        self.tile_hot = MetricTile(tr("intent.hot"), "0", theme.DANGER)
        self.tile_bookings = MetricTile(tr("mkt.bookings"), "0", theme.INFO)
        self.tile_won = MetricTile(tr("status.won"), "0", theme.SUCCESS)
        self.tile_revenue = MetricTile(tr("common.revenue"), "0", theme.SUCCESS)
        self.tile_conversion = MetricTile(tr("mkt.conversion"), "0%", theme.ACCENT)
        for tile in (
            self.tile_total,
            self.tile_hot,
            self.tile_bookings,
            self.tile_won,
            self.tile_revenue,
            self.tile_conversion,
        ):
            metrics.addWidget(tile)
        metrics.addStretch(1)
        self.body().addLayout(metrics)

        # Filters
        filters = Panel(padding=10, spacing=8)
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.search_box = SearchBox(tr("common.search"))
        self.search_box.textChanged.connect(self._debounced_reload)
        row1.addWidget(self.search_box, 2)

        self.status_box = combo(status_items())
        self.status_box.currentIndexChanged.connect(self.reload)
        row1.addWidget(self.status_box)

        self.channel_box = combo(channel_items())
        self.channel_box.currentIndexChanged.connect(self.reload)
        row1.addWidget(self.channel_box)

        self.intent_box = combo(intent_items())
        self.intent_box.currentIndexChanged.connect(self.reload)
        row1.addWidget(self.intent_box)

        operators = auth_service.list_operators()
        self.owner_box = combo(
            [(tr("common.all"), None), (tr("common.unassigned"), -1)]
            + [(u.full_name, u.id) for u in operators]
        )
        self.owner_box.currentIndexChanged.connect(self.reload)
        row1.addWidget(self.owner_box)
        filters.body().addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        sources = company_service.list_sources()
        self.source_box = combo([(tr("common.all"), None)] + [(s.name, s.id) for s in sources])
        self.source_box.currentIndexChanged.connect(self.reload)
        row2.addWidget(self.source_box)

        campaigns = company_service.list_campaigns()
        self.campaign_box = combo([(tr("common.all"), None)] + [(c.name, c.id) for c in campaigns])
        self.campaign_box.currentIndexChanged.connect(self.reload)
        row2.addWidget(self.campaign_box)

        services = company_service.list_services()
        self.service_box = combo([(tr("common.all"), None)] + [(s.name, s.id) for s in services])
        self.service_box.currentIndexChanged.connect(self.reload)
        row2.addWidget(self.service_box)

        self.date_from = QDateEdit(QDate.currentDate().addMonths(-3))
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.dateChanged.connect(self.reload)
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.dateChanged.connect(self.reload)
        row2.addWidget(QLabel(tr("common.from")))
        row2.addWidget(self.date_from)
        row2.addWidget(QLabel(tr("common.to")))
        row2.addWidget(self.date_to)

        self.archived_box = QCheckBox(tr("leads.archived_only"))
        self.archived_box.stateChanged.connect(self.reload)
        row2.addWidget(self.archived_box)

        self.reset_button = QPushButton(tr("common.reset"))
        self.reset_button.setObjectName("Ghost")
        self.reset_button.clicked.connect(self._reset_filters)
        row2.addWidget(self.reset_button)
        row2.addStretch(1)
        filters.body().addLayout(row2)
        self.body().addWidget(filters)

        # Table + detail
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        table_panel = Panel(padding=8, spacing=6)
        self.table = DataTable([tr(key) for key in COLUMNS], stretch_column=0)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.table.doubleClicked.connect(self._edit_selected)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_row_menu)
        table_panel.body().addWidget(self.table, 1)
        self.pager = Pager(50)
        self.pager.page_changed.connect(lambda _p: self.reload(keep_page=True))
        table_panel.body().addWidget(self.pager)
        splitter.addWidget(table_panel)

        self.detail_panel = Panel(padding=12, spacing=8)
        detail_title = QLabel(tr("leads.timeline"))
        detail_title.setObjectName("SectionTitle")
        self.detail_title = detail_title
        self.detail_panel.body().addWidget(detail_title)
        self.detail_header = QLabel("—")
        self.detail_header.setWordWrap(True)
        self.detail_header.setTextFormat(Qt.TextFormat.RichText)
        self.detail_panel.body().addWidget(self.detail_header)

        buttons = QHBoxLayout()
        self.open_inbox_button = QPushButton(tr("nav.inbox"))
        self.open_inbox_button.clicked.connect(self._open_in_inbox)
        self.status_button = QPushButton(tr("inbox.change_status"))
        self.status_button.clicked.connect(self._change_status)
        buttons.addWidget(self.open_inbox_button)
        buttons.addWidget(self.status_button)
        buttons.addStretch(1)
        self.detail_panel.body().addLayout(buttons)

        self.timeline_list = QListWidget()
        self.detail_panel.body().addWidget(self.timeline_list, 1)
        self.detail_panel.setMinimumWidth(300)
        splitter.addWidget(self.detail_panel)
        splitter.setSizes([900, 320])
        self.body().addWidget(splitter, 1)

    # ------------------------------------------------------------------ #
    def _debounced_reload(self) -> None:
        """Reload shortly after typing stops."""
        QTimer.singleShot(220, self.reload)

    def _reset_filters(self) -> None:
        """Clear every filter."""
        self.search_box.clear()
        for box in (
            self.status_box,
            self.channel_box,
            self.intent_box,
            self.owner_box,
            self.source_box,
            self.campaign_box,
            self.service_box,
        ):
            box.setCurrentIndex(0)
        self.date_from.setDate(QDate.currentDate().addMonths(-3))
        self.date_to.setDate(QDate.currentDate())
        self.archived_box.setChecked(False)
        self.reload()

    def current_filter(self) -> LeadFilter:
        """Build a :class:`LeadFilter` from the toolbar state."""
        owner = self.owner_box.currentData()
        owner_ids: list[int] = []
        only_unassigned = False
        if owner == -1:
            only_unassigned = True
        elif owner:
            owner_ids = [owner]
        status = self.status_box.currentData()
        channel = self.channel_box.currentData()
        intent = self.intent_box.currentData()
        return LeadFilter(
            search=self.search_box.text(),
            statuses=[status] if status else [],
            channels=[channel] if channel else [],
            intents=[intent] if intent else [],
            owner_ids=owner_ids,
            only_unassigned=only_unassigned,
            source_ids=[self.source_box.currentData()] if self.source_box.currentData() else [],
            campaign_ids=(
                [self.campaign_box.currentData()] if self.campaign_box.currentData() else []
            ),
            service_ids=[self.service_box.currentData()] if self.service_box.currentData() else [],
            date_from=start_of_day(self.date_from.date().toPython()),
            date_to=end_of_day(self.date_to.date().toPython()),
            include_archived=self.archived_box.isChecked(),
        )

    def reload(self, keep_page: bool = False) -> None:
        """Reload the table and the metric tiles."""
        if not keep_page:
            self.pager.reset()
        flt = self.current_filter()
        try:
            leads, total = lead_service.search_leads(
                flt,
                actor=self.user,
                limit=self.pager.page_size,
                offset=self.pager.offset(),
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.pager.set_total(total)

        rows = []
        ids = []
        for lead in leads:
            ids.append(lead.id)
            rows.append(
                [
                    lead.display_name,
                    pretty_phone(lead.phone),
                    channel_label(lead.channel),
                    colored_item(status_label(lead.status), status_color(lead.status), bold=True),
                    colored_item(intent_label(lead.intent), intent_color(lead.intent)),
                    numeric_item(lead.score, str(lead.score)),
                    lead.owner.full_name if lead.owner else "—",
                    lead.source.name if lead.source else (lead.utm_source or "—"),
                    lead.service.name if lead.service else "—",
                    numeric_item(
                        lead.revenue or 0, fmt_money(lead.revenue) if lead.revenue else "—"
                    ),
                    fmt_date(lead.created_at),
                ]
            )
        self.table.fill(rows, ids=ids)
        self._reload_metrics(flt)

    def _reload_metrics(self, flt: LeadFilter) -> None:
        """Refresh the KPI tiles."""
        period = analytics_service.PeriodFilter(
            date_from=flt.date_from.date() if flt.date_from else None,
            date_to=flt.date_to.date() if flt.date_to else None,
            channels=flt.channels,
            owner_ids=flt.owner_ids,
            source_ids=flt.source_ids,
            campaign_ids=flt.campaign_ids,
            service_ids=flt.service_ids,
            statuses=flt.statuses,
        )
        try:
            summary = analytics_service.workspace_summary(period)
        except Exception:
            logger.exception("Workspace summary failed")
            return
        self.tile_total.set_value(str(int(summary["leads"])))
        self.tile_hot.set_value(str(int(summary["hot"])))
        self.tile_bookings.set_value(str(int(summary["bookings"])))
        self.tile_won.set_value(str(int(summary["won"])))
        self.tile_revenue.set_value(fmt_money(summary["revenue"]))
        self.tile_conversion.set_value(f"{summary['conversion']:.1f}%")

    # ------------------------------------------------------------------ #
    def _on_selection(self) -> None:
        """Fill the detail drawer for the selected lead."""
        lead_id = self.table.selected_id()
        if lead_id is None:
            return
        lead = lead_service.get_lead(lead_id)
        if lead is None:
            return
        self.detail_header.setText(
            f"<b style='font-size:15px'>{lead.display_name}</b><br>"
            f"<span style='color:{theme.TEXT_MUTED}'>{pretty_phone(lead.phone)} · "
            f"{channel_label(lead.channel)}</span><br>"
            f"<span style='color:{status_color(lead.status)}'>{status_label(lead.status)}</span> · "
            f"<span style='color:{score_color(lead.score)}'>{tr('common.score')}: {lead.score}</span><br>"
            f"<span style='color:{theme.TEXT_MUTED}'>{tr('leads.first_response')}: "
            f"{lead.first_response_seconds or '—'} s</span>"
        )
        self.timeline_list.clear()
        for activity in lead_service.timeline(lead_id):
            self.timeline_list.addItem(
                f"{fmt_datetime(activity.created_at)} · {activity.title}"
                + (f"\n    {activity.detail}" if activity.detail else "")
            )
        self.timeline_list.scrollToBottom()

    def _show_row_menu(self, position) -> None:
        """Right-click menu on a table row."""
        lead_id = self.table.selected_id()
        if lead_id is None:
            return
        menu = QMenu(self)
        menu.addAction(tr("common.edit"), self._edit_selected)
        menu.addAction(tr("inbox.change_status"), self._change_status)
        menu.addAction(tr("nav.inbox"), self._open_in_inbox)
        menu.addSeparator()
        if self.user.can(Perm.LEAD_ASSIGN):
            assign_menu = menu.addMenu(tr("common.assign"))
            assign_menu.addAction(tr("common.unassigned"), lambda: self._assign_selected(None))
            for operator in auth_service.list_operators():
                assign_menu.addAction(
                    operator.full_name, lambda _c=False, uid=operator.id: self._assign_selected(uid)
                )
        if self.user.can(Perm.LEAD_DELETE):
            menu.addSeparator()
            menu.addAction(tr("common.archive"), self._archive_selected)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def create_lead(self) -> None:
        """Open the create-lead dialog (Ctrl+N)."""
        if not self.require(Perm.LEAD_EDIT):
            return
        dialog = LeadDialog(self.user, parent=self)
        if dialog.exec():
            self.reload()
            self.context.leads_updated.emit()

    def _edit_selected(self) -> None:
        """Edit the selected lead."""
        lead_id = self.table.selected_id()
        if lead_id is None:
            show_error(self, tr("err.select_row"))
            return
        lead = lead_service.get_lead(lead_id)
        if lead is None:
            return
        dialog = LeadDialog(self.user, lead, parent=self)
        if dialog.exec():
            self.reload()

    def _change_status(self) -> None:
        """Open the status dialog for the selected lead."""
        lead_id = self.table.selected_id()
        if lead_id is None:
            show_error(self, tr("err.select_row"))
            return
        lead = lead_service.get_lead(lead_id)
        if lead is None:
            return
        dialog = StatusChangeDialog(self.user, lead.id, lead.status, parent=self)
        if dialog.exec():
            self.reload()

    def _assign_selected(self, owner_id: int | None) -> None:
        """Assign the selected leads to an operator."""
        ids = self.table.selected_ids() or (
            [self.table.selected_id()] if self.table.selected_id() else []
        )
        if not ids:
            return
        try:
            count = lead_service.bulk_assign(ids, owner_id, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        show_info(self, f"{count} {tr('common.rows')}")
        self.reload()

    def _archive_selected(self) -> None:
        """Archive the selected leads."""
        ids = self.table.selected_ids()
        if not ids:
            show_error(self, tr("err.select_row"))
            return
        if not confirm(self, tr("common.confirm")):
            return
        try:
            lead_service.archive_leads(ids, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.reload()

    def _show_bulk_menu(self) -> None:
        """Bulk actions for the current selection."""
        ids = self.table.selected_ids()
        if not ids:
            show_error(self, tr("err.select_row"))
            return
        menu = QMenu(self)
        status_menu = menu.addMenu(tr("inbox.change_status"))
        for label, value in status_items(include_all=False):
            status_menu.addAction(label, lambda _c=False, v=value: self._bulk_status(ids, v))
        if self.user.can(Perm.LEAD_ASSIGN):
            assign_menu = menu.addMenu(tr("common.assign"))
            for operator in auth_service.list_operators():
                assign_menu.addAction(
                    operator.full_name,
                    lambda _c=False, uid=operator.id: self._assign_selected(uid),
                )
        tag_menu = menu.addMenu(tr("common.tags"))
        for tag in lead_service.list_tags():
            tag_menu.addAction(tag.name, lambda _c=False, tid=tag.id: self._bulk_tag(ids, tid))
        if self.user.can(Perm.LEAD_DELETE):
            menu.addSeparator()
            menu.addAction(tr("common.archive"), self._archive_selected)
        menu.exec(self.bulk_button.mapToGlobal(self.bulk_button.rect().bottomLeft()))

    def _bulk_status(self, ids: list[int], status: str) -> None:
        """Apply one status to many leads."""
        if status == LeadStatus.LOST:
            show_error(self, tr("err.loss_reason_required"))
            return
        ok, errors = lead_service.bulk_status(ids, status, actor=self.user)
        if errors:
            show_info(self, f"{ok} OK · {len(errors)} {tr('common.error')}")
        self.reload()

    def _bulk_tag(self, ids: list[int], tag_id: int) -> None:
        """Add a tag to many leads."""
        try:
            lead_service.add_tag_to_leads(ids, tag_id, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.reload()

    def _show_duplicates(self) -> None:
        """Open the duplicate merge dialog."""
        if not self.require(Perm.LEAD_MERGE):
            return
        groups = lead_service.find_duplicate_groups()
        if not groups:
            show_info(self, tr("common.empty"))
            return
        dialog = MergeLeadsDialog(self.user, groups[0], parent=self)
        if dialog.exec():
            self.reload()
            show_info(self, tr("common.success"))

    def _open_in_inbox(self) -> None:
        """Jump to the conversation of the selected lead."""
        lead_id = self.table.selected_id()
        if lead_id is None:
            show_error(self, tr("err.select_row"))
            return
        self.context.open_lead_requested.emit(lead_id)

    def _export(self) -> None:
        """Export the current selection to Excel."""
        if not self.require(Perm.REPORT_EXPORT):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("common.export_excel"), "leads.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        leads, _ = lead_service.search_leads(
            self.current_filter(), actor=self.user, limit=10000, offset=0
        )
        try:
            excel_export.export_leads(leads, path)
        except Exception as exc:
            show_error(self, tr("err.export_failed", detail=str(exc)))
            return
        show_info(self, tr("rep.saved_to", path=path))

    # ------------------------------------------------------------------ #
    def retranslate(self) -> None:
        """Reapply translated captions."""
        super().retranslate()
        self.new_button.setText(tr("leads.new"))
        self.bulk_button.setText(tr("leads.bulk"))
        self.duplicates_button.setText(tr("leads.duplicates"))
        self.export_button.setText(tr("common.export_excel"))
        self.reset_button.setText(tr("common.reset"))
        self.detail_title.setText(tr("leads.timeline"))
        self.open_inbox_button.setText(tr("nav.inbox"))
        self.status_button.setText(tr("inbox.change_status"))
        self.table.set_headers([tr(key) for key in COLUMNS])
        self.tile_total.set_label(tr("mkt.leads"))
        self.tile_hot.set_label(tr("intent.hot"))
        self.tile_bookings.set_label(tr("mkt.bookings"))
        self.tile_won.set_label(tr("status.won"))
        self.tile_revenue.set_label(tr("common.revenue"))
        self.tile_conversion.set_label(tr("mkt.conversion"))
        self.pager.retranslate()
        self.reload()
