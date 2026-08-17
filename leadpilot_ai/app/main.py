"""Entry point of LeadPilot AI."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

if __package__ in (None, ""):  # allow `python app/main.py`
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QDialog  # noqa: E402

from app.bootstrap import create_application, init_backend  # noqa: E402
from app.controllers.app_context import AppContext  # noqa: E402
from app.ui.dialogs.login_dialog import LoginDialog  # noqa: E402
from app.ui.main_window import MainWindow, center_on_screen  # noqa: E402

logger = logging.getLogger("leadpilot")


def run() -> int:
    """Start the application; returns the process exit code."""
    init_backend()
    application = create_application(sys.argv)

    while True:
        login = LoginDialog()
        if login.exec() != QDialog.DialogCode.Accepted or login.current_user is None:
            return 0

        context = AppContext(login.current_user)
        window = MainWindow(context)
        center_on_screen(window)
        if context.config.window_maximized:
            window.showMaximized()
        else:
            window.show()
        context.start()
        application.exec()

        if not window.logout_requested:
            return 0
        logger.info("User signed out — returning to the login screen")


if __name__ == "__main__":
    sys.exit(run())
