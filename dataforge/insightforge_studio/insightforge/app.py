from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .config import APP_NAME, ORG_NAME


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--demo", action="store_true", help="demo dataset bilan ochish")
    args, qt_args = parser.parse_known_args(argv)
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication([sys.argv[0], *qt_args])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(ORG_NAME)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI Variable", 9))

    from .ui.main_window import MainWindow
    window = MainWindow(demo=args.demo)
    window.show()
    return app.exec()

