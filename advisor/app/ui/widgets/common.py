"""Umumiy UI yordamchi widgetlar."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class Card(QFrame):
    """Chegarali, yumaloq burchakli konteyner."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(10)

    def layout(self) -> QVBoxLayout:  # type: ignore[override]
        return self._layout


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        layout.addWidget(title_label)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("PageSubtitle")
            sub.setWordWrap(True)
            layout.addWidget(sub)


class StatTile(Card):
    def __init__(self, label: str, value: str = "—", parent: QWidget | None = None):
        super().__init__(parent)
        self._layout.setSpacing(4)
        self._label = QLabel(label)
        self._label.setObjectName("StatLabel")
        self._value = QLabel(value)
        self._value.setObjectName("StatValue")
        self._layout.addWidget(self._label)
        self._layout.addWidget(self._value)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


def confidence_badge(confidence: float, category: str = "") -> QLabel:
    """Ishonchlilik darajasi belgisi (rangli)."""
    from app.ui.theme.palette import Colors as C

    pct = round(confidence * 100)
    ok = confidence >= 0.6
    color = C.SUCCESS if ok else C.WARNING
    label = QLabel(f"  Ishonch: {pct}%  ")
    label.setStyleSheet(
        f"background-color: {C.BG_ELEVATED}; color: {color}; "
        f"border: 1px solid {color}; border-radius: 10px; padding: 2px 6px; font-size: 11px;"
    )
    if category:
        label.setToolTip(f"Kategoriya: {category}")
    label.setAlignment(Qt.AlignmentFlag.AlignLeft)
    return label


def hline_row(*widgets: QWidget) -> QWidget:
    """Widgetlarni gorizontal joylashtiruvchi konteyner."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    for widget in widgets:
        layout.addWidget(widget)
    return container
