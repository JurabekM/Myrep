"""Notification centre and global search overlays."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.enums import NotificationLevel
from app.repositories.lead_repository import LeadFilter
from app.services import lead_service, notification_service
from app.services.auth_service import CurrentUser
from app.ui.i18n import tr
from app.ui.styles import theme
from app.utils.dates import fmt_datetime, humanize_delta
from app.utils.formatting import pretty_phone, truncate

LEVEL_COLORS = {
    NotificationLevel.INFO: theme.INFO,
    NotificationLevel.SUCCESS: theme.SUCCESS,
    NotificationLevel.WARNING: theme.WARNING,
    NotificationLevel.CRITICAL: theme.DANGER,
}


class NotificationPanel(QDialog):
    """Popup listing the notification centre entries."""

    lead_requested = Signal(int)

    def __init__(self, user: CurrentUser, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.user = user
        self.setWindowFlags(Qt.WindowType.Popup)
        self.setMinimumSize(420, 480)
        self.setObjectName("RootWindow")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel(tr("topbar.notifications"))
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.mark_button = QPushButton(tr("common.apply"))
        self.mark_button.setObjectName("Ghost")
        self.mark_button.clicked.connect(self._mark_all)
        header.addWidget(self.mark_button)
        layout.addLayout(header)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._open_lead)
        layout.addWidget(self.list, 1)
        self.reload()

    def reload(self) -> None:
        """Reload the notifications."""
        self.list.clear()
        for notification in notification_service.list_notifications(user_id=self.user.id):
            color = LEVEL_COLORS.get(notification.level, theme.TEXT_MUTED)
            prefix = "●" if not notification.is_read else "○"
            item = QListWidgetItem(
                f"{prefix} {notification.title}\n    {truncate(notification.body, 70)}"
                f"  ·  {humanize_delta(notification.created_at)}"
            )
            item.setForeground(Qt.GlobalColor.white)
            item.setData(Qt.ItemDataRole.UserRole, notification.lead_id)
            item.setToolTip(fmt_datetime(notification.created_at))
            from PySide6.QtGui import QColor

            item.setForeground(QColor(color if not notification.is_read else theme.TEXT_MUTED))
            self.list.addItem(item)

    def _mark_all(self) -> None:
        """Mark everything as read."""
        notification_service.mark_all_read(self.user.id)
        self.reload()

    def _open_lead(self, item: QListWidgetItem) -> None:
        """Jump to the lead referenced by the notification."""
        lead_id = item.data(Qt.ItemDataRole.UserRole)
        if lead_id:
            self.lead_requested.emit(int(lead_id))
            self.close()


class GlobalSearchDialog(QDialog):
    """Ctrl+K quick lead search."""

    lead_selected = Signal(int)

    def __init__(self, user: CurrentUser, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.user = user
        self.setWindowFlags(Qt.WindowType.Popup)
        self.setMinimumSize(560, 420)
        self.setObjectName("RootWindow")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        self.input = QLineEdit()
        self.input.setPlaceholderText(tr("topbar.global_search"))
        self.input.setMinimumHeight(40)
        self.input.textChanged.connect(self.reload)
        self.input.returnPressed.connect(self._accept_current)
        layout.addWidget(self.input)

        self.results = QListWidget()
        self.results.itemDoubleClicked.connect(lambda _i: self._accept_current())
        layout.addWidget(self.results, 1)
        self.reload()
        self.input.setFocus()

    def reload(self) -> None:
        """Search leads matching the query."""
        query = self.input.text().strip()
        self.results.clear()
        leads, _ = lead_service.search_leads(
            LeadFilter(search=query), actor=self.user, limit=30, offset=0
        )
        for lead in leads:
            item = QListWidgetItem(
                f"{lead.display_name}  ·  {pretty_phone(lead.phone)}  ·  {lead.status}"
            )
            item.setData(Qt.ItemDataRole.UserRole, lead.id)
            self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)

    def _accept_current(self) -> None:
        """Emit the selected lead id."""
        item = self.results.currentItem()
        if item is None:
            return
        self.lead_selected.emit(int(item.data(Qt.ItemDataRole.UserRole)))
        self.close()
