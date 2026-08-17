"""Application configuration (Pydantic based).

Secrets are never stored in this file. API credentials live either in the OS
keyring (preferred) or in an encrypted-at-rest row of the ``integration_config``
table.  Only non sensitive settings are persisted in ``config.json``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

APP_NAME = "LeadPilot AI"
APP_VERSION = "1.0.0"
ORG_NAME = "LeadPilot"
KEYRING_SERVICE = "LeadPilotAI"

TIMEZONE = "Asia/Tashkent"
DATE_FORMAT = "%d.%m.%Y"
DATETIME_FORMAT = "%d.%m.%Y %H:%M"
TIME_FORMAT = "%H:%M"

Language = Literal["uz", "ru"]


def _is_frozen() -> bool:
    """Return True when running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def base_dir() -> Path:
    """Return the directory that holds the application source / bundle."""
    if _is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """Return a writable directory for database, logs and exports."""
    override = os.environ.get("LEADPILOT_DATA_DIR")
    if override:
        path = Path(override)
    elif _is_frozen():
        path = Path(os.environ.get("APPDATA", Path.home())) / "LeadPilotAI"
    else:
        path = base_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


class AppConfig(BaseModel):
    """Non secret application settings persisted to ``config.json``."""

    language: Language = "uz"
    demo_mode: bool = True
    database_file: str = "leadpilot.db"
    log_level: str = "INFO"
    remember_username: str | None = None
    window_maximized: bool = True
    poll_interval_ms: int = Field(default=4000, ge=1000, le=60000)
    autonomous_ai: bool = False

    @property
    def database_path(self) -> Path:
        """Absolute path of the SQLite database file."""
        return data_dir() / self.database_file

    @property
    def database_url(self) -> str:
        """SQLAlchemy connection URL."""
        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def logs_dir(self) -> Path:
        """Directory where rotating log files are written."""
        path = data_dir() / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def exports_dir(self) -> Path:
        """Default directory for generated reports."""
        path = data_dir() / "exports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def attachments_dir(self) -> Path:
        """Directory where message / knowledge base attachments are copied."""
        path = data_dir() / "attachments"
        path.mkdir(parents=True, exist_ok=True)
        return path


_CONFIG_PATH = data_dir() / "config.json"
_config: AppConfig | None = None


def load_config() -> AppConfig:
    """Load configuration from disk (cached)."""
    global _config
    if _config is not None:
        return _config
    if _CONFIG_PATH.exists():
        try:
            raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            _config = AppConfig(**raw)
        except Exception:  # pragma: no cover - corrupted config falls back
            _config = AppConfig()
    else:
        _config = AppConfig()
    return _config


def save_config(config: AppConfig | None = None) -> None:
    """Persist configuration to disk."""
    global _config
    if config is not None:
        _config = config
    if _config is None:
        return
    _CONFIG_PATH.write_text(
        json.dumps(_config.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
