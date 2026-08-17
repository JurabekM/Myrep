"""Launcher: ``python run.py``.

Kept at the project root so the application starts from a double-click, from any
working directory, and as the PyInstaller entry point.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
