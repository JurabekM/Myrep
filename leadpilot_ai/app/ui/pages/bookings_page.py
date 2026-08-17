"""Bookings worksheet: day / week / list views with conflict-safe editing."""

from __future__ import annotations

from datetime import timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QWidget,
)

from app.controllers.app_context import AppContext
from app.models.enums import BookingStatus
from app.models.enums import Permission as Perm
from app.services import auth_service, booking_service, company_service
from app.ui.dialogs.booking_dialog import BookingDialog
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
    confirm,
    show_error,
    show_info,
)
from app.ui.widgets.labels import (
    booking_color,
    booking_status_items,
    booking_status_label,
    purpose_label,
)
from app.utils.dates import fmt_datetime, start_of_week, today
from app.utils.formatting import pretty_phone

COLUMNS = [
    "booking.starts_at",
    "common.name",
    "common.phone",
    "common.service",
    "common.branch",
    "booking.specialist",
    "booking.purpose",
    "common.status",
    "common.duration",
]


class BookingsPage(BasePage):
    """Desktop calendar-style booking manager."""

    title_key = "booking.title"
    subtitle_key = "app.subtitle"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self.view_mode = "week"
        self.anchor_date = today()
        self._build()
        context.leads_updated.connect(self.reload)

    def _build(self) -> None:
        """Assemble the toolbar and the table."""
        self.new_button = QPushButton(tr("booking.new"))
        self.new_button.setObjectName("Primary")
        self.new_button.setIcon(theme.icon("fa6s.plus", "#FFFFFF"))
        self.new_button.clicked.connect(self._create)
        self.header().addWidget(self.new_button)

        self.remind_button = QPushButton(tr("booking.remind"))
        self.remind_button.clicked.connect(self._send_reminders)
        self.header().addWidget(self.remind_button)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.tile_total = MetricTile(tr("mkt.bookings"), "0", theme.TEXT)
        self.tile_confirmed = MetricTile(tr("bstatus.confirmed"), "0", theme.SUCCESS)
        self.tile_pending = MetricTile(tr("bstatus.pending"), "0", theme.WARNING)
        self.tile_no_show = MetricTile(tr("bstatus.no_show"), "0", theme.DANGER)
        self.tile_ai = MetricTile(tr("booking.created_by_ai"), "0", theme.PURPLE)
        for tile in (
            self.tile_total,
            self.tile_confirmed,
            self.tile_pending,
            self.tile_no_show,
            self.tile_ai,
        ):
            metrics.addWidget(tile)
        metrics.addStretch(1)
        self.body().addLayout(metrics)

        filters = Panel(padding=10, spacing=8)
        row = QHBoxLayout()
        row.setSpacing(8)

        self.view_group = QButtonGroup(self)
        self.chip_day = FilterChip(tr("common.day"))
        self.chip_week = FilterChip(tr("common.week"), checked=True)
        self.chip_list = FilterChip(tr("common.list"))
        for chip, mode in (
            (self.chip_day, "day"),
            (self.chip_week, "week"),
            (self.chip_list, "list"),
        ):
            chip.setCheckable(True)
            self.view_group.addButton(chip)
            chip.clicked.connect(lambda _c=False, m=mode: self._set_mode(m))
            row.addWidget(chip)
        self.view_group.setExclusive(True)

        self.prev_button = QPushButton("◀")
        self.prev_button.setObjectName("Ghost")
        self.prev_button.setFixedWidth(36)
        self.prev_button.clicked.connect(lambda: self._shift(-1))
        self.today_button = QPushButton(tr("common.today"))
        self.today_button.setObjectName("Ghost")
        self.today_button.clicked.connect(self._go_today)
        self.next_button = QPushButton("▶")
        self.next_button.setObjectName("Ghost")
        self.next_button.setFixedWidth(36)
        self.next_button.clicked.connect(lambda: self._shift(1))
        self.period_label = QLabel("")
        self.period_label.setObjectName("SectionTitle")
        row.addWidget(self.prev_button)
        row.addWidget(self.today_button)
        row.addWidget(self.next_button)
        row.addWidget(self.period_label)
        row.addSpacing(12)

        self.search_box = SearchBox(tr("common.search"))
        self.search_box.textChanged.connect(self.reload)
        row.addWidget(self.search_box, 1)

        self.status_box = combo(booking_status_items())
        self.status_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.status_box)

        branches = company_service.list_branches()
        self.branch_box = combo([(tr("common.all"), None)] + [(b.name, b.id) for b in branches])
        self.branch_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.branch_box)

        specialists = auth_service.list_operators()
        self.specialist_box = combo(
            [(tr("common.all"), None)] + [(u.full_name, u.id) for u in specialists]
        )
        self.specialist_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.specialist_box)
        filters.body().addLayout(row)
        self.body().addWidget(filters)

        panel = Panel(padding=8, spacing=6)
        self.table = DataTable([tr(key) for key in COLUMNS], stretch_column=1)
        self.table.doubleClicked.connect(self._edit)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_menu)
        panel.body().addWidget(self.table, 1)
        self.body().addWidget(panel, 1)

    # ------------------------------------------------------------------ #
    def _set_mode(self, mode: str) -> None:
        """Switch between day, week and list views."""
        self.view_mode = mode
        self.reload()

    def _shift(self, direction: int) -> None:
        """Move the visible period forward or backward."""
        step = 1 if self.view_mode == "day" else 7
        self.anchor_date = self.anchor_date + timedelta(days=direction * step)
        self.reload()

    def _go_today(self) -> None:
        """Jump back to today."""
        self.anchor_date = today()
        self.reload()

    def _range(self) -> tuple[object, object]:
        """Return the visible date range for the current view mode."""
        if self.view_mode == "day":
            return self.anchor_date, self.anchor_date
        if self.view_mode == "week":
            start = start_of_week(self.anchor_date)
            return start, start + timedelta(days=6)
        return self.anchor_date - timedelta(days=30), self.anchor_date + timedelta(days=60)

    def reload(self) -> None:
        """Reload the booking table."""
        day_from, day_to = self._range()
        status = self.status_box.currentData()
        try:
            bookings = booking_service.list_bookings(
                day_from=day_from,
                day_to=day_to,
                statuses=[status] if status else None,
                branch_id=self.branch_box.currentData(),
                specialist_id=self.specialist_box.currentData(),
                search=self.search_box.text(),
            )
        except Exception as exc:
            self.handle_error(exc)
            return

        self.period_label.setText(
            f"{day_from.strftime('%d.%m.%Y')} — {day_to.strftime('%d.%m.%Y')}"
        )
        rows = []
        ids = []
        counters = {"confirmed": 0, "pending": 0, "no_show": 0, "ai": 0}
        for booking in bookings:
            ids.append(booking.id)
            if booking.status == BookingStatus.CONFIRMED:
                counters["confirmed"] += 1
            if booking.status == BookingStatus.PENDING:
                counters["pending"] += 1
            if booking.status == BookingStatus.NO_SHOW:
                counters["no_show"] += 1
            if booking.created_by_ai:
                counters["ai"] += 1
            rows.append(
                [
                    fmt_datetime(booking.starts_at),
                    booking.lead.display_name if booking.lead else "—",
                    pretty_phone(booking.lead.phone) if booking.lead else "—",
                    booking.service.name if booking.service else "—",
                    booking.branch.name if booking.branch else "—",
                    booking.specialist.full_name if booking.specialist else "—",
                    purpose_label(booking.purpose),
                    colored_item(
                        booking_status_label(booking.status),
                        booking_color(booking.status),
                        bold=True,
                    ),
                    f"{booking.duration_minutes} min",
                ]
            )
        self.table.fill(rows, ids=ids)
        self.tile_total.set_value(str(len(bookings)))
        self.tile_confirmed.set_value(str(counters["confirmed"]))
        self.tile_pending.set_value(str(counters["pending"]))
        self.tile_no_show.set_value(str(counters["no_show"]))
        self.tile_ai.set_value(str(counters["ai"]))

    # ------------------------------------------------------------------ #
    def _create(self) -> None:
        """Create a booking (asks which lead through the leads page normally)."""
        if not self.require(Perm.BOOKING_MANAGE):
            return
        from app.repositories.lead_repository import LeadFilter
        from app.services import lead_service

        leads, _ = lead_service.search_leads(LeadFilter(only_open=True), actor=self.user, limit=1)
        if not leads:
            show_error(self, tr("err.lead_not_found"))
            return
        dialog = BookingDialog(self.user, lead_id=leads[0].id, parent=self)
        if dialog.exec():
            self.reload()

    def _edit(self) -> None:
        """Edit the selected booking."""
        booking_id = self.table.selected_id()
        if booking_id is None:
            return
        bookings = {b.id: b for b in booking_service.list_bookings(limit=5000)}
        booking = bookings.get(booking_id)
        if booking is None:
            return
        dialog = BookingDialog(self.user, booking=booking, parent=self)
        if dialog.exec():
            self.reload()

    def _show_menu(self, position) -> None:
        """Row context menu with the status transitions."""
        booking_id = self.table.selected_id()
        if booking_id is None:
            return
        menu = QMenu(self)
        menu.addAction(tr("common.edit"), self._edit)
        menu.addSeparator()
        menu.addAction(
            tr("booking.confirm"), lambda: self._change_status(booking_id, BookingStatus.CONFIRMED)
        )
        menu.addAction(
            tr("booking.arrived"), lambda: self._change_status(booking_id, BookingStatus.ARRIVED)
        )
        menu.addAction(
            tr("booking.no_show"), lambda: self._change_status(booking_id, BookingStatus.NO_SHOW)
        )
        menu.addAction(
            tr("bstatus.completed"),
            lambda: self._change_status(booking_id, BookingStatus.COMPLETED),
        )
        menu.addSeparator()
        menu.addAction(tr("booking.cancel"), lambda: self._cancel(booking_id))
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _change_status(self, booking_id: int, status: str) -> None:
        """Apply a booking status change."""
        try:
            booking_service.change_status(booking_id, status, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.reload()
        self.context.tasks_updated.emit()

    def _cancel(self, booking_id: int) -> None:
        """Cancel a booking after confirmation."""
        if not confirm(self, tr("booking.cancel") + "?"):
            return
        try:
            booking_service.cancel_booking(booking_id, "Operator bekor qildi", actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.reload()

    def _send_reminders(self) -> None:
        """Send reminders for the bookings of the next 24 hours."""
        try:
            sent = booking_service.send_reminders()
        except Exception as exc:
            self.handle_error(exc)
            return
        show_info(self, f"{sent} {tr('common.rows')}")
        self.reload()

    # ------------------------------------------------------------------ #
    def retranslate(self) -> None:
        """Reapply translated captions."""
        super().retranslate()
        self.new_button.setText(tr("booking.new"))
        self.remind_button.setText(tr("booking.remind"))
        self.chip_day.setText(tr("common.day"))
        self.chip_week.setText(tr("common.week"))
        self.chip_list.setText(tr("common.list"))
        self.today_button.setText(tr("common.today"))
        self.table.set_headers([tr(key) for key in COLUMNS])
        self.tile_total.set_label(tr("mkt.bookings"))
        self.tile_confirmed.set_label(tr("bstatus.confirmed"))
        self.tile_pending.set_label(tr("bstatus.pending"))
        self.tile_no_show.set_label(tr("bstatus.no_show"))
        self.tile_ai.set_label(tr("booking.created_by_ai"))
        self.reload()
