"""`monitor` plaginini sinov uchun o'rnatish."""

import json
import shutil
from pathlib import Path

from srv1_core.plugins.registry import BUILTIN_DIR

# Hamma qoida o'chiq: sinov mashinasining haqiqiy yuklamasi natijaga ta'sir qilmasin.
QUIET = {"memory_percent": 0, "cpu_percent": 0, "cpu_minutes": 0, "disk_free_gb": 0}


def install_monitor(
    plugin_root: Path,
    data_dir: Path,
    mode: str = "inprocess",
    interval_s: float = 3600,
    **thresholds: float,
) -> None:
    """Plaginni nusxalaydi. Standart: jadval bo'yicha o'lchov yo'q (faqat `POST /sample`)."""
    target = plugin_root / "monitor"
    shutil.copytree(BUILTIN_DIR / "monitor", target, ignore=shutil.ignore_patterns("__pycache__"))
    manifest = target / "plugin.toml"
    text = manifest.read_text(encoding="utf-8")
    assert 'mode = "inprocess"' in text
    manifest.write_text(text.replace('mode = "inprocess"', f'mode = "{mode}"'), encoding="utf-8")
    data_dir.mkdir(parents=True, exist_ok=True)
    config = {"interval_s": interval_s, "thresholds": QUIET | thresholds}
    (data_dir / "monitor.json").write_text(json.dumps({"config": config}), encoding="utf-8")
