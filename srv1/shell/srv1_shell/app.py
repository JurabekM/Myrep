"""Shell'ni ishga tushirish: uslub, shrift, yadroni ko'tarish, token, asosiy oyna."""

import sys
from pathlib import Path

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QInputDialog, QLineEdit

from srv1_shell.config import (
    ShellConfig,
    default_token_file,
    load_config,
    read_token,
    save_config,
)
from srv1_shell.i18n import I18n
from srv1_shell.icon import app_icon
from srv1_shell.launcher import Launcher, service_name
from srv1_shell.main_window import MainWindow
from srv1_shell.server_control import ServerControl

THEME_FILE = Path(__file__).with_name("theme.qss")
# Shrift QSS orqali emas: bir nechta zaxira oilasi faqat QFont bilan to'g'ri ishlaydi.
FONT_FAMILIES = ["Segoe UI", "Noto Sans", "Arial"]


def apply_theme(app: QApplication) -> None:
    font = QFont()
    font.setFamilies(FONT_FAMILIES)
    font.setPointSize(10)
    app.setFont(font)
    app.setStyleSheet(THEME_FILE.read_text(encoding="utf-8"))


def ask_token(config: ShellConfig, token_file: Path) -> str | None:
    i18n = I18n(config.language)
    text, accepted = QInputDialog.getText(
        None,
        i18n.t("token.title"),
        i18n.t("token.prompt", path=token_file),
        QLineEdit.EchoMode.Password,
    )
    token = text.strip()
    return token if accepted and token and token.isascii() else None


def main(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("SRV_1")
    app.setWindowIcon(app_icon())
    apply_theme(app)
    config = load_config()
    token_file = default_token_file()
    launcher = Launcher(config.http_url, token_file.parent, service_name=service_name())
    control = ServerControl(launcher)

    def remember_language(_language: str) -> None:
        save_config(config)

    window = MainWindow(
        config,
        read_token(token_file) or "",
        on_language_changed=remember_language,
        control=control,
    )
    asked = False

    def offer_manual_token() -> None:
        """Zaxira yo'l: yadro ishlayapti, lekin token fayli o'qilmadi (boshqa hisobniki)."""
        nonlocal asked
        if asked or control.reason != "no_token":
            return
        asked = True
        token = ask_token(config, token_file)
        if token is not None:
            window.use_token(token)

    control.changed.connect(offer_manual_token)
    window.show()
    # Yadro ishlamayotgan bo'lsa, oynasiz ko'tariladi; oyna yopilganda u ishlashda davom etadi.
    control.ensure()
    code = app.exec()
    window.shutdown()
    return code
