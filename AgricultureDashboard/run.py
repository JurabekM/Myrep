"""AgroVision — Qishloq xo'jaligi analitik platformasi. Kirish nuqtasi.

Ishga tushirish:  python run.py
Qo'shimcha:       python run.py --selfcheck   (tizim salomatligi tekshiruvi)
                  python run.py --port 8090   (boshqa port)
                  python run.py --yes         (paketlarni so'ramasdan o'rnatish)
"""
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys

MIN_PYTHON = (3, 10)


def _print_banner() -> None:
    print(r"""
   _____                    ___    ___      _
  |  _  |___ ___ ___ ___   |  _|  |  _|___ |_|___ ___
  |     | . |  _| . |  _|  |  |   |  ||_ -|| | . |   |
  |__|__|_  |_| |___|_|     \__\   \__\___||_|___|_|_|
        |___|   AgroVision — Enterprise Agriculture Analytics
    """)


def ensure_dependencies(auto_yes: bool = False) -> bool:
    """Check required packages; offer to pip-install anything missing."""
    from config import settings

    missing = [pip_name for pip_name, module in settings.REQUIRED_PACKAGES.items()
               if importlib.util.find_spec(module) is None]
    if not missing:
        return True

    print("Quyidagi zarur kutubxonalar topilmadi:")
    for name in missing:
        print(f"  - {name}")
    if not auto_yes:
        answer = input("Ularni pip orqali o'rnatishga ruxsat berasizmi? [Y/n]: ")
        if answer.strip().lower() not in ("", "y", "yes", "ha"):
            print("O'rnatish bekor qilindi. Qo'lda o'rnating: "
                  f"pip install {' '.join(missing)}")
            return False
    print("O'rnatilmoqda... (bir necha daqiqa olishi mumkin)")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *missing])
    except subprocess.CalledProcessError as exc:
        print(f"pip xatosi ({exc.returncode}). Qo'lda o'rnating: "
              f"pip install {' '.join(missing)}")
        return False
    still_missing = [pip for pip, module in settings.REQUIRED_PACKAGES.items()
                     if importlib.util.find_spec(module) is None]
    if still_missing:
        print(f"O'rnatib bo'lmadi: {still_missing}")
        return False
    print("Barcha zarur kutubxonalar tayyor.")
    return True


def initialize(debug: bool = False) -> None:
    """Installer sequence: folders, logging, database, seed, ML models."""
    from config import settings
    from core.logging_setup import setup_logging

    settings.ensure_directories()
    log = setup_logging(debug=debug)

    from database.engine import init_db
    from database.seed import seed_if_empty

    init_db()
    if seed_if_empty():
        log.info("Birinchi ishga tushirish yakunlandi: demo ma'lumotlar yaratildi.")

    from ml.service import MODEL_FILES, train_all

    if not all(path.exists() for path in MODEL_FILES.values()):
        log.info("ML modellari o'qitilmoqda (birinchi marta, ~10-30 soniya)...")
        train_all()

    _write_default_plugin()


def _write_default_plugin() -> None:
    """Ship the example Soil Analysis plugin on first run (plugin system demo)."""
    from config import settings

    target = settings.PLUGINS_DIR / "soil_analysis.py"
    if target.exists():
        return
    try:
        import plugin_templates  # embedded in the monolith build

        target.write_text(plugin_templates.SOIL_ANALYSIS, encoding="utf-8")
    except ImportError:
        # Modular layout ships the plugin file directly in plugins/.
        pass


def selfcheck() -> int:
    """Health check: every subsystem exercised end-to-end. Returns exit code."""
    initialize()
    checks: list[tuple[str, bool, str]] = []

    def run_check(name: str, fn) -> None:
        try:
            detail = fn()
            checks.append((name, True, str(detail)))
        except Exception as exc:  # noqa: BLE001
            checks.append((name, False, f"{type(exc).__name__}: {exc}"))

    def check_db() -> str:
        from database.engine import db_stats

        stats = db_stats()
        assert stats["users"] >= 3 and stats["fields"] >= 100
        return f"{sum(stats.values()):,} yozuv, {len(stats)} jadval"

    def check_kpi() -> str:
        from analytics.kpi import compute_kpi

        kpi = compute_kpi()
        assert kpi.total_area_ha > 0 and kpi.production_t > 0
        return f"{kpi.year}: {kpi.avg_yield_t_ha} t/ga, ROI {kpi.roi_percent}%"

    def check_ml() -> str:
        from ml.service import model_status, predict_yield

        status = model_status()
        value = predict_yield(1, 1, 50, 150, 24, 350, 450, 1.0)
        assert 0 < value < 100
        return f"yield R²={status['yield']['r2']}, prognoz={value} t/ga"

    def check_ai() -> str:
        from ai.engine import assistant

        result = assistant.ask("Jizzaxda bug'doy hosili nima uchun pasaydi?")
        assert len(result["answer"]) > 40
        return result["answer"].splitlines()[0][:80]

    def check_map() -> str:
        from gis.maps import build_map

        html = build_map()
        assert len(html) > 10_000
        return f"xarita HTML {len(html) // 1024} KB"

    def check_report() -> str:
        from analytics.kpi import yield_trend
        from reports.exporter import export_dataframe

        path = export_dataframe(yield_trend(), "selfcheck", "csv")
        assert path.exists()
        path.unlink()
        return "CSV eksport OK"

    def check_security() -> str:
        from core.security import create_token, hash_password, verify_password, verify_token

        assert verify_password("test123", hash_password("test123"))
        token = verify_token(create_token("admin", "admin"))
        assert token and token["sub"] == "admin"
        return "PBKDF2 + HMAC token OK"

    def check_backup() -> str:
        from database.backup import create_backup, list_backups

        path = create_backup("selfcheck")
        assert path is not None and list_backups()
        path.unlink()
        return "backup/restore OK"

    run_check("Ma'lumotlar bazasi", check_db)
    run_check("KPI analitikasi", check_kpi)
    run_check("ML modellari", check_ml)
    run_check("AI yordamchi", check_ai)
    run_check("GIS xarita", check_map)
    run_check("Hisobot eksporti", check_report)
    run_check("Xavfsizlik", check_security)
    run_check("Zaxira nusxa", check_backup)

    print("\n=== O'z-o'zini tekshirish natijalari ===")
    failed = 0
    for name, ok, detail in checks:
        mark = "OK " if ok else "XATO"
        if not ok:
            failed += 1
        print(f"  [{mark}] {name:22s} {detail}")
    print(f"\nJami: {len(checks)}, muvaffaqiyatli: {len(checks) - failed}, "
          f"xato: {failed}")
    return 1 if failed else 0


def _force_utf8_console() -> None:
    """Windows consoles often default to cp1251/cp866 — switch to UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main() -> None:
    _force_utf8_console()
    if sys.version_info < MIN_PYTHON:
        print(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ talab qilinadi "
              f"(sizda {sys.version_info.major}.{sys.version_info.minor}).")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="AgroVision platformasi")
    parser.add_argument("--host", default=None, help="Server manzili")
    parser.add_argument("--port", type=int, default=None, help="Server porti")
    parser.add_argument("--no-browser", action="store_true",
                        help="Brauzerni avtomatik ochmaslik")
    parser.add_argument("--yes", action="store_true",
                        help="Paketlarni so'ramasdan o'rnatish")
    parser.add_argument("--debug", action="store_true", help="Debug rejimi")
    parser.add_argument("--selfcheck", action="store_true",
                        help="Tizim salomatligini tekshirish va chiqish")
    args = parser.parse_args()

    _print_banner()
    if not ensure_dependencies(auto_yes=args.yes):
        sys.exit(1)

    if args.selfcheck:
        sys.exit(selfcheck())

    initialize(debug=args.debug)

    from config import settings

    host = args.host or settings.DEFAULT_HOST
    port = args.port or settings.DEFAULT_PORT
    print(f"\n  Dashboard:  http://{host}:{port}")
    print("  Demo login: admin / admin123\n")

    from app.main import start

    start(host=host, port=port, open_browser=not args.no_browser,
          debug=args.debug)


if __name__ in {"__main__", "__mp_main__"}:
    main()
