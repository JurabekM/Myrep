"""Attachment storage helpers."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from app.config import FILES_DIR

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_name(name: str) -> str:
    """Return a filesystem-safe version of ``name``."""
    return _SAFE.sub("_", name).strip("_") or "file"


def store_file(source: str | Path, category: str = "misc") -> str:
    """Copy ``source`` into the managed files directory and return the new path."""
    src = Path(source)
    if not src.is_file():
        raise FileNotFoundError(str(src))
    target_dir = FILES_DIR / safe_name(category)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    target = target_dir / f"{stamp}_{safe_name(src.name)}"
    shutil.copy2(src, target)
    return str(target)


def open_path(path: str | Path) -> bool:
    """Open a file or folder with the OS default handler. Returns success."""
    target = Path(path)
    if not target.exists():
        return False
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(target))  # noqa: S606  # nosec - user initiated
        elif sys.platform == "darwin":  # pragma: no cover
            subprocess.Popen(["open", str(target)])
        else:  # pragma: no cover
            subprocess.Popen(["xdg-open", str(target)])
        return True
    except OSError:
        return False
