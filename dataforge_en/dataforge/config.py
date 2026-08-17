"""Global configuration, paths and constants."""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "DataForge Pro"
APP_ID = "dataforge"
VERSION = "1.0.0"
ORG = "DataForge"

# ------------------------------------------------------------------ paths ---
PKG_DIR = Path(__file__).resolve().parent
ROOT_DIR = PKG_DIR.parent
SAMPLES_DIR = ROOT_DIR / "samples"


def _user_dir() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / APP_ID
    return Path.home() / f".{APP_ID}"


USER_DIR = _user_dir()
MODELS_DIR = USER_DIR / "models"
EXPORTS_DIR = USER_DIR / "exports"
PROJECTS_DIR = USER_DIR / "projects"
CACHE_DIR = USER_DIR / "cache"

for _d in (USER_DIR, MODELS_DIR, EXPORTS_DIR, PROJECTS_DIR, CACHE_DIR):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except OSError:  # read-only environment — fail silently
        pass

# ----------------------------------------------------------------- limits ---
MAX_HISTORY = 25              # states kept for undo/redo
PREVIEW_ROWS = 200_000        # max rows rendered in the table view
SNIFF_BYTES = 256 * 1024      # bytes read for format detection
MAX_CATEGORY_ONEHOT = 40      # max distinct values allowed for one-hot encoding
SAMPLE_FOR_HEAVY = 20_000     # sample size for heavy ops (t-SNE, pairplot)

# ----------------------------------------------------------------- colors ---
PALETTE = {
    "bg":        "#0B0F14",
    "surface":   "#131A22",
    "surface2":  "#1A232E",
    "surface3":  "#212C39",
    "border":    "#26313D",
    "border2":   "#33404F",
    "text":      "#E6EDF3",
    "muted":     "#8B98A5",
    "faint":     "#5C6B7A",
    "accent":    "#4C9AFF",
    "accent2":   "#22D3EE",
    "success":   "#34D399",
    "warning":   "#FBBF24",
    "danger":    "#F87171",
    "purple":    "#A78BFA",
    "pink":      "#F472B6",
}

CHART_COLORS = [
    "#4C9AFF", "#22D3EE", "#34D399", "#FBBF24", "#F87171",
    "#A78BFA", "#F472B6", "#60A5FA", "#2DD4BF", "#FB923C",
]

LEVEL_COLORS = {
    "TRACE": "#5C6B7A", "DEBUG": "#8B98A5", "INFO": "#4C9AFF",
    "NOTICE": "#22D3EE", "WARN": "#FBBF24", "WARNING": "#FBBF24",
    "ERROR": "#F87171", "CRITICAL": "#EF4444", "FATAL": "#DC2626",
    "ALERT": "#F472B6", "EMERG": "#DC2626",
}
