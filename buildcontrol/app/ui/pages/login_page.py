"""Login window and first-run administrator setup."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_TITLE, APP_VERSION
from app.controllers.app_state import app_state
from app.models.enums import RoleCode
from app.services import auth_service
from app.services.auth_service import AuthError, CurrentUser
from app.ui.main_window.frameless import FramelessWindow
from app.ui.styles.theme import COLORS, RADIUS_LG, SPACING, SPACING_LG, SPACING_SM
from app.ui.widgets.common import Separator, button
from app.utils.i18n import tr


class LoginWindow(FramelessWindow):
    """Sign-in window; switches to the setup form when no user exists yet."""

    logged_in = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RootWindow")
        self.setMinimumSize(880, 540)
        self.resize(920, 560)
        self._setup_mode = not auth_service.has_any_user()

        root = QHBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        root.addWidget(self._build_branding(), 1)
        root.addWidget(self._build_form(), 0)

    # -- layout ------------------------------------------------------------- #
    def _build_branding(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("BrandPanel")
        panel.setStyleSheet(
            f"#BrandPanel {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            f" stop:0 {COLORS.sidebar}, stop:1 {COLORS.accent_soft});"
            f" border-top-left-radius: {RADIUS_LG}px;"
            f" border-bottom-left-radius: {RADIUS_LG}px; }}"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(SPACING_LG + 16, SPACING_LG + 12, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_SM)
        layout.addStretch(1)

        mark = QLabel("◆")
        mark.setStyleSheet(f"color: {COLORS.accent}; font-size: 40px;")
        layout.addWidget(mark)

        title = QLabel(APP_TITLE)
        title.setStyleSheet("font-size: 34px; font-weight: 800; letter-spacing: 0.5px;")
        layout.addWidget(title)

        subtitle = QLabel(tr("app_subtitle"))
        subtitle.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 15px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(SPACING_LG)
        for key in ("tab_estimate", "tab_purchases", "tab_warehouse", "tab_stages", "reports"):
            row = QLabel(f"—   {tr(key)}")
            row.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 13px;")
            layout.addWidget(row)

        layout.addStretch(2)
        version = QLabel(f"v{APP_VERSION}  ·  offline")
        version.setStyleSheet(f"color: {COLORS.text_faint}; font-size: 11px;")
        layout.addWidget(version)
        return panel

    def _build_form(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("LoginPanel")
        panel.setFixedWidth(400)
        # Object-name selector so the rule does not cascade onto child widgets.
        panel.setStyleSheet(
            f"#LoginPanel {{ background: {COLORS.bg};"
            f" border-top-right-radius: {RADIUS_LG}px;"
            f" border-bottom-right-radius: {RADIUS_LG}px; }}"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(SPACING_LG + 8, SPACING, SPACING_LG + 8, SPACING_LG)
        layout.setSpacing(SPACING_SM)

        top = QHBoxLayout()
        top.addStretch(1)
        close_btn = button("✕", variant="Ghost")
        close_btn.setFixedWidth(32)
        close_btn.clicked.connect(self.close)
        top.addWidget(close_btn)
        layout.addLayout(top)
        layout.addStretch(1)

        heading = QLabel(tr("first_admin_title") if self._setup_mode else tr("login"))
        heading.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(heading)

        hint = QLabel(tr("first_admin_hint") if self._setup_mode else tr("demo_hint"))
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addSpacing(SPACING_SM)

        self.full_name_input = QLineEdit()
        self.full_name_input.setPlaceholderText(tr("full_name"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(tr("username"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(tr("password"))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password2_input = QLineEdit()
        self.password2_input.setPlaceholderText(tr("password_repeat"))
        self.password2_input.setEchoMode(QLineEdit.EchoMode.Password)

        if self._setup_mode:
            layout.addWidget(self.full_name_input)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        if self._setup_mode:
            layout.addWidget(self.password2_input)

        self.remember_box = QCheckBox(tr("remember_me"))
        if not self._setup_mode:
            self.remember_box.setChecked(app_state.remember_enabled)
            self.username_input.setText(app_state.remembered_username)
            layout.addWidget(self.remember_box)

        self.error_label = QLabel("")
        self.error_label.setObjectName("FieldError")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        self.submit_btn = button(
            tr("create") if self._setup_mode else tr("login"), "approve", "Primary"
        )
        self.submit_btn.setMinimumHeight(38)
        self.submit_btn.clicked.connect(self._submit)
        layout.addWidget(self.submit_btn)

        layout.addSpacing(SPACING_SM)
        layout.addWidget(Separator())
        footer = QLabel(f"{APP_TITLE} v{APP_VERSION}  ·  offline")
        footer.setObjectName("Hint")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
        layout.addStretch(2)

        self.password_input.returnPressed.connect(self._submit)
        self.username_input.returnPressed.connect(self._submit)
        (self.full_name_input if self._setup_mode else self.username_input).setFocus()
        return panel

    # -- behaviour ----------------------------------------------------------- #
    def _error(self, key_or_text: str) -> None:
        self.error_label.setText(tr(key_or_text))
        self.error_label.setVisible(True)

    def _submit(self) -> None:
        """Validate the form and either create the admin or sign in."""
        self.error_label.setVisible(False)
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self._error("required_field")
            return
        try:
            if self._setup_mode:
                if password != self.password2_input.text():
                    self._error("passwords_mismatch")
                    return
                user = auth_service.create_user(
                    username=username,
                    password=password,
                    full_name=self.full_name_input.text().strip() or username,
                    role_code=RoleCode.ADMIN.value,
                )
                user = auth_service.authenticate(username, password)
            else:
                user = auth_service.authenticate(username, password)
        except AuthError as exc:
            self._error(exc.key)
            return
        except Exception as exc:  # unexpected failure must still be visible
            self._error(str(exc))
            return

        if not self._setup_mode:
            app_state.remember(username, self.remember_box.isChecked())
        self._finish(user)

    def _finish(self, user: CurrentUser) -> None:
        app_state.set_user(user)
        self.logged_in.emit(user)
        self.close()
