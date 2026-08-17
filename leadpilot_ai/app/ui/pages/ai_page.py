"""AI sales operator: configuration, scoring rules and quality review."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
    QWidget,
)

from app.controllers.app_context import AppContext
from app.database.engine import session_scope
from app.models.enums import AIErrorCategory, AIInteractionStatus
from app.models.enums import Permission as Perm
from app.services import ai_agent_service, integration_service, lead_service
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
    set_combo_value,
    show_error,
    show_info,
)
from app.ui.widgets.labels import ai_status_items, ai_status_label, tone_items
from app.utils.dates import fmt_datetime, parse_hhmm
from app.utils.formatting import truncate

REVIEW_COLUMNS = [
    "common.date",
    "ai.provider",
    "common.status",
    "ai.state",
    "common.name",
    "inbox.ai_suggestion",
]

SCORING_COLUMNS = ["common.name", "common.count", "kb.keywords", "common.active"]

STATUS_COLORS = {
    AIInteractionStatus.SUGGESTED: theme.INFO,
    AIInteractionStatus.SENT: theme.SUCCESS,
    AIInteractionStatus.EDITED: theme.WARNING,
    AIInteractionStatus.REJECTED: theme.DANGER,
    AIInteractionStatus.ESCALATED: theme.PURPLE,
    AIInteractionStatus.POSITIVE_REPLY: theme.SUCCESS,
}


class AIPage(BasePage):
    """Three tabs: configuration, quality review and scoring rules."""

    title_key = "ai.title"
    subtitle_key = "app.subtitle"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self._build()

    def _build(self) -> None:
        """Assemble the tab widget."""
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_config(), tr("ai.config"))
        self.tabs.addTab(self._build_review(), tr("ai.quality"))
        self.tabs.addTab(self._build_scoring(), tr("ai.scoring"))
        self.body().addWidget(self.tabs, 1)

    # ------------------------------------------------------------------ #
    # Configuration tab
    # ------------------------------------------------------------------ #
    def _build_config(self) -> QWidget:
        """AI profile editor."""
        panel = Panel(padding=16, spacing=12)
        layout = panel.body()

        provider_row = QHBoxLayout()
        self.provider_label = QLabel("")
        self.provider_label.setObjectName("Muted")
        provider_row.addWidget(self.provider_label)
        provider_row.addStretch(1)
        layout.addLayout(provider_row)

        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.enabled_box = QCheckBox(tr("ai.enabled"))
        self.autonomous_box = QCheckBox(tr("ai.autonomous"))
        self.autonomous_box.setToolTip(tr("ai.autonomous_hint"))
        self.agent_name_input = QLineEdit()
        self.tone_box = combo(tone_items())
        self.languages_input = QLineEdit()
        self.work_start = QTimeEdit()
        self.work_start.setDisplayFormat("HH:mm")
        self.work_end = QTimeEdit()
        self.work_end.setDisplayFormat("HH:mm")
        self.max_messages = QSpinBox()
        self.max_messages.setRange(1, 50)
        self.escalate_negative = QCheckBox(tr("ai.esc_negative"))
        self.escalate_price = QCheckBox(tr("ai.esc_price"))
        self.escalate_human = QCheckBox(tr("ai.esc_human"))
        self.escalate_unanswered = QSpinBox()
        self.escalate_unanswered.setRange(1, 10)
        self.escalate_score = QSpinBox()
        self.escalate_score.setRange(0, 100)
        self.booking_fields = QLineEdit()
        self.forbidden_input = QTextEdit()
        self.forbidden_input.setMaximumHeight(60)
        self.signature_input = QLineEdit()
        self.night_send = QCheckBox(tr("ai.night_send"))

        form.addRow("", self.enabled_box)
        form.addRow("", self.autonomous_box)
        form.addRow(tr("ai.agent_name"), self.agent_name_input)
        form.addRow(tr("ai.tone"), self.tone_box)
        form.addRow(tr("common.language"), self.languages_input)
        form.addRow(tr("ai.work_hours") + " " + tr("common.from"), self.work_start)
        form.addRow(tr("ai.work_hours") + " " + tr("common.to"), self.work_end)
        form.addRow(tr("ai.max_messages"), self.max_messages)
        form.addRow(tr("ai.escalation"), self.escalate_negative)
        form.addRow("", self.escalate_price)
        form.addRow("", self.escalate_human)
        form.addRow(tr("ai.esc_unanswered"), self.escalate_unanswered)
        form.addRow(tr("ai.esc_score"), self.escalate_score)
        form.addRow(tr("ai.booking_fields"), self.booking_fields)
        form.addRow(tr("ai.forbidden"), self.forbidden_input)
        form.addRow(tr("ai.signature"), self.signature_input)
        form.addRow("", self.night_send)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.save_button = QPushButton(tr("common.save"))
        self.save_button.setObjectName("Primary")
        self.save_button.clicked.connect(self._save_profile)
        self.test_button = QPushButton(tr("int.test"))
        self.test_button.clicked.connect(self._test_provider)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.test_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addStretch(1)
        return panel

    def _load_profile(self) -> None:
        """Fill the configuration form from the database."""
        profile = ai_agent_service.get_profile()
        self.enabled_box.setChecked(profile.is_enabled)
        self.autonomous_box.setChecked(profile.autonomous)
        self.agent_name_input.setText(profile.agent_name)
        set_combo_value(self.tone_box, profile.tone)
        self.languages_input.setText(profile.languages)
        start = parse_hhmm(profile.work_start)
        end = parse_hhmm(profile.work_end)
        self.work_start.setTime(QTime(start.hour, start.minute))
        self.work_end.setTime(QTime(end.hour, end.minute))
        self.max_messages.setValue(profile.max_auto_messages)
        self.escalate_negative.setChecked(profile.escalate_on_negative)
        self.escalate_price.setChecked(profile.escalate_on_price_negotiation)
        self.escalate_human.setChecked(profile.escalate_on_human_request)
        self.escalate_unanswered.setValue(profile.escalate_after_unanswered)
        self.escalate_score.setValue(profile.escalate_score_threshold)
        self.booking_fields.setText(profile.booking_required_fields)
        self.forbidden_input.setPlainText(profile.forbidden_topics)
        self.signature_input.setText(profile.signature)
        self.night_send.setChecked(profile.night_send_allowed)

        provider = integration_service.llm_provider()
        self.provider_label.setText(
            f"{tr('ai.provider')}: {provider.title} "
            f"({tr('istatus.demo') if provider.is_demo else tr('istatus.connected')})"
        )

    def _save_profile(self) -> None:
        """Persist the AI configuration."""
        if not self.require(Perm.AI_CONFIGURE):
            return
        try:
            ai_agent_service.save_profile(
                actor=self.user,
                is_enabled=self.enabled_box.isChecked(),
                autonomous=self.autonomous_box.isChecked(),
                agent_name=self.agent_name_input.text().strip() or "AI",
                tone=self.tone_box.currentData(),
                languages=self.languages_input.text().strip() or "uz,ru",
                work_start=self.work_start.time().toString("HH:mm"),
                work_end=self.work_end.time().toString("HH:mm"),
                max_auto_messages=self.max_messages.value(),
                escalate_on_negative=self.escalate_negative.isChecked(),
                escalate_on_price_negotiation=self.escalate_price.isChecked(),
                escalate_on_human_request=self.escalate_human.isChecked(),
                escalate_after_unanswered=self.escalate_unanswered.value(),
                escalate_score_threshold=self.escalate_score.value(),
                booking_required_fields=self.booking_fields.text().strip(),
                forbidden_topics=self.forbidden_input.toPlainText(),
                signature=self.signature_input.text().strip(),
                night_send_allowed=self.night_send.isChecked(),
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        show_info(self, tr("common.saved"))

    def _test_provider(self) -> None:
        """Run a connection test against the LLM provider."""
        result = integration_service.test_connection("openai_compatible", actor=self.user)
        if result.ok:
            show_info(self, result.message)
        else:
            show_error(self, result.message)
        self._load_profile()
        self.context.integrations_updated.emit()

    # ------------------------------------------------------------------ #
    # Quality review tab
    # ------------------------------------------------------------------ #
    def _build_review(self) -> QWidget:
        """AI answer review worksheet."""
        panel = Panel(padding=10, spacing=8)
        layout = panel.body()

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.tile_total = MetricTile(tr("common.total"), "0", theme.TEXT)
        self.tile_sent = MetricTile(tr("ai.sent"), "0", theme.SUCCESS)
        self.tile_edited = MetricTile(tr("ai.edited"), "0", theme.WARNING)
        self.tile_rejected = MetricTile(tr("ai.rejected"), "0", theme.DANGER)
        self.tile_escalated = MetricTile(tr("ai.escalated"), "0", theme.PURPLE)
        self.tile_useful = MetricTile(tr("ai.review_useful"), "0%", theme.ACCENT)
        for tile in (
            self.tile_total,
            self.tile_sent,
            self.tile_edited,
            self.tile_rejected,
            self.tile_escalated,
            self.tile_useful,
        ):
            metrics.addWidget(tile)
        metrics.addStretch(1)
        layout.addLayout(metrics)

        row = QHBoxLayout()
        self.review_search = SearchBox(tr("common.search"))
        self.review_search.textChanged.connect(self._reload_review)
        row.addWidget(self.review_search, 2)
        self.review_status_box = combo(ai_status_items())
        self.review_status_box.currentIndexChanged.connect(self._reload_review)
        row.addWidget(self.review_status_box)
        self.chip_unreviewed = FilterChip(tr("ai.quality"))
        self.chip_unreviewed.clicked.connect(self._reload_review)
        row.addWidget(self.chip_unreviewed)
        row.addStretch(1)
        layout.addLayout(row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.review_table = DataTable([tr(key) for key in REVIEW_COLUMNS], stretch_column=5)
        self.review_table.itemSelectionChanged.connect(self._on_review_selected)
        self.review_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.review_table.customContextMenuRequested.connect(self._show_review_menu)
        splitter.addWidget(self.review_table)

        detail = Panel(padding=12, spacing=8)
        self.review_detail = QTextEdit()
        self.review_detail.setReadOnly(True)
        detail.body().addWidget(self.review_detail, 1)
        buttons = QHBoxLayout()
        self.useful_button = QPushButton("👍 " + tr("ai.review_useful"))
        self.useful_button.setObjectName("Success")
        self.useful_button.clicked.connect(lambda: self._review(True, ""))
        self.wrong_button = QPushButton("👎 " + tr("ai.review_wrong"))
        self.wrong_button.setObjectName("Danger")
        self.wrong_button.clicked.connect(self._review_wrong_menu)
        buttons.addWidget(self.useful_button)
        buttons.addWidget(self.wrong_button)
        buttons.addStretch(1)
        detail.body().addLayout(buttons)
        detail.setMinimumWidth(320)
        splitter.addWidget(detail)
        splitter.setSizes([820, 340])
        layout.addWidget(splitter, 1)
        return panel

    def _reload_review(self) -> None:
        """Reload the AI interaction table and its metrics."""
        status = self.review_status_box.currentData()
        try:
            interactions = ai_agent_service.list_interactions(
                search=self.review_search.text(),
                statuses=[status] if status else None,
                only_unreviewed=self.chip_unreviewed.isChecked(),
            )
            summary = ai_agent_service.quality_summary()
        except Exception as exc:
            self.handle_error(exc)
            return

        rows = []
        ids = []
        for item in interactions:
            ids.append(item.id)
            lead = lead_service.get_lead(item.lead_id)
            rows.append(
                [
                    fmt_datetime(item.created_at),
                    f"{item.provider}",
                    colored_item(
                        ai_status_label(item.status),
                        STATUS_COLORS.get(item.status, theme.TEXT_MUTED),
                        bold=True,
                    ),
                    item.state_after,
                    lead.display_name if lead else "—",
                    truncate(item.suggested_reply, 80),
                ]
            )
        self.review_table.fill(rows, ids=ids)
        self.tile_total.set_value(f"{int(summary['total'])}")
        self.tile_sent.set_value(f"{int(summary['sent'])}")
        self.tile_edited.set_value(f"{int(summary['edited'])}")
        self.tile_rejected.set_value(f"{int(summary['rejected'])}")
        self.tile_escalated.set_value(f"{int(summary['escalated'])}")
        self.tile_useful.set_value(f"{summary['useful_ratio']:.0f}%")

    def _on_review_selected(self) -> None:
        """Show the full dialogue turn of the selected AI answer."""
        interaction_id = self.review_table.selected_id()
        if interaction_id is None:
            return
        for item in ai_agent_service.list_interactions(limit=400):
            if item.id != interaction_id:
                continue
            self.review_detail.setPlainText(
                f"{tr('common.date')}: {fmt_datetime(item.created_at)}\n"
                f"{tr('ai.provider')}: {item.provider} / {item.model}\n"
                f"{tr('ai.state')}: {item.state_before} → {item.state_after}\n"
                f"{tr('common.status')}: {ai_status_label(item.status)}\n"
                f"{tr('ai.escalation')}: {item.escalation_reason or '—'}\n"
                f"\n— {tr('common.name')} —\n{item.customer_message}\n"
                f"\n— {tr('inbox.ai_suggestion')} —\n{item.suggested_reply}\n"
                f"\n— {tr('inbox.send')} —\n{item.final_reply or '—'}\n"
                f"\n{tr('common.comment')}: {item.review_comment or '—'}"
            )
            return

    def _show_review_menu(self, position) -> None:
        """Context menu for review actions."""
        menu = QMenu(self)
        menu.addAction(tr("ai.review_useful"), lambda: self._review(True, ""))
        wrong_menu = menu.addMenu(tr("ai.review_wrong"))
        for category in AIErrorCategory:
            wrong_menu.addAction(
                tr(f"ai.err_{category.value}"),
                lambda _c=False, cat=category.value: self._review(False, cat),
            )
        menu.exec(self.review_table.viewport().mapToGlobal(position))

    def _review_wrong_menu(self) -> None:
        """Pick an error category for a negative review."""
        menu = QMenu(self)
        for category in AIErrorCategory:
            menu.addAction(
                tr(f"ai.err_{category.value}"),
                lambda _c=False, cat=category.value: self._review(False, cat),
            )
        menu.exec(self.wrong_button.mapToGlobal(self.wrong_button.rect().bottomLeft()))

    def _review(self, useful: bool, category: str) -> None:
        """Store the manager's verdict."""
        interaction_id = self.review_table.selected_id()
        if interaction_id is None:
            show_error(self, tr("err.select_row"))
            return
        try:
            ai_agent_service.review_interaction(
                interaction_id, actor=self.user, useful=useful, category=category
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self._reload_review()

    # ------------------------------------------------------------------ #
    # Scoring tab
    # ------------------------------------------------------------------ #
    def _build_scoring(self) -> QWidget:
        """Scoring rule editor."""
        panel = Panel(padding=10, spacing=8)
        layout = panel.body()
        hint = QLabel(tr("ai.scoring"))
        hint.setObjectName("SectionTitle")
        layout.addWidget(hint)
        self.scoring_table = DataTable([tr(key) for key in SCORING_COLUMNS], stretch_column=0)
        self.scoring_table.doubleClicked.connect(self._edit_rule)
        layout.addWidget(self.scoring_table, 1)

        row = QHBoxLayout()
        self.points_input = QSpinBox()
        self.points_input.setRange(-100, 100)
        self.apply_points_button = QPushButton(tr("common.apply"))
        self.apply_points_button.setObjectName("Primary")
        self.apply_points_button.clicked.connect(self._edit_rule)
        row.addWidget(QLabel(tr("common.score")))
        row.addWidget(self.points_input)
        row.addWidget(self.apply_points_button)
        row.addStretch(1)
        layout.addLayout(row)
        return panel

    def _reload_scoring(self) -> None:
        """Reload the scoring rules table."""
        with session_scope() as session:
            rules = lead_service.load_scoring_rules(session)
            rows = []
            ids = []
            for rule in rules:
                ids.append(rule.id)
                rows.append(
                    [
                        rule.title_uz,
                        colored_item(
                            f"{rule.points:+d}",
                            theme.SUCCESS if rule.points > 0 else theme.DANGER,
                            bold=True,
                        ),
                        truncate(f"{rule.keywords_uz} {rule.keywords_ru}", 60),
                        tr("common.yes") if rule.is_active else tr("common.no"),
                    ]
                )
        self.scoring_table.fill(rows, ids=ids)

    def _edit_rule(self) -> None:
        """Apply the points value to the selected scoring rule."""
        if not self.require(Perm.AI_CONFIGURE):
            return
        rule_id = self.scoring_table.selected_id()
        if rule_id is None:
            show_error(self, tr("err.select_row"))
            return
        from app.models.intelligence import ScoringRule

        with session_scope() as session:
            rule = session.get(ScoringRule, rule_id)
            if rule is None:
                return
            rule.points = self.points_input.value()
        self._reload_scoring()
        show_info(self, tr("common.saved"))

    # ------------------------------------------------------------------ #
    def reload(self) -> None:
        """Reload every tab."""
        self._load_profile()
        self._reload_review()
        self._reload_scoring()

    def retranslate(self) -> None:
        """Reapply translated captions."""
        super().retranslate()
        self.tabs.setTabText(0, tr("ai.config"))
        self.tabs.setTabText(1, tr("ai.quality"))
        self.tabs.setTabText(2, tr("ai.scoring"))
        self.save_button.setText(tr("common.save"))
        self.test_button.setText(tr("int.test"))
        self.review_table.set_headers([tr(key) for key in REVIEW_COLUMNS])
        self.scoring_table.set_headers([tr(key) for key in SCORING_COLUMNS])
        self.reload()
