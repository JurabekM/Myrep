"""Collapsible right-hand detail panel shared by every record page."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.i18n import t
from app.ui.widgets.common import StatusBadge, button, key_value_row, separator


class DetailPanel(QWidget):
    """Right-hand panel showing the selected record with tabs and actions."""

    closed = Signal()

    def __init__(self, parent: QWidget | None = None, width: int = 380) -> None:
        super().__init__(parent)
        self.setObjectName("DetailPanel")
        self.setMinimumWidth(300)
        self.setMaximumWidth(560)
        self.resize(width, self.height())

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        self.title = QLabel("")
        self.title.setObjectName("DetailTitle")
        self.title.setWordWrap(True)
        self.badge = StatusBadge()
        self.badge.setVisible(False)
        close_button = button("✕", self._on_close, "Ghost")
        close_button.setFixedWidth(34)
        close_button.setToolTip(t("common.close"))
        header.addWidget(self.title, 1)
        header.addWidget(self.badge)
        header.addWidget(close_button)
        root.addLayout(header)

        self.subtitle = QLabel("")
        self.subtitle.setObjectName("Muted")
        self.subtitle.setWordWrap(True)
        root.addWidget(self.subtitle)

        self.actions = QHBoxLayout()
        self.actions.setSpacing(6)
        root.addLayout(self.actions)
        root.addWidget(separator())

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        root.addWidget(self.tabs, 1)

        self.placeholder = QLabel(t("common.no_data"))
        self.placeholder.setObjectName("Hint")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setWordWrap(True)
        root.addWidget(self.placeholder)
        self.set_empty()

    # ------------------------------------------------------------ content
    def set_empty(self, message: str | None = None) -> None:
        """Show the empty-state message."""
        self.title.setText("")
        self.subtitle.setText("")
        self.badge.setVisible(False)
        self.tabs.setVisible(False)
        self.clear_actions()
        self.placeholder.setText(message or t("common.no_data"))
        self.placeholder.setVisible(True)

    def set_header(
        self, title: str, subtitle: str = "", status_group: str = "", status: str = ""
    ) -> None:
        """Fill the panel header."""
        self.placeholder.setVisible(False)
        self.tabs.setVisible(True)
        self.title.setText(title)
        self.subtitle.setText(subtitle)
        self.subtitle.setVisible(bool(subtitle))
        if status:
            self.badge.set_status(status_group, status)
            self.badge.setVisible(True)
        else:
            self.badge.setVisible(False)

    def clear_tabs(self) -> None:
        """Remove every tab."""
        while self.tabs.count():
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            widget.deleteLater()

    def clear_actions(self) -> None:
        """Remove every action button."""
        while self.actions.count():
            item = self.actions.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def add_action(
        self, text: str, on_click: Callable[[], None], kind: str = "", enabled: bool = True
    ):
        """Append an action button under the header."""
        widget = button(text, on_click, kind, enabled)
        self.actions.addWidget(widget)
        return widget

    def add_tab(self, title: str, widget: QWidget) -> QWidget:
        """Append a tab wrapped in a scroll area."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(widget)
        self.tabs.addTab(scroll, title)
        return widget

    def add_fields_tab(self, title: str, rows: list[tuple[str, str]]) -> QWidget:
        """Append a tab built from key/value pairs."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 6, 2, 6)
        layout.setSpacing(2)
        for key, value in rows:
            layout.addWidget(key_value_row(key, value))
        layout.addStretch(1)
        return self.add_tab(title, container)

    def add_list_tab(self, title: str, lines: list[str], empty_text: str = "") -> QWidget:
        """Append a tab containing a simple text list."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 6, 2, 6)
        layout.setSpacing(4)
        if not lines:
            hint = QLabel(empty_text or t("common.no_data"))
            hint.setObjectName("Hint")
            hint.setWordWrap(True)
            layout.addWidget(hint)
        for line in lines:
            item = QLabel(line)
            item.setWordWrap(True)
            item.setObjectName("Muted")
            item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            layout.addWidget(item)
        layout.addStretch(1)
        return self.add_tab(title, container)

    def _on_close(self) -> None:
        self.setVisible(False)
        self.closed.emit()
