"""Application entry point.

All three invocation styles work::

    python run.py
    python -m dataforge
    python dataforge/main.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

if __package__ in (None, ""):  # the `python dataforge/main.py` case
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "dataforge"

from dataforge.config import APP_NAME, ORG, VERSION  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """Launch the graphical interface."""
    argv = list(sys.argv if argv is None else argv)

    if "--version" in argv:
        print(f"{APP_NAME} v{VERSION}")
        return 0
    if "--help" in argv or "-h" in argv:
        print(f"{APP_NAME} v{VERSION}\n"
              "  python run.py                 launch the GUI\n"
              "  python run.py --samples       generate the demo data\n"
              "  python run.py --version       show the version\n")
        return 0
    if "--samples" in argv:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from samples.generate_samples import generate_all

        print("Generating the demo data…")
        generate_all()
        return 0

    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName(ORG)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    from dataforge.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
