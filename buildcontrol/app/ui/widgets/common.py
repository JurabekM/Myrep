"""Small reusable presentation widgets (badges, cards, toasts, headers)."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.styles.theme import COLORS, RADIUS_SM, SPACING, SPACING_SM, status_colors
from app.ui.widgets.icons import icon
from app.utils.i18n import tr


class Badge(QLabel):
    """Small pill showing a status with semantic coloring."""

    def __init__(
        self, text: str = "", kind: str = "neutral", parent: QWidget | None = None
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("Badge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_kind(kind)

    def set_kind(self, kind: str) -> None:
        """Recolor the badge according to a semantic ``kind``."""
        fg, bg = status_colors(kind)
        self.setStyleSheet(f"#Badge {{ color: {fg}; background: {bg}; }}")


class Card(QFrame):
    """Rounded surface container with an optional title."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(SPACING, SPACING, SPACING, SPACING)
        self._layout.setSpacing(SPACING_SM)
        self.title_label: QLabel | None = None
        if title:
            self.title_label = QLabel(title)
            self.title_label.setObjectName("CardTitle")
            self._layout.addWidget(self.title_label)

    def body(self) -> QVBoxLayout:
        """Return the card's content layout."""
        return self._layout

    def add(self, widget: QWidget, stretch: int = 0) -> QWidget:
        """Append a widget to the card body."""
        self._layout.addWidget(widget, stretch)
        return widget


class MetricCard(Card):
    """KPI tile: caption, big value and an optional hint line."""

    def __init__(
        self,
        title: str,
        value: str = "—",
        hint: str = "",
        kind: str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, parent)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("CardValue")
        self.value_label.setWordWrap(True)
        self.value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._layout.addWidget(self.value_label)
        self.hint_label = QLabel(hint)
        self.hint_label.setObjectName("CardHint")
        self.hint_label.setWordWrap(True)
        self._layout.addWidget(self.hint_label)
        self._layout.addStretch(1)
        self.setMinimumWidth(180)
        self.set_kind(kind)

    def set_kind(self, kind: str) -> None:
        """Color the value according to a semantic ``kind``."""
        fg, _ = status_colors(kind)
        color = COLORS.text if kind == "neutral" else fg
        self.value_label.setStyleSheet(f"color: {color};")

    def update_values(self, value: str, hint: str = "", kind: str | None = None) -> None:
        """Refresh the tile content."""
        self.value_label.setText(value)
        self.hint_label.setText(hint)
        self.hint_label.setVisible(bool(hint))
        if kind:
            self.set_kind(kind)


class SectionHeader(QWidget):
    """Title + subtitle + right-aligned action slot."""

    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("PageTitle")
        texts.addWidget(self.title_label)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("PageSubtitle")
        self.subtitle_label.setVisible(bool(subtitle))
        texts.addWidget(self.subtitle_label)
        layout.addLayout(texts)
        layout.addStretch(1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(SPACING_SM)
        layout.addLayout(self.actions)

    def add_action(self, widget: QWidget) -> QWidget:
        """Append a widget to the right-hand action area."""
        self.actions.addWidget(widget)
        return widget

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.setText(text)
        self.subtitle_label.setVisible(bool(text))


class SearchBox(QLineEdit):
    """Line edit pre-configured as a search field."""

    def __init__(self, placeholder: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SearchBox")
        self.setPlaceholderText(placeholder or tr("search_ph"))
        self.setClearButtonEnabled(True)
        self.addAction(icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        self.setMinimumWidth(220)


class Separator(QFrame):
    """Thin horizontal rule."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Separator")
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class EmptyState(QWidget):
    """Centered placeholder shown when a view has no data."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel(text or tr("no_data"))
        self.label.setObjectName("EmptyState")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

    def set_text(self, text: str) -> None:
        self.label.setText(text)


class ProgressBadge(QWidget):
    """Slim progress indicator used inside tables and cards."""

    def __init__(self, value: float = 0.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = value
        self.setMinimumHeight(18)

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(100.0, float(value or 0.0)))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(0, 5, -1, -5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLORS.bg_alt))
        painter.drawRoundedRect(rect, 4, 4)
        if self._value > 0:
            filled = rect.adjusted(0, 0, -int(rect.width() * (1 - self._value / 100.0)), 0)
            color = (
                COLORS.success
                if self._value >= 100
                else (COLORS.accent if self._value >= 50 else COLORS.warning)
            )
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(filled, 4, 4)
        painter.setPen(QPen(QColor(COLORS.text_muted)))
        font = QFont(painter.font())
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self._value:.0f}%")
        painter.end()
        del event


class BudgetBar(QWidget):
    """Horizontal budget usage bar with a threshold marker."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ratio = 0.0
        self.setMinimumHeight(14)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_ratio(self, ratio: float) -> None:
        """Set the used share of the budget (1.0 == fully used)."""
        self._ratio = max(0.0, float(ratio or 0.0))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(0, 3, -1, -3)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLORS.bg_alt))
        painter.drawRoundedRect(rect, RADIUS_SM // 2, RADIUS_SM // 2)
        share = min(1.0, self._ratio)
        if share > 0:
            width = int(rect.width() * share)
            color = (
                COLORS.danger
                if self._ratio > 1.0
                else (COLORS.warning if self._ratio >= 0.9 else COLORS.success)
            )
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(
                rect.adjusted(0, 0, -(rect.width() - width), 0), RADIUS_SM // 2, RADIUS_SM // 2
            )
        painter.end()
        del event


class Toast(QFrame):
    """Transient message shown in the corner of a page."""

    def __init__(self, parent: QWidget, text: str, kind: str = "info", timeout: int = 3200) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(SPACING_SM)
        fg, _ = status_colors(kind)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {fg}; font-size: 14px;")
        layout.addWidget(dot)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setMaximumWidth(360)
        layout.addWidget(label)
        self.adjustSize()
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(220)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        QTimer.singleShot(timeout, self._fade_out)

    def _fade_out(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()

    def show_at_corner(self) -> None:
        """Position the toast in the bottom-right corner of its parent."""
        parent = self.parentWidget()
        if parent is not None:
            self.move(
                max(10, parent.width() - self.width() - 24),
                max(10, parent.height() - self.height() - 24),
            )
        self.show()
        self.raise_()
        self._anim.start()


def toast(parent: QWidget, text: str, kind: str = "info") -> Toast:
    """Show a transient message on ``parent`` and return the widget."""
    widget = Toast(parent, text, kind)
    widget.show_at_corner()
    return widget


def button(
    text: str,
    icon_name: str = "",
    variant: str = "",
    tooltip: str = "",
    parent: QWidget | None = None,
) -> QPushButton:
    """Create a themed push button.

    ``variant`` maps to the QSS object names: ``Primary``, ``Danger``,
    ``Success``, ``Ghost``, ``LinkButton`` — empty means the default surface.
    """
    btn = QPushButton(text, parent)
    if variant:
        btn.setObjectName(variant)
    if icon_name:
        tint = {
            "Primary": "#FFFFFF",
            "Danger": COLORS.danger,
            "Success": COLORS.success,
        }.get(variant, COLORS.text_muted)
        btn.setIcon(icon(icon_name, tint))
    if tooltip:
        btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def field_label(text: str, required: bool = False) -> QLabel:
    """Create a form field caption."""
    label = QLabel(f"{text} *" if required else text)
    label.setObjectName("FieldLabel")
    return label
