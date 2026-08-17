"""Frameless main window hosting the sidebar, the top bar and the page stack."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME
from app.controllers.app_context import AppContext
from app.services import conversation_service, task_service
from app.ui.dialogs.misc_dialogs import PasswordDialog
from app.ui.i18n import translator
from app.ui.main_window.notification_panel import GlobalSearchDialog, NotificationPanel
from app.ui.main_window.sidebar import Sidebar
from app.ui.main_window.top_bar import TopBar
from app.ui.pages import (
    AIPage,
    AuditPage,
    BookingsPage,
    CallsPage,
    InboxPage,
    KnowledgePage,
    LeadsPage,
    MarketingPage,
    OperatorsPage,
    ReportsPage,
    SettingsPage,
    TasksPage,
)

logger = logging.getLogger(__name__)

PAGE_CLASSES = {
    "inbox": InboxPage,
    "leads": LeadsPage,
    "bookings": BookingsPage,
    "calls": CallsPage,
    "tasks": TasksPage,
    "knowledge": KnowledgePage,
    "ai": AIPage,
    "marketing": MarketingPage,
    "operators": OperatorsPage,
    "reports": ReportsPage,
    "audit": AuditPage,
    "settings": SettingsPage,
}


class MainWindow(QMainWindow):
    """The single window of the application."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.pages: dict[str, QWidget] = {}
        self._logout_requested = False

        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(1200, 720)

        self._build()
        self._connect()
        self._install_shortcuts()

        self._badge_timer = QTimer(self)
        self._badge_timer.setInterval(8000)
        self._badge_timer.timeout.connect(self.refresh_badges)
        self._badge_timer.start()
        self.refresh_badges()

    # ------------------------------------------------------------------ #
    def _build(self) -> None:
        """Assemble the window layout."""
        root = QWidget()
        root.setObjectName("RootWindow")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.top_bar = TopBar(self.context.user)
        outer.addWidget(self.top_bar)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.sidebar = Sidebar(self.context.user)
        content_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)
        outer.addWidget(content, 1)

        for key in self.sidebar.available_keys():
            page_class = PAGE_CLASSES.get(key)
            if page_class is None:
                continue
            page = page_class(self.context)
            self.pages[key] = page
            self.stack.addWidget(page)

        first_key = next(iter(self.pages), None)
        if first_key:
            self.sidebar.select(first_key)
            self.show_page(first_key)

    def _connect(self) -> None:
        """Wire signals between the shell and the context."""
        self.sidebar.page_selected.connect(self.show_page)
        self.top_bar.minimize_requested.connect(self.showMinimized)
        self.top_bar.maximize_requested.connect(self._toggle_maximized)
        self.top_bar.close_requested.connect(self.close)
        self.top_bar.logout_requested.connect(self._logout)
        self.top_bar.search_requested.connect(self.open_global_search)
        self.top_bar.notifications_requested.connect(self.open_notifications)
        self.top_bar.settings_requested.connect(lambda: self.show_page("settings"))
        self.top_bar.password_change_requested.connect(self._change_password)

        self.context.notifications_updated.connect(self.top_bar.refresh_notifications)
        self.context.notifications_updated.connect(self.refresh_badges)
        self.context.inbox_updated.connect(self.refresh_badges)
        self.context.tasks_updated.connect(self.refresh_badges)
        self.context.integrations_updated.connect(self.top_bar.refresh_integrations)
        self.context.open_lead_requested.connect(self._open_lead)
        translator.language_changed.connect(lambda _l: self.top_bar.retranslate())

    def _install_shortcuts(self) -> None:
        """Register the global keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self.open_global_search)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._new_lead)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._send_message)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._send_message)
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self.show_page("inbox"))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self.show_page("leads"))
        QShortcut(QKeySequence("Ctrl+3"), self, activated=lambda: self.show_page("bookings"))
        QShortcut(QKeySequence("F5"), self, activated=self._refresh_current)

    # ------------------------------------------------------------------ #
    def show_page(self, key: str) -> None:
        """Switch the central stack to ``key``."""
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self.sidebar.select(key)
        try:
            page.ensure_loaded()
        except Exception:
            logger.exception("Failed to load page %s", key)

    def refresh_badges(self) -> None:
        """Update the sidebar badges and the top-bar counters."""
        try:
            self.sidebar.set_badge("inbox", conversation_service.total_unread(self.context.user))
            self.sidebar.set_badge("tasks", task_service.open_task_count(self.context.user))
        except Exception:
            logger.exception("Badge refresh failed")
        self.top_bar.refresh_notifications()
        self.top_bar.refresh_integrations()

    def open_global_search(self) -> None:
        """Open the Ctrl+K lead search."""
        dialog = GlobalSearchDialog(self.context.user, self)
        dialog.lead_selected.connect(self._open_lead)
        dialog.move(self.geometry().center() - dialog.rect().center())
        dialog.exec()

    def open_notifications(self) -> None:
        """Open the notification centre popup."""
        panel = NotificationPanel(self.context.user, self)
        panel.lead_requested.connect(self._open_lead)
        top_right = self.mapToGlobal(self.rect().topRight())
        panel.move(top_right.x() - panel.width() - 16, top_right.y() + 56)
        panel.exec()
        self.top_bar.refresh_notifications()

    def _open_lead(self, lead_id: int) -> None:
        """Show a lead in the inbox (or the leads table as a fallback)."""
        inbox = self.pages.get("inbox")
        if inbox is not None:
            self.show_page("inbox")
            inbox.open_lead(lead_id)
            return
        leads = self.pages.get("leads")
        if leads is not None:
            self.show_page("leads")

    def _new_lead(self) -> None:
        """Ctrl+N: create a lead."""
        page = self.pages.get("leads")
        if page is None:
            return
        self.show_page("leads")
        page.create_lead()

    def _send_message(self) -> None:
        """Ctrl+Enter: send the inbox composer content."""
        page = self.pages.get("inbox")
        if page is not None and self.stack.currentWidget() is page:
            page.send_current_message()

    def _refresh_current(self) -> None:
        """F5: reload the current page."""
        current = self.stack.currentWidget()
        if hasattr(current, "reload"):
            try:
                current.reload()
            except Exception:
                logger.exception("Reload failed")

    def _change_password(self) -> None:
        """Open the change-password dialog."""
        PasswordDialog(self.context.user, self).exec()

    def _toggle_maximized(self) -> None:
        """Toggle between maximised and normal geometry."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _logout(self) -> None:
        """Close the window and signal the bootstrap to show the login again."""
        self._logout_requested = True
        self.close()

    @property
    def logout_requested(self) -> bool:
        """Whether the window was closed because the user signed out."""
        return self._logout_requested

    # ------------------------------------------------------------------ #
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt signature
        """Stop background workers before closing."""
        self.context.stop()
        self.context.save_preferences(window_maximized=self.isMaximized())
        super().closeEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt signature
        """Keep the maximise button caption in sync."""
        super().changeEvent(event)
        if hasattr(self, "top_bar"):
            self.top_bar.max_button.setText("❐" if self.isMaximized() else "▢")

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt signature
        """Escape closes popups, not the window."""
        if event.key() == Qt.Key.Key_Escape:
            return
        super().keyPressEvent(event)


def center_on_screen(window: QMainWindow) -> None:
    """Center a window on the primary screen."""
    screen = QApplication.primaryScreen()
    if screen is None:
        return
    geometry = screen.availableGeometry()
    window.resize(int(geometry.width() * 0.9), int(geometry.height() * 0.9))
    window.move(
        geometry.center().x() - window.width() // 2,
        geometry.center().y() - window.height() // 2,
    )
