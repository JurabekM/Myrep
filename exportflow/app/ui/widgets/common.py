"""Small reusable widgets: badges, cards, headers, toasts and form fields."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Iterable

from PySide6.QtCore import QDate, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.ui.i18n import t, te
from app.ui.styles.theme import COLORS, status_colors
from app.utils.formatting import fmt_date, parse_date


class StatusBadge(QLabel):
    """Rounded pill showing a translated status value."""

    def __init__(self, group: str = "", value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setContentsMargins(0, 0, 0, 0)
        self._group = group
        self.set_status(group, value)

    def set_status(self, group: str, value: str | None, text: str | None = None) -> None:
        """Update the badge text and colours."""
        self._group = group
        fg, bg = status_colors(value)
        self.setText(text if text is not None else te(group, value))
        self.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 9px;"
            f"padding: 3px 10px; font-size: 11px; font-weight: 600;"
        )


class Card(QFrame):
    """Surface container with the standard border and radius."""

    def __init__(self, parent: QWidget | None = None, spacing: int = 10, margins: int = 14) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(margins, margins, margins, margins)
        self.layout_.setSpacing(spacing)

    def add(self, widget: QWidget) -> QWidget:
        """Append a widget to the card layout."""
        self.layout_.addWidget(widget)
        return widget


class StatCard(QFrame):
    """Compact metric tile used on the workspace page."""

    clicked = Signal()

    def __init__(
        self, label: str, value: str = "0", accent: str = "accent", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(2)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("StatValue")
        self.value_label.setStyleSheet(f"color: {COLORS.get(accent, COLORS['accent'])};")
        self.text_label = QLabel(label)
        self.text_label.setObjectName("StatLabel")
        self.text_label.setWordWrap(True)
        layout.addWidget(self.value_label)
        layout.addWidget(self.text_label)
        self.setMinimumWidth(150)

    def set_value(self, value: str) -> None:
        """Update the displayed metric."""
        self.value_label.setText(value)

    def set_label(self, label: str) -> None:
        """Update the metric caption."""
        self.text_label.setText(label)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Emit ``clicked`` so the tile can act as a navigation shortcut."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class PageHeader(QWidget):
    """Title, subtitle and a right-aligned action area."""

    def __init__(self, title: str = "", subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("PageTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("PageSubtitle")
        text_box.addWidget(self.title_label)
        text_box.addWidget(self.subtitle_label)
        layout.addLayout(text_box)
        layout.addStretch(1)

        self.actions = QHBoxLayout()
        self.actions.setSpacing(8)
        layout.addLayout(self.actions)

    def set_texts(self, title: str, subtitle: str = "") -> None:
        """Update the header labels (used when the language changes)."""
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))

    def add_action(self, widget: QWidget) -> QWidget:
        """Append a button to the header action area."""
        self.actions.addWidget(widget)
        return widget


class Toast(QLabel):
    """Transient message shown at the bottom of the main window."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setVisible(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._animation = QPropertyAnimation(self._effect, b"opacity", self)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)

    def show_message(self, message: str, level: str = "info", msec: int = 3800) -> None:
        """Display a message with a level-specific colour."""
        colors = {
            "info": (COLORS["accent_soft"], "#FFFFFF"),
            "success": (COLORS["success_soft"], "#BBF7D0"),
            "warning": (COLORS["warning_soft"], "#FDE68A"),
            "error": (COLORS["danger_soft"], "#FECACA"),
        }
        bg, fg = colors.get(level, colors["info"])
        self.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 9px;"
            f"padding: 10px 18px; font-weight: 500;"
        )
        self.setText(message)
        self.adjustSize()
        self.reposition()
        self.setVisible(True)
        self.raise_()
        self._effect.setOpacity(1.0)
        self._timer.start(msec)

    def reposition(self) -> None:
        """Center the toast near the bottom of its parent."""
        parent = self.parentWidget()
        if parent is None:
            return
        self.move(
            max(12, (parent.width() - self.width()) // 2),
            max(12, parent.height() - self.height() - 26),
        )

    def _fade_out(self) -> None:
        self._animation.stop()
        self._animation.setDuration(420)
        self._animation.setStartValue(1.0)
        self._animation.setEndValue(0.0)
        self._animation.finished.connect(self._hide_once)
        self._animation.start()

    def _hide_once(self) -> None:
        try:
            self._animation.finished.disconnect(self._hide_once)
        except (RuntimeError, TypeError):  # pragma: no cover - already disconnected
            pass
        self.setVisible(False)


# --------------------------------------------------------------- form fields
def label(text: str, muted: bool = True) -> QLabel:
    """Create a form label."""
    widget = QLabel(text)
    if muted:
        widget.setObjectName("Muted")
    return widget


def line_edit(placeholder: str = "", text: str = "") -> QLineEdit:
    """Create a single-line text input."""
    widget = QLineEdit()
    widget.setPlaceholderText(placeholder)
    widget.setText(text or "")
    return widget


def text_area(placeholder: str = "", text: str = "", height: int = 90) -> QPlainTextEdit:
    """Create a multi-line text input."""
    widget = QPlainTextEdit()
    widget.setPlaceholderText(placeholder)
    widget.setPlainText(text or "")
    widget.setMinimumHeight(height)
    return widget


def spin(
    minimum: float = 0, maximum: float = 1e12, value: float = 0, decimals: int = 2
) -> QDoubleSpinBox:
    """Create a numeric input."""
    widget = QDoubleSpinBox()
    widget.setRange(minimum, maximum)
    widget.setDecimals(decimals)
    widget.setValue(float(value or 0))
    widget.setGroupSeparatorShown(True)
    widget.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
    return widget


def int_spin(minimum: int = 0, maximum: int = 1_000_000, value: int = 0) -> QSpinBox:
    """Create an integer input."""
    widget = QSpinBox()
    widget.setRange(minimum, maximum)
    widget.setValue(int(value or 0))
    return widget


def date_edit(value: dt.date | None = None, allow_empty: bool = True) -> QDateEdit:
    """Create a date input honouring the dd.MM.yyyy display format."""
    widget = QDateEdit()
    widget.setDisplayFormat("dd.MM.yyyy")
    widget.setCalendarPopup(True)
    widget.setSpecialValueText(" " if allow_empty else "")
    widget.setMinimumDate(QDate(2000, 1, 1))
    if value:
        widget.setDate(QDate(value.year, value.month, value.day))
    elif allow_empty:
        widget.setDate(widget.minimumDate())
    else:
        today = dt.date.today()
        widget.setDate(QDate(today.year, today.month, today.day))
    return widget


def date_value(widget: QDateEdit) -> dt.date | None:
    """Read a date input, treating the minimum date as "empty"."""
    if widget.date() == widget.minimumDate():
        return None
    return widget.date().toPython()


def set_date(widget: QDateEdit, value: dt.date | str | None) -> None:
    """Write a date into a date input."""
    if isinstance(value, str):
        value = parse_date(value)
    if value:
        widget.setDate(QDate(value.year, value.month, value.day))
    else:
        widget.setDate(widget.minimumDate())


def combo(
    items: Iterable[tuple[str, str]] | Iterable[str],
    current: str | None = None,
    with_empty: bool = False,
    empty_label: str | None = None,
) -> QComboBox:
    """Create a combo box from ``(value, label)`` pairs or plain values."""
    widget = QComboBox()
    if with_empty:
        widget.addItem(empty_label if empty_label is not None else t("common.all"), None)
    for item in items:
        if isinstance(item, tuple):
            widget.addItem(str(item[1]), item[0])
        else:
            widget.addItem(str(item), item)
    if current is not None:
        index = widget.findData(current)
        if index >= 0:
            widget.setCurrentIndex(index)
    return widget


def enum_combo(
    group: str,
    values: Iterable[str],
    current: str | None = None,
    with_empty: bool = False,
) -> QComboBox:
    """Combo box populated with translated enum labels."""
    return combo([(value, te(group, value)) for value in values], current, with_empty)


def combo_value(widget: QComboBox) -> object:
    """Read the data payload of the selected combo item."""
    return widget.currentData()


def set_combo(widget: QComboBox, value: object) -> None:
    """Select the combo item carrying ``value``."""
    index = widget.findData(value)
    widget.setCurrentIndex(index if index >= 0 else 0)


def checkbox(text: str, checked: bool = False) -> QCheckBox:
    """Create a checkbox."""
    widget = QCheckBox(text)
    widget.setChecked(bool(checked))
    return widget


def button(
    text: str,
    on_click: Callable[[], None] | None = None,
    kind: str = "",
    enabled: bool = True,
    tooltip: str = "",
) -> QPushButton:
    """Create a themed push button."""
    widget = QPushButton(text)
    if kind:
        widget.setObjectName(kind)
    if on_click is not None:
        widget.clicked.connect(lambda: on_click())
    widget.setEnabled(enabled)
    if tooltip:
        widget.setToolTip(tooltip)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


def separator() -> QFrame:
    """Thin horizontal rule."""
    line = QFrame()
    line.setObjectName("Separator")
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    return line


def section_title(text: str) -> QLabel:
    """Bold section caption."""
    widget = QLabel(text)
    widget.setObjectName("SectionTitle")
    return widget


def banner(text: str, level: str = "info") -> QLabel:
    """Coloured information banner."""
    widget = QLabel(text)
    widget.setObjectName(
        {"info": "Banner", "warning": "BannerWarning", "error": "BannerDanger"}.get(level, "Banner")
    )
    widget.setWordWrap(True)
    return widget


def key_value_row(key: str, value: str) -> QWidget:
    """Two-column key/value row used in detail panels."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 2, 0, 2)
    layout.setSpacing(10)
    key_label = QLabel(key)
    key_label.setObjectName("DetailKey")
    key_label.setMinimumWidth(126)
    key_label.setMaximumWidth(180)
    key_label.setWordWrap(True)
    key_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    value_label = QLabel(str(value) if value not in (None, "") else "—")
    value_label.setObjectName("DetailValue")
    value_label.setWordWrap(True)
    value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    value_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout.addWidget(key_label)
    layout.addWidget(value_label, 1)
    return row


def big_number(text: str, color: str = "text") -> QLabel:
    """Large emphasised number used in summary strips."""
    widget = QLabel(text)
    font = QFont()
    font.setPointSize(15)
    font.setBold(True)
    widget.setFont(font)
    widget.setStyleSheet(f"color: {COLORS.get(color, color)};")
    return widget


def format_date_cell(value) -> str:
    """Format a date-like value for a table cell."""
    if isinstance(value, dt.datetime):
        return fmt_date(value.date())
    if isinstance(value, dt.date):
        return fmt_date(value)
    return str(value or "")
