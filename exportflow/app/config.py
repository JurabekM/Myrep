"""Application-wide configuration and filesystem paths.

Everything the application writes (database, logs, exports, attachments) lives
under a single writable data directory so that a PyInstaller one-file build
never tries to write next to the frozen executable.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "ExportFlow"
APP_VERSION = "1.0.0"
ORG_NAME = "ExportFlow"

DEFAULT_TIMEZONE = "Asia/Tashkent"
DATE_FORMAT = "%d.%m.%Y"
DATETIME_FORMAT = "%d.%m.%Y %H:%M"
BASE_CURRENCY = "USD"
SUPPORTED_CURRENCIES = ("USD", "EUR", "UZS")
SUPPORTED_LANGUAGES = ("uz", "ru", "en")


def _is_frozen() -> bool:
    """Return True when running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def package_root() -> Path:
    """Directory that contains bundled read-only resources."""
    if _is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def data_root() -> Path:
    """Writable data directory (per-user)."""
    override = os.environ.get("EXPORTFLOW_HOME")
    if override:
        return Path(override).expanduser().resolve()
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


@dataclass(frozen=True)
class Paths:
    """Resolved filesystem layout used across the application."""

    root: Path = field(default_factory=data_root)

    @property
    def database_file(self) -> Path:
        return self.root / "exportflow.db"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def exports_dir(self) -> Path:
        return self.root / "exports"

    @property
    def attachments_dir(self) -> Path:
        return self.root / "attachments"

    @property
    def media_dir(self) -> Path:
        return self.root / "media"

    @property
    def outbox_dir(self) -> Path:
        return self.root / "outbox"

    @property
    def settings_file(self) -> Path:
        return self.root / "settings.json"

    @property
    def templates_dir(self) -> Path:
        return package_root() / "templates"

    @property
    def resources_dir(self) -> Path:
        return package_root() / "resources"

    def ensure(self) -> Paths:
        """Create every writable directory if it does not exist yet."""
        for directory in (
            self.root,
            self.logs_dir,
            self.exports_dir,
            self.attachments_dir,
            self.media_dir,
            self.outbox_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return self


PATHS = Paths()


def database_url() -> str:
    """SQLAlchemy URL for the local SQLite database."""
    override = os.environ.get("EXPORTFLOW_DB_URL")
    if override:
        return override
    return f"sqlite+pysqlite:///{PATHS.database_file.as_posix()}"
