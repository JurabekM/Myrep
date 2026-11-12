"""Hosting sozlamalari va loyiha tavsifi; `hosting.json` da saqlanadi."""

import ipaddress
import json
import shlex
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

STORE_FILE = "hosting.json"
# Nom host yorlig'i bo'ladi: <nom>.localhost
NAME_PATTERN = r"^[a-z]([a-z0-9-]{0,30}[a-z0-9])?$"
Kind = Literal["static", "python", "node"]
State = Literal["stopped", "starting", "running", "sleeping", "failed"]


class HostingError(Exception):
    """Amal bajarilmadi; `status` — klientga qaytadigan HTTP kodi."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _split_command(value: Any) -> Any:  # noqa: ANN401 — pydantic'ning xom kirishi
    """`"node server.js"` -> `["node", "server.js"]`. Qo'shtirnoq ichidagi bo'shliq saqlanadi."""
    if isinstance(value, str):
        return [part.strip('"') for part in shlex.split(value, posix=False)]
    return value


class HostingConfig(_Model):
    listen_host: str = "127.0.0.1"
    listen_port: int = Field(default=8080, ge=1, le=65535)
    admin_port: int = Field(default=2019, ge=1, le=65535)
    wake_port: int = Field(default=9099, ge=1, le=65535)
    port_first: int = Field(default=9000, ge=1, le=65535)
    port_last: int = Field(default=9098, ge=1, le=65535)
    domain: str = Field(default="localhost", pattern=r"^[a-z0-9.-]{1,100}$")
    # Loopback bo'lmagan manzilda tinglash uchun ataylab true qilinadi.
    allow_non_loopback: bool = False
    ready_timeout_s: float = Field(default=20.0, ge=1, le=300)
    idle_check_s: float = Field(default=10.0, ge=0.2, le=600)
    # Bir vaqtda ochiq tunnellar soni (har biri alohida cloudflared jarayoni).
    tunnel_max: int = Field(default=2, ge=0, le=8)
    tunnel_timeout_s: float = Field(default=30.0, ge=1, le=300)
    # cloudflared buyrug'ining boshi; bo'sh bo'lsa `tools/cloudflared.exe`.
    tunnel_command: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _loopback_by_default(self) -> Self:
        try:
            loopback = ipaddress.ip_address(self.listen_host).is_loopback
        except ValueError:
            loopback = self.listen_host == "localhost"
        if not loopback and not self.allow_non_loopback:
            raise ValueError(
                f"listen_host={self.listen_host!r} loopback emas; allow_non_loopback = true qiling"
            )
        if self.port_last < self.port_first:
            raise ValueError("port_last port_first dan kichik")
        return self


class ProjectConfig(_Model):
    name: str = Field(pattern=NAME_PATTERN)
    kind: Kind
    # Ishga tushirish buyrug'i (shell ishlatilmaydi). `{port}` ajratilgan portga almashadi.
    command: Annotated[tuple[str, ...], BeforeValidator(_split_command)] = ()
    # Statik sayt uchun loyiha papkasi ichidagi ildiz ("" — papkaning o'zi).
    root: str = Field(default="", max_length=200)
    memory_limit_mb: int = Field(default=256, ge=64, le=2048)
    # 0 — hech qachon uxlatilmaydi.
    idle_minutes: float = Field(default=15.0, ge=0, le=1440)
    autostart: bool = False
    port: int | None = None

    @model_validator(mode="after")
    def _command_required(self) -> Self:
        if self.kind != "static" and not self.command:
            raise ValueError(f"{self.kind} loyihasi uchun command kerak")
        if self.kind == "static" and self.command:
            raise ValueError("statik saytda command bo'lmaydi")
        return self


class Store(_Model):
    config: HostingConfig = HostingConfig()
    projects: list[ProjectConfig] = Field(default_factory=list[ProjectConfig])


def load_store(path: Path) -> Store:
    """Fayl yo'q bo'lsa standart sozlama; buzuq bo'lsa xato (jim almashtirilmaydi)."""
    if not path.is_file():
        return Store()
    return Store.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_store(path: Path, store: Store) -> None:
    text = json.dumps(store.model_dump(mode="json"), ensure_ascii=False, indent=2)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
