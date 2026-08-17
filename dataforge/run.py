#!/usr/bin/env python3
"""DataForge Pro — ishga tushirish nuqtasi.

    python run.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataforge.main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
