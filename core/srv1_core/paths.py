"""Ma'lumotlar papkasi va xavfsiz yo'l birlashtirish."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from srv1_sdk.pathsafe import PathTraversalError, safe_join

__all__ = ["DataPaths", "PathTraversalError", "resolve_data_dir", "safe_join"]

ENV_DATA_DIR = "SRV1_DATA_DIR"
APP_DIR_NAME = "SRV_1"


@dataclass(frozen=True, slots=True)
class DataPaths:
    """Ma'lumotlar papkasi ichidagi barcha yo'llar."""

    root: Path

    @property
    def config_file(self) -> Path:
        return self.root / "config.toml"

    @property
    def db_file(self) -> Path:
        return self.root / "srv1.db"

    @property
    def token_file(self) -> Path:
        return self.root / "auth.token"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def projects_dir(self) -> Path:
        return self.root / "projects"

    @property
    def plugins_dir(self) -> Path:
        return self.root / "plugins"

    def plugin_data_dir(self, name: str) -> Path:
        """Plaginning o'z ish papkasi: `plugins/<nom>/data`."""
        return safe_join(self.plugins_dir, name, "data")

    def ensure(self) -> None:
        """Papka va ichki papkalarni yaratadi (bor bo'lsa tegmaydi)."""
        for directory in (self.root, self.logs_dir, self.projects_dir, self.plugins_dir):
            directory.mkdir(parents=True, exist_ok=True)


def resolve_data_dir(env: Mapping[str, str] | None = None) -> Path:
    """`SRV1_DATA_DIR` yoki `%PROGRAMDATA%\\SRV_1` ni qaytaradi."""
    source = os.environ if env is None else env
    override = source.get(ENV_DATA_DIR, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    program_data = source.get("PROGRAMDATA", "").strip() or r"C:\ProgramData"
    return (Path(program_data) / APP_DIR_NAME).resolve()
