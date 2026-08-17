"""Application context shared by every page.

Holds the signed-in user, the background polling timers and the cross-page
signals used to keep the workspace in sync (a new message must refresh the
inbox badge, the lead table and the notification centre at once).
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QTimer, Signal

from app.config import AppConfig, load_config, save_config
from app.services import integration_service, task_service
from app.services.auth_service import CurrentUser
from app.ui.i18n import translator

logger = logging.getLogger(__name__)


class AppContext(QObject):
    """Runtime state and event bus of the desktop application."""

    #: Emitted whenever new inbound messages were ingested.
    inbox_updated = Signal()
    #: Emitted when a lead changed and tables must be refreshed.
    leads_updated = Signal()
    #: Emitted when notifications changed.
    notifications_updated = Signal()
    #: Emitted when tasks changed.
    tasks_updated = Signal()
    #: Emitted when the user asks to open a lead somewhere else in the app.
    open_lead_requested = Signal(int)
    #: Emitted when integration statuses were refreshed.
    integrations_updated = Signal()

    def __init__(self, user: CurrentUser) -> None:
        super().__init__()
        self.user = user
        self.config: AppConfig = load_config()

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self.config.poll_interval_ms)
        self._poll_timer.timeout.connect(self.poll_channels)

        self._rules_timer = QTimer(self)
        self._rules_timer.setInterval(60_000)
        self._rules_timer.timeout.connect(self.run_rules)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        """Start background polling and the automation rule engine."""
        self._poll_timer.start()
        self._rules_timer.start()
        logger.info("Background workers started (poll=%s ms)", self.config.poll_interval_ms)

    def stop(self) -> None:
        """Stop every background worker."""
        self._poll_timer.stop()
        self._rules_timer.stop()

    # ------------------------------------------------------------------ #
    # Background work
    # ------------------------------------------------------------------ #
    def poll_channels(self) -> None:
        """Pull new messages from every channel adapter."""
        try:
            ingested = integration_service.poll_channels()
        except Exception:
            logger.exception("Channel polling failed")
            return
        if ingested:
            self.inbox_updated.emit()
            self.leads_updated.emit()
            self.notifications_updated.emit()

    def run_rules(self) -> None:
        """Evaluate the follow-up automation rules."""
        try:
            counters = task_service.run_rules()
        except Exception:
            logger.exception("Rule engine failed")
            return
        if any(counters.values()):
            self.tasks_updated.emit()
            self.notifications_updated.emit()

    # ------------------------------------------------------------------ #
    # Preferences
    # ------------------------------------------------------------------ #
    def set_language(self, language: str) -> None:
        """Switch the interface language application-wide."""
        translator.set_language(language)
        self.config = load_config()

    def save_preferences(self, **values: object) -> None:
        """Persist non-secret preferences."""
        for key, value in values.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        save_config(self.config)

    def notify_all(self) -> None:
        """Force every listening page to reload."""
        self.inbox_updated.emit()
        self.leads_updated.emit()
        self.tasks_updated.emit()
        self.notifications_updated.emit()
