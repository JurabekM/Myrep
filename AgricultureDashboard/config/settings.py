"""AgroVision — application configuration, filesystem layout and constants.

Every path in the project is derived from ``BASE_DIR`` so the whole platform
works both as the modular package and as the generated single-file monolith.
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

APP_NAME = "AgroVision"
APP_TITLE = "AgroVision — Qishloq xo'jaligi analitik platformasi"
APP_VERSION = "1.0.0"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


def _resolve_base_dir() -> Path:
    """Resolve the project root for both modular and monolith execution."""
    env = os.environ.get("AGRIDASH_HOME")
    if env:
        return Path(env).resolve()
    main = sys.modules.get("__main__")
    main_file = getattr(main, "__file__", None)
    if main_file:
        candidate = Path(main_file).resolve().parent
        if (
            (candidate / "run.py").exists()
            or (candidate / "AgricultureDashboard.py").exists()
            or (candidate / "config").is_dir()
        ):
            return candidate
    return Path.cwd()


BASE_DIR: Path = _resolve_base_dir()
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "backups"
EXPORT_DIR = BASE_DIR / "exports"
UPLOAD_DIR = BASE_DIR / "uploads"
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
PLUGINS_DIR = BASE_DIR / "plugins"

RUNTIME_DIRS = [
    DATA_DIR, CACHE_DIR, LOG_DIR, BACKUP_DIR, EXPORT_DIR,
    UPLOAD_DIR, MODELS_DIR, STATIC_DIR, TEMPLATES_DIR, PLUGINS_DIR,
]

DB_PATH = DATA_DIR / "agriculture.db"
SECRET_FILE = DATA_DIR / "secret.key"

# pip package name -> importable module name
REQUIRED_PACKAGES: dict[str, str] = {
    "nicegui": "nicegui",
    "sqlalchemy": "sqlalchemy",
    "pandas": "pandas",
    "numpy": "numpy",
    "requests": "requests",
    "openpyxl": "openpyxl",
    "folium": "folium",
    "fpdf2": "fpdf",
    "scikit-learn": "sklearn",
}

# Optional accelerators / integrations — the platform degrades gracefully
# to fully working fallbacks when any of these are missing.
OPTIONAL_PACKAGES: dict[str, str] = {
    "xgboost": "xgboost",
    "lightgbm": "lightgbm",
    "catboost": "catboost",
    "tensorflow": "tensorflow",
    "geopandas": "geopandas",
    "shapely": "shapely",
    "pyproj": "pyproj",
    "fiona": "fiona",
    "rasterio": "rasterio",
    "pyshp": "shapefile",
    "python-docx": "docx",
    "matplotlib": "matplotlib",
    "meteostat": "meteostat",
    "earthengine-api": "ee",
    "Pillow": "PIL",
    "cryptography": "cryptography",
}

# Default values written into the ``settings`` table on first launch.
DEFAULT_SETTINGS: dict[str, str] = {
    "theme": "light",
    "language": "uz",
    "offline_mode": "auto",              # auto | on | off
    "weather_provider": "open-meteo",    # open-meteo | nasa-power
    "gee_service_account": "",
    "gee_key_file": "",
    "planet_api_key": "",
    "map_default_lat": "41.3",
    "map_default_lon": "64.5",
    "map_default_zoom": "6",
    "ml_auto_retrain_days": "30",
    "backup_keep": "20",
    "auto_backup_hours": "24",
}

TOKEN_TTL_SECONDS = 12 * 3600
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCK_MINUTES = 10
API_RATE_LIMIT_PER_MINUTE = 120

WEATHER_SEASON_MONTHS = (4, 5, 6, 7, 8, 9)   # vegetation season Apr..Sep
HISTORY_START_YEAR = 2021


def ensure_directories() -> None:
    """Installer step: create every runtime folder if missing."""
    for directory in RUNTIME_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def get_storage_secret() -> str:
    """Persistent random secret used for sessions and API token signing."""
    ensure_directories()
    if SECRET_FILE.exists():
        secret = SECRET_FILE.read_text(encoding="utf-8").strip()
        if secret:
            return secret
    secret = secrets.token_hex(32)
    SECRET_FILE.write_text(secret, encoding="utf-8")
    return secret
