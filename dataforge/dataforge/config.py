"""Global konfiguratsiya, yo'llar va konstantalar."""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "DataForge Pro"
APP_ID = "dataforge"
VERSION = "1.0.0"
ORG = "DataForge"

# ---------------------------------------------------------------- yo'llar ---
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
    except OSError:  # read-only muhit — jim o'tamiz
        pass

# ------------------------------------------------------------- limitlar ---
MAX_HISTORY = 25              # undo/redo uchun saqlanadigan holatlar soni
PREVIEW_ROWS = 200_000        # jadvalda ko'rsatiladigan maksimal qator
SNIFF_BYTES = 256 * 1024      # format aniqlash uchun o'qiladigan bayt
MAX_CATEGORY_ONEHOT = 40      # one-hot uchun maksimal unikal qiymat
SAMPLE_FOR_HEAVY = 20_000     # t-SNE / pairplot kabi og'ir amallar uchun namuna

# -------------------------------------------------------------- ranglar ---
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
