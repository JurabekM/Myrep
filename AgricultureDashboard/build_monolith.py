"""Variant-2 generator: bundles the whole modular project into ONE runnable file.

    python build_monolith.py            ->  AgricultureDashboard.py

The generated file embeds every module's source code and installs an
in-memory import finder, so ``python AgricultureDashboard.py`` behaves
identically to ``python run.py`` — same pages, same database, same API —
with zero extra files required.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT = BASE_DIR / "AgricultureDashboard.py"

PACKAGE_DIRS = [
    "config", "core", "database", "analytics", "gis", "ml", "weather",
    "market", "irrigation", "finance", "satellite", "ai", "reports",
    "utils", "api", "app", "dashboard",
]

HEADER = '''#!/usr/bin/env python3
"""AgricultureDashboard — AgroVision platformasining monolit (bitta fayl) nashri.

Ishga tushirish:   python AgricultureDashboard.py
Salomatlik testi:  python AgricultureDashboard.py --selfcheck

Ushbu fayl `build_monolith.py` tomonidan avtomatik yaratilgan — qo'lda
tahrirlamang; o'zgarishlarni modulli loyihada qiling va qayta yig'ing.
Yaratilgan vaqt: {timestamp}
"""
import importlib.abc
import importlib.util
import sys

'''

FOOTER = '''

class _EmbeddedFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Serves every embedded module straight from the _SOURCES dictionary."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in _SOURCES:
            return None
        return importlib.util.spec_from_loader(
            fullname, self, origin=f"<embedded:{fullname}>",
            is_package=fullname in _PACKAGES)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        origin = f"<embedded:{module.__name__}>"
        module.__file__ = origin
        code = compile(_SOURCES[module.__name__], origin, "exec")
        exec(code, module.__dict__)


def _install_finder() -> None:
    if not any(isinstance(f, _EmbeddedFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _EmbeddedFinder())


if __name__ in {"__main__", "__mp_main__"}:
    _install_finder()
    import run

    run.main()
'''


def collect_sources() -> tuple[dict[str, str], set[str]]:
    """Read every module of the project into {module_name: source}."""
    sources: dict[str, str] = {}
    packages: set[str] = set()
    for package in PACKAGE_DIRS:
        root = BASE_DIR / package
        if not root.is_dir():
            raise SystemExit(f"Paket topilmadi: {package}")
        for path in sorted(root.rglob("*.py")):
            relative = path.relative_to(BASE_DIR)
            parts = list(relative.with_suffix("").parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
                packages.add(".".join(parts))
            module_name = ".".join(parts)
            sources[module_name] = path.read_text(encoding="utf-8")
    sources["run"] = (BASE_DIR / "run.py").read_text(encoding="utf-8")

    plugin_path = BASE_DIR / "plugins" / "soil_analysis.py"
    if plugin_path.exists():
        sources["plugin_templates"] = (
            '"""Embedded plugin templates written to plugins/ on first run."""\n'
            f"SOIL_ANALYSIS = {plugin_path.read_text(encoding='utf-8')!r}\n"
        )
    return sources, packages


def build() -> Path:
    """Generate AgricultureDashboard.py and return its path."""
    sources, packages = collect_sources()
    lines: list[str] = [
        HEADER.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        f"_PACKAGES = {packages!r}\n\n",
        "_SOURCES = {\n",
    ]
    for name in sorted(sources):
        lines.append(f"    {name!r}: {sources[name]!r},\n")
    lines.append("}\n")
    lines.append(FOOTER)
    OUTPUT.write_text("".join(lines), encoding="utf-8")
    size_kb = OUTPUT.stat().st_size // 1024
    print(f"Monolit yaratildi: {OUTPUT.name} "
          f"({len(sources)} modul, {size_kb} KB)")
    return OUTPUT


if __name__ == "__main__":
    build()
