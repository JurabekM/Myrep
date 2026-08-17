"""ExportFlow application entry point."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Running this file directly (``python app\main.py`` or a double click) puts the
# ``app`` folder on sys.path instead of the project root, so ``import app``
# would fail. Prepend the project root before any application import.
if __package__ in (None, ""):  # pragma: no cover - only on direct execution
    _PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from app.bootstrap import bootstrap  # noqa: E402
from app.config import APP_NAME, APP_VERSION, ORG_NAME  # noqa: E402
from app.controllers.app_context import AppContext  # noqa: E402
from app.ui.dialogs.login_dialog import LoginDialog  # noqa: E402
from app.ui.i18n import TR  # noqa: E402
from app.ui.main_window.main_window import MainWindow  # noqa: E402
from app.ui.styles.theme import base_font, build_stylesheet  # noqa: E402
from app.utils.logging_setup import get_logger, setup_logging  # noqa: E402

log = get_logger(__name__)


def _install_excepthook(app: QApplication) -> None:
    """Show unexpected errors in a dialog instead of crashing silently."""

    def _hook(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):  # pragma: no cover
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log.error(
            "Unhandled exception: %s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle(APP_NAME)
        box.setText(TR.t("error.generic"))
        box.setDetailedText(f"{exc_type.__name__}: {exc_value}")
        box.exec()

    sys.excepthook = _hook
    _ = app


def create_application() -> QApplication:
    """Create and theme the Qt application object."""
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, False)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORG_NAME)
    app.setStyle("Fusion")
    app.setFont(base_font())
    app.setStyleSheet(build_stylesheet())
    return app


def main() -> int:
    """Run the application: bootstrap, sign in, then show the main window."""
    setup_logging()
    app = create_application()
    _install_excepthook(app)

    try:
        state = bootstrap(with_demo=True)
        log.info("Bootstrap finished: %s", state)
    except Exception as exc:  # pragma: no cover - fatal start-up failure
        log.exception("Bootstrap failed")
        QMessageBox.critical(None, APP_NAME, f"Startup failed:\n{type(exc).__name__}: {exc}")
        return 1

    while True:
        login = LoginDialog()
        if not login.exec() or login.user is None:
            return 0

        context = AppContext(login.user)
        window = MainWindow(context)
        window.show()
        app.exec()

        if not window.logout_requested:
            return 0
        window.deleteLater()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
