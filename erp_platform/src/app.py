# -*- coding: utf-8 -*-
"""
Ilova orkestratori: argumentlarni o'qiydi, bootstrap qiladi va
web-server + desktop GUI ni kerakli kombinatsiyada ishga tushiradi.

``run.py`` shu modulning :func:`main` funksiyasini chaqiradi.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import threading
from pathlib import Path

from src import __app_name__, __version__
from src.core.bootstrap import AppContext, initialize
from src.core.logger import get_logger

BASE_DIR = Path(__file__).resolve().parent.parent


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI argumentlar tavsifi."""
    parser = argparse.ArgumentParser(
        prog="run.py",
        description=f"{__app_name__} v{__version__} — Enterprise ERP (faqat Python)",
    )
    parser.add_argument("--web-only", action="store_true",
                        help="faqat web-server (desktop GUI ochilmaydi)")
    parser.add_argument("--desktop-only", action="store_true",
                        help="faqat desktop GUI (web-server baribir ichkarida ishlaydi)")
    parser.add_argument("--selfcheck", action="store_true",
                        help="tizimni tekshirish va chiqish")
    parser.add_argument("--port", type=int, default=None,
                        help="web-server porti (standart: config.yaml dagi qiymat)")
    parser.add_argument("--no-install", action="store_true",
                        help="avtomatik pip install ni o'chirish")
    parser.add_argument("--demo", action="store_true",
                        help="namunaviy (demo) ma'lumotlarni yuklash")
    return parser


# ---------------------------------------------------------------------- #
#  Selfcheck
# ---------------------------------------------------------------------- #

def run_selfcheck(ctx: AppContext) -> int:
    """
    Tizim salomatligini tekshiradi va natijalar jadvalini chiqaradi.

    :return: 0 — hammasi joyida, 1 — kamida bitta muammo bor.
    """
    checks: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, note: str = "") -> None:
        checks.append((name, ok, note))

    # Konfiguratsiya
    add("config.yaml mavjud", (ctx.base_dir / "config.yaml").exists())
    add("secret_key o'rnatilgan", bool(ctx.config.get("app.secret_key")))

    # Papkalar
    for name in ("data", "logs", "backups", "exports", "plugins"):
        add(f"papka: {name}/", (ctx.base_dir / name).is_dir())

    # Database
    tables = ctx.db.table_names()
    add(f"database ({ctx.db.engine})", len(tables) >= 25, f"{len(tables)} ta jadval")
    admin_count = int(ctx.db.scalar(
        "SELECT COUNT(*) FROM users WHERE role = 'administrator'", (), 0) or 0)
    add("admin foydalanuvchi", admin_count >= 1, f"{admin_count} ta")
    accounts = int(ctx.db.scalar("SELECT COUNT(*) FROM accounts", (), 0) or 0)
    add("hisoblar rejasi (NAS-21)", accounts >= 15, f"{accounts} ta hisob")

    # Paketlar
    for module_name, label, required in (
        ("flask", "Flask (web)", True),
        ("yaml", "PyYAML (config)", True),
        ("PyQt6", "PyQt6 (desktop GUI)", False),
        ("PySide6", "PySide6 (desktop GUI, muqobil)", False),
        ("openpyxl", "openpyxl (Excel eksport)", False),
        ("fpdf", "fpdf2 (PDF eksport)", False),
        ("docx", "python-docx (Word eksport)", False),
        ("psycopg2", "psycopg2 (PostgreSQL, ixtiyoriy)", False),
    ):
        installed = importlib.util.find_spec(module_name) is not None
        ok = installed or not required
        note = "o'rnatilgan" if installed else (
            "MAJBURIY — o'rnatilmagan!" if required else "yo'q (funksiya o'chadi)"
        )
        add(label, ok, note)

    # Servislar
    add("auth servisi", ctx.services.has("auth"))
    business = [n for n in ("sales", "inventory", "accounting", "hr", "reports")
                if ctx.services.has(n)]
    add("biznes servislar", True, ", ".join(business) or "keyingi bosqichda")

    # Natija
    print()
    print("=" * 64)
    print(f"  {__app_name__} v{__version__} — SELFCHECK")
    print("=" * 64)
    failed = 0
    for name, ok, note in checks:
        mark = "[OK]  " if ok else "[FAIL]"
        if not ok:
            failed += 1
        suffix = f"  ({note})" if note else ""
        print(f"  {mark} {name}{suffix}")
    print("-" * 64)
    print(f"  Jami: {len(checks)} ta tekshiruv, xato: {failed} ta")
    print("=" * 64)
    return 1 if failed else 0


# ---------------------------------------------------------------------- #
#  Ishga tushirish rejimlari
# ---------------------------------------------------------------------- #

def _try_import_web():
    """Web-server modulini yuklashga urinadi (hali yozilmagan bo'lishi mumkin)."""
    try:
        from src.web.server import create_app, run_server  # noqa: F401
        return create_app, run_server
    except ImportError:
        return None, None


def _try_import_desktop():
    """Desktop GUI modulini yuklashga urinadi."""
    try:
        from src.ui.desktop import run_desktop  # noqa: F401
        return run_desktop
    except ImportError:
        return None


def _print_banner(ctx: AppContext, web_ok: bool, gui_ok: bool) -> None:
    """Ishga tushish ma'lumotlarini konsolga chiqaradi."""
    host = ctx.config.get("server.host", "127.0.0.1")
    port = ctx.config.get("server.port", 8000)
    print()
    print("=" * 64)
    print(f"  {__app_name__} v{__version__} — Enterprise ERP")
    print("=" * 64)
    print(f"  Database : {ctx.db.engine}")
    if web_ok:
        print(f"  Web      : http://{host}:{port}")
    if gui_ok:
        print("  Desktop  : GUI oynasi ochilmoqda...")
    if ctx.admin_password:
        print("-" * 64)
        print("  BIRINCHI ISHGA TUSHISH — administrator hisobi yaratildi:")
        print("    Login:  admin")
        print(f"    Parol:  {ctx.admin_password}")
        print("  (nusxasi: data/admin_credentials.txt — kirgach o'chiring!)")
    print("=" * 64)
    print()


def main(argv: list[str] | None = None) -> int:
    """Asosiy kirish nuqtasi. run.py dan chaqiriladi."""
    args = build_arg_parser().parse_args(argv)

    ctx = initialize(BASE_DIR, flags={
        "port": args.port,
        "demo": args.demo,
        "web_only": args.web_only,
        "desktop_only": args.desktop_only,
    })
    log = get_logger("app")

    # Demo ma'lumotlar (ixtiyoriy)
    if args.demo:
        try:
            from src.database.demo import seed_demo_data
            seed_demo_data(ctx)
            print("  Demo ma'lumotlar yuklandi.")
        except ImportError:
            print("  Demo ma'lumotlar moduli hali mavjud emas.")

    if args.selfcheck:
        code = run_selfcheck(ctx)
        ctx.close()
        return code

    create_app, run_server = _try_import_web()
    run_desktop = _try_import_desktop()

    web_available = create_app is not None and not args.desktop_only
    gui_available = run_desktop is not None and not args.web_only

    _print_banner(ctx, web_available or args.desktop_only, gui_available)

    if not web_available and not gui_available:
        print("  Interfeys modullari hali qurilmoqda (keyingi bosqichlar).")
        print("  Hozircha tekshirish uchun: python run.py --selfcheck")
        ctx.close()
        return 0

    # Auto-backup fon oqimi (config: backup.auto_backup)
    if ctx.services.has("backup"):
        try:
            ctx.services.get("backup").start_auto()
        except Exception:  # noqa: BLE001
            log.exception("Auto-backup ishga tushmadi")

    try:
        if gui_available:
            # Web-server fonda (desktop GUI ichidagi WebView ham shundan foydalanadi)
            if create_app is not None:
                server_thread = threading.Thread(
                    target=run_server, args=(ctx,), daemon=True,
                    name="uzerp-web",
                )
                server_thread.start()
            return int(run_desktop(ctx) or 0)

        # Faqat web rejimi — asosiy oqimda ishlaydi
        run_server(ctx)
        return 0
    except KeyboardInterrupt:
        print("\n  To'xtatildi (Ctrl+C).")
        return 0
    finally:
        ctx.audit.log("system.stop", category="system")
        ctx.close()
        log.info("UzERP to'xtadi.")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
