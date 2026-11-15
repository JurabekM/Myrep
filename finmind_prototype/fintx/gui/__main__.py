"""`python -m fintx.gui` — desktop interfeys (macOS; Windows va Linux'da ham ishlaydi)."""

from __future__ import annotations

import argparse
import sys
import traceback


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fintx.gui",
        description="FinTx — moliyaviy tranzaksiyalar prototipi (desktop interfeys).",
    )
    parser.add_argument(
        "--db",
        metavar="FAYL",
        help="ma'lumotlar bazasi fayli (standart: foydalanuvchi papkasida)",
    )
    args = parser.parse_args(argv)

    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except ImportError:
        print(
            "Desktop interfeys uchun PySide6 kerak:\n"
            "    python -m pip install -r requirements-gui.txt\n"
            "Terminal interfeysi PySide6'siz ishlaydi: python -m fintx",
            file=sys.stderr,
        )
        return 1

    from ..app import App
    from ..errors import FinTxError
    from .theme import apply_theme
    from .views import MainWindow

    qt_app = QApplication(sys.argv[:1])
    qt_app.setApplicationName("FinTx")
    apply_theme(qt_app)

    def report_unexpected(kind: type, value: BaseException, trace: object) -> None:
        # Tafsilot faqat stderr'ga; foydalanuvchiga ichki ma'lumot ko'rsatilmaydi.
        traceback.print_exception(kind, value, trace)  # type: ignore[arg-type]
        QMessageBox.critical(None, "FinTx", "Kutilmagan xato yuz berdi.")

    sys.excepthook = report_unexpected

    try:
        core = App.open(args.db)
    except (FinTxError, OSError) as exc:
        text = (
            str(exc)
            if isinstance(exc, FinTxError)
            else ("Ma'lumotlar bazasi faylini ochib bo'lmadi.")
        )
        QMessageBox.critical(None, "FinTx", text)
        return 1

    window = MainWindow(core)
    window.show()
    try:
        return qt_app.exec()
    finally:
        core.close()


if __name__ == "__main__":
    raise SystemExit(main())
