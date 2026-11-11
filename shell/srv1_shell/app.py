"""Shell'ni ishga tushirish: uslub, shrift, token, asosiy oyna."""

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
from srv1_shell.main_window import MainWindow

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
    return token if accepted and token else None


def main(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("SRV_1")
    apply_theme(app)
    config = load_config()
    token_file = default_token_file()
    token = read_token(token_file) or ask_token(config, token_file)
    if token is None:
        return 1

    def remember_language(_language: str) -> None:
        save_config(config)

    window = MainWindow(config, token, on_language_changed=remember_language)
    window.show()
    code = app.exec()
    window.shutdown()
    return code
