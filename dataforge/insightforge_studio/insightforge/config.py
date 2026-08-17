from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "InsightForge Studio"
APP_VERSION = "0.1.0"
ORG_NAME = "InsightForge"

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent


def user_data_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    return Path(root) / "InsightForge" if root else Path.home() / ".insightforge"


DATA_DIR = user_data_dir()
EXPORT_DIR = DATA_DIR / "exports"
MODEL_DIR = DATA_DIR / "models"
for folder in (DATA_DIR, EXPORT_DIR, MODEL_DIR):
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

MAX_PREVIEW_ROWS = 100_000
MAX_IMPORT_BYTES = 256 * 1024 * 1024
MAX_URL_BYTES = 64 * 1024 * 1024
MAX_ZIP_MEMBERS = 100
MAX_ZIP_EXPANDED_BYTES = 512 * 1024 * 1024

COLORS = {
    "canvas": "#080B12",
    "panel": "#0F1420",
    "raised": "#171E2E",
    "raised2": "#202A3E",
    "border": "#2A3650",
    "text": "#EEF3FF",
    "muted": "#98A6BF",
    "primary": "#7C5CFC",
    "primary2": "#31C6FF",
    "success": "#38D996",
    "warning": "#FFCB66",
    "danger": "#FF6B86",
}

CHART_COLORS = [
    "#7C5CFC", "#31C6FF", "#38D996", "#FFCB66", "#FF6B86",
    "#C084FC", "#2DD4BF", "#FB923C", "#60A5FA", "#F472B6",
]

