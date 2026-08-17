"""Application entry point.

Runnable every way a user is likely to try::

    python -m app.main            # from the project root
    python app/main.py            # direct path
    python run.py                 # convenience launcher
    BuildControl.exe              # frozen build

When the file is executed directly, Python puts ``app/`` on ``sys.path`` instead
of the project root, so ``import app`` would fail; the block below restores it
before any project import happens.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from types import TracebackType

if __package__ in (None, ""):  # executed as a script, not as a module
    _ROOT = str(Path(__file__).resolve().parent.parent)
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QFont, QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from app.config import APP_NAME, APP_VERSION, ORG_NAME  # noqa: E402
from app.controllers.app_state import bootstrap, configure_logging  # noqa: E402
from app.ui.styles.stylesheet import build_stylesheet  # noqa: E402
from app.ui.styles.theme import FONT_SIZE  # noqa: E402


def _install_excepthook(app: QApplication) -> None:
    """Show unexpected errors in a dialog instead of dying silently."""

    def hook(
        exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None
    ) -> None:  # pragma: no cover - interactive
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        sys.stderr.write(text)
        box = QMessageBox()
        box.setWindowTitle(APP_NAME)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setText(str(exc))
        box.setDetailedText(text)
        box.exec()

    sys.excepthook = hook
    del app


def create_app() -> QApplication:
    """Create and theme the QApplication instance."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORG_NAME)
    app.setWindowIcon(QIcon())
    font = QFont("Segoe UI", FONT_SIZE - 2)
    app.setFont(font)
    app.setStyleSheet(build_stylesheet())
    return app


def main() -> int:
    """Start BuildControl."""
    configure_logging()
    app = create_app()
    _install_excepthook(app)
    bootstrap(seed_demo=True)

    from app.ui.main_window.main_window import MainWindow
    from app.ui.pages.login_page import LoginWindow

    windows: dict[str, object] = {}

    def open_main(_user) -> None:
        window = MainWindow()
        windows["main"] = window
        window.show()

    login = LoginWindow()
    login.logged_in.connect(open_main)
    login.show()
    windows["login"] = login

    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
