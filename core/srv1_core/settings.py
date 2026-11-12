"""Sozlamalar: `config.toml` + `SRV1_*` muhit o'zgaruvchilari."""

import ipaddress
from pathlib import Path
from typing import Literal, Self, override

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

DEFAULT_CONFIG_TOML = """\
# SRV_1 sozlamalari. O'zgartirgandan keyin yadroni qayta ishga tushiring.
# Har qiymatni muhit o'zgaruvchisi bilan ham berish mumkin: SRV1_SERVER__PORT=8711

[server]
host = "127.0.0.1"
port = 8710
# Loopback bo'lmagan manzilga bog'lanish uchun ataylab true qiling.
allow_non_loopback = false

[logging]
level = "INFO"
max_bytes = 5000000
backup_count = 3

[events]
queue_size = 256
# Tizim holati hodisasi (system.stats) oralig'i, soniya. Obunachi bo'lmasa o'lchanmaydi.
stats_interval_s = 5.0

[plugins]
# Repozitoriydagi plugins/ papkasini yuklash.
load_builtin = true
# Qo'shimcha plagin papkalari (mutlaq yo'llar). <ma'lumotlar>/plugins har doim qaraladi.
dirs = []
"""


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class ServerSettings(_Section):
    host: str = "127.0.0.1"
    port: int = Field(default=8710, ge=1, le=65535)
    allow_non_loopback: bool = False

    @model_validator(mode="after")
    def _loopback_only_by_default(self) -> Self:
        if not is_loopback(self.host) and not self.allow_non_loopback:
            raise ValueError(
                f"host={self.host!r} loopback emas; ataylab ochish uchun "
                "server.allow_non_loopback = true qiling"
            )
        return self


class LoggingSettings(_Section):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    max_bytes: int = Field(default=5_000_000, ge=10_000)
    backup_count: int = Field(default=3, ge=0, le=50)


class EventSettings(_Section):
    queue_size: int = Field(default=256, ge=1, le=10_000)
    stats_interval_s: float = Field(default=5.0, ge=0.5, le=3600)


class PluginSettings(_Section):
    load_builtin: bool = True
    dirs: tuple[Path, ...] = ()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SRV1_", env_nested_delimiter="__", extra="ignore", frozen=True
    )

    server: ServerSettings = ServerSettings()
    logging: LoggingSettings = LoggingSettings()
    events: EventSettings = EventSettings()
    plugins: PluginSettings = PluginSettings()


def ensure_config_file(config_file: Path) -> bool:
    """Fayl yo'q bo'lsa standart `config.toml` yozadi. Yaratilgan bo'lsa `True`."""
    if config_file.exists():
        return False
    config_file.write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")
    return True


def load_settings(config_file: Path) -> Settings:
    """Ustuvorlik: muhit o'zgaruvchilari > `config.toml` > standart qiymatlar."""

    class _FileSettings(Settings):
        @classmethod
        @override
        def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> tuple[PydanticBaseSettingsSource, ...]:
            toml = TomlConfigSettingsSource(settings_cls, toml_file=config_file)
            return (init_settings, env_settings, toml)

    return _FileSettings()
