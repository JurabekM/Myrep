"""Frameless custom title bar with company, integrations, language and user."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QPushButton, QWidget

from app.config import APP_NAME, APP_VERSION
from app.controllers.app_context import AppContext
from app.ui.i18n import LANGUAGE_NAMES, t, te
from app.ui.styles.theme import COLORS
from app.ui.widgets.common import StatusBadge


class TitleBar(QWidget):
    """Draggable title bar hosting the window controls and global state."""

    logout_requested = Signal()
    profile_requested = Signal()
    search_requested = Signal()

    def __init__(self, ctx: AppContext, window: QWidget) -> None:
        super().__init__(window)
        self.setObjectName("TitleBar")
        self.ctx = ctx
        self.window_ref = window
        self._drag_offset: QPoint | None = None
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(12)

        self.app_label = QLabel(APP_NAME)
        self.app_label.setObjectName("TitleAppName")
        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setObjectName("Hint")
        layout.addWidget(self.app_label)
        layout.addWidget(self.version_label)

        self.company_label = QLabel("")
        self.company_label.setObjectName("TitleMeta")
        layout.addSpacing(10)
        layout.addWidget(self.company_label)
        layout.addStretch(1)

        self.search_button = QPushButton("⌕  " + t("shortcut.global_search"))
        self.search_button.setObjectName("Ghost")
        self.search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_button.clicked.connect(self.search_requested.emit)
        layout.addWidget(self.search_button)

        self.integration_box = QWidget()
        integration_layout = QHBoxLayout(self.integration_box)
        integration_layout.setContentsMargins(0, 0, 0, 0)
        integration_layout.setSpacing(5)
        self.integration_badges: dict[str, StatusBadge] = {}
        for kind in ("llm", "email", "lead_import"):
            badge = StatusBadge("integration_kind", kind)
            badge.setCursor(Qt.CursorShape.WhatsThisCursor)
            self.integration_badges[kind] = badge
            integration_layout.addWidget(badge)
        layout.addWidget(self.integration_box)

        self.language_button = QPushButton()
        self.language_button.setObjectName("Ghost")
        self.language_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.language_button.clicked.connect(self._show_language_menu)
        layout.addWidget(self.language_button)

        self.user_button = QPushButton()
        self.user_button.setObjectName("Ghost")
        self.user_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.user_button.clicked.connect(self._show_user_menu)
        layout.addWidget(self.user_button)

        for text, name, slot in (
            ("—", "WindowButton", self._minimize),
            ("▢", "WindowButton", self._toggle_maximize),
            ("✕", "WindowClose", self.window_ref.close),
        ):
            widget = QPushButton(text)
            widget.setObjectName(name if name != "WindowClose" else "WindowClose")
            widget.setProperty("class", "window")
            widget.setCursor(Qt.CursorShape.PointingHandCursor)
            widget.setFixedWidth(40)
            widget.clicked.connect(slot)
            if name == "WindowClose":
                widget.setStyleSheet(
                    "QPushButton{background:transparent;border:none;border-radius:6px;"
                    f"padding:6px 12px;color:{COLORS['text_muted']};font-size:14px;}}"
                    f"QPushButton:hover{{background-color:{COLORS['danger']};color:#fff;}}"
                )
            else:
                widget.setObjectName("WindowButton")
            layout.addWidget(widget)

        self.refresh_state()

    # ------------------------------------------------------------- content
    def refresh_state(self) -> None:
        """Refresh company, user, language and integration indicators."""
        self.company_label.setText(f"{t('titlebar.company')}: {self.ctx.company_name()}")
        user = self.ctx.user
        self.user_button.setText(f"{user.full_name}  ·  {te('role', user.role_code)}")
        self.language_button.setText(LANGUAGE_NAMES.get(self.ctx.language(), "EN"))
        self.search_button.setText("⌕  " + t("shortcut.global_search"))
        for state in self.ctx.integration_states():
            badge = self.integration_badges.get(state["kind"])
            if badge is None:
                continue
            status = "demo" if state["is_demo"] else state.get("status") or "configured"
            badge.set_status(
                "integration_kind",
                status,
                text=f"{te('integration_kind', state['kind'])}: "
                f"{t('common.demo_mode') if state['is_demo'] else state['label']}",
            )
            badge.setToolTip(state.get("last_error") or state["label"])

    # -------------------------------------------------------------- menus
    def _show_language_menu(self) -> None:
        menu = QMenu(self)
        for code, name in LANGUAGE_NAMES.items():
            action = menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(code == self.ctx.language())
            action.triggered.connect(lambda _checked=False, c=code: self.ctx.set_language(c))
        menu.exec(self.language_button.mapToGlobal(QPoint(0, self.language_button.height())))

    def _show_user_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction(t("titlebar.profile")).triggered.connect(self.profile_requested.emit)
        menu.addSeparator()
        menu.addAction(t("titlebar.logout")).triggered.connect(self.logout_requested.emit)
        menu.exec(self.user_button.mapToGlobal(QPoint(0, self.user_button.height())))

    # ------------------------------------------------------- window control
    def _minimize(self) -> None:
        self.window_ref.showMinimized()

    def _toggle_maximize(self) -> None:
        if self.window_ref.isMaximized():
            self.window_ref.showNormal()
        else:
            self.window_ref.showMaximized()

    # ---------------------------------------------------------- dragging
    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Start dragging the frameless window."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.window_ref.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Move the window while the title bar is dragged."""
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if self.window_ref.isMaximized():
                self.window_ref.showNormal()
                self._drag_offset = QPoint(self.window_ref.width() // 2, 20)
            self.window_ref.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Stop dragging."""
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Maximise / restore on double click."""
        self._toggle_maximize()
        super().mouseDoubleClickEvent(event)
