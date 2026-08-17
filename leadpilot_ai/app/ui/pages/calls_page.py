"""Calls worksheet with transcript and AI call analysis."""

from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextEdit,
    QWidget,
)

from app.controllers.app_context import AppContext
from app.models.enums import Permission as Perm
from app.services import auth_service, call_service
from app.ui.dialogs.misc_dialogs import CallLogDialog
from app.ui.i18n import tr
from app.ui.pages.base_page import BasePage
from app.ui.styles import theme
from app.ui.widgets.common import (
    DataTable,
    MetricTile,
    Panel,
    SearchBox,
    colored_item,
    combo,
    show_error,
    show_info,
)
from app.ui.widgets.labels import (
    outcome_items,
    outcome_label,
    sentiment_color,
    sentiment_items,
    sentiment_label,
)
from app.utils.dates import fmt_datetime
from app.utils.formatting import fmt_duration, pretty_phone

COLUMNS = [
    "common.date",
    "common.name",
    "common.phone",
    "calls.direction",
    "common.duration",
    "common.result",
    "common.operator",
    "calls.quality",
    "calls.sentiment",
]

OUTCOME_COLORS = {
    "no_answer": theme.TEXT_MUTED,
    "callback": theme.WARNING,
    "interested": theme.INFO,
    "booked": theme.SUCCESS,
    "too_expensive": theme.WARNING,
    "wrong_number": theme.TEXT_DISABLED,
    "sold": theme.SUCCESS,
    "refused": theme.DANGER,
}


class CallsPage(BasePage):
    """Call register plus the analysis drawer."""

    title_key = "calls.title"
    subtitle_key = "app.subtitle"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self._build()

    def _build(self) -> None:
        """Assemble the toolbar, table and detail drawer."""
        self.log_button = QPushButton(tr("calls.log"))
        self.log_button.setObjectName("Primary")
        self.log_button.clicked.connect(self._log_call)
        self.header().addWidget(self.log_button)

        self.transcribe_button = QPushButton(tr("calls.transcribe"))
        self.transcribe_button.clicked.connect(self._transcribe)
        self.header().addWidget(self.transcribe_button)

        self.analyze_button = QPushButton(tr("calls.analyze"))
        self.analyze_button.clicked.connect(self._analyze)
        self.header().addWidget(self.analyze_button)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.tile_total = MetricTile(tr("nav.calls"), "0", theme.TEXT)
        self.tile_booked = MetricTile(tr("outcome.booked"), "0", theme.SUCCESS)
        self.tile_no_answer = MetricTile(tr("outcome.no_answer"), "0", theme.TEXT_MUTED)
        self.tile_negative = MetricTile(tr("sentiment.negative"), "0", theme.DANGER)
        self.tile_quality = MetricTile(tr("calls.quality"), "0", theme.ACCENT)
        for tile in (
            self.tile_total,
            self.tile_booked,
            self.tile_no_answer,
            self.tile_negative,
            self.tile_quality,
        ):
            metrics.addWidget(tile)
        metrics.addStretch(1)
        self.body().addLayout(metrics)

        filters = Panel(padding=10, spacing=8)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.search_box = SearchBox(tr("common.search"))
        self.search_box.textChanged.connect(self.reload)
        row.addWidget(self.search_box, 2)

        self.outcome_box = combo(outcome_items())
        self.outcome_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.outcome_box)

        self.sentiment_box = combo(sentiment_items())
        self.sentiment_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.sentiment_box)

        operators = auth_service.list_operators()
        self.operator_box = combo(
            [(tr("common.all"), None)] + [(u.full_name, u.id) for u in operators]
        )
        self.operator_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.operator_box)

        from PySide6.QtWidgets import QDateEdit

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
        splitter.setChildrenCollapsible(False)

        table_panel = Panel(padding=8, spacing=6)
        self.table = DataTable([tr(key) for key in COLUMNS], stretch_column=1)
        self.table.itemSelectionChanged.connect(self._on_selection)
        table_panel.body().addWidget(self.table, 1)
        splitter.addWidget(table_panel)

        detail = Panel(padding=12, spacing=8)
        self.detail_title = QLabel(tr("calls.analysis"))
        self.detail_title.setObjectName("SectionTitle")
        detail.body().addWidget(self.detail_title)
        self.analysis_label = QLabel("—")
        self.analysis_label.setWordWrap(True)
        self.analysis_label.setTextFormat(Qt.TextFormat.RichText)
        detail.body().addWidget(self.analysis_label)
        self.transcript_title = QLabel(tr("calls.transcript"))
        self.transcript_title.setObjectName("SectionTitle")
        detail.body().addWidget(self.transcript_title)
        self.transcript_view = QTextEdit()
        self.transcript_view.setReadOnly(True)
        detail.body().addWidget(self.transcript_view, 1)
        detail.setMinimumWidth(340)
        splitter.addWidget(detail)
        splitter.setSizes([880, 340])
        self.body().addWidget(splitter, 1)

    # ------------------------------------------------------------------ #
    def reload(self) -> None:
        """Reload the call table."""
        outcome = self.outcome_box.currentData()
        try:
            calls = call_service.list_calls(
                actor=self.user,
                search=self.search_box.text(),
                outcomes=[outcome] if outcome else None,
                operator_id=self.operator_box.currentData(),
                sentiment=self.sentiment_box.currentData() or "",
                date_from=self.date_from.date().toPython(),
                date_to=self.date_to.date().toPython(),
            )
        except Exception as exc:
            self.handle_error(exc)
            return

        rows = []
        ids = []
        booked = no_answer = negative = 0
        quality_values = []
        for call in calls:
            ids.append(call.id)
            analysis = call.analysis
            if call.outcome == "booked":
                booked += 1
            if call.outcome == "no_answer":
                no_answer += 1
            if analysis is not None:
                if analysis.sentiment == "negative":
                    negative += 1
                quality_values.append(analysis.quality_score)
            rows.append(
                [
                    fmt_datetime(call.started_at),
                    call.lead.display_name if call.lead else "—",
                    pretty_phone(call.phone),
                    tr(f"calls.{call.direction}"),
                    fmt_duration(call.duration_seconds),
                    colored_item(
                        outcome_label(call.outcome),
                        OUTCOME_COLORS.get(call.outcome, theme.TEXT_MUTED),
                        bold=True,
                    ),
                    call.operator.full_name if call.operator else "—",
                    str(analysis.quality_score) if analysis else "—",
                    colored_item(
                        sentiment_label(analysis.sentiment) if analysis else "—",
                        sentiment_color(analysis.sentiment) if analysis else theme.TEXT_MUTED,
                    ),
                ]
            )
        self.table.fill(rows, ids=ids)
        self.tile_total.set_value(str(len(calls)))
        self.tile_booked.set_value(str(booked))
        self.tile_no_answer.set_value(str(no_answer))
        self.tile_negative.set_value(str(negative))
        self.tile_quality.set_value(
            f"{sum(quality_values) / len(quality_values):.0f}" if quality_values else "—"
        )

    def _on_selection(self) -> None:
        """Show the transcript and the analysis of the selected call."""
        call_id = self.table.selected_id()
        if call_id is None:
            return
        call, transcript, analysis = call_service.get_call_detail(call_id)
        if call is None:
            return
        self.transcript_view.setPlainText(transcript.text if transcript else "—")
        if analysis is None:
            self.analysis_label.setText("—")
            return
        muted = theme.TEXT_MUTED
        self.analysis_label.setText(
            f"<b>{tr('calls.summary')}:</b> {analysis.summary}<br><br>"
            f"<span style='color:{muted}'>{tr('calls.need')}:</span> {analysis.customer_need}<br>"
            f"<span style='color:{muted}'>{tr('calls.objections')}:</span> {analysis.objections}<br>"
            f"<span style='color:{muted}'>{tr('calls.mistakes')}:</span> {analysis.operator_mistakes}<br>"
            f"<span style='color:{muted}'>{tr('calls.next_step')}:</span> "
            f"<b>{analysis.next_best_action}</b><br>"
            f"<span style='color:{muted}'>{tr('calls.quality')}:</span> {analysis.quality_score}/100<br>"
            f"<span style='color:{muted}'>{tr('calls.sentiment')}:</span> "
            f"<span style='color:{sentiment_color(analysis.sentiment)}'>"
            f"{sentiment_label(analysis.sentiment)}</span><br><br>"
            f"{'✅' if analysis.got_phone else '❌'} {tr('calls.got_phone')}<br>"
            f"{'✅' if analysis.got_purpose else '❌'} {tr('calls.got_purpose')}<br>"
            f"{'✅' if analysis.got_booking else '❌'} {tr('calls.got_booking')}"
        )

    def _log_call(self) -> None:
        """Register a manual call for the first open lead."""
        if not self.require(Perm.CALL_MANAGE):
            return
        from app.repositories.lead_repository import LeadFilter
        from app.services import lead_service

        leads, _ = lead_service.search_leads(LeadFilter(only_open=True), actor=self.user, limit=1)
        if not leads:
            show_error(self, tr("err.lead_not_found"))
            return
        dialog = CallLogDialog(self.user, leads[0].id, parent=self)
        if dialog.exec():
            self.reload()
            self.context.leads_updated.emit()

    def _transcribe(self) -> None:
        """Run speech-to-text on the selected call."""
        call_id = self.table.selected_id()
        if call_id is None:
            show_error(self, tr("err.select_row"))
            return
        try:
            call_service.transcribe_call(call_id, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        self._on_selection()
        show_info(self, tr("common.success"))

    def _analyze(self) -> None:
        """Analyse the transcript of the selected call."""
        call_id = self.table.selected_id()
        if call_id is None:
            show_error(self, tr("err.select_row"))
            return
        try:
            call_service.analyze_call(call_id)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.reload()
        self._on_selection()
        self.context.notifications_updated.emit()

    def retranslate(self) -> None:
        """Reapply translated captions."""
        super().retranslate()
        self.log_button.setText(tr("calls.log"))
        self.transcribe_button.setText(tr("calls.transcribe"))
        self.analyze_button.setText(tr("calls.analyze"))
        self.detail_title.setText(tr("calls.analysis"))
        self.transcript_title.setText(tr("calls.transcript"))
        self.table.set_headers([tr(key) for key in COLUMNS])
        self.reload()
