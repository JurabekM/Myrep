"""Sarlavhaning eng kichik kengligini haqiqiy Windows shrifti bilan o'lchaydi (JSON chiqaradi).

Test muhiti (`offscreen`) harflarni keng "quti" qilib chizadi, shuning uchun kenglikni u yerda
o'lchab bo'lmaydi. Bu skript alohida jarayonda, `QT_QPA_PLATFORM=windows` bilan yuritiladi;
oyna ekranga chiqmaydi (`WA_DontShowOnScreen`).
"""

import json
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from srv1_shell.app import apply_theme
from srv1_shell.config import ShellConfig
from srv1_shell.launcher import Launcher
from srv1_shell.main_window import MainWindow
from srv1_shell.server_control import ServerControl
from srv1_shell.translations import LANGUAGE_NAMES

STATES = ("running", "stopped", "checking", "starting", "stopping", "failed")


def main() -> int:
    app = QApplication(sys.argv)
    apply_theme(app)
    launcher = Launcher("http://127.0.0.1:8710", Path("yoq-papka"), service_name="yoq-xizmat")
    control = ServerControl(launcher)
    window = MainWindow(ShellConfig(language="uz"), "", control=control)
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    header = window.title.parentWidget()
    if header is None:
        return 1
    widths: dict[str, int] = {}
    for language in LANGUAGE_NAMES:
        window.set_language(language)
        for state in STATES:
            control.state = state
            for connected in (True, False):
                window._render_status(connected)  # pyright: ignore[reportPrivateUsage]
                key = f"{language}/{state}/{'ulangan' if connected else 'uzilgan'}"
                widths[key] = header.minimumSizeHint().width()
    report = {"platform": app.platformName(), "minimum": window.minimumWidth(), "widths": widths}
    window.shutdown()
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
