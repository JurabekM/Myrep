#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UzERP — Enterprise Resource Planning platformasi (yagona kirish nuqtasi).

Ishga tushirish:

    python run.py

Shu bitta buyruqning o'zi quyidagilarni avtomatik bajaradi:
  * kerakli papkalarni yaratadi   (data/, logs/, backups/, exports/, plugins/)
  * config.yaml faylini generatsiya qiladi
  * ma'lumotlar bazasini yaratadi va migratsiyalarni bajaradi
  * admin foydalanuvchini yaratadi (parol data/admin_credentials.txt ichida)
  * yetishmayotgan Python paketlarni avtomatik o'rnatadi (auto-installer)
  * Flask web-serverni ishga tushiradi  ->  http://127.0.0.1:8000
  * Desktop GUI (PyQt6/PySide6) oynasini ochadi

Qo'shimcha parametrlar:

    python run.py --web-only        faqat web-server (GUI ochilmaydi)
    python run.py --desktop-only    faqat desktop GUI
    python run.py --selfcheck       tizimni tekshiradi va chiqadi
    python run.py --port 8080       web-server portini o'zgartirish
    python run.py --no-install      avtomatik pip install ni o'chirish
    python run.py --demo            namunaviy (demo) ma'lumotlar bilan
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

MIN_PYTHON = (3, 10)
PROJECT_ROOT = Path(__file__).resolve().parent

#: (import nomi, pip spetsifikatsiyasi) — ishlash uchun majburiy paketlar.
CORE_PACKAGES = [
    ("flask", "flask>=3.0"),
    ("yaml", "PyYAML>=6.0"),
]

#: Desktop GUI uchun — bittasi yetarli (PyQt6 birinchi tanlov).
GUI_PACKAGES = [
    ("PyQt6", "PyQt6>=6.6"),
    ("PySide6", "PySide6>=6.6"),
]

#: Eksport funksiyalari uchun ixtiyoriy paketlar (bo'lmasa — funksiya o'chadi).
EXTRA_PACKAGES = [
    ("openpyxl", "openpyxl>=3.1"),
    ("fpdf", "fpdf2>=2.7"),
    ("docx", "python-docx>=1.1"),
]


def _is_installed(module_name: str) -> bool:
    """Modul import qilinishi mumkinligini (o'rnatilganligini) tekshiradi."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def _pip_install(spec: str) -> bool:
    """Bitta paketni pip orqali jimgina o'rnatadi. Muvaffaqiyat holatini qaytaradi."""
    print(f"  [installer] o'rnatilmoqda: {spec} ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", spec],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  [installer] XATO: {spec} o'rnatilmadi.")
        return False
    print(f"  [installer] OK: {spec}")
    return True


def check_python() -> None:
    """Python versiyasi minimal talabga mosligini tekshiradi."""
    if sys.version_info < MIN_PYTHON:
        need = ".".join(map(str, MIN_PYTHON))
        have = ".".join(map(str, sys.version_info[:3]))
        sys.exit(f"XATO: Python {need}+ kerak, sizda {have}.")


def auto_install(no_install: bool, web_only: bool) -> None:
    """
    Yetishmayotgan paketlarni avtomatik o'rnatadi (Auto Installer).

    Majburiy paketlar o'rnatilmasa dastur to'xtaydi; GUI va eksport
    paketlari o'rnatilmasa — tegishli funksiya o'chirilgan holda davom etadi.
    """
    missing_core = [(m, s) for m, s in CORE_PACKAGES if not _is_installed(m)]
    gui_ok = any(_is_installed(m) for m, _ in GUI_PACKAGES)
    missing_extra = [(m, s) for m, s in EXTRA_PACKAGES if not _is_installed(m)]

    if not missing_core and (gui_ok or web_only) and not missing_extra:
        return

    if no_install:
        if missing_core:
            names = ", ".join(s for _, s in missing_core)
            sys.exit(
                f"XATO: majburiy paketlar yetishmayapti: {names}\n"
                f"O'rnatish: pip install -r requirements.txt"
            )
        return

    print("=" * 60)
    print("  UzERP Auto-Installer: paketlar tekshirilmoqda...")
    print("=" * 60)

    for _, spec in missing_core:
        if not _pip_install(spec):
            sys.exit(
                f"XATO: majburiy paket o'rnatilmadi: {spec}\n"
                f"Qo'lda o'rnating: pip install {spec}"
            )

    if not gui_ok and not web_only:
        if not _pip_install(GUI_PACKAGES[0][1]):
            print("  [installer] OGOHLANTIRISH: GUI o'rnatilmadi — web rejimida davom etadi.")

    for _, spec in missing_extra:
        _pip_install(spec)  # best-effort: xato bo'lsa ham davom etamiz


def main() -> int:
    """Bootstrap: paketlarni tekshiradi va asosiy ilovani ishga tushiradi."""
    check_python()
    args = sys.argv[1:]
    auto_install(
        no_install="--no-install" in args,
        web_only="--web-only" in args,
    )
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.app import main as app_main  # importni auto-installdan KEYIN qilamiz

    return app_main(args)


if __name__ == "__main__":
    sys.exit(main())
