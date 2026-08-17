"""AI Chat sahifasi — jonli oqim (streaming) bilan."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.container import Container
from app.ui.widgets.chat_bubble import ChatBubble
from app.ui.widgets.common import PageHeader
from app.ui.widgets.workers import StreamChatRunnable

_MODULES = [
    ("Umumiy", "chat", False),
    ("Huquq (lex.uz)", "legal", True),
    ("Soliq", "tax", False),
    ("Marketing", "marketing", False),
]


class ChatPage(QWidget):
    def __init__(self, container: Container, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._pool = QThreadPool.globalInstance()
        self._conversation_id: int | None = None
        self._current_bubble: ChatBubble | None = None
        self._busy = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(PageHeader("AI Chat", "Biznesingiz haqida savol bering"))
        header.addStretch(1)
        self._module_box = QComboBox()
        for label, _, _ in _MODULES:
            self._module_box.addItem(label)
        self._module_box.setFixedWidth(180)
        header.addWidget(self._module_box)
        new_btn = QPushButton("Yangi suhbat")
        new_btn.clicked.connect(self._new_conversation)
        header.addWidget(new_btn)
        root.addLayout(header)

        # Xabarlar ro'yxati (scroll)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._messages_container = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._messages_layout.setSpacing(6)
        self._scroll.setWidget(self._messages_container)
        root.addWidget(self._scroll, stretch=1)

        self._placeholder = QLabel(
            "Strategiya, soliq, marketing yoki huquq bo'yicha savolingizni yozing…"
        )
        self._placeholder.setObjectName("Muted")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._messages_layout.addWidget(self._placeholder)

        # Kiritish paneli
        input_row = QHBoxLayout()
        self._input = QTextEdit()
        self._input.setPlaceholderText("Xabar yozing… (Ctrl+Enter — yuborish)")
        self._input.setFixedHeight(72)
        input_row.addWidget(self._input, stretch=1)
        self._send_btn = QPushButton("Yuborish")
        self._send_btn.setObjectName("Primary")
        self._send_btn.setFixedWidth(120)
        self._send_btn.clicked.connect(self._send)
        input_row.addWidget(self._send_btn)
        root.addLayout(input_row)

        # Ctrl+Enter yuborish
        self._input.installEventFilter(self)

    # --------------------------------------------------------------- events

    def eventFilter(self, obj, event):  # type: ignore[no-untyped-def]
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent

        if obj is self._input and event.type() == QEvent.Type.KeyPress:
            key_event: QKeyEvent = event  # type: ignore[assignment]
            if key_event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (
                key_event.modifiers() & Qt.KeyboardModifier.ControlModifier
            ):
                self._send()
                return True
        return super().eventFilter(obj, event)

    # ---------------------------------------------------------------- logic

    def _new_conversation(self) -> None:
        self._conversation_id = None
        self._clear_messages()

    def _clear_messages(self) -> None:
        while self._messages_layout.count():
            item = self._messages_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _add_bubble(self, role: str, text: str = "") -> ChatBubble:
        if self._placeholder is not None:
            self._placeholder.deleteLater()
            self._placeholder = None
        bubble = ChatBubble(role)
        bubble.set_text(text)
        self._messages_layout.addWidget(bubble)
        self._scroll_to_bottom()
        return bubble

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _send(self) -> None:
        if self._busy:
            return
        content = self._input.toPlainText().strip()
        if not content:
            return
        self._input.clear()
        _, module, use_rag = _MODULES[self._module_box.currentIndex()]

        self._add_bubble("user", content)
        self._current_bubble = self._add_bubble("assistant", "")
        self._set_busy(True)

        def chat_call(on_token, on_provider):  # type: ignore[no-untyped-def]
            return self._container.chat_service.send_stream(
                self._conversation_id, content, module=module, use_rag=use_rag,
                on_token=on_token, on_provider=on_provider,
            )

        runnable = StreamChatRunnable(chat_call)
        runnable.signals.token.connect(self._on_token)
        runnable.signals.finished.connect(self._on_finished)
        runnable.signals.error.connect(self._on_error)
        self._pool.start(runnable)

    def _on_token(self, piece: str) -> None:
        if self._current_bubble is not None:
            self._current_bubble.append_text(piece)
            self._scroll_to_bottom()

    def _on_finished(self, result) -> None:  # type: ignore[no-untyped-def]
        self._conversation_id = result.conversation_id
        assistant = result.assistant_message
        if self._current_bubble is not None:
            self._current_bubble.set_text(assistant.content)
            if assistant.sources:
                self._current_bubble.add_sources(assistant.sources)
            if assistant.confidence is not None:
                self._current_bubble.add_confidence(
                    assistant.confidence, assistant.category or ""
                )
        self._set_busy(False)

    def _on_error(self, message: str) -> None:
        if self._current_bubble is not None:
            self._current_bubble.set_text(f"⚠️ Xatolik: {message}")
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._send_btn.setEnabled(not busy)
        self._send_btn.setText("Yozilmoqda…" if busy else "Yuborish")
