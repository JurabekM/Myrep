"""Chat xabar pufakchasi (foydalanuvchi / AI)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.theme.palette import Colors as C
from app.ui.widgets.common import confidence_badge
from app.ui.widgets.markdown_view import MarkdownView


class ChatBubble(QWidget):
    def __init__(self, role: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._role = role
        self._raw = ""

        outer = QHBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        bubble = QWidget()
        bubble.setObjectName("Bubble")
        color = C.BUBBLE_USER if role == "user" else C.BUBBLE_ASSISTANT
        bubble.setStyleSheet(
            f"#Bubble {{ background-color: {color}; border: 1px solid {C.BORDER}; "
            f"border-radius: 12px; }}"
        )
        self._inner = QVBoxLayout(bubble)
        self._inner.setContentsMargins(12, 8, 12, 8)
        self._inner.setSpacing(4)

        self._view = MarkdownView()
        self._view.setMinimumWidth(360)
        self._inner.addWidget(self._view)

        bubble.setMaximumWidth(720)
        if role == "user":
            outer.addStretch(1)
            outer.addWidget(bubble)
        else:
            outer.addWidget(bubble)
            outer.addStretch(1)

    def set_text(self, text: str) -> None:
        self._raw = text
        self._view.set_markdown(text or "…")

    def append_text(self, piece: str) -> None:
        self._raw += piece
        self._view.set_markdown(self._raw)

    def text(self) -> str:
        return self._raw

    def add_confidence(self, confidence: float, category: str = "") -> None:
        if self._role == "assistant":
            self._inner.addWidget(confidence_badge(confidence, category))

    def add_sources(self, sources: list[dict]) -> None:
        if not sources:
            return
        lines = ["**Manbalar:**"]
        for i, s in enumerate(sources, start=1):
            title = s.get("title", "Manba")
            article = f", {s['article']}" if s.get("article") else ""
            lines.append(f"[{i}] {title}{article}")
        label = QLabel("\n".join(lines))
        label.setObjectName("Muted")
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.MarkdownText)
        label.setStyleSheet(f"color: {C.TEXT_MUTED}; font-size: 11px;")
        self._inner.addWidget(label)
