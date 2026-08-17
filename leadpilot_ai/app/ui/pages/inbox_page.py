"""Unified Inbox — the central workspace of LeadPilot AI."""

from __future__ import annotations

import logging

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.controllers.app_context import AppContext
from app.models.enums import (
    AIInteractionStatus,
    Channel,
    MessageSender,
    MessageStatus,
)
from app.models.enums import (
    Permission as Perm,
)
from app.repositories.conversation_repository import ConversationFilter
from app.services import (
    ai_agent_service,
    booking_service,
    call_service,
    conversation_service,
    integration_service,
    lead_service,
)
from app.ui.dialogs.booking_dialog import BookingDialog
from app.ui.dialogs.lead_dialog import StatusChangeDialog
from app.ui.i18n import tr
from app.ui.pages.base_page import BasePage
from app.ui.styles import theme
from app.ui.widgets.common import (
    Avatar,
    Badge,
    Card,
    EmptyState,
    FilterChip,
    Panel,
    SearchBox,
    combo,
    confirm,
    show_error,
    show_info,
)
from app.ui.widgets.labels import (
    channel_color,
    channel_items,
    channel_label,
    intent_color,
    intent_label,
    score_color,
    status_color,
    status_label,
)
from app.utils.dates import fmt_datetime, humanize_delta
from app.utils.formatting import initials, pretty_phone, truncate

logger = logging.getLogger(__name__)


class ConversationRow(QWidget):
    """One row of the conversation list."""

    def __init__(self, data: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        self.avatar = Avatar(initials(data["name"]), channel_color(data["channel"]), 36)
        layout.addWidget(self.avatar)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        top = QHBoxLayout()
        top.setSpacing(6)
        name = QLabel(truncate(data["name"], 22))
        name.setStyleSheet("font-weight: 600; font-size: 13px;")
        channel_badge = Badge(channel_label(data["channel"]), channel_color(data["channel"]))
        top.addWidget(name)
        top.addWidget(channel_badge)
        top.addStretch(1)
        time_label = QLabel(data["time"])
        time_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        top.addWidget(time_label)
        text_box.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        preview = QLabel(truncate(data["preview"], 30))
        preview.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px;")
        preview.setMaximumWidth(190)
        bottom.addWidget(preview)
        bottom.addStretch(1)
        if data["score"] >= 70:
            bottom.addWidget(Badge(f"🔥 {data['score']}", theme.DANGER))
        if data["unread"]:
            bottom.addWidget(Badge(str(data["unread"]), theme.ACCENT))
        text_box.addLayout(bottom)

        layout.addLayout(text_box, 1)


class MessageBubble(QFrame):
    """One chat bubble (customer, AI, operator or internal note)."""

    def __init__(self, message, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outgoing = message.sender != MessageSender.CUSTOMER
        if message.is_internal:
            background, border, align = "#3A2C0B", theme.WARNING, Qt.AlignmentFlag.AlignRight
        elif message.sender == MessageSender.AI:
            background, border, align = "#22304A", theme.PURPLE, Qt.AlignmentFlag.AlignRight
        elif outgoing:
            background, border, align = theme.ACCENT_SOFT, theme.ACCENT, Qt.AlignmentFlag.AlignRight
        else:
            background, border, align = theme.PANEL_ALT, theme.BORDER, Qt.AlignmentFlag.AlignLeft
        self.align = align

        self.setStyleSheet(
            f"background: {background}; border: 1px solid {border};"
            f" border-radius: {theme.RADIUS}px;"
        )
        self.setMaximumWidth(560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 8)
        layout.setSpacing(4)

        who = {
            MessageSender.CUSTOMER: "👤",
            MessageSender.AI: "🤖 AI",
            MessageSender.OPERATOR: "🧑‍💼",
            MessageSender.SYSTEM: "⚙",
        }.get(message.sender, "")
        if message.is_internal:
            who = "📝 " + tr("inbox.internal_note")
        header = QLabel(who)
        header.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px; font-weight: 600;")
        layout.addWidget(header)

        body = QLabel(message.body or "")
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(body)

        if message.attachments:
            for attachment in message.attachments:
                chip = QLabel(f"📎 {attachment.file_name}")
                chip.setStyleSheet(f"color: {theme.INFO}; font-size: 11px;")
                layout.addWidget(chip)

        status_map = {
            MessageStatus.SENT: tr("inbox.msg_sent"),
            MessageStatus.DELIVERED: tr("inbox.msg_sent"),
            MessageStatus.READ: tr("inbox.msg_read"),
            MessageStatus.FAILED: tr("inbox.msg_failed"),
        }
        footer_text = fmt_datetime(message.created_at)
        if outgoing and not message.is_internal:
            footer_text += " · " + status_map.get(message.status, "")
        footer = QLabel(footer_text)
        color = theme.DANGER if message.status == MessageStatus.FAILED else theme.TEXT_MUTED
        footer.setStyleSheet(f"color: {color}; font-size: 10px;")
        layout.addWidget(footer)
        if message.error_text:
            error = QLabel(truncate(message.error_text, 90))
            error.setStyleSheet(f"color: {theme.DANGER}; font-size: 10px;")
            error.setWordWrap(True)
            layout.addWidget(error)


class InboxPage(BasePage):
    """Three-column messenger workspace with the AI assistant strip."""

    title_key = "nav.inbox"
    subtitle_key = "app.subtitle"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self.current_conversation_id: int | None = None
        self.current_lead_id: int | None = None
        self.pending_interaction_id: int | None = None
        self._conversations: list[dict] = []
        self._build()
        context.inbox_updated.connect(self._on_inbox_updated)

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    def _build(self) -> None:
        """Assemble the three columns."""
        self.simulate_button = QPushButton(tr("inbox.simulate_new"))
        self.simulate_button.setObjectName("Ghost")
        self.simulate_button.setIcon(theme.icon("fa6s.flask", theme.INFO))
        self.simulate_button.clicked.connect(self._simulate_new_lead)
        self.header().addWidget(self.simulate_button)

        self.refresh_button = QPushButton(tr("common.refresh"))
        self.refresh_button.setObjectName("Ghost")
        self.refresh_button.clicked.connect(self.reload)
        self.header().addWidget(self.refresh_button)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        left = self._build_left()
        center = self._build_center()
        right = self._build_right()
        self._set_composer_enabled(False)
        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([320, 700, 320])
        self.splitter = splitter
        self.body().addWidget(splitter, 1)

    def _build_left(self) -> QWidget:
        """Conversation list with filters."""
        panel = Panel(padding=10, spacing=8)
        layout = panel.body()

        self.search_box = SearchBox(tr("common.search"))
        self.search_box.textChanged.connect(self._debounced_reload)
        layout.addWidget(self.search_box)

        self.channel_box = combo(channel_items())
        self.channel_box.currentIndexChanged.connect(self.reload)
        layout.addWidget(self.channel_box)

        chips = QWidget()
        chip_layout = QHBoxLayout(chips)
        chip_layout.setContentsMargins(0, 0, 0, 0)
        chip_layout.setSpacing(5)
        self.chip_mine = FilterChip(tr("inbox.f_mine"))
        self.chip_waiting = FilterChip(tr("inbox.f_waiting_ai"))
        self.chip_hot = FilterChip(tr("inbox.f_hot"))
        for chip in (self.chip_mine, self.chip_waiting, self.chip_hot):
            chip.clicked.connect(self.reload)
            chip_layout.addWidget(chip)
        chip_layout.addStretch(1)
        layout.addWidget(chips)

        chips2 = QWidget()
        chip2_layout = QHBoxLayout(chips2)
        chip2_layout.setContentsMargins(0, 0, 0, 0)
        chip2_layout.setSpacing(5)
        self.chip_unanswered = FilterChip(tr("inbox.f_unanswered"))
        self.chip_closed = FilterChip(tr("inbox.f_closed"))
        for chip in (self.chip_unanswered, self.chip_closed):
            chip.clicked.connect(self.reload)
            chip2_layout.addWidget(chip)
        chip2_layout.addStretch(1)
        layout.addWidget(chips2)

        self.conversation_list = QListWidget()
        self.conversation_list.setMinimumWidth(280)
        self.conversation_list.currentItemChanged.connect(self._on_conversation_selected)
        layout.addWidget(self.conversation_list, 1)

        self.count_label = QLabel("")
        self.count_label.setObjectName("Muted")
        layout.addWidget(self.count_label)
        return panel

    def _build_center(self) -> QWidget:
        """Chat area, AI strip and composer."""
        panel = Panel(padding=0, spacing=0)
        layout = panel.body()

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 10)
        header_layout.setSpacing(10)
        self.chat_avatar = Avatar("?", theme.ACCENT, 36)
        header_layout.addWidget(self.chat_avatar)
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        self.chat_title = QLabel(tr("inbox.no_conversation"))
        self.chat_title.setObjectName("SectionTitle")
        self.chat_subtitle = QLabel("")
        self.chat_subtitle.setObjectName("Muted")
        title_box.addWidget(self.chat_title)
        title_box.addWidget(self.chat_subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch(1)

        self.channel_badge = Badge("", theme.TEXT_MUTED)
        self.status_badge = Badge("", theme.TEXT_MUTED)
        header_layout.addWidget(self.channel_badge)
        header_layout.addWidget(self.status_badge)

        self.ai_toggle_button = QPushButton(tr("inbox.ai_on"))
        self.ai_toggle_button.setObjectName("Ghost")
        self.ai_toggle_button.clicked.connect(self._toggle_ai)
        header_layout.addWidget(self.ai_toggle_button)

        self.more_button = QPushButton("⋯")
        self.more_button.setObjectName("IconButton")
        self.more_button.setFixedWidth(32)
        self.more_button.clicked.connect(self._show_conversation_menu)
        header_layout.addWidget(self.more_button)
        layout.addWidget(header)

        self.message_search = SearchBox(tr("inbox.search_messages"))
        self.message_search.setMaximumHeight(30)
        self.message_search.textChanged.connect(self._reload_messages)
        search_wrap = QWidget()
        search_layout = QHBoxLayout(search_wrap)
        search_layout.setContentsMargins(14, 0, 14, 6)
        search_layout.addWidget(self.message_search)
        layout.addWidget(search_wrap)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(14, 8, 14, 8)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch(1)
        self.scroll.setWidget(self.messages_container)
        layout.addWidget(self.scroll, 1)

        self.empty_state = EmptyState(tr("inbox.no_conversation"), tr("inbox.no_conversation_hint"))
        layout.addWidget(self.empty_state)
        self.scroll.hide()

        # AI suggestion strip
        self.ai_card = Card(padding=10, spacing=6)
        self.ai_card.setStyleSheet(
            f"background: #22304A; border: 1px solid {theme.PURPLE};"
            f" border-radius: {theme.RADIUS}px;"
        )
        ai_header = QHBoxLayout()
        ai_title = QLabel("🤖 " + tr("inbox.ai_suggestion"))
        ai_title.setStyleSheet(f"color: {theme.PURPLE}; font-weight: 600; font-size: 12px;")
        ai_header.addWidget(ai_title)
        ai_header.addStretch(1)
        self.ai_meta = QLabel("")
        self.ai_meta.setObjectName("Muted")
        ai_header.addWidget(self.ai_meta)
        self.ai_card.body().addLayout(ai_header)

        self.ai_text = QTextEdit()
        self.ai_text.setMaximumHeight(90)
        self.ai_card.body().addWidget(self.ai_text)

        ai_buttons = QHBoxLayout()
        self.ai_send_button = QPushButton(tr("inbox.ai_accept"))
        self.ai_send_button.setObjectName("Primary")
        self.ai_send_button.clicked.connect(self._send_ai_suggestion)
        self.ai_reject_button = QPushButton(tr("inbox.ai_reject"))
        self.ai_reject_button.setObjectName("Ghost")
        self.ai_reject_button.clicked.connect(self._reject_ai_suggestion)
        ai_buttons.addWidget(self.ai_send_button)
        ai_buttons.addWidget(self.ai_reject_button)
        ai_buttons.addStretch(1)
        self.ai_card.body().addLayout(ai_buttons)
        self.ai_card.hide()
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(14, 0, 14, 6)
        wrapper_layout.addWidget(self.ai_card)
        layout.addWidget(wrapper)

        # Composer
        composer = QWidget()
        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(14, 4, 14, 12)
        composer_layout.setSpacing(6)

        # Two compact toolbar rows so nothing is clipped on narrow windows.
        tools_top = QHBoxLayout()
        tools_top.setSpacing(6)
        self.ai_suggest_button = QPushButton(tr("inbox.ai_suggest_short"))
        self.ai_suggest_button.setIcon(theme.icon("fa6s.robot", theme.PURPLE))
        self.ai_suggest_button.setToolTip(tr("inbox.ai_suggest"))
        self.ai_suggest_button.clicked.connect(self._request_ai_suggestion)
        tools_top.addWidget(self.ai_suggest_button)

        self.quick_button = QPushButton(tr("inbox.quick_replies_short"))
        self.quick_button.setToolTip(tr("inbox.quick_replies"))
        self.quick_button.clicked.connect(self._show_quick_replies)
        tools_top.addWidget(self.quick_button)

        self.attach_button = QPushButton("")
        self.attach_button.setIcon(theme.icon("fa6s.paperclip", theme.TEXT_MUTED))
        self.attach_button.setToolTip(tr("inbox.attach"))
        self.attach_button.setFixedWidth(42)
        self.attach_button.clicked.connect(self._pick_attachment)
        tools_top.addWidget(self.attach_button)

        self.note_button = QPushButton(tr("inbox.internal_note_short"))
        self.note_button.setToolTip(tr("inbox.internal_note_hint"))
        self.note_button.clicked.connect(self._add_internal_note)
        tools_top.addWidget(self.note_button)
        tools_top.addStretch(1)
        composer_layout.addLayout(tools_top)

        tools_bottom = QHBoxLayout()
        tools_bottom.setSpacing(6)
        self.escalate_button = QPushButton(tr("inbox.escalate_short"))
        self.escalate_button.setIcon(theme.icon("fa6s.user-tie", theme.WARNING))
        self.escalate_button.setToolTip(tr("inbox.escalate"))
        self.escalate_button.clicked.connect(self._escalate)
        tools_bottom.addWidget(self.escalate_button)

        self.booking_button = QPushButton(tr("inbox.create_booking_short"))
        self.booking_button.setIcon(theme.icon("fa6s.calendar-plus", theme.SUCCESS))
        self.booking_button.setToolTip(tr("inbox.create_booking"))
        self.booking_button.clicked.connect(self._create_booking)
        tools_bottom.addWidget(self.booking_button)

        self.status_button = QPushButton(tr("inbox.change_status_short"))
        self.status_button.setIcon(theme.icon("fa6s.arrow-right-arrow-left", theme.INFO))
        self.status_button.setToolTip(tr("inbox.change_status"))
        self.status_button.clicked.connect(self._change_status)
        tools_bottom.addWidget(self.status_button)
        tools_bottom.addStretch(1)
        composer_layout.addLayout(tools_bottom)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.composer = QPlainTextEdit()
        self.composer.setPlaceholderText(tr("inbox.write_message"))
        self.composer.setMaximumHeight(90)
        input_row.addWidget(self.composer, 1)
        self.send_button = QPushButton(tr("inbox.send"))
        self.send_button.setObjectName("Primary")
        self.send_button.setMinimumHeight(60)
        self.send_button.setMinimumWidth(110)
        self.send_button.clicked.connect(self.send_current_message)
        input_row.addWidget(self.send_button)
        composer_layout.addLayout(input_row)

        self.attachment_label = QLabel("")
        self.attachment_label.setObjectName("Muted")
        composer_layout.addWidget(self.attachment_label)
        self._attachments: list[str] = []

        layout.addWidget(composer)
        return panel

    def _build_right(self) -> QWidget:
        """Lead quick-detail column."""
        panel = Panel(padding=12, spacing=10)
        layout = panel.body()

        title = QLabel(tr("inbox.lead_card"))
        title.setObjectName("SectionTitle")
        self.detail_title = title
        layout.addWidget(title)

        self.lead_name_label = QLabel("—")
        self.lead_name_label.setStyleSheet("font-size: 15px; font-weight: 700;")
        layout.addWidget(self.lead_name_label)

        badges = QHBoxLayout()
        badges.setSpacing(6)
        self.lead_status_badge = Badge("", theme.TEXT_MUTED)
        self.lead_intent_badge = Badge("", theme.TEXT_MUTED)
        self.lead_score_badge = Badge("", theme.INFO)
        badges.addWidget(self.lead_status_badge)
        badges.addWidget(self.lead_intent_badge)
        badges.addWidget(self.lead_score_badge)
        badges.addStretch(1)
        layout.addLayout(badges)

        self.detail_fields = QLabel("")
        self.detail_fields.setWordWrap(True)
        self.detail_fields.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.detail_fields)

        self.call_button = QPushButton(tr("calls.place"))
        self.call_button.setIcon(theme.icon("fa6s.phone", theme.SUCCESS))
        self.call_button.clicked.connect(self._place_call)
        layout.addWidget(self.call_button)

        bookings_title = QLabel(tr("inbox.bookings"))
        bookings_title.setObjectName("SectionTitle")
        self.bookings_title = bookings_title
        layout.addWidget(bookings_title)
        self.bookings_list = QListWidget()
        self.bookings_list.setMaximumHeight(96)
        self.bookings_list.setWordWrap(True)
        layout.addWidget(self.bookings_list)

        activity_title = QLabel(tr("inbox.activity"))
        activity_title.setObjectName("SectionTitle")
        self.activity_title = activity_title
        layout.addWidget(activity_title)
        self.activity_list = QListWidget()
        self.activity_list.setWordWrap(True)
        layout.addWidget(self.activity_list, 1)

        panel.setMinimumWidth(280)
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        return panel

    # ------------------------------------------------------------------ #
    # Data loading
    # ------------------------------------------------------------------ #
    def _debounced_reload(self) -> None:
        """Reload after the user stops typing."""
        QTimer.singleShot(220, self.reload)

    def _current_filter(self) -> ConversationFilter:
        """Build the filter from the current UI state."""
        channel = self.channel_box.currentData()
        return ConversationFilter(
            search=self.search_box.text(),
            channels=[channel] if channel else [],
            only_mine=self.chip_mine.isChecked(),
            only_waiting_ai=self.chip_waiting.isChecked(),
            only_hot=self.chip_hot.isChecked(),
            only_unanswered=self.chip_unanswered.isChecked(),
            only_closed=self.chip_closed.isChecked(),
        )

    def reload(self) -> None:
        """Reload the conversation list, preserving the selection."""
        try:
            conversations = conversation_service.list_conversations(
                self._current_filter(), actor=self.user
            )
        except Exception as exc:
            self.handle_error(exc)
            return

        self._conversations = [
            {
                "id": c.id,
                "lead_id": c.lead_id,
                "name": c.lead.display_name if c.lead else f"#{c.lead_id}",
                "channel": c.channel,
                "preview": c.last_message_preview or "",
                "time": humanize_delta(c.last_message_at),
                "unread": c.unread_count or 0,
                "score": c.lead.score if c.lead else 0,
            }
            for c in conversations
        ]

        self.conversation_list.blockSignals(True)
        self.conversation_list.clear()
        selected_row = -1
        for index, data in enumerate(self._conversations):
            item = QListWidgetItem()
            widget = ConversationRow(data)
            item.setSizeHint(QSize(0, widget.sizeHint().height()))
            item.setData(Qt.ItemDataRole.UserRole, data["id"])
            self.conversation_list.addItem(item)
            self.conversation_list.setItemWidget(item, widget)
            if data["id"] == self.current_conversation_id:
                selected_row = index
        self.conversation_list.blockSignals(False)
        self.count_label.setText(f"{len(self._conversations)} {tr('common.rows')}")

        if selected_row >= 0:
            self.conversation_list.setCurrentRow(selected_row)
            self._reload_messages()
            self._reload_detail()
        elif self.current_conversation_id is not None:
            self._clear_conversation()

    def _on_inbox_updated(self) -> None:
        """React to background polling."""
        self.reload()

    def _on_conversation_selected(self, current: QListWidgetItem | None, _prev) -> None:
        """Load the selected conversation."""
        if current is None:
            return
        self.current_conversation_id = current.data(Qt.ItemDataRole.UserRole)
        conversation = conversation_service.get_conversation(self.current_conversation_id)
        if conversation is None:
            return
        self.current_lead_id = conversation.lead_id
        conversation_service.mark_read(self.current_conversation_id, actor=self.user)
        self._reload_messages()
        self._reload_detail()
        self._set_composer_enabled(True)
        self.ai_card.hide()
        self.pending_interaction_id = None

    def _clear_conversation(self) -> None:
        """Reset the centre and right columns."""
        self.current_conversation_id = None
        self.current_lead_id = None
        self.scroll.hide()
        self.empty_state.show()
        self.chat_title.setText(tr("inbox.no_conversation"))
        self.chat_subtitle.setText("")
        self._set_composer_enabled(False)

    def _reload_messages(self) -> None:
        """Render the message bubbles."""
        if self.current_conversation_id is None:
            return
        messages = conversation_service.messages_of(
            self.current_conversation_id, search=self.message_search.text()
        )
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for message in messages:
            row = QHBoxLayout()
            bubble = MessageBubble(message)
            if bubble.align == Qt.AlignmentFlag.AlignRight:
                row.addStretch(1)
                row.addWidget(bubble)
            else:
                row.addWidget(bubble)
                row.addStretch(1)
            container = QWidget()
            container.setLayout(row)
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, container)

        self.empty_state.setVisible(not messages)
        self.scroll.setVisible(bool(messages))
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        """Scroll the chat to the newest message."""
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _reload_detail(self) -> None:
        """Refresh the right-hand lead card."""
        if self.current_lead_id is None:
            return
        lead = lead_service.get_lead(self.current_lead_id)
        conversation = conversation_service.get_conversation(self.current_conversation_id or 0)
        if lead is None:
            return

        self.chat_title.setText(truncate(lead.display_name, 28))
        self.chat_subtitle.setText(pretty_phone(lead.phone))
        self.chat_avatar.set_data(initials(lead.display_name), channel_color(lead.channel))
        if conversation is not None:
            self.channel_badge.set_state(
                channel_label(conversation.channel), channel_color(conversation.channel)
            )
            self.ai_toggle_button.setText(
                tr("inbox.ai_on") if conversation.ai_enabled else tr("inbox.ai_off")
            )
        self.status_badge.set_state(status_label(lead.status), status_color(lead.status))

        self.lead_name_label.setText(lead.display_name)
        self.lead_status_badge.set_state(status_label(lead.status), status_color(lead.status))
        self.lead_intent_badge.set_state(intent_label(lead.intent), intent_color(lead.intent))
        self.lead_score_badge.set_state(f"{lead.score}/100", score_color(lead.score))

        owner = lead.owner.full_name if lead.owner else tr("common.unassigned")
        service = lead.service.name if lead.service else "—"
        source = lead.source.name if lead.source else (lead.utm_source or "—")
        campaign = lead.campaign.name if lead.campaign else (lead.utm_campaign or "—")
        dnc = (
            f"<br><b style='color:{theme.DANGER}'>⛔ {tr('leads.dnc')}</b>"
            if lead.do_not_contact
            else ""
        )
        self.detail_fields.setText(
            f"<span style='color:{theme.TEXT_MUTED}'>{tr('common.phone')}:</span> {pretty_phone(lead.phone)}<br>"
            f"<span style='color:{theme.TEXT_MUTED}'>{tr('common.language')}:</span> {lead.language}<br>"
            f"<span style='color:{theme.TEXT_MUTED}'>{tr('common.channel')}:</span> {channel_label(lead.channel)}<br>"
            f"<span style='color:{theme.TEXT_MUTED}'>{tr('leads.interest')}:</span> {lead.interest or service}<br>"
            f"<span style='color:{theme.TEXT_MUTED}'>{tr('common.source')}:</span> {source}<br>"
            f"<span style='color:{theme.TEXT_MUTED}'>{tr('common.campaign')}:</span> {campaign}<br>"
            f"<span style='color:{theme.TEXT_MUTED}'>{tr('leads.owner')}:</span> {owner}<br>"
            f"<span style='color:{theme.TEXT_MUTED}'>{tr('inbox.last_action')}:</span> "
            f"{fmt_datetime(lead.last_activity_at)}{dnc}"
        )

        self.bookings_list.clear()
        for booking in booking_service.bookings_for_lead(lead.id)[:5]:
            self.bookings_list.addItem(f"{fmt_datetime(booking.starts_at)} · {booking.status}")

        self.activity_list.clear()
        for activity in reversed(lead_service.timeline(lead.id)[-25:]):
            self.activity_list.addItem(f"{fmt_datetime(activity.created_at)} · {activity.title}")

    def _set_composer_enabled(self, enabled: bool) -> None:
        """Enable or disable every composer control."""
        for widget in (
            self.composer,
            self.send_button,
            self.ai_suggest_button,
            self.quick_button,
            self.attach_button,
            self.note_button,
            self.escalate_button,
            self.booking_button,
            self.status_button,
            self.ai_toggle_button,
            self.call_button,
            self.more_button,
        ):
            widget.setEnabled(enabled)
        if enabled and not self.user.can(Perm.CONVERSATION_REPLY):
            self.composer.setEnabled(False)
            self.send_button.setEnabled(False)

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def send_current_message(self) -> None:
        """Send whatever is in the composer (Ctrl+Enter shortcut target)."""
        if self.current_conversation_id is None:
            return
        text = self.composer.toPlainText().strip()
        if not text and not self._attachments:
            return
        try:
            conversation_service.send_message(
                self.current_conversation_id,
                text,
                actor=self.user,
                attachments=self._attachments or None,
            )
            if self.pending_interaction_id:
                ai_agent_service.mark_interaction(
                    self.pending_interaction_id,
                    AIInteractionStatus.EDITED,
                    actor=self.user,
                    final_reply=text,
                )
                self.pending_interaction_id = None
        except Exception as exc:
            self.handle_error(exc)
            return
        self.composer.clear()
        self._attachments = []
        self.attachment_label.setText("")
        self.ai_card.hide()
        self._reload_messages()
        self._reload_detail()
        self.context.leads_updated.emit()
        self.reload()

    def _request_ai_suggestion(self) -> None:
        """Ask the AI agent for a reply proposal."""
        if self.current_conversation_id is None:
            return
        try:
            result = ai_agent_service.suggest_reply(
                self.current_conversation_id, actor=self.user, auto_send=False
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.pending_interaction_id = result.interaction_id
        self.ai_text.setPlainText(result.text)
        meta = f"{result.provider} · {result.model} · {result.next_state}"
        if result.escalate:
            meta += f" · ⚠ {result.escalation_reason}"
        self.ai_meta.setText(meta)
        self.ai_card.show()
        if result.escalate:
            self._reload_detail()
            self.reload()

    def _send_ai_suggestion(self) -> None:
        """Deliver the AI proposal (possibly edited) to the customer."""
        if self.current_conversation_id is None:
            return
        text = self.ai_text.toPlainText().strip()
        if not text:
            return
        try:
            conversation_service.send_message(
                self.current_conversation_id,
                text,
                actor=self.user,
                sender=MessageSender.AI,
                ai_interaction_id=self.pending_interaction_id,
            )
            if self.pending_interaction_id:
                ai_agent_service.mark_interaction(
                    self.pending_interaction_id,
                    AIInteractionStatus.SENT,
                    actor=self.user,
                    final_reply=text,
                )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.pending_interaction_id = None
        self.ai_card.hide()
        self._reload_messages()
        self.reload()

    def _reject_ai_suggestion(self) -> None:
        """Discard the AI proposal and record the rejection."""
        if self.pending_interaction_id:
            try:
                ai_agent_service.mark_interaction(
                    self.pending_interaction_id, AIInteractionStatus.REJECTED, actor=self.user
                )
            except Exception as exc:
                self.handle_error(exc)
        self.pending_interaction_id = None
        self.ai_card.hide()

    def _show_quick_replies(self) -> None:
        """Insert a canned answer into the composer."""
        replies = conversation_service.list_quick_replies()
        if not replies:
            show_info(self, tr("common.empty"))
            return
        menu = QMenu(self)
        lead = lead_service.get_lead(self.current_lead_id) if self.current_lead_id else None
        language = lead.language if lead and lead.language == "ru" else "uz"
        for reply in replies:
            body = reply.body_ru if language == "ru" and reply.body_ru else reply.body_uz
            menu.addAction(reply.title, lambda b=body: self.composer.setPlainText(b))
        menu.exec(self.quick_button.mapToGlobal(self.quick_button.rect().bottomLeft()))

    def _pick_attachment(self) -> None:
        """Attach one or more files to the next message."""
        paths, _ = QFileDialog.getOpenFileName(self, tr("common.attach"), "", "All files (*.*)")
        if paths:
            self._attachments.append(paths)
            names = ", ".join(p.split("/")[-1].split("\\")[-1] for p in self._attachments)
            self.attachment_label.setText(f"📎 {names}")

    def _add_internal_note(self) -> None:
        """Save the composer content as an internal note."""
        if self.current_conversation_id is None:
            return
        text = self.composer.toPlainText().strip()
        if not text:
            show_info(self, tr("err.message_empty"))
            return
        try:
            conversation_service.add_internal_note(
                self.current_conversation_id, text, actor=self.user
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.composer.clear()
        self._reload_messages()

    def _escalate(self) -> None:
        """Hand the conversation over to a human operator."""
        if self.current_conversation_id is None:
            return
        try:
            conversation_service.escalate(
                self.current_conversation_id, "Operator eskalatsiya qildi", actor=self.user
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self._reload_detail()
        self.reload()
        self.context.notifications_updated.emit()

    def _create_booking(self) -> None:
        """Open the booking dialog for the current lead."""
        if self.current_lead_id is None:
            return
        dialog = BookingDialog(self.user, lead_id=self.current_lead_id, parent=self)
        if dialog.exec():
            self._reload_detail()
            self._reload_messages()
            self.context.leads_updated.emit()

    def _change_status(self) -> None:
        """Open the lead status dialog."""
        if self.current_lead_id is None:
            return
        lead = lead_service.get_lead(self.current_lead_id)
        if lead is None:
            return
        dialog = StatusChangeDialog(self.user, lead.id, lead.status, parent=self)
        if dialog.exec():
            self._reload_detail()
            self.context.leads_updated.emit()
            self.reload()

    def _toggle_ai(self) -> None:
        """Enable or disable the AI for this conversation."""
        if self.current_conversation_id is None:
            return
        conversation = conversation_service.get_conversation(self.current_conversation_id)
        if conversation is None:
            return
        try:
            conversation_service.set_ai_enabled(
                conversation.id, not conversation.ai_enabled, actor=self.user
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self._reload_detail()

    def _place_call(self) -> None:
        """Place a call through the telephony adapter."""
        if self.current_lead_id is None:
            return
        if not confirm(self, tr("calls.place") + "?"):
            return
        try:
            call = call_service.place_call(self.current_lead_id, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        show_info(self, f"{tr('common.result')}: {call.outcome}")
        self._reload_detail()
        self.context.leads_updated.emit()

    def _show_conversation_menu(self) -> None:
        """Context menu with the less frequent conversation actions."""
        if self.current_conversation_id is None:
            return
        menu = QMenu(self)
        menu.addAction(tr("inbox.close_dialog"), self._close_conversation)
        menu.addAction(tr("inbox.export_chat"), self._export_chat)
        menu.addSeparator()
        menu.addAction(tr("inbox.simulate_reply"), self._simulate_reply)
        menu.exec(self.more_button.mapToGlobal(self.more_button.rect().bottomLeft()))

    def _close_conversation(self) -> None:
        """Mark the conversation as closed."""
        if self.current_conversation_id is None:
            return
        try:
            conversation_service.close_conversation(self.current_conversation_id, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.reload()

    def _export_chat(self) -> None:
        """Export the whole dialogue to a text file."""
        if self.current_conversation_id is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("inbox.export_chat"), "chat.txt", "Text (*.txt)"
        )
        if not path:
            return
        messages = conversation_service.messages_of(self.current_conversation_id)
        try:
            with open(path, "w", encoding="utf-8") as handle:
                for message in messages:
                    prefix = "IN " if message.sender == MessageSender.CUSTOMER else "OUT"
                    if message.is_internal:
                        prefix = "NOTE"
                    handle.write(f"[{fmt_datetime(message.created_at)}] {prefix}: {message.body}\n")
        except OSError as exc:
            show_error(self, tr("err.export_failed", detail=str(exc)))
            return
        show_info(self, tr("rep.saved_to", path=path))

    # ------------------------------------------------------------------ #
    # Demo simulation
    # ------------------------------------------------------------------ #
    def _simulate_new_lead(self) -> None:
        """Generate a brand new demo customer on a random channel."""
        adapter = integration_service.demo_channel(Channel.DEMO)
        adapter.simulate_new_lead()
        self.context.poll_channels()
        self.reload()

    def _simulate_reply(self) -> None:
        """Generate a demo follow-up message in the current conversation."""
        if self.current_conversation_id is None:
            return
        conversation = conversation_service.get_conversation(self.current_conversation_id)
        lead = lead_service.get_lead(self.current_lead_id or 0)
        if conversation is None or lead is None:
            return
        adapter = integration_service.demo_channel(conversation.channel)
        adapter.simulate_reply(
            conversation.external_chat_id or str(lead.id),
            conversation.channel,
            lead.language if lead.language in ("uz", "ru") else "uz",
        )
        self.context.poll_channels()
        self.reload()
        self._reload_messages()

    # ------------------------------------------------------------------ #
    def retranslate(self) -> None:
        """Reapply translated captions."""
        super().retranslate()
        self.simulate_button.setText(tr("inbox.simulate_new"))
        self.refresh_button.setText(tr("common.refresh"))
        self.chip_mine.setText(tr("inbox.f_mine"))
        self.chip_waiting.setText(tr("inbox.f_waiting_ai"))
        self.chip_hot.setText(tr("inbox.f_hot"))
        self.chip_unanswered.setText(tr("inbox.f_unanswered"))
        self.chip_closed.setText(tr("inbox.f_closed"))
        self.send_button.setText(tr("inbox.send"))
        self.ai_suggest_button.setText(tr("inbox.ai_suggest_short"))
        self.quick_button.setText(tr("inbox.quick_replies_short"))
        self.attach_button.setToolTip(tr("inbox.attach"))
        self.note_button.setText(tr("inbox.internal_note_short"))
        self.escalate_button.setText(tr("inbox.escalate_short"))
        self.booking_button.setText(tr("inbox.create_booking_short"))
        self.status_button.setText(tr("inbox.change_status_short"))
        self.ai_send_button.setText(tr("inbox.ai_accept"))
        self.ai_reject_button.setText(tr("inbox.ai_reject"))
        self.call_button.setText(tr("calls.place"))
        self.detail_title.setText(tr("inbox.lead_card"))
        self.bookings_title.setText(tr("inbox.bookings"))
        self.activity_title.setText(tr("inbox.activity"))
        self.composer.setPlaceholderText(tr("inbox.write_message"))
        self.empty_state.set_texts(tr("inbox.no_conversation"), tr("inbox.no_conversation_hint"))
        self.reload()

    def open_lead(self, lead_id: int) -> None:
        """Select the conversation belonging to ``lead_id`` if there is one."""
        conversations = conversation_service.conversations_for_lead(lead_id)
        if not conversations:
            return
        target = conversations[0].id
        for index in range(self.conversation_list.count()):
            item = self.conversation_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == target:
                self.conversation_list.setCurrentRow(index)
                return
        self.current_conversation_id = target
        self.reload()
