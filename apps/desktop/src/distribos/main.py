"""DistribOS AI desktop — kirish nuqtasi.

Uch xil usulda ishga tushadi (testda qulflangan):

* ``python run.py``
* ``python -m distribos.main``
* ``python apps/desktop/src/distribos/main.py``
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Fayl to'g'ridan-to'g'ri ishga tushirilganda paket topilishi uchun.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from distribos.infrastructure.config import (
    PUBLIC_PILOT_WARNING,
    AppSettings,
    ConfigError,
    load_settings,
)

logger = logging.getLogger("distribos")


def configure_logging(settings: AppSettings) -> None:
    """Fayl + konsol jurnali, aylanish bilan.

    Jurnalda maxfiy payload, kalit yoki mijoz ma'lumoti BO'LMASLIGI kerak —
    buni `tests/security/test_logging.py` tekshiradi.
    """
    settings.paths.ensure()
    log_file = settings.paths.log_dir / "distribos.log"

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console)

    # Kutubxonalar juda gapiruvchan; ularni jimroq qilamiz.
    logging.getLogger("paho").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def run_gui(argv: list[str] | None = None) -> int:
    """Grafik ilovani ishga tushiradi."""
    from PySide6.QtWidgets import QApplication, QMessageBox

    from distribos.app_context import build_context
    from distribos.presentation.main_window import MainWindow
    from distribos.presentation.theme import stylesheet

    try:
        settings = load_settings()
    except ConfigError as exc:
        # Qt hali yo'q — konsolga chiqaramiz.
        print(f"Konfiguratsiya xatosi:\n{exc}", file=sys.stderr)
        return 2

    configure_logging(settings)
    logger.info("DistribOS AI ishga tushmoqda (profil: %s)", settings.mqtt.profile.value)

    application = QApplication(argv if argv is not None else sys.argv)
    application.setApplicationName("DistribOS AI")
    application.setOrganizationName("DistribOS")
    application.setStyleSheet(stylesheet())

    try:
        context = build_context(settings, allow_insecure_secrets=True)
    except Exception as exc:
        logger.exception("Ishga tushirib bo'lmadi")
        QMessageBox.critical(
            None, "Ishga tushmadi",
            f"Dasturni ishga tushirib bo'lmadi.\n\n{exc}\n\n"
            f"Jurnal: {settings.paths.log_dir / 'distribos.log'}",
        )
        return 1

    if settings.requires_public_pilot_consent:
        answer = QMessageBox.warning(
            None, "Ochiq broker rejimi",
            PUBLIC_PILOT_WARNING + "\n\nDavom etasizmi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            context.close()
            return 0

    window = MainWindow(context)
    window.show()

    # Brokerga ulanish UI ko'ringandan KEYIN — ulanish sekin bo'lsa ham
    # oyna darhol chiqadi va dastur "qotib qolgan"dek ko'rinmaydi.
    try:
        if context.transport is not None:
            context.transport.connect()   # type: ignore[union-attr]
    except Exception as exc:
        logger.warning("Brokerga ulanib bo'lmadi: %s", exc)
        window.statusBar().showMessage(
            "Brokerga ulanib bo'lmadi — dastur ulanishsiz ishlashda davom etadi", 8000
        )

    window.start_sync()
    return application.exec()


def run_console() -> int:
    """Grafik muhitsiz holat tekshiruvi (CI va diagnostika uchun).

    DIQQAT: paketlangan (`--windowed`) build'da `sys.stdout` yo'q va
    ko'tarilgan istisno PyInstaller'ning MODAL dialogiga aylanadi —
    tashqaridan bu "dastur osilib qoldi" bo'lib ko'rinadi. Shuning
    uchun bu yerda hamma narsa ushlanadi va natija:

    * stdout ga (bo'lsa),
    * jurnal fayliga (doim),
    * `--check` uchun `status.txt` ga

    yoziladi. Chiqish kodi ham to'g'ri qaytariladi.
    """
    from distribos.app_context import build_context

    settings = load_settings()
    configure_logging(settings)

    lines: list[str] = []

    def emit(text: str = "") -> None:
        lines.append(text)
        try:
            print(text)
        except Exception:
            pass   # windowed build'da stdout yo'q — jurnal baribir bor

    try:
        context = build_context(settings, allow_insecure_secrets=True)
    except Exception as exc:
        logger.exception("Holat tekshiruvi bajarilmadi")
        emit(f"XATOLIK: {type(exc).__name__}: {exc}")
        _write_status(settings, lines)
        return 1

    try:
        health = context.provider.protocol_health_check()
        queued, dead = context.engine.queue_depth()
        emit("DistribOS AI — holat")
        emit(f"  Protokol       : AETHER-Q {health.protocol_version} "
             f"(profil 0x{health.profile_id:02x})")
        emit(f"  Kalit avlodi   : #{health.epoch}")
        emit(f"  Qurilma        : {health.device_id_masked}")
        emit(f"  Qurilmalar     : {health.peers_known} "
             f"({health.peers_revoked} bekor qilingan)")
        emit(f"  Broker profili : {settings.mqtt.profile.value}")
        emit(f"  Broker         : {settings.mqtt.host}:{settings.mqtt.port}")
        emit(f"  Navbat         : {queued} yuborilmagan, {dead} xato")
        emit(f"  Baza           : {settings.paths.database_path}")
        if health.blocking_reasons:
            emit("  E'tibor        : " + "; ".join(health.blocking_reasons))
        _write_status(settings, lines)
        return 0
    except Exception as exc:
        logger.exception("Holat tekshiruvi bajarilmadi")
        emit(f"XATOLIK: {type(exc).__name__}: {exc}")
        _write_status(settings, lines)
        return 1
    finally:
        context.close()


def _write_status(settings: AppSettings, lines: list[str]) -> None:
    """Holatni faylga yozadi — grafik build'da stdout ishonchsiz."""
    try:
        settings.paths.ensure()
        (settings.paths.log_dir / "status.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
    except OSError:
        logger.warning("status.txt yozilmadi", exc_info=True)


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv[1:])
    if "--check" in arguments or "--status" in arguments:
        return run_console()
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
