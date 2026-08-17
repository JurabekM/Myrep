"""Collapsible navigation sidebar."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.enums import Permission as Perm
from app.services.auth_service import CurrentUser
from app.ui.i18n import tr, translator
from app.ui.styles import theme


@dataclass(frozen=True)
class NavItem:
    """One navigation entry."""

    key: str
    label_key: str
    icon_name: str
    permission: str | None = None


NAV_ITEMS: list[NavItem] = [
    NavItem("inbox", "nav.inbox", "fa6s.comments", Perm.CONVERSATION_VIEW),
    NavItem("leads", "nav.leads", "fa6s.users", None),
    NavItem("bookings", "nav.bookings", "fa6s.calendar-check", Perm.BOOKING_MANAGE),
    NavItem("calls", "nav.calls", "fa6s.phone", Perm.CALL_MANAGE),
    NavItem("tasks", "nav.tasks", "fa6s.list-check", Perm.TASK_MANAGE),
    NavItem("knowledge", "nav.knowledge", "fa6s.book", None),
    NavItem("ai", "nav.ai", "fa6s.robot", None),
    NavItem("marketing", "nav.marketing", "fa6s.chart-line", Perm.MARKETING_VIEW),
    NavItem("operators", "nav.operators", "fa6s.user-tie", Perm.OPERATOR_REVIEW),
    NavItem("reports", "nav.reports", "fa6s.file-lines", Perm.REPORT_VIEW),
    NavItem("audit", "nav.audit", "fa6s.shield-halved", Perm.AUDIT_VIEW),
    NavItem("settings", "nav.settings", "fa6s.gear", None),
]


class Sidebar(QWidget):
    """Left navigation column with badges and a collapse toggle."""

    page_selected = Signal(str)

    EXPANDED_WIDTH = 228
    COLLAPSED_WIDTH = 62

    def __init__(self, user: CurrentUser, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.user = user
        self.collapsed = False
        self.buttons: dict[str, QPushButton] = {}
        self.badges: dict[str, QLabel] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._build()
        self.setFixedWidth(self.EXPANDED_WIDTH)
        translator.language_changed.connect(lambda _l: self.retranslate())

    # ------------------------------------------------------------------ #
    def _build(self) -> None:
        """Create the navigation buttons available to the current role."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(4)

        for item in NAV_ITEMS:
            if item.permission and not self.user.can(item.permission):
                continue
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)

            button = QPushButton(tr(item.label_key))
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIcon(theme.icon(item.icon_name, theme.TEXT_MUTED))
            button.setIconSize(QSize(17, 17))
            button.setMinimumHeight(40)
            button.clicked.connect(
                lambda _checked=False, key=item.key: self.page_selected.emit(key)
            )
            self._group.addButton(button)
            self.buttons[item.key] = button

            badge = QLabel("")
            badge.setStyleSheet(
                f"background: {theme.DANGER}; color: white; border-radius: 8px;"
                " padding: 1px 6px; font-size: 10px; font-weight: 700;"
            )
            badge.hide()
            self.badges[item.key] = badge

            row.addWidget(button, 1)
            row.addWidget(badge)
            row.addSpacing(6)
            layout.addWidget(container)

        layout.addStretch(1)

        self.collapse_button = QPushButton()
        self.collapse_button.setObjectName("NavButton")
        self.collapse_button.setIcon(theme.icon("fa6s.bars", theme.TEXT_MUTED))
        self.collapse_button.setIconSize(QSize(16, 16))
        self.collapse_button.setMinimumHeight(36)
        self.collapse_button.clicked.connect(self.toggle)
        layout.addWidget(self.collapse_button)

        self.retranslate()

    # ------------------------------------------------------------------ #
    def toggle(self) -> None:
        """Collapse or expand the sidebar."""
        self.collapsed = not self.collapsed
        self.setFixedWidth(self.COLLAPSED_WIDTH if self.collapsed else self.EXPANDED_WIDTH)
        for item in NAV_ITEMS:
            button = self.buttons.get(item.key)
            if button is None:
                continue
            button.setText("" if self.collapsed else tr(item.label_key))
            button.setToolTip(tr(item.label_key) if self.collapsed else "")
        self.collapse_button.setText("" if self.collapsed else tr("nav.collapse"))

    def select(self, key: str) -> None:
        """Programmatically activate a page button."""
        button = self.buttons.get(key)
        if button is not None:
            button.setChecked(True)

    def set_badge(self, key: str, count: int) -> None:
        """Show a numeric badge next to a navigation entry."""
        badge = self.badges.get(key)
        if badge is None:
            return
        if count > 0:
            badge.setText(str(count if count < 100 else "99+"))
            badge.show()
        else:
            badge.hide()

    def available_keys(self) -> list[str]:
        """Keys of the pages this user may open."""
        return list(self.buttons.keys())

    def retranslate(self) -> None:
        """Reapply translated captions."""
        for item in NAV_ITEMS:
            button = self.buttons.get(item.key)
            if button is None:
                continue
            button.setText("" if self.collapsed else tr(item.label_key))
            button.setToolTip(tr(item.label_key) if self.collapsed else "")
        self.collapse_button.setText("" if self.collapsed else tr("nav.collapse"))
