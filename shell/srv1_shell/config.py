"""Shell sozlamalari (til, yadro manzili) va tokenni topish. Token faylga saqlanmaydi."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from srv1_shell.translations import DEFAULT_LANGUAGE, LANGUAGE_NAMES

ENV_CONFIG = "SRV1_SHELL_CONFIG"
ENV_DATA_DIR = "SRV1_DATA_DIR"


@dataclass(slots=True)
class ShellConfig:
    language: str = DEFAULT_LANGUAGE
    host: str = "127.0.0.1"
    port: int = 8710

    @property
    def http_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}/ws/events"


def config_path() -> Path:
    override = os.environ.get(ENV_CONFIG, "").strip()
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA", "").strip() or str(Path.home())
    return Path(appdata) / "SRV_1" / "shell.json"


def load_config(path: Path | None = None) -> ShellConfig:
    """Fayl yo'q yoki buzuq bo'lsa standart qiymatlar qaytadi."""
    source = path or config_path()
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ShellConfig()
    if not isinstance(raw, dict):
        return ShellConfig()
    config = ShellConfig()
    language, host, port = raw.get("language"), raw.get("host"), raw.get("port")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    if isinstance(language, str) and language in LANGUAGE_NAMES:
        config.language = language
    if isinstance(host, str) and host:
        config.host = host
    if isinstance(port, int) and not isinstance(port, bool) and 1 <= port <= 65535:
        config.port = port
    return config


def save_config(config: ShellConfig, path: Path | None = None) -> None:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")


def default_token_file() -> Path:
    """Yadro tokeni: `SRV1_DATA_DIR` yoki `%PROGRAMDATA%\\SRV_1` ichidagi `auth.token`."""
    override = os.environ.get(ENV_DATA_DIR, "").strip()
    if override:
        return Path(override) / "auth.token"
    program_data = os.environ.get("PROGRAMDATA", "").strip() or r"C:\ProgramData"
    return Path(program_data) / "SRV_1" / "auth.token"


def read_token(token_file: Path) -> str | None:
    try:
        token = token_file.read_text(encoding="ascii").strip()
    except (OSError, ValueError):
        return None
    return token or None
