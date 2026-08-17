"""Custom window title bar: branding, integration status, user menu, controls."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_VERSION
from app.services import integration_service, notification_service
from app.services.auth_service import CurrentUser
from app.ui.i18n import tr, translator
from app.ui.styles import theme
from app.ui.widgets.common import Avatar, Badge
from app.ui.widgets.labels import integration_color, integration_status_label
from app.utils.formatting import initials


class IntegrationDot(QWidget):
    """One coloured dot with the provider name, shown in the top bar."""

    def __init__(self, provider: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.provider = provider
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {theme.TEXT_DISABLED}; font-size: 12px;")
        self.name = QLabel(provider.replace("_compatible", "").replace("_", " ").title())
        self.name.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(self.dot)
        layout.addWidget(self.name)

    def set_status(self, status: str, last_error: str = "") -> None:
        """Update the dot colour and tooltip."""
        color = integration_color(status)
        self.dot.setStyleSheet(f"color: {color}; font-size: 12px;")
        tooltip = f"{self.provider}: {integration_status_label(status)}"
        if last_error:
            tooltip += f"\n{last_error}"
        self.setToolTip(tooltip)


class TopBar(QWidget):
    """Frameless-window title bar with workspace context."""

    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()
    logout_requested = Signal()
    search_requested = Signal()
    notifications_requested = Signal()
    settings_requested = Signal()
    password_change_requested = Signal()

    def __init__(self, user: CurrentUser, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(56)
        self.user = user
        self._drag_offset = None
        self._dots: dict[str, IntegrationDot] = {}
        self._build()
        self.refresh_integrations()
        self.refresh_notifications()
        translator.language_changed.connect(lambda _l: self.retranslate())

    # ------------------------------------------------------------------ #
    def _build(self) -> None:
        """Create the widgets."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 10, 6)
        layout.setSpacing(14)

        brand = QVBoxLayout()
        brand.setSpacing(0)
        self.title_label = QLabel("LeadPilot AI")
        self.title_label.setObjectName("TopBarTitle")
        self.company_label = QLabel(self.user.company_name or "—")
        self.company_label.setObjectName("TopBarSubtitle")
        brand.addWidget(self.title_label)
        brand.addWidget(self.company_label)
        layout.addLayout(brand)

        self.demo_badge = Badge(tr("app.demo_mode"), theme.INFO)
        layout.addWidget(self.demo_badge)

        layout.addSpacing(8)
        self.integration_box = QHBoxLayout()
        self.integration_box.setSpacing(12)
        for provider in ("telegram", "whatsapp", "instagram", "website", "openai_compatible"):
            dot = IntegrationDot(provider)
            self._dots[provider] = dot
            self.integration_box.addWidget(dot)
        layout.addLayout(self.integration_box)

        layout.addStretch(1)

        self.search_button = QPushButton()
        self.search_button.setObjectName("Ghost")
        self.search_button.setIcon(theme.icon("fa6s.magnifying-glass", theme.TEXT_MUTED))
        self.search_button.setMinimumWidth(180)
        self.search_button.clicked.connect(self.search_requested.emit)
        layout.addWidget(self.search_button)

        self.language_box = QComboBox()
        self.language_box.addItem("UZ", "uz")
        self.language_box.addItem("RU", "ru")
        self.language_box.setCurrentIndex(0 if translator.language == "uz" else 1)
        self.language_box.setFixedWidth(70)
        self.language_box.currentIndexChanged.connect(
            lambda: translator.set_language(self.language_box.currentData())
        )
        layout.addWidget(self.language_box)

        self.notification_button = QPushButton()
        self.notification_button.setObjectName("IconButton")
        self.notification_button.setIcon(theme.icon("fa6s.bell", theme.TEXT_MUTED))
        self.notification_button.setIconSize(QSize(16, 16))
        self.notification_button.clicked.connect(self.notifications_requested.emit)
        layout.addWidget(self.notification_button)

        self.notification_badge = Badge("0", theme.DANGER)
        self.notification_badge.hide()
        layout.addWidget(self.notification_badge)

        self.avatar = Avatar(initials(self.user.full_name), self.user.avatar_color, 32)
        layout.addWidget(self.avatar)

        user_box = QVBoxLayout()
        user_box.setSpacing(0)
        self.user_label = QLabel(self.user.full_name)
        self.user_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        self.role_label = QLabel()
        self.role_label.setObjectName("TopBarSubtitle")
        user_box.addWidget(self.user_label)
        user_box.addWidget(self.role_label)
        layout.addLayout(user_box)

        self.menu_button = QPushButton("⋯")
        self.menu_button.setObjectName("IconButton")
        self.menu_button.setFixedWidth(30)
        self.menu_button.clicked.connect(self._show_menu)
        layout.addWidget(self.menu_button)

        layout.addSpacing(6)
        self.min_button = QPushButton("—")
        self.min_button.setObjectName("WindowButton")
        self.min_button.setFixedSize(36, 28)
        self.min_button.clicked.connect(self.minimize_requested.emit)
        self.max_button = QPushButton("▢")
        self.max_button.setObjectName("WindowButton")
        self.max_button.setFixedSize(36, 28)
        self.max_button.clicked.connect(self.maximize_requested.emit)
        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("WindowCloseButton")
        self.close_button.setFixedSize(36, 28)
        self.close_button.clicked.connect(self.close_requested.emit)
        layout.addWidget(self.min_button)
        layout.addWidget(self.max_button)
        layout.addWidget(self.close_button)

        self.retranslate()

    # ------------------------------------------------------------------ #
    def retranslate(self) -> None:
        """Reapply translated captions."""
        self.search_button.setText("  " + tr("topbar.global_search"))
        self.role_label.setText(
            self.user.role_title_ru if translator.language == "ru" else self.user.role_title_uz
        )
        self.demo_badge.setText(tr("app.demo_mode"))
        self.min_button.setToolTip(tr("topbar.minimize"))
        self.max_button.setToolTip(tr("topbar.maximize"))
        self.close_button.setToolTip(tr("topbar.close"))
        self.notification_button.setToolTip(tr("topbar.notifications"))

    def _show_menu(self) -> None:
        """Show the user context menu."""
        menu = QMenu(self)
        menu.addAction(tr("set.title"), self.settings_requested.emit)
        menu.addAction(tr("topbar.change_password"), self.password_change_requested.emit)
        menu.addSeparator()
        menu.addAction(tr("topbar.logout"), self.logout_requested.emit)
        menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))

    def refresh_integrations(self) -> None:
        """Update the connection dots and the demo badge."""
        demo_only = True
        for entry in integration_service.status_overview():
            dot = self._dots.get(entry["provider"])
            if dot is not None:
                dot.set_status(entry["status"], entry.get("error", ""))
            if entry["status"] == "connected":
                demo_only = False
        self.demo_badge.setVisible(demo_only)

    def refresh_notifications(self) -> None:
        """Update the unread notification badge."""
        count = notification_service.unread_count(self.user.id)
        self.notification_badge.setText(str(count))
        self.notification_badge.setVisible(count > 0)

    def set_company(self, name: str) -> None:
        """Update the company caption."""
        self.company_label.setText(name)

    # ------------------------------------------------------------------ #
    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt signature
        """Begin dragging the window."""
        window = self.window()
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - window.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt signature
        """Drag the window."""
        window = self.window()
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if window.isMaximized():
                return
            window.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt signature
        """Stop dragging."""
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt signature
        """Toggle maximised state on double click."""
        self.maximize_requested.emit()
        super().mouseDoubleClickEvent(event)

    def version_text(self) -> str:
        """Return the application version string (used in tooltips)."""
        return f"v{APP_VERSION}"
