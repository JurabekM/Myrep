"""AI Business Advisor Uzbekistan — yagona ishga tushirish nuqtasi.

Ishga tushirish:  python main.py

Bu skript ketma-ket:
  1. Muhitni tekshiradi (majburiy paketlar, ixtiyoriylar, AI rejimi).
  2. Konfiguratsiya + loglashni sozlaydi.
  3. SQLite bazasini ochadi va migratsiya qiladi.
  4. Bog'liqliklarni yig'adi (Container).
  5. Ultra Dark PyQt6 UI'ni ochadi.

Hech qanday Docker, tashqi baza yoki port TALAB ETILMAYDI.
"""

from __future__ import annotations

import sys


def _print_missing_and_exit(missing: list[str]) -> None:
    print("=" * 60)
    print("  Majburiy Python paketlari yetishmaydi:")
    for pip_name in missing:
        print(f"    - {pip_name}")
    print()
    print("  O'rnatish uchun (loyiha papkasida):")
    print("    pip install -r requirements.txt")
    print("=" * 60)
    sys.exit(1)


def main() -> int:
    # --- Konfiguratsiya va loglash ---
    from app.core.config import AppConfig
    from app.core.logging_setup import configure_logging, get_logger

    config = AppConfig.load()
    configure_logging(config.paths.log_file)
    logger = get_logger("main")
    logger.info("AI Business Advisor ishga tushmoqda…")

    # --- Muhit tekshiruvi ---
    from app.core.bootstrap import check_environment

    report = check_environment(config)
    if not report.ok:
        _print_missing_and_exit(report.missing_required)

    if report.missing_optional:
        logger.info(
            "Ixtiyoriy imkoniyatlar o'chirilgan (paket yo'q): %s",
            ", ".join(f"{pip} ({desc})" for pip, desc in report.missing_optional),
        )
    logger.info("AI rejimi: %s", report.ai_mode)

    # --- Ma'lumotlar bazasi ---
    from app.data.database import Database
    from app.data.schema import migrate

    database = Database(config.paths.database_file)
    applied = migrate(database)
    logger.info("Baza tayyor (%d migratsiya qo'llandi)", applied)

    # --- Bog'liqliklar ---
    from app.container import Container

    container = Container(config, database)

    # --- UI ---
    from PyQt6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow
    from app.ui.theme.styles import build_stylesheet

    app = QApplication(sys.argv)
    app.setApplicationName("AI Business Advisor Uzbekistan")
    app.setStyleSheet(build_stylesheet())

    window = MainWindow(container)
    window.show()

    if not report.cloud_ai_available and not report.local_ai_available:
        _warn_no_ai(window)

    exit_code = app.exec()

    container.shutdown()
    logger.info("Ilova yopildi")
    return exit_code


def _warn_no_ai(parent) -> None:  # type: ignore[no-untyped-def]
    from PyQt6.QtWidgets import QMessageBox

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle("AI sozlanmagan")
    box.setText(
        "Hech qanday AI provayder topilmadi.\n\n"
        "Chat va generatsiya ishlashi uchun 'Sozlamalar' sahifasida bepul kalit "
        "kiriting (Groq / Gemini / OpenRouter — bepul, karta shart emas) yoki "
        "models/ papkasiga GGUF model joylashtiring.\n\n"
        "Soliq va moliya kalkulyatorlari AI'siz ham to'liq ishlaydi."
    )
    box.exec()


if __name__ == "__main__":
    raise SystemExit(main())
