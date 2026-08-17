# -*- coding: utf-8 -*-
"""
ERP_MONOLITH.py generatori.

Barcha ``src/`` manba modullarini bitta faylga joylashtirib, o'zini o'zi
yuklaydigan (self-bootstrapping) monolit yaratadi. Har bir modul manbasi
base64 sifatida saqlanadi va maxsus import-finder orqali ``sys.modules``
ga xotiradan yuklanadi — natijada:

  * Enterprise struktura va monolit AYNAN bir xil kodni ishlatadi
    (funksional 100% teng).
  * Barcha importlar (``from src.core.utils import D`` va h.k.) buzilmasdan
    ishlaydi — nom to'qnashuvi yo'q.
  * Yagona ``ERP_MONOLITH.py`` faylini ko'chirib, ``python ERP_MONOLITH.py``
    bilan ishga tushirsa bo'ladi (Enterprise papka strukturasi shart emas).

Ishga tushirish:

    python tools/build_monolith.py
"""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
OUTPUT = PROJECT_ROOT / "ERP_MONOLITH.py"


def collect_modules() -> list[tuple[str, bool, str]]:
    """
    ``src/`` ichidagi barcha ``.py`` fayllarni yig'adi.

    :return: (modul_nomi, paketmi, manba_kodi) ro'yxati (import tartibida).
    """
    modules: list[tuple[str, bool, str]] = []
    for path in sorted(SRC_DIR.rglob("*.py")):
        rel = path.relative_to(PROJECT_ROOT).with_suffix("")
        parts = list(rel.parts)  # ['src', 'core', 'utils'] yoki [..., '__init__']
        is_package = parts[-1] == "__init__"
        if is_package:
            parts = parts[:-1]
        module_name = ".".join(parts)
        source = path.read_text(encoding="utf-8")
        modules.append((module_name, is_package, source))
    # Paketlar (kalta nom) submodullardan oldin kelishi uchun saralash
    modules.sort(key=lambda m: m[0].count("."))
    return modules


MONOLITH_TEMPLATE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UzERP — ENTERPRISE ERP (MONOLITH)
=================================

Bu YAGONA fayl butun ERP platformasini o'z ichiga oladi:
barcha klasslar, modullar, REST API, GUI, ma'lumotlar bazasi va web-server.

Ishga tushirish (boshqa hech narsa kerak emas):

    python ERP_MONOLITH.py

Parametrlar (run.py bilan bir xil):

    python ERP_MONOLITH.py --web-only     faqat web-server
    python ERP_MONOLITH.py --desktop-only faqat desktop GUI
    python ERP_MONOLITH.py --selfcheck    tizimni tekshirish
    python ERP_MONOLITH.py --demo         demo ma'lumotlar bilan
    python ERP_MONOLITH.py --port 8080    boshqa port

Bu fayl `tools/build_monolith.py` orqali Enterprise strukturadan
AVTOMATIK generatsiya qilingan — ikkalasi bir xil kodni ishlatadi.

Generatsiya sanasi: {generated_at}
Modullar soni: {module_count}
"""
from __future__ import annotations

import base64
import importlib.abc
import importlib.machinery
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

MIN_PYTHON = (3, 10)

# ====================================================================== #
#  1. Auto-installer — yetishmagan paketlarni avtomatik o'rnatadi
# ====================================================================== #

CORE_PACKAGES = [("flask", "flask>=3.0"), ("yaml", "PyYAML>=6.0")]
GUI_PACKAGES = [("PyQt6", "PyQt6>=6.6"), ("PySide6", "PySide6>=6.6")]
EXTRA_PACKAGES = [("openpyxl", "openpyxl>=3.1"), ("fpdf", "fpdf2>=2.7"),
                  ("docx", "python-docx>=1.1")]


def _is_installed(module_name):
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def _pip_install(spec):
    print(f"  [installer] o'rnatilmoqda: {{spec}} ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
         spec], capture_output=True, text=True)
    ok = result.returncode == 0
    print(f"  [installer] {{'OK' if ok else 'XATO'}}: {{spec}}")
    return ok


def auto_install(no_install, web_only):
    missing_core = [(m, s) for m, s in CORE_PACKAGES if not _is_installed(m)]
    gui_ok = any(_is_installed(m) for m, _ in GUI_PACKAGES)
    missing_extra = [(m, s) for m, s in EXTRA_PACKAGES if not _is_installed(m)]
    if not missing_core and (gui_ok or web_only) and not missing_extra:
        return
    if no_install:
        if missing_core:
            names = ", ".join(s for _, s in missing_core)
            sys.exit(f"XATO: majburiy paketlar yetishmayapti: {{names}}")
        return
    print("=" * 60)
    print("  UzERP Monolith Auto-Installer")
    print("=" * 60)
    for _, spec in missing_core:
        if not _pip_install(spec):
            sys.exit(f"XATO: majburiy paket o'rnatilmadi: {{spec}}")
    if not gui_ok and not web_only:
        _pip_install(GUI_PACKAGES[0][1])
    for _, spec in missing_extra:
        _pip_install(spec)


# ====================================================================== #
#  2. Joylashtirilgan manba modullari (base64)
# ====================================================================== #

_SOURCES = {{
{sources_block}
}}
_PACKAGES = {packages_set}


# ====================================================================== #
#  3. Xotiradan yuklovchi import-finder (barcha `src.*` importlari uchun)
# ====================================================================== #

class _MonolithLoader(importlib.abc.Loader):
    """Joylashtirilgan base64 manbadan modul yuklaydi."""

    def __init__(self, name, source, is_package, base_dir):
        self._name = name
        self._source = source
        self._is_package = is_package
        self._base_dir = base_dir

    def create_module(self, spec):
        return None  # standart modul yaratish

    def exec_module(self, module):
        # Sintetik __file__ — modul darajasidagi Path(__file__) ishlashi uchun.
        # Monolit papkasiga nisbatan qo'yiladi (BASE_DIR to'g'ri chiqadi).
        rel = self._name.replace(".", "/")
        rel += "/__init__.py" if self._is_package else ".py"
        module.__file__ = str(self._base_dir / rel)
        if self._is_package:
            module.__path__ = []  # paket sifatida belgilash
        code = compile(self._source, module.__file__, "exec")
        exec(code, module.__dict__)


class _MonolithFinder(importlib.abc.MetaPathFinder):
    """`src.*` modullarini joylashtirilgan manbadan topadi."""

    def __init__(self, base_dir):
        self._base_dir = base_dir

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in _SOURCES:
            return None
        source = base64.b64decode(_SOURCES[fullname]).decode("utf-8")
        is_package = fullname in _PACKAGES
        loader = _MonolithLoader(fullname, source, is_package, self._base_dir)
        spec = importlib.machinery.ModuleSpec(
            fullname, loader, is_package=is_package)
        if is_package:
            spec.submodule_search_locations = []
        return spec


def _install_finder(base_dir):
    """Import-finder'ni sys.meta_path boshiga qo'yadi."""
    if not any(isinstance(f, _MonolithFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _MonolithFinder(base_dir))


# ====================================================================== #
#  4. Kirish nuqtasi
# ====================================================================== #

def main():
    if sys.version_info < MIN_PYTHON:
        need = ".".join(map(str, MIN_PYTHON))
        sys.exit(f"XATO: Python {{need}}+ kerak.")

    args = sys.argv[1:]
    auto_install(no_install="--no-install" in args,
                 web_only="--web-only" in args)

    # Monolit joylashgan papkani bazaviy papka sifatida ishlatamiz
    # (data/, logs/, config.yaml shu yerda yaratiladi).
    base_dir = Path(__file__).resolve().parent
    _install_finder(base_dir)

    from src.core.bootstrap import initialize  # noqa: E402
    from src.app import (  # noqa: E402
        build_arg_parser, run_selfcheck, _try_import_web, _try_import_desktop,
        _print_banner,
    )
    import threading  # noqa: E402

    parsed = build_arg_parser().parse_args(args)
    ctx = initialize(base_dir, flags={{
        "port": parsed.port, "demo": parsed.demo,
        "web_only": parsed.web_only, "desktop_only": parsed.desktop_only,
    }})

    if parsed.demo:
        try:
            from src.database.demo import seed_demo_data
            seed_demo_data(ctx)
            print("  Demo ma'lumotlar yuklandi.")
        except Exception as exc:  # noqa: BLE001
            print(f"  Demo xatosi: {{exc}}")

    if parsed.selfcheck:
        code = run_selfcheck(ctx)
        ctx.close()
        return code

    create_app, run_server = _try_import_web()
    run_desktop = _try_import_desktop()
    web_available = create_app is not None and not parsed.desktop_only
    gui_available = run_desktop is not None and not parsed.web_only

    _print_banner(ctx, web_available or parsed.desktop_only, gui_available)

    if not web_available and not gui_available:
        print("  Interfeys modullari topilmadi.")
        ctx.close()
        return 0
    try:
        if gui_available:
            if create_app is not None:
                threading.Thread(target=run_server, args=(ctx,), daemon=True,
                                 name="uzerp-web").start()
            return int(run_desktop(ctx) or 0)
        run_server(ctx)
        return 0
    except KeyboardInterrupt:
        print("\\n  To'xtatildi (Ctrl+C).")
        return 0
    finally:
        ctx.close()


if __name__ == "__main__":
    sys.exit(main())
'''


def build() -> None:
    """Monolitni generatsiya qiladi va faylga yozadi."""
    modules = collect_modules()

    source_lines = []
    packages = []
    for name, is_package, source in modules:
        encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
        # Uzun stringni o'qilishi uchun bo'laklarga bo'lamiz
        chunks = [encoded[i:i + 120] for i in range(0, len(encoded), 120)]
        joined = "\n        ".join(f'"{c}"' for c in chunks)
        source_lines.append(f'    "{name}": (\n        {joined}\n    ),')
        if is_package:
            packages.append(name)

    sources_block = "\n".join(source_lines)
    packages_set = "{\n    " + ",\n    ".join(
        f'"{p}"' for p in sorted(packages)) + ",\n}"

    content = MONOLITH_TEMPLATE.format(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        module_count=len(modules),
        sources_block=sources_block,
        packages_set=packages_set,
    )
    OUTPUT.write_text(content, encoding="utf-8")

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"ERP_MONOLITH.py yaratildi: {len(modules)} ta modul, "
          f"{size_kb:.0f} KB")
    print(f"Fayl: {OUTPUT}")


if __name__ == "__main__":
    build()
