"""Application-wide configuration and filesystem layout.

All runtime data (database, backups, attachments, generated reports) lives in
``%APPDATA%/BuildControl`` so the application works from a read-only install
directory (e.g. a PyInstaller onefile build).
"""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME: str = "BuildControl"
APP_TITLE: str = "BuildControl"
APP_VERSION: str = "1.0.0"
ORG_NAME: str = "BuildControl"

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #


def _app_data_dir() -> Path:
    """Return (and create) the per-user data directory."""
    base = os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


DATA_DIR: Path = _app_data_dir()
DB_PATH: Path = DATA_DIR / "buildcontrol.db"
BACKUP_DIR: Path = DATA_DIR / "backups"
FILES_DIR: Path = DATA_DIR / "files"
REPORTS_DIR: Path = DATA_DIR / "reports"
LOG_PATH: Path = DATA_DIR / "buildcontrol.log"

for _d in (BACKUP_DIR, FILES_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

PACKAGE_DIR: Path = Path(__file__).resolve().parent
RESOURCES_DIR: Path = PACKAGE_DIR / "resources"

DB_URL: str = f"sqlite:///{DB_PATH}"

# --------------------------------------------------------------------------- #
# Locale / money
# --------------------------------------------------------------------------- #

DEFAULT_LANGUAGE: str = "uz"
SUPPORTED_LANGUAGES: tuple[str, ...] = ("uz", "en")

BASE_CURRENCY: str = "UZS"
#: Suffix rendered after an amount, per language. Adding USD later only
#: requires extending :data:`CURRENCY_SUFFIX` and the rate table in settings.
CURRENCY_SUFFIX: dict[str, dict[str, str]] = {
    "UZS": {"uz": "so'm", "en": "UZS"},
    "USD": {"uz": "$", "en": "$"},
}

DATE_FORMAT: str = "dd.MM.yyyy"
PY_DATE_FORMAT: str = "%d.%m.%Y"
PY_DATETIME_FORMAT: str = "%d.%m.%Y %H:%M"

#: Rows rendered per page in the paginated tables.
DEFAULT_PAGE_SIZE: int = 50
PAGE_SIZES: tuple[int, ...] = (25, 50, 100, 250)

#: Warn when actual cost exceeds this share of the planned value.
BUDGET_WARN_RATIO: float = 0.9

# --------------------------------------------------------------------------- #
# Synchronisation
# --------------------------------------------------------------------------- #

#: Workspace key: installations sharing it exchange data with each other.
SYNC_DEFAULT_TENANT: str = "buildcontrol"
#: Seconds between automatic synchronisation rounds.
SYNC_DEFAULT_INTERVAL: int = 300
SYNC_MIN_INTERVAL: int = 30
