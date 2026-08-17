"""Login window and the first-run administrator setup."""

from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, APP_VERSION, PATHS
from app.services import auth_service
from app.services.auth_service import CurrentUser
from app.ui.i18n import LANGUAGE_NAMES, TR, t
from app.ui.widgets.common import banner, button, checkbox, combo, combo_value, line_edit
from app.utils.errors import ExportFlowError

_REMEMBER_FILE = "login.json"


def _remember_path():
    PATHS.ensure()
    return PATHS.root / _REMEMBER_FILE


def load_remembered() -> dict:
    """Read the remembered username (never the password)."""
    path = _remember_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover - corrupted file
        return {}


def save_remembered(username: str, language: str, remember: bool) -> None:
    """Persist the username and language for the next start-up."""
    path = _remember_path()
    if not remember:
        path.unlink(missing_ok=True)
        return
    path.write_text(
        json.dumps({"username": username, "language": language}, ensure_ascii=False),
        encoding="utf-8",
    )


class LoginDialog(QDialog):
    """Frameless sign-in dialog; creates the first administrator when needed."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.user: CurrentUser | None = None
        self.first_run = not auth_service.has_any_user()
        self.setWindowTitle(APP_NAME)
        self.setModal(True)
        self.setFixedWidth(430)

        remembered = load_remembered()
        if remembered.get("language"):
            TR.set_language(remembered["language"])

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 20)
        root.setSpacing(12)

        title = QLabel(APP_NAME)
        title.setObjectName("PageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        subtitle = QLabel(t("app.tagline") + f"  ·  v{APP_VERSION}")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(subtitle)

        self.error_label = QLabel("")
        self.error_label.setObjectName("BannerDanger")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        root.addWidget(self.error_label)

        form = QFormLayout()
        form.setSpacing(9)
        self.language_combo = combo(
            [(code, name) for code, name in LANGUAGE_NAMES.items()], TR.language, False
        )
        self.language_combo.currentIndexChanged.connect(self._on_language)
        self.username = line_edit(t("login.username"), remembered.get("username", ""))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText(t("login.password"))
        self.password.returnPressed.connect(self._submit)
        form.addRow(t("common.language"), self.language_combo)
        form.addRow(t("login.username"), self.username)
        form.addRow(t("login.password"), self.password)

        if self.first_run:
            self.full_name = line_edit(t("login.full_name"))
            self.confirm = QLineEdit()
            self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
            form.addRow(t("login.full_name"), self.full_name)
            form.addRow(t("login.confirm_password"), self.confirm)
        root.addLayout(form)

        self.remember = checkbox(t("login.remember"), bool(remembered))
        root.addWidget(self.remember)

        if self.first_run:
            root.addWidget(banner(t("login.first_run"), "info"))
        else:
            hint = QLabel(t("login.demo_hint"))
            hint.setObjectName("Hint")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            root.addWidget(hint)

        buttons = QHBoxLayout()
        buttons.addWidget(button(t("common.cancel"), self.reject, "Ghost"))
        buttons.addWidget(
            button(
                t("login.create") if self.first_run else t("login.submit"), self._submit, "Primary"
            )
        )
        root.addLayout(buttons)

        self.username.setFocus() if not self.username.text() else self.password.setFocus()

    def _on_language(self) -> None:
        TR.set_language(combo_value(self.language_combo))

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def _submit(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        try:
            if self.first_run:
                auth_service.validate_password(password, self.confirm.text())
                self.user = auth_service.create_first_admin(
                    username, password, self.full_name.text().strip(), TR.language
                )
            else:
                self.user = auth_service.authenticate(username, password)
        except ExportFlowError as exc:
            params = {k: v for k, v in exc.params.items() if isinstance(v, (str, int, float))}
            self._show_error(t(exc.key, **params))
            return
        except Exception as exc:  # noqa: BLE001 - surfaced inside the dialog
            self._show_error(f"{type(exc).__name__}: {exc}")
            return
        save_remembered(username, TR.language, self.remember.isChecked())
        self.accept()
