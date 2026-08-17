"""Login and first-run administrator setup dialog."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import load_config, save_config
from app.models.enums import RoleName
from app.services import auth_service
from app.services.auth_service import AuthError, CurrentUser
from app.ui.i18n import tr, translator
from app.ui.styles import theme
from app.ui.widgets.common import Panel

logger = logging.getLogger(__name__)


class LoginDialog(QDialog):
    """Frameless login window; switches to setup mode when no user exists."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_user: CurrentUser | None = None
        self.setup_mode = not auth_service.has_any_user()
        self._drag_offset = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 560 if self.setup_mode else 480)
        self._build()
        self._retranslate()
        translator.language_changed.connect(lambda _l: self._retranslate())

    # ------------------------------------------------------------------ #
    def _build(self) -> None:
        """Create the widgets."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        root = QWidget()
        root.setObjectName("RootWindow")
        outer.addWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 22, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        self.language_box = QComboBox()
        self.language_box.addItem("O'zbekcha", "uz")
        self.language_box.addItem("Русский", "ru")
        self.language_box.setCurrentIndex(0 if translator.language == "uz" else 1)
        self.language_box.setFixedWidth(120)
        self.language_box.currentIndexChanged.connect(self._on_language)
        close_button = QPushButton("✕")
        close_button.setObjectName("WindowCloseButton")
        close_button.setFixedSize(30, 28)
        close_button.clicked.connect(self.reject)
        header.addWidget(self.language_box)
        header.addStretch(1)
        header.addWidget(close_button)
        layout.addLayout(header)

        self.logo_label = QLabel("LeadPilot AI")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet(
            f"font-size: 24px; font-weight: 800; color: {theme.ACCENT}; padding-top: 6px;"
        )
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("Muted")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.logo_label)
        layout.addWidget(self.subtitle_label)
        layout.addSpacing(6)

        form = Panel(padding=18, spacing=10)
        body = form.body()

        self.full_name_label = QLabel()
        self.full_name_input = QLineEdit()
        self.full_name_input.setMinimumHeight(38)
        if self.setup_mode:
            body.addWidget(self.full_name_label)
            body.addWidget(self.full_name_input)
        else:
            self.full_name_label.hide()
            self.full_name_input.hide()

        self.username_label = QLabel()
        self.username_input = QLineEdit()
        self.username_input.setMinimumHeight(38)
        body.addWidget(self.username_label)
        body.addWidget(self.username_input)

        self.password_label = QLabel()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(38)
        body.addWidget(self.password_label)
        body.addWidget(self.password_input)

        self.repeat_label = QLabel()
        self.repeat_input = QLineEdit()
        self.repeat_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.repeat_input.setMinimumHeight(38)
        if self.setup_mode:
            body.addWidget(self.repeat_label)
            body.addWidget(self.repeat_input)
        else:
            self.repeat_label.hide()
            self.repeat_input.hide()

        self.remember_box = QCheckBox()
        if not self.setup_mode:
            body.addWidget(self.remember_box)
        else:
            self.remember_box.hide()

        layout.addWidget(form)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(f"color: {theme.DANGER}; font-size: 12px;")
        self.error_label.setMinimumHeight(34)
        layout.addWidget(self.error_label)

        self.submit_button = QPushButton()
        self.submit_button.setObjectName("Primary")
        self.submit_button.setMinimumHeight(42)
        self.submit_button.clicked.connect(self._submit)
        layout.addWidget(self.submit_button)

        self.hint_label = QLabel()
        self.hint_label.setObjectName("Muted")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint_label)
        layout.addStretch(1)

        config = load_config()
        if not self.setup_mode and config.remember_username:
            self.username_input.setText(config.remember_username)
            self.remember_box.setChecked(True)
            self.password_input.setFocus()
        else:
            (self.full_name_input if self.setup_mode else self.username_input).setFocus()

        self.password_input.returnPressed.connect(self._submit)
        self.repeat_input.returnPressed.connect(self._submit)
        self.username_input.returnPressed.connect(self._submit)

    # ------------------------------------------------------------------ #
    def _retranslate(self) -> None:
        """Apply the active language to every caption."""
        self.setWindowTitle(tr("login.title"))
        self.subtitle_label.setText(
            tr("login.setup_hint") if self.setup_mode else tr("app.subtitle")
        )
        self.full_name_label.setText(tr("login.full_name"))
        self.username_label.setText(tr("login.username"))
        self.password_label.setText(tr("login.password"))
        self.repeat_label.setText(tr("login.password_repeat"))
        self.remember_box.setText(tr("login.remember"))
        self.submit_button.setText(tr("login.create") if self.setup_mode else tr("login.submit"))
        self.hint_label.setText("" if self.setup_mode else tr("login.demo_hint"))

    def _on_language(self) -> None:
        """Language combo handler."""
        translator.set_language(self.language_box.currentData())

    # ------------------------------------------------------------------ #
    def _submit(self) -> None:
        """Validate the form and either create the admin or sign in."""
        self.error_label.setText("")
        username = self.username_input.text().strip()
        password = self.password_input.text()
        try:
            if self.setup_mode:
                if password != self.repeat_input.text():
                    self.error_label.setText(tr("err.password_mismatch"))
                    return
                auth_service.create_user(
                    username=username,
                    password=password,
                    full_name=self.full_name_input.text().strip(),
                    role_name=RoleName.ADMIN,
                    language=translator.language,
                )
                self.current_user = auth_service.authenticate(username, password)
            else:
                self.current_user = auth_service.authenticate(username, password)
                config = load_config()
                config.remember_username = username if self.remember_box.isChecked() else None
                save_config(config)
        except AuthError as exc:
            self.error_label.setText(tr(f"err.{exc.code}"))
            self.password_input.selectAll()
            self.password_input.setFocus()
            return
        except Exception:
            logger.exception("Login failed unexpectedly")
            self.error_label.setText(tr("err.unknown"))
            return
        self.accept()

    # ------------------------------------------------------------------ #
    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt signature
        """Start dragging the frameless window."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt signature
        """Move the frameless window."""
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt signature
        """Stop dragging."""
        self._drag_offset = None
        super().mouseReleaseEvent(event)
