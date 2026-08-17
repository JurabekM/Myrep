"""Settings workspace: company, users, catalogue, integrations, data."""

from __future__ import annotations

import logging

from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import load_config
from app.controllers.app_context import AppContext
from app.models.enums import IntegrationKind, MarketingSourceType
from app.models.enums import Permission as Perm
from app.reports import excel_export
from app.services import (
    auth_service,
    company_service,
    conversation_service,
    integration_service,
    lead_service,
)
from app.ui.dialogs.misc_dialogs import UserDialog
from app.ui.i18n import tr
from app.ui.pages.base_page import BasePage
from app.ui.styles import theme
from app.ui.widgets.common import (
    DataTable,
    Panel,
    colored_item,
    combo,
    confirm,
    set_combo_value,
    show_error,
    show_info,
)
from app.ui.widgets.labels import (
    integration_color,
    integration_status_label,
    language_items,
    role_label,
)
from app.utils.dates import fmt_datetime, parse_hhmm
from app.utils.formatting import fmt_money, mask_secret

logger = logging.getLogger(__name__)

#: Providers shown on the integrations tab with their editable fields.
INTEGRATION_FIELDS: dict[str, tuple[str, str, list[tuple[str, str, bool]]]] = {
    "telegram": (
        IntegrationKind.CHANNEL,
        "Telegram",
        [("bot_token", "Bot token", True)],
    ),
    "whatsapp": (
        IntegrationKind.CHANNEL,
        "WhatsApp Cloud API",
        [
            ("phone_number_id", "Phone number ID", True),
            ("access_token", "Access token", True),
            ("relay_url", "Relay URL", False),
        ],
    ),
    "instagram": (
        IntegrationKind.CHANNEL,
        "Instagram",
        [
            ("ig_account_id", "IG account ID", True),
            ("access_token", "Access token", True),
            ("relay_url", "Relay URL", False),
        ],
    ),
    "website": (
        IntegrationKind.CHANNEL,
        "Website chat",
        [("relay_url", "Relay URL", False), ("send_url", "Send URL", False)],
    ),
    "twilio": (
        IntegrationKind.TELEPHONY,
        "Twilio Voice",
        [
            ("account_sid", "Account SID", True),
            ("auth_token", "Auth token", True),
            ("from_number", "From number", False),
        ],
    ),
    "sip": (
        IntegrationKind.TELEPHONY,
        "SIP / PBX",
        [("base_url", "Base URL", False), ("api_key", "API key", True)],
    ),
    "openai_compatible": (
        IntegrationKind.LLM,
        "LLM (OpenAI-compatible)",
        [
            ("api_key", "API key", True),
            ("base_url", "Base URL", False),
            ("model", "Model", False),
        ],
    ),
    "openai_stt": (
        IntegrationKind.STT,
        "Speech-to-Text",
        [("api_key", "API key", True), ("model", "Model", False)],
    ),
    "bitrix24": (IntegrationKind.CRM, "Bitrix24", [("webhook_base", "Webhook URL", True)]),
    "amocrm": (
        IntegrationKind.CRM,
        "amoCRM",
        [("base_url", "Base URL", False), ("access_token", "Access token", True)],
    ),
    "webhook": (
        IntegrationKind.CRM,
        "Webhook",
        [("webhook_url", "Webhook URL", False), ("webhook_token", "Token", True)],
    ),
}


class SettingsPage(BasePage):
    """Tabbed settings workspace."""

    title_key = "set.title"
    subtitle_key = "app.subtitle"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self._integration_inputs: dict[str, dict[str, QLineEdit]] = {}
        self._integration_flags: dict[str, tuple[QCheckBox, QCheckBox, QLabel]] = {}
        self._build()

    def _build(self) -> None:
        """Assemble the tabs."""
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_company(), tr("set.company"))
        self.tabs.addTab(self._build_users(), tr("set.users"))
        self.tabs.addTab(self._build_services(), tr("set.services"))
        self.tabs.addTab(self._build_branches(), tr("set.branches"))
        self.tabs.addTab(self._build_marketing(), tr("set.marketing"))
        self.tabs.addTab(self._build_tags(), tr("set.tags"))
        self.tabs.addTab(self._build_integrations(), tr("set.integrations"))
        self.tabs.addTab(self._build_data(), tr("set.data"))
        self.body().addWidget(self.tabs, 1)

    # ------------------------------------------------------------------ #
    # Company tab
    # ------------------------------------------------------------------ #
    def _build_company(self) -> QWidget:
        """Company profile editor."""
        panel = Panel(padding=16, spacing=12)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(9)

        self.company_name = QLineEdit()
        self.company_legal = QLineEdit()
        self.company_industry = QLineEdit()
        self.company_phone = QLineEdit()
        self.company_email = QLineEdit()
        self.company_address = QLineEdit()
        self.company_currency = QLineEdit()
        self.company_language = combo(language_items(include_unknown=False))
        self.company_timezone = QLineEdit()
        self.work_start = QTimeEdit()
        self.work_start.setDisplayFormat("HH:mm")
        self.work_end = QTimeEdit()
        self.work_end.setDisplayFormat("HH:mm")
        self.work_days = QLineEdit()
        self.logo_path = QLineEdit()
        logo_button = QPushButton(tr("common.select"))
        logo_button.setObjectName("Ghost")
        logo_button.clicked.connect(self._pick_logo)
        logo_row = QHBoxLayout()
        logo_row.addWidget(self.logo_path, 1)
        logo_row.addWidget(logo_button)

        form.addRow(tr("common.name"), self.company_name)
        form.addRow("Legal name", self.company_legal)
        form.addRow("Industry", self.company_industry)
        form.addRow(tr("common.phone"), self.company_phone)
        form.addRow(tr("common.email"), self.company_email)
        form.addRow(tr("common.address"), self.company_address)
        form.addRow(tr("set.currency"), self.company_currency)
        form.addRow(tr("set.default_lang"), self.company_language)
        form.addRow(tr("set.timezone"), self.company_timezone)
        form.addRow(tr("set.work_hours") + " " + tr("common.from"), self.work_start)
        form.addRow(tr("set.work_hours") + " " + tr("common.to"), self.work_end)
        form.addRow(tr("set.work_days"), self.work_days)
        form.addRow(tr("set.logo"), logo_row)
        panel.body().addLayout(form)

        self.save_company_button = QPushButton(tr("common.save"))
        self.save_company_button.setObjectName("Primary")
        self.save_company_button.clicked.connect(self._save_company)
        buttons = QHBoxLayout()
        buttons.addWidget(self.save_company_button)
        buttons.addStretch(1)
        panel.body().addLayout(buttons)
        panel.body().addStretch(1)
        return panel

    def _pick_logo(self) -> None:
        """Choose a logo image."""
        path, _ = QFileDialog.getOpenFileName(
            self, tr("set.logo"), "", "Images (*.png *.jpg *.jpeg *.svg)"
        )
        if path:
            self.logo_path.setText(path)

    def _load_company(self) -> None:
        """Fill the company form."""
        company = company_service.get_company()
        if company is None:
            return
        self.company_name.setText(company.name)
        self.company_legal.setText(company.legal_name)
        self.company_industry.setText(company.industry)
        self.company_phone.setText(company.phone)
        self.company_email.setText(company.email)
        self.company_address.setText(company.address)
        self.company_currency.setText(company.currency)
        set_combo_value(self.company_language, company.default_language)
        self.company_timezone.setText(company.timezone)
        start = parse_hhmm(company.work_start)
        end = parse_hhmm(company.work_end)
        self.work_start.setTime(QTime(start.hour, start.minute))
        self.work_end.setTime(QTime(end.hour, end.minute))
        self.work_days.setText(company.work_days)
        self.logo_path.setText(company.logo_path or "")

    def _save_company(self) -> None:
        """Persist the company profile."""
        if not self.require(Perm.SETTINGS_MANAGE):
            return
        try:
            company = company_service.save_company(
                actor=self.user,
                name=self.company_name.text().strip(),
                legal_name=self.company_legal.text().strip(),
                industry=self.company_industry.text().strip(),
                phone=self.company_phone.text().strip(),
                email=self.company_email.text().strip(),
                address=self.company_address.text().strip(),
                currency=self.company_currency.text().strip() or "so'm",
                default_language=self.company_language.currentData(),
                timezone=self.company_timezone.text().strip() or "Asia/Tashkent",
                work_start=self.work_start.time().toString("HH:mm"),
                work_end=self.work_end.time().toString("HH:mm"),
                work_days=self.work_days.text().strip() or "1,2,3,4,5,6",
                logo_path=self.logo_path.text().strip() or None,
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.user.company_name = company.name
        show_info(self, tr("common.saved"))

    # ------------------------------------------------------------------ #
    # Users tab
    # ------------------------------------------------------------------ #
    def _build_users(self) -> QWidget:
        """User management."""
        panel = Panel(padding=10, spacing=8)
        row = QHBoxLayout()
        self.user_new_button = QPushButton(tr("common.add"))
        self.user_new_button.setObjectName("Primary")
        self.user_new_button.clicked.connect(self._create_user)
        self.user_edit_button = QPushButton(tr("common.edit"))
        self.user_edit_button.clicked.connect(self._edit_user)
        self.user_archive_button = QPushButton(tr("common.archive"))
        self.user_archive_button.setObjectName("Danger")
        self.user_archive_button.clicked.connect(self._archive_user)
        row.addWidget(self.user_new_button)
        row.addWidget(self.user_edit_button)
        row.addWidget(self.user_archive_button)
        row.addStretch(1)
        panel.body().addLayout(row)

        self.users_table = DataTable(
            [
                tr("login.username"),
                tr("login.full_name"),
                tr("common.role"),
                tr("common.email"),
                tr("common.phone"),
                tr("common.branch"),
                tr("common.active"),
            ],
            stretch_column=1,
        )
        self.users_table.doubleClicked.connect(self._edit_user)
        panel.body().addWidget(self.users_table, 1)
        return panel

    def _load_users(self) -> None:
        """Reload the user table."""
        users = auth_service.list_users(include_archived=True)
        rows = []
        ids = []
        for user in users:
            ids.append(user.id)
            rows.append(
                [
                    user.username,
                    user.full_name,
                    role_label(user.role.name),
                    user.email,
                    user.phone,
                    user.branch.name if user.branch else "—",
                    colored_item(
                        (
                            tr("common.yes")
                            if user.is_active and not user.is_archived
                            else tr("common.no")
                        ),
                        theme.SUCCESS if user.is_active and not user.is_archived else theme.DANGER,
                    ),
                ]
            )
        self.users_table.fill(rows, ids=ids)

    def _create_user(self) -> None:
        """Open the create-user dialog."""
        if not self.require(Perm.USER_MANAGE):
            return
        dialog = UserDialog(self.user, parent=self)
        if dialog.exec():
            self._load_users()

    def _edit_user(self) -> None:
        """Edit the selected user."""
        if not self.require(Perm.USER_MANAGE):
            return
        user_id = self.users_table.selected_id()
        if user_id is None:
            show_error(self, tr("err.select_row"))
            return
        target = next(
            (u for u in auth_service.list_users(include_archived=True) if u.id == user_id), None
        )
        if target is None:
            return
        dialog = UserDialog(self.user, target, parent=self)
        if dialog.exec():
            self._load_users()

    def _archive_user(self) -> None:
        """Archive the selected user."""
        if not self.require(Perm.USER_MANAGE):
            return
        user_id = self.users_table.selected_id()
        if user_id is None:
            show_error(self, tr("err.select_row"))
            return
        if not confirm(self, tr("common.confirm")):
            return
        try:
            auth_service.archive_user(user_id, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        self._load_users()

    # ------------------------------------------------------------------ #
    # Services tab
    # ------------------------------------------------------------------ #
    def _build_services(self) -> QWidget:
        """Service catalogue editor."""
        panel = Panel(padding=10, spacing=8)
        form = QHBoxLayout()
        self.service_name = QLineEdit()
        self.service_name.setPlaceholderText(tr("common.name"))
        self.service_name_ru = QLineEdit()
        self.service_name_ru.setPlaceholderText(tr("common.name") + " (RU)")
        self.service_category = QLineEdit()
        self.service_category.setPlaceholderText(tr("common.category"))
        self.service_price = QDoubleSpinBox()
        self.service_price.setRange(0, 10_000_000_000)
        self.service_price.setGroupSeparatorShown(True)
        self.service_duration = QSpinBox()
        self.service_duration.setRange(10, 480)
        self.service_duration.setValue(30)
        self.service_duration.setSuffix(" min")
        self.service_save = QPushButton(tr("common.save"))
        self.service_save.setObjectName("Primary")
        self.service_save.clicked.connect(self._save_service)
        for widget in (
            self.service_name,
            self.service_name_ru,
            self.service_category,
            self.service_price,
            self.service_duration,
            self.service_save,
        ):
            form.addWidget(widget)
        panel.body().addLayout(form)

        self.services_table = DataTable(
            [
                tr("common.name"),
                tr("common.name") + " (RU)",
                tr("common.category"),
                tr("common.price"),
                tr("common.duration"),
                tr("common.active"),
            ],
            stretch_column=0,
        )
        self.services_table.itemSelectionChanged.connect(self._on_service_selected)
        panel.body().addWidget(self.services_table, 1)

        buttons = QHBoxLayout()
        self.service_archive = QPushButton(tr("common.archive"))
        self.service_archive.setObjectName("Danger")
        self.service_archive.clicked.connect(self._archive_service)
        buttons.addWidget(self.service_archive)
        buttons.addStretch(1)
        panel.body().addLayout(buttons)
        self._editing_service_id: int | None = None
        return panel

    def _load_services(self) -> None:
        """Reload the service table."""
        services = company_service.list_services()
        rows = []
        ids = []
        for service in services:
            ids.append(service.id)
            rows.append(
                [
                    service.name,
                    service.name_ru,
                    service.category,
                    fmt_money(service.price),
                    f"{service.duration_minutes} min",
                    colored_item(
                        tr("common.yes") if service.is_active else tr("common.no"),
                        theme.SUCCESS if service.is_active else theme.TEXT_DISABLED,
                    ),
                ]
            )
        self.services_table.fill(rows, ids=ids)

    def _on_service_selected(self) -> None:
        """Copy the selected service into the inline editor."""
        service_id = self.services_table.selected_id()
        if service_id is None:
            return
        service = next((s for s in company_service.list_services() if s.id == service_id), None)
        if service is None:
            return
        self._editing_service_id = service.id
        self.service_name.setText(service.name)
        self.service_name_ru.setText(service.name_ru)
        self.service_category.setText(service.category)
        self.service_price.setValue(float(service.price))
        self.service_duration.setValue(service.duration_minutes)

    def _save_service(self) -> None:
        """Create or update a service."""
        if not self.require(Perm.SETTINGS_MANAGE):
            return
        try:
            company_service.save_service(
                actor=self.user,
                service_id=self._editing_service_id,
                name=self.service_name.text(),
                name_ru=self.service_name_ru.text(),
                category=self.service_category.text(),
                price=self.service_price.value(),
                duration_minutes=self.service_duration.value(),
                company_id=self.user.company_id,
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self._editing_service_id = None
        self.service_name.clear()
        self.service_name_ru.clear()
        self.service_category.clear()
        self.service_price.setValue(0)
        self._load_services()

    def _archive_service(self) -> None:
        """Archive the selected service."""
        service_id = self.services_table.selected_id()
        if service_id is None:
            show_error(self, tr("err.select_row"))
            return
        try:
            company_service.archive_service(service_id, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        self._load_services()

    # ------------------------------------------------------------------ #
    # Branches tab
    # ------------------------------------------------------------------ #
    def _build_branches(self) -> QWidget:
        """Branch editor."""
        panel = Panel(padding=10, spacing=8)
        form = QHBoxLayout()
        self.branch_name = QLineEdit()
        self.branch_name.setPlaceholderText(tr("common.name"))
        self.branch_address = QLineEdit()
        self.branch_address.setPlaceholderText(tr("common.address"))
        self.branch_phone = QLineEdit()
        self.branch_phone.setPlaceholderText(tr("common.phone"))
        self.branch_start = QTimeEdit()
        self.branch_start.setDisplayFormat("HH:mm")
        self.branch_start.setTime(QTime(9, 0))
        self.branch_end = QTimeEdit()
        self.branch_end.setDisplayFormat("HH:mm")
        self.branch_end.setTime(QTime(19, 0))
        self.branch_save = QPushButton(tr("common.save"))
        self.branch_save.setObjectName("Primary")
        self.branch_save.clicked.connect(self._save_branch)
        for widget in (
            self.branch_name,
            self.branch_address,
            self.branch_phone,
            self.branch_start,
            self.branch_end,
            self.branch_save,
        ):
            form.addWidget(widget)
        panel.body().addLayout(form)

        self.branches_table = DataTable(
            [
                tr("common.name"),
                tr("common.address"),
                tr("common.phone"),
                tr("set.work_hours"),
                tr("common.active"),
            ],
            stretch_column=1,
        )
        self.branches_table.itemSelectionChanged.connect(self._on_branch_selected)
        panel.body().addWidget(self.branches_table, 1)
        self._editing_branch_id: int | None = None
        return panel

    def _load_branches(self) -> None:
        """Reload the branch table."""
        branches = company_service.list_branches()
        rows = []
        ids = []
        for branch in branches:
            ids.append(branch.id)
            rows.append(
                [
                    branch.name,
                    branch.address,
                    branch.phone,
                    f"{branch.work_start}–{branch.work_end}",
                    colored_item(
                        tr("common.yes") if branch.is_active else tr("common.no"),
                        theme.SUCCESS if branch.is_active else theme.TEXT_DISABLED,
                    ),
                ]
            )
        self.branches_table.fill(rows, ids=ids)

    def _on_branch_selected(self) -> None:
        """Copy the selected branch into the inline editor."""
        branch_id = self.branches_table.selected_id()
        if branch_id is None:
            return
        branch = next((b for b in company_service.list_branches() if b.id == branch_id), None)
        if branch is None:
            return
        self._editing_branch_id = branch.id
        self.branch_name.setText(branch.name)
        self.branch_address.setText(branch.address)
        self.branch_phone.setText(branch.phone)
        start = parse_hhmm(branch.work_start)
        end = parse_hhmm(branch.work_end)
        self.branch_start.setTime(QTime(start.hour, start.minute))
        self.branch_end.setTime(QTime(end.hour, end.minute))

    def _save_branch(self) -> None:
        """Create or update a branch."""
        if not self.require(Perm.SETTINGS_MANAGE):
            return
        try:
            company_service.save_branch(
                actor=self.user,
                branch_id=self._editing_branch_id,
                name=self.branch_name.text(),
                address=self.branch_address.text(),
                phone=self.branch_phone.text(),
                work_start=self.branch_start.time().toString("HH:mm"),
                work_end=self.branch_end.time().toString("HH:mm"),
                company_id=self.user.company_id,
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self._editing_branch_id = None
        self.branch_name.clear()
        self.branch_address.clear()
        self.branch_phone.clear()
        self._load_branches()

    # ------------------------------------------------------------------ #
    # Marketing tab
    # ------------------------------------------------------------------ #
    def _build_marketing(self) -> QWidget:
        """Marketing source and campaign editor."""
        panel = Panel(padding=10, spacing=8)

        source_row = QHBoxLayout()
        self.source_name = QLineEdit()
        self.source_name.setPlaceholderText(tr("common.source"))
        self.source_type = combo([(t.value, t.value) for t in MarketingSourceType])
        self.source_utm = QLineEdit()
        self.source_utm.setPlaceholderText("utm_source")
        self.source_save = QPushButton(tr("common.add"))
        self.source_save.setObjectName("Primary")
        self.source_save.clicked.connect(self._save_source)
        for widget in (self.source_name, self.source_type, self.source_utm, self.source_save):
            source_row.addWidget(widget)
        panel.body().addLayout(source_row)

        self.sources_table = DataTable(
            [tr("common.name"), tr("common.type"), "utm_source", tr("common.active")],
            stretch_column=0,
        )
        self.sources_table.setMaximumHeight(160)
        panel.body().addWidget(self.sources_table)

        campaign_row = QHBoxLayout()
        self.campaign_source = combo([])
        self.campaign_name = QLineEdit()
        self.campaign_name.setPlaceholderText(tr("common.campaign"))
        self.campaign_utm = QLineEdit()
        self.campaign_utm.setPlaceholderText("utm_campaign")
        self.campaign_cost = QDoubleSpinBox()
        self.campaign_cost.setRange(0, 10_000_000_000)
        self.campaign_cost.setGroupSeparatorShown(True)
        self.campaign_start = QDateEdit(QDate.currentDate().addMonths(-1))
        self.campaign_start.setCalendarPopup(True)
        self.campaign_start.setDisplayFormat("dd.MM.yyyy")
        self.campaign_end = QDateEdit(QDate.currentDate().addMonths(1))
        self.campaign_end.setCalendarPopup(True)
        self.campaign_end.setDisplayFormat("dd.MM.yyyy")
        self.campaign_save = QPushButton(tr("common.add"))
        self.campaign_save.setObjectName("Primary")
        self.campaign_save.clicked.connect(self._save_campaign)
        for widget in (
            self.campaign_source,
            self.campaign_name,
            self.campaign_utm,
            self.campaign_cost,
            self.campaign_start,
            self.campaign_end,
            self.campaign_save,
        ):
            campaign_row.addWidget(widget)
        panel.body().addLayout(campaign_row)

        self.campaigns_table = DataTable(
            [
                tr("common.name"),
                tr("common.source"),
                "utm_campaign",
                tr("mkt.cost"),
                tr("common.date"),
                tr("common.active"),
            ],
            stretch_column=0,
        )
        self.campaigns_table.itemSelectionChanged.connect(self._on_campaign_selected)
        panel.body().addWidget(self.campaigns_table, 1)
        self._editing_campaign_id: int | None = None
        return panel

    def _load_marketing(self) -> None:
        """Reload sources and campaigns."""
        sources = company_service.list_sources()
        rows = []
        ids = []
        for source in sources:
            ids.append(source.id)
            rows.append(
                [
                    source.name,
                    source.source_type,
                    source.utm_source,
                    tr("common.yes") if source.is_active else tr("common.no"),
                ]
            )
        self.sources_table.fill(rows, ids=ids)

        current = self.campaign_source.currentData()
        self.campaign_source.blockSignals(True)
        self.campaign_source.clear()
        for source in sources:
            self.campaign_source.addItem(source.name, source.id)
        index = self.campaign_source.findData(current)
        self.campaign_source.setCurrentIndex(index if index >= 0 else 0)
        self.campaign_source.blockSignals(False)

        campaigns = company_service.list_campaigns()
        rows = []
        ids = []
        for campaign in campaigns:
            ids.append(campaign.id)
            rows.append(
                [
                    campaign.name,
                    campaign.source.name if campaign.source else "—",
                    campaign.utm_campaign,
                    fmt_money(campaign.cost),
                    f"{campaign.start_date or '—'} — {campaign.end_date or '—'}",
                    tr("common.yes") if campaign.is_active else tr("common.no"),
                ]
            )
        self.campaigns_table.fill(rows, ids=ids)

    def _on_campaign_selected(self) -> None:
        """Copy the selected campaign into the editor."""
        campaign_id = self.campaigns_table.selected_id()
        if campaign_id is None:
            return
        campaign = next((c for c in company_service.list_campaigns() if c.id == campaign_id), None)
        if campaign is None:
            return
        self._editing_campaign_id = campaign.id
        set_combo_value(self.campaign_source, campaign.source_id)
        self.campaign_name.setText(campaign.name)
        self.campaign_utm.setText(campaign.utm_campaign)
        self.campaign_cost.setValue(float(campaign.cost))
        if campaign.start_date:
            self.campaign_start.setDate(QDate(campaign.start_date))
        if campaign.end_date:
            self.campaign_end.setDate(QDate(campaign.end_date))

    def _save_source(self) -> None:
        """Create a marketing source."""
        if not self.require(Perm.MARKETING_EDIT):
            return
        try:
            company_service.save_source(
                actor=self.user,
                name=self.source_name.text(),
                source_type=self.source_type.currentData(),
                utm_source=self.source_utm.text(),
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.source_name.clear()
        self.source_utm.clear()
        self._load_marketing()

    def _save_campaign(self) -> None:
        """Create or update a campaign with its budget."""
        if not self.require(Perm.MARKETING_EDIT):
            return
        source_id = self.campaign_source.currentData()
        if source_id is None:
            show_error(self, tr("err.source_not_found"))
            return
        try:
            company_service.save_campaign(
                actor=self.user,
                campaign_id=self._editing_campaign_id,
                source_id=source_id,
                name=self.campaign_name.text(),
                utm_campaign=self.campaign_utm.text(),
                cost=self.campaign_cost.value(),
                start_date=self.campaign_start.date().toPython(),
                end_date=self.campaign_end.date().toPython(),
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self._editing_campaign_id = None
        self.campaign_name.clear()
        self.campaign_utm.clear()
        self.campaign_cost.setValue(0)
        self._load_marketing()

    # ------------------------------------------------------------------ #
    # Tags & quick replies tab
    # ------------------------------------------------------------------ #
    def _build_tags(self) -> QWidget:
        """Tag and quick-reply editor."""
        panel = Panel(padding=10, spacing=8)
        row = QHBoxLayout()
        self.tag_name = QLineEdit()
        self.tag_name.setPlaceholderText(tr("common.tags"))
        self.tag_color = QLineEdit("#3B82F6")
        self.tag_color.setMaximumWidth(110)
        self.tag_save = QPushButton(tr("common.add"))
        self.tag_save.setObjectName("Primary")
        self.tag_save.clicked.connect(self._save_tag)
        row.addWidget(self.tag_name)
        row.addWidget(self.tag_color)
        row.addWidget(self.tag_save)
        row.addStretch(1)
        panel.body().addLayout(row)

        self.tags_table = DataTable([tr("common.name"), tr("common.description")], stretch_column=0)
        self.tags_table.setMaximumHeight(180)
        panel.body().addWidget(self.tags_table)

        quick_label = QLabel(tr("set.quick_replies"))
        quick_label.setObjectName("SectionTitle")
        panel.body().addWidget(quick_label)

        quick_row = QHBoxLayout()
        self.quick_title = QLineEdit()
        self.quick_title.setPlaceholderText(tr("common.title"))
        self.quick_uz = QLineEdit()
        self.quick_uz.setPlaceholderText("UZ")
        self.quick_ru = QLineEdit()
        self.quick_ru.setPlaceholderText("RU")
        self.quick_save = QPushButton(tr("common.add"))
        self.quick_save.setObjectName("Primary")
        self.quick_save.clicked.connect(self._save_quick_reply)
        for widget in (self.quick_title, self.quick_uz, self.quick_ru, self.quick_save):
            quick_row.addWidget(widget)
        panel.body().addLayout(quick_row)

        self.quick_table = DataTable([tr("common.title"), "UZ", "RU"], stretch_column=1)
        panel.body().addWidget(self.quick_table, 1)
        return panel

    def _load_tags(self) -> None:
        """Reload tags and quick replies."""
        tags = lead_service.list_tags()
        self.tags_table.fill(
            [[tag.name, tag.description] for tag in tags], ids=[tag.id for tag in tags]
        )
        replies = conversation_service.list_quick_replies()
        self.quick_table.fill(
            [[r.title, r.body_uz, r.body_ru] for r in replies], ids=[r.id for r in replies]
        )

    def _save_tag(self) -> None:
        """Create a tag."""
        try:
            lead_service.create_tag(
                self.tag_name.text().strip(), self.tag_color.text().strip(), actor=self.user
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.tag_name.clear()
        self._load_tags()

    def _save_quick_reply(self) -> None:
        """Create a quick reply template."""
        try:
            conversation_service.save_quick_reply(
                title=self.quick_title.text().strip(),
                body_uz=self.quick_uz.text(),
                body_ru=self.quick_ru.text(),
                actor=self.user,
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.quick_title.clear()
        self.quick_uz.clear()
        self.quick_ru.clear()
        self._load_tags()

    # ------------------------------------------------------------------ #
    # Integrations tab
    # ------------------------------------------------------------------ #
    def _build_integrations(self) -> QWidget:
        """Credential editor with connection tests."""
        from PySide6.QtWidgets import QFrame, QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        hint = QLabel(tr("int.secret_hint"))
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        from app.utils.security import keyring_available

        if not keyring_available():
            warning = QLabel("⚠ " + tr("int.keyring_missing"))
            warning.setStyleSheet(f"color: {theme.WARNING};")
            warning.setWordWrap(True)
            layout.addWidget(warning)

        for provider, (kind, title, fields) in INTEGRATION_FIELDS.items():
            card = Panel(padding=12, spacing=8)
            header = QHBoxLayout()
            name_label = QLabel(f"{title}  ·  {kind}")
            name_label.setObjectName("SectionTitle")
            status_label = QLabel("")
            header.addWidget(name_label)
            header.addStretch(1)
            header.addWidget(status_label)
            card.body().addLayout(header)

            form = QFormLayout()
            inputs: dict[str, QLineEdit] = {}
            for field, label, secret in fields:
                edit = QLineEdit()
                if secret:
                    edit.setEchoMode(QLineEdit.EchoMode.Password)
                form.addRow(label, edit)
                inputs[field] = edit
            card.body().addLayout(form)

            flags = QHBoxLayout()
            enabled_box = QCheckBox(tr("int.enabled"))
            demo_box = QCheckBox(tr("int.use_demo"))
            flags.addWidget(enabled_box)
            flags.addWidget(demo_box)
            flags.addStretch(1)
            save_button = QPushButton(tr("common.save"))
            save_button.setObjectName("Primary")
            save_button.clicked.connect(lambda _c=False, p=provider: self._save_integration(p))
            test_button = QPushButton(tr("int.test"))
            test_button.clicked.connect(lambda _c=False, p=provider: self._test_integration(p))
            flags.addWidget(save_button)
            flags.addWidget(test_button)
            card.body().addLayout(flags)

            self._integration_inputs[provider] = inputs
            self._integration_flags[provider] = (enabled_box, demo_box, status_label)
            layout.addWidget(card)

        layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

    def _load_integrations(self) -> None:
        """Fill the integration cards with the stored (masked) settings."""
        for provider, (_kind, _title, fields) in INTEGRATION_FIELDS.items():
            config = integration_service.get_config(provider)
            credentials = integration_service.load_credentials(provider)
            inputs = self._integration_inputs[provider]
            enabled_box, demo_box, status_label = self._integration_flags[provider]
            for field, _label, secret in fields:
                value = credentials.get(field)
                if value:
                    inputs[field].setPlaceholderText(mask_secret(value) if secret else value)
                    inputs[field].clear()
            enabled_box.setChecked(bool(config.is_enabled) if config else False)
            demo_box.setChecked(bool(config.use_demo) if config else True)
            status = config.status if config else "demo"
            text = integration_status_label(status)
            if config and config.last_sync_at:
                text += f" · {fmt_datetime(config.last_sync_at)}"
            status_label.setText(text)
            status_label.setStyleSheet(f"color: {integration_color(status)}; font-weight: 600;")
            if config and config.last_error:
                status_label.setToolTip(config.last_error)

    def _save_integration(self, provider: str) -> None:
        """Persist the credentials of one provider."""
        if not self.require(Perm.INTEGRATION_MANAGE):
            return
        kind, _title, fields = INTEGRATION_FIELDS[provider]
        inputs = self._integration_inputs[provider]
        enabled_box, demo_box, _status = self._integration_flags[provider]
        existing = integration_service.load_credentials(provider)
        secrets = {}
        for field, _label, _secret in fields:
            typed = inputs[field].text().strip()
            secrets[field] = typed or existing.get(field)
        try:
            integration_service.save_credentials(
                provider,
                kind=kind,
                secrets={k: v for k, v in secrets.items() if v},
                is_enabled=enabled_box.isChecked(),
                use_demo=demo_box.isChecked(),
                actor=self.user,
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self._load_integrations()
        self.context.integrations_updated.emit()
        show_info(self, tr("common.saved"))

    def _test_integration(self, provider: str) -> None:
        """Run the connection test of one provider."""
        result = integration_service.test_connection(provider, actor=self.user)
        if result.ok:
            show_info(self, result.message)
        else:
            show_error(self, result.message)
        self._load_integrations()
        self.context.integrations_updated.emit()

    # ------------------------------------------------------------------ #
    # Data tab
    # ------------------------------------------------------------------ #
    def _build_data(self) -> QWidget:
        """Backup / restore and Excel import / export."""
        panel = Panel(padding=16, spacing=12)
        layout = panel.body()

        backup_title = QLabel(tr("set.backup"))
        backup_title.setObjectName("SectionTitle")
        layout.addWidget(backup_title)
        row = QHBoxLayout()
        self.backup_button = QPushButton(tr("set.create_backup"))
        self.backup_button.setObjectName("Primary")
        self.backup_button.clicked.connect(self._backup)
        self.restore_button = QPushButton(tr("set.restore_backup"))
        self.restore_button.setObjectName("Danger")
        self.restore_button.clicked.connect(self._restore)
        row.addWidget(self.backup_button)
        row.addWidget(self.restore_button)
        row.addStretch(1)
        layout.addLayout(row)
        warning = QLabel(tr("set.restore_warning"))
        warning.setObjectName("Muted")
        layout.addWidget(warning)

        data_title = QLabel(tr("set.data"))
        data_title.setObjectName("SectionTitle")
        layout.addWidget(data_title)
        row2 = QHBoxLayout()
        self.import_button = QPushButton(tr("set.import_leads"))
        self.import_button.clicked.connect(self._import_leads)
        self.export_button = QPushButton(tr("set.export_leads"))
        self.export_button.clicked.connect(self._export_leads)
        row2.addWidget(self.import_button)
        row2.addWidget(self.export_button)
        row2.addStretch(1)
        layout.addLayout(row2)

        path_label = QLabel(f"{tr('common.file')}: {load_config().database_path}")
        path_label.setObjectName("Muted")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        layout.addStretch(1)
        return panel

    def _backup(self) -> None:
        """Create a database backup."""
        path, _ = QFileDialog.getSaveFileName(
            self, tr("set.create_backup"), "leadpilot_backup.db", "SQLite (*.db)"
        )
        if not path:
            return
        try:
            company_service.backup_database(path, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        show_info(self, tr("rep.saved_to", path=path))

    def _restore(self) -> None:
        """Restore the database from a backup."""
        path, _ = QFileDialog.getOpenFileName(self, tr("set.restore_backup"), "", "SQLite (*.db)")
        if not path:
            return
        if not confirm(self, tr("set.restore_warning")):
            return
        try:
            safety = company_service.restore_database(path, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        show_info(self, tr("rep.saved_to", path=safety))

    def _import_leads(self) -> None:
        """Import leads from an Excel workbook."""
        if not self.require(Perm.LEAD_EDIT):
            return
        path, _ = QFileDialog.getOpenFileName(
            self, tr("set.import_leads"), "", "Excel (*.xlsx *.xlsm)"
        )
        if not path:
            return
        try:
            payloads = excel_export.import_leads(path)
        except Exception as exc:
            show_error(self, tr("err.import_failed", detail=str(exc)))
            return
        created = 0
        for payload in payloads:
            try:
                lead_service.create_lead(
                    actor=self.user, company_id=self.user.company_id, **payload
                )
                created += 1
            except Exception:
                logger.exception("Import row failed")
        show_info(self, f"{created} {tr('common.rows')}")
        self.context.leads_updated.emit()

    def _export_leads(self) -> None:
        """Export every lead to Excel."""
        if not self.require(Perm.REPORT_EXPORT):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("set.export_leads"), "leads.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        from app.repositories.lead_repository import LeadFilter

        leads, _ = lead_service.search_leads(
            LeadFilter(include_archived=True), actor=self.user, limit=100000
        )
        try:
            excel_export.export_leads(leads, path)
        except Exception as exc:
            show_error(self, tr("err.export_failed", detail=str(exc)))
            return
        show_info(self, tr("rep.saved_to", path=path))

    # ------------------------------------------------------------------ #
    def reload(self) -> None:
        """Reload every tab."""
        self._load_company()
        self._load_users()
        self._load_services()
        self._load_branches()
        self._load_marketing()
        self._load_tags()
        self._load_integrations()

    def retranslate(self) -> None:
        """Reapply translated captions."""
        super().retranslate()
        for index, key in enumerate(
            [
                "set.company",
                "set.users",
                "set.services",
                "set.branches",
                "set.marketing",
                "set.tags",
                "set.integrations",
                "set.data",
            ]
        ):
            self.tabs.setTabText(index, tr(key))
        self.reload()
