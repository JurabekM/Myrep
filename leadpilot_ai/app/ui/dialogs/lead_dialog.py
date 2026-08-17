"""Create / edit lead dialog and the status-change dialog."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.crm import Lead
from app.models.enums import Channel, LeadStatus
from app.services import auth_service, company_service, lead_service
from app.services.auth_service import CurrentUser
from app.ui.i18n import tr
from app.ui.widgets.common import combo, set_combo_value, show_error
from app.ui.widgets.labels import (
    channel_items,
    language_items,
    loss_items,
    status_items,
)
from app.utils.dates import now


class LeadDialog(QDialog):
    """Create or edit one lead."""

    def __init__(self, actor: CurrentUser, lead: Lead | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.actor = actor
        self.lead = lead
        self.lead_id: int | None = lead.id if lead else None
        self.setWindowTitle(tr("leads.new") if lead is None else tr("common.edit"))
        self.setMinimumWidth(520)
        self._build()
        if lead is not None:
            self._fill(lead)

    def _build(self) -> None:
        """Create the form."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+998 90 123 45 67")
        self.email_input = QLineEdit()
        self.telegram_input = QLineEdit()
        self.interest_input = QLineEdit()
        self.channel_box = combo(channel_items(include_all=False))
        self.language_box = combo(language_items())
        self.status_box = combo(status_items(include_all=False))

        services = company_service.list_services(only_active=True)
        self.service_box = combo([("—", None)] + [(s.name, s.id) for s in services])
        branches = company_service.list_branches()
        self.branch_box = combo([("—", None)] + [(b.name, b.id) for b in branches])
        operators = auth_service.list_operators()
        self.owner_box = combo(
            [(tr("common.unassigned"), None)] + [(u.full_name, u.id) for u in operators]
        )
        sources = company_service.list_sources()
        self.source_box = combo([("—", None)] + [(s.name, s.id) for s in sources])
        campaigns = company_service.list_campaigns()
        self.campaign_box = combo([("—", None)] + [(c.name, c.id) for c in campaigns])

        self.utm_source = QLineEdit()
        self.utm_medium = QLineEdit()
        self.utm_campaign = QLineEdit()
        self.utm_content = QLineEdit()
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)

        form.addRow(tr("login.full_name"), self.name_input)
        form.addRow(tr("common.phone"), self.phone_input)
        form.addRow(tr("common.email"), self.email_input)
        form.addRow(tr("leads.telegram"), self.telegram_input)
        form.addRow(tr("common.language"), self.language_box)
        form.addRow(tr("common.channel"), self.channel_box)
        form.addRow(tr("common.status"), self.status_box)
        form.addRow(tr("leads.interest"), self.interest_input)
        form.addRow(tr("common.service"), self.service_box)
        form.addRow(tr("common.branch"), self.branch_box)
        form.addRow(tr("leads.owner"), self.owner_box)
        form.addRow(tr("common.source"), self.source_box)
        form.addRow(tr("common.campaign"), self.campaign_box)
        form.addRow("utm_source", self.utm_source)
        form.addRow("utm_medium", self.utm_medium)
        form.addRow("utm_campaign", self.utm_campaign)
        form.addRow("utm_content", self.utm_content)
        form.addRow(tr("common.comment"), self.notes_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox()
        save_button = buttons.addButton(tr("common.save"), QDialogButtonBox.ButtonRole.AcceptRole)
        save_button.setObjectName("Primary")
        buttons.addButton(tr("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _fill(self, lead: Lead) -> None:
        """Populate the form from an existing lead."""
        self.name_input.setText(lead.full_name)
        self.phone_input.setText(lead.phone or "")
        self.email_input.setText(lead.email)
        self.telegram_input.setText(lead.telegram_username)
        self.interest_input.setText(lead.interest)
        set_combo_value(self.channel_box, lead.channel)
        set_combo_value(self.language_box, lead.language)
        set_combo_value(self.status_box, lead.status)
        set_combo_value(self.service_box, lead.service_id)
        set_combo_value(self.branch_box, lead.branch_id)
        set_combo_value(self.owner_box, lead.owner_id)
        set_combo_value(self.source_box, lead.source_id)
        set_combo_value(self.campaign_box, lead.campaign_id)
        self.utm_source.setText(lead.utm_source)
        self.utm_medium.setText(lead.utm_medium)
        self.utm_campaign.setText(lead.utm_campaign)
        self.utm_content.setText(lead.utm_content)
        self.notes_input.setPlainText(lead.notes)
        self.status_box.setEnabled(False)  # status changes go through the dedicated dialog

    def _save(self) -> None:
        """Validate and persist the lead."""
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        if not name and not phone and not self.telegram_input.text().strip():
            show_error(self, tr("err.fullname_required"))
            return
        payload = {
            "full_name": name,
            "phone": phone,
            "email": self.email_input.text().strip(),
            "telegram_username": self.telegram_input.text().strip().lstrip("@"),
            "interest": self.interest_input.text().strip(),
            "language": self.language_box.currentData(),
            "service_id": self.service_box.currentData(),
            "branch_id": self.branch_box.currentData(),
            "owner_id": self.owner_box.currentData(),
            "source_id": self.source_box.currentData(),
            "campaign_id": self.campaign_box.currentData(),
            "utm_source": self.utm_source.text().strip(),
            "utm_medium": self.utm_medium.text().strip(),
            "utm_campaign": self.utm_campaign.text().strip(),
            "utm_content": self.utm_content.text().strip(),
            "notes": self.notes_input.toPlainText(),
        }
        try:
            if self.lead_id:
                lead_service.update_lead(self.lead_id, actor=self.actor, **payload)
            else:
                created = lead_service.create_lead(
                    actor=self.actor,
                    company_id=self.actor.company_id,
                    channel=self.channel_box.currentData() or Channel.MANUAL,
                    status=self.status_box.currentData() or LeadStatus.NEW,
                    utm={
                        "utm_source": payload.pop("utm_source"),
                        "utm_medium": payload.pop("utm_medium"),
                        "utm_campaign": payload.pop("utm_campaign"),
                        "utm_content": payload.pop("utm_content"),
                    },
                    **payload,
                )
                self.lead_id = created.id
        except Exception as exc:
            code = getattr(exc, "code", None)
            show_error(self, tr(f"err.{code}") if code else tr("err.unknown"))
            return
        self.accept()


class StatusChangeDialog(QDialog):
    """Change a lead status, asking for the mandatory extra fields."""

    def __init__(
        self,
        actor: CurrentUser,
        lead_id: int,
        current_status: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.actor = actor
        self.lead_id = lead_id
        self.current_status = current_status
        self.setWindowTitle(tr("inbox.change_status"))
        self.setMinimumWidth(420)
        self._build()

    def _build(self) -> None:
        """Create the form."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        allowed = [
            (label, value)
            for label, value in status_items(include_all=False)
            if lead_service.can_transition(self.current_status, value)
        ]
        self.status_box = combo(allowed)
        set_combo_value(self.status_box, self.current_status)
        self.status_box.currentIndexChanged.connect(self._toggle_fields)

        form = QFormLayout()
        form.addRow(tr("common.status"), self.status_box)

        self.loss_box = combo(loss_items())
        self.loss_label = QLabel(tr("leads.loss_reason"))
        form.addRow(self.loss_label, self.loss_box)

        self.revenue_input = QDoubleSpinBox()
        self.revenue_input.setRange(0, 10_000_000_000)
        self.revenue_input.setSingleStep(100_000)
        self.revenue_input.setGroupSeparatorShown(True)
        self.revenue_label = QLabel(tr("leads.revenue_prompt"))
        form.addRow(self.revenue_label, self.revenue_input)

        self.sale_date = QDateEdit(QDate.currentDate())
        self.sale_date.setCalendarPopup(True)
        self.sale_date.setDisplayFormat("dd.MM.yyyy")
        self.sale_date_label = QLabel(tr("leads.sale_date"))
        form.addRow(self.sale_date_label, self.sale_date)

        self.comment_input = QTextEdit()
        self.comment_input.setMaximumHeight(70)
        form.addRow(tr("common.comment"), self.comment_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        apply_button = buttons.addButton(tr("common.apply"), QDialogButtonBox.ButtonRole.AcceptRole)
        apply_button.setObjectName("Primary")
        buttons.addButton(tr("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._toggle_fields()

    def _toggle_fields(self) -> None:
        """Show only the fields required by the selected status."""
        status = self.status_box.currentData()
        is_lost = status == LeadStatus.LOST
        is_won = status == LeadStatus.WON
        self.loss_box.setVisible(is_lost)
        self.loss_label.setVisible(is_lost)
        self.revenue_input.setVisible(is_won)
        self.revenue_label.setVisible(is_won)
        self.sale_date.setVisible(is_won)
        self.sale_date_label.setVisible(is_won)

    def _apply(self) -> None:
        """Apply the status change through the service layer."""
        status = self.status_box.currentData()
        sale_date = None
        if status == LeadStatus.WON:
            picked = self.sale_date.date().toPython()
            sale_date = datetime.combine(picked, now().time())
        try:
            lead_service.change_status(
                self.lead_id,
                status,
                actor=self.actor,
                loss_reason=self.loss_box.currentData() if status == LeadStatus.LOST else "",
                loss_comment=self.comment_input.toPlainText(),
                revenue=self.revenue_input.value() if status == LeadStatus.WON else None,
                sale_date=sale_date,
            )
        except Exception as exc:
            code = getattr(exc, "code", None)
            detail = getattr(exc, "detail", "")
            show_error(self, tr(f"err.{code}", detail=detail) if code else tr("err.unknown"))
            return
        self.accept()


class MergeLeadsDialog(QDialog):
    """Pick which duplicate is merged into which primary lead."""

    def __init__(self, actor: CurrentUser, leads: list[Lead], parent: QWidget | None = None):
        super().__init__(parent)
        self.actor = actor
        self.leads = leads
        self.setWindowTitle(tr("leads.merge"))
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        hint = QLabel(tr("leads.merge_hint"))
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        options = [(f"#{lead.id} · {lead.display_name}", lead.id) for lead in leads]
        self.primary_box: QComboBox = combo(options)
        self.duplicate_box: QComboBox = combo(options)
        if len(options) > 1:
            self.duplicate_box.setCurrentIndex(1)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr("leads.merge") + " →"))
        row.addWidget(self.primary_box, 1)
        layout.addLayout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel(tr("leads.duplicates")))
        row2.addWidget(self.duplicate_box, 1)
        layout.addLayout(row2)

        buttons = QDialogButtonBox()
        merge_button = buttons.addButton(tr("leads.merge"), QDialogButtonBox.ButtonRole.AcceptRole)
        merge_button.setObjectName("Primary")
        buttons.addButton(tr("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._merge)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _merge(self) -> None:
        """Perform the merge."""
        try:
            lead_service.merge_leads(
                self.primary_box.currentData(),
                self.duplicate_box.currentData(),
                actor=self.actor,
            )
        except Exception as exc:
            code = getattr(exc, "code", None)
            show_error(self, tr(f"err.{code}") if code else tr("err.unknown"))
            return
        self.accept()
