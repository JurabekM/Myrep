"""`python -m fintx.gui` — desktop interfeys (macOS; Windows va Linux'da ham ishlaydi)."""

from __future__ import annotations

import argparse
import secrets
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
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    # Notanish argumentlar e'tiborsiz qoldiriladi: operatsion tizim ilovani
    # o'z argumentlari bilan ishga tushirishi mumkin.
    args, _unknown = parser.parse_known_args(argv)

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

    if args.self_test:
        return _self_test(qt_app)

    def report_unexpected(kind: type, value: BaseException, trace: object) -> None:
        # Tafsilot faqat stderr'ga; foydalanuvchiga ichki ma'lumot ko'rsatilmaydi.
        # Konsolsiz (oynali) ijro faylda stderr umuman bo'lmaydi.
        if sys.stderr is not None:
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


def _self_test(qt_app: object) -> int:
    """Reliz tekshiruvi: yadro, shrift va asosiy oyna (CI ishlatadi).

    Chiqish kodi: 0 — hammasi joyida; 3 — yadro; 4 — shrift; 5 — oyna; 6 — belgi.
    """
    from PySide6.QtGui import QFontDatabase

    from ..app import App
    from ..db import MEMORY
    from ..security import PasswordHasher
    from ..selftest import run_core_selftest
    from .theme import FONT_FAMILY, app_icon
    from .views import MainWindow

    def say(text: str) -> None:
        if sys.stdout is not None:
            print(text, flush=True)

    try:
        for step in run_core_selftest():
            say(f"ok: {step}")
    except Exception as exc:
        say(f"yadro: {type(exc).__name__}: {exc}")
        return 3
    if FONT_FAMILY not in QFontDatabase.families():
        say("ilova ichidagi shrift yuklanmadi")
        return 4
    say("ok: shrift")
    # Belgi fayllari paketga kirganmi (barcha tizimlarda) va oynaga o'rnatilganmi
    # (macOS'dan tashqari — u yerda Dock belgisi `.app` paketidan olinadi).
    icon_sizes = sorted(size.width() for size in app_icon().availableSizes())
    if icon_sizes[:1] != [16] or 256 not in icon_sizes:
        say(f"ilova belgisi fayllari topilmadi: {icon_sizes}")
        return 6
    if sys.platform != "darwin" and qt_app.windowIcon().isNull():  # type: ignore[attr-defined]
        say("oyna belgisi o'rnatilmagan")
        return 6
    say("ok: belgi")
    try:
        core = App.open(MEMORY, hasher=PasswordHasher(scrypt_ln=8))
        window = MainWindow(core)
        window.show()
        qt_app.processEvents()  # type: ignore[attr-defined]
        if sys.platform != "darwin" and window.windowIcon().isNull():
            raise AssertionError("asosiy oynada belgi yo'q")
        password = secrets.token_urlsafe(18)
        core.auth.register("selftest", password)
        view = window.auth_view
        view.username.setText("selftest")
        view.password.setText(password)
        view.submit()
        if window.ctx.session is None:
            raise AssertionError("kirish oynasi sessiya ochmadi")
        window.show_page(1)
        window.transactions.amount.setText("125 000,50")
        window.transactions.save()
        if window.transactions.table.rowCount() != 1:
            raise AssertionError("tranzaksiya jadvalga tushmadi")
        qt_app.processEvents()  # type: ignore[attr-defined]
        window.close()
        core.close()
    except Exception as exc:
        say(f"oyna: {type(exc).__name__}: {exc}")
        return 5
    say("ok: asosiy oyna")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
