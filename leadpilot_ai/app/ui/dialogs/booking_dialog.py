"""Create / edit booking dialog with free-slot suggestions."""

from __future__ import annotations

from datetime import timedelta

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database.engine import session_scope
from app.models.operations import Booking
from app.services import auth_service, booking_service, company_service
from app.services.auth_service import CurrentUser
from app.ui.i18n import tr
from app.ui.widgets.common import combo, set_combo_value, show_error
from app.ui.widgets.labels import purpose_items
from app.utils.dates import fmt_datetime, now


class BookingDialog(QDialog):
    """Create or reschedule a booking; refuses overlapping slots."""

    def __init__(
        self,
        actor: CurrentUser,
        *,
        lead_id: int | None = None,
        booking: Booking | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.actor = actor
        self.booking = booking
        self.lead_id = lead_id or (booking.lead_id if booking else None)
        self.booking_id = booking.id if booking else None
        self.setWindowTitle(tr("booking.new") if booking is None else tr("common.edit"))
        self.setMinimumWidth(520)
        self._build()
        if booking is not None:
            self._fill(booking)
        self._refresh_slots()

    def _build(self) -> None:
        """Create the form."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        services = company_service.list_services(only_active=True)
        self.service_box = combo([("—", None)] + [(s.name, s.id) for s in services])
        self.service_box.currentIndexChanged.connect(self._on_service_changed)
        branches = company_service.list_branches()
        self.branch_box = combo([("—", None)] + [(b.name, b.id) for b in branches])
        self.branch_box.currentIndexChanged.connect(self._refresh_slots)
        operators = auth_service.list_operators()
        self.specialist_box = combo([("—", None)] + [(u.full_name, u.id) for u in operators])
        self.specialist_box.currentIndexChanged.connect(self._refresh_slots)
        self.purpose_box = combo(purpose_items())

        self.datetime_input = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.datetime_input.setCalendarPopup(True)
        self.datetime_input.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.datetime_input.setMinimumHeight(34)

        self.duration_input = QSpinBox()
        self.duration_input.setRange(10, 480)
        self.duration_input.setSingleStep(10)
        self.duration_input.setValue(30)
        self.duration_input.setSuffix(" min")
        self.duration_input.valueChanged.connect(self._refresh_slots)

        self.note_input = QTextEdit()
        self.note_input.setMaximumHeight(70)

        form.addRow(tr("common.service"), self.service_box)
        form.addRow(tr("common.branch"), self.branch_box)
        form.addRow(tr("booking.specialist"), self.specialist_box)
        form.addRow(tr("booking.purpose"), self.purpose_box)
        form.addRow(tr("booking.starts_at"), self.datetime_input)
        form.addRow(tr("common.duration"), self.duration_input)
        form.addRow(tr("common.note"), self.note_input)
        layout.addLayout(form)

        slots_label = QLabel(tr("booking.free_slots"))
        slots_label.setObjectName("SectionTitle")
        layout.addWidget(slots_label)
        self.slots_list = QListWidget()
        self.slots_list.setMaximumHeight(120)
        self.slots_list.itemClicked.connect(self._on_slot_picked)
        layout.addWidget(self.slots_list)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #EF4444; font-size: 12px;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox()
        save_button = buttons.addButton(tr("common.save"), QDialogButtonBox.ButtonRole.AcceptRole)
        save_button.setObjectName("Primary")
        buttons.addButton(tr("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _fill(self, booking: Booking) -> None:
        """Populate the form from an existing booking."""
        set_combo_value(self.service_box, booking.service_id)
        set_combo_value(self.branch_box, booking.branch_id)
        set_combo_value(self.specialist_box, booking.specialist_id)
        set_combo_value(self.purpose_box, booking.purpose)
        self.datetime_input.setDateTime(QDateTime(booking.starts_at))
        self.duration_input.setValue(booking.duration_minutes)
        self.note_input.setPlainText(booking.note)

    def _on_service_changed(self) -> None:
        """Adopt the default duration of the selected service."""
        service_id = self.service_box.currentData()
        if service_id:
            for service in company_service.list_services():
                if service.id == service_id:
                    self.duration_input.setValue(service.duration_minutes or 30)
                    break
        self._refresh_slots()

    def _refresh_slots(self) -> None:
        """Reload the list of free slots for the chosen resource."""
        self.slots_list.clear()
        with session_scope() as session:
            slots = booking_service.free_slots(
                session,
                duration_minutes=self.duration_input.value(),
                branch_id=self.branch_box.currentData(),
                specialist_id=self.specialist_box.currentData(),
                limit=12,
            )
        for slot in slots:
            item = QListWidgetItem(fmt_datetime(slot))
            item.setData(Qt.ItemDataRole.UserRole, slot)
            self.slots_list.addItem(item)

    def _on_slot_picked(self, item: QListWidgetItem) -> None:
        """Copy the chosen slot into the datetime field."""
        slot = item.data(Qt.ItemDataRole.UserRole)
        if slot:
            self.datetime_input.setDateTime(QDateTime(slot))

    def _save(self) -> None:
        """Create or update the booking."""
        self.error_label.setText("")
        starts_at = self.datetime_input.dateTime().toPython()
        try:
            if self.booking_id:
                booking_service.update_booking(
                    self.booking_id,
                    actor=self.actor,
                    starts_at=starts_at,
                    duration_minutes=self.duration_input.value(),
                    service_id=self.service_box.currentData(),
                    branch_id=self.branch_box.currentData(),
                    specialist_id=self.specialist_box.currentData(),
                    purpose=self.purpose_box.currentData(),
                    note=self.note_input.toPlainText(),
                )
            else:
                if self.lead_id is None:
                    show_error(self, tr("err.lead_not_found"))
                    return
                booking_service.create_booking(
                    lead_id=self.lead_id,
                    starts_at=starts_at,
                    duration_minutes=self.duration_input.value(),
                    service_id=self.service_box.currentData(),
                    branch_id=self.branch_box.currentData(),
                    specialist_id=self.specialist_box.currentData(),
                    purpose=self.purpose_box.currentData(),
                    note=self.note_input.toPlainText(),
                    created_channel="manual",
                    actor=self.actor,
                )
        except Exception as exc:
            code = getattr(exc, "code", None)
            detail = getattr(exc, "detail", "")
            self.error_label.setText(
                tr(f"err.{code}", detail=detail) if code else tr("err.unknown")
            )
            return
        self.accept()


def default_start() -> QDateTime:
    """Next round hour, used as the default booking time."""
    reference = now() + timedelta(hours=1)
    return QDateTime(reference.replace(minute=0, second=0, microsecond=0))
