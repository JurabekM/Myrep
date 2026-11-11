"""`plugin.toml` manifesti."""

import re
import tomllib
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

MANIFEST_FILE = "plugin.toml"
NAME_PATTERN = r"^[a-z][a-z0-9_]{1,31}$"
_SERIAL_RE = re.compile(r"COM[1-9][0-9]{0,2}")
_PORT_RANGE_RE = re.compile(r"(\d{1,5})\s*-\s*(\d{1,5})")


class ManifestError(ValueError):
    """`plugin.toml` yo'q, o'qib bo'lmaydi yoki yaroqsiz."""


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PortRange(_Frozen):
    start: int = Field(ge=1, le=65535)
    end: int = Field(ge=1, le=65535)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.end < self.start:
            raise ValueError(f"port oralig'i teskari: {self.start}-{self.end}")
        return self

    def __contains__(self, port: object) -> bool:
        return isinstance(port, int) and self.start <= port <= self.end


def _parse_port(value: Any) -> Any:  # noqa: ANN401 — pydantic'ning xom kirishi
    """`9000` yoki `"9000-9010"` ni `PortRange` kirishiga aylantiradi."""
    if isinstance(value, bool):
        raise ValueError("port bool bo'lishi mumkin emas")
    if isinstance(value, int):
        return {"start": value, "end": value}
    if isinstance(value, str):
        match = _PORT_RANGE_RE.fullmatch(value.strip())
        if match is None:
            raise ValueError(f"port oralig'i 'a-b' ko'rinishida bo'lsin: {value!r}")
        return {"start": int(match[1]), "end": int(match[2])}
    return value


class Permissions(_Frozen):
    """Plagin so'rashi mumkin bo'lgan resurslar. Ro'yxatda yo'q narsa rad etiladi."""

    paths: tuple[Path, ...] = ()
    ports: tuple[Annotated[PortRange, BeforeValidator(_parse_port)], ...] = ()
    serial: tuple[str, ...] = ()
    # Jarayon ishga tushirish (`ctx.spawn`) — har biri auditga yoziladi.
    spawn: bool = False
    # Umumiy `<ma'lumotlar>/projects` papkasiga kirish.
    projects: bool = False

    @field_validator("paths")
    @classmethod
    def _absolute(cls, value: tuple[Path, ...]) -> tuple[Path, ...]:
        for path in value:
            if not path.is_absolute():
                raise ValueError(f"ruxsat yo'li mutlaq bo'lishi shart: {path}")
        return value

    @field_validator("serial")
    @classmethod
    def _com_ports(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalised = tuple(device.strip().upper() for device in value)
        for device in normalised:
            if _SERIAL_RE.fullmatch(device) is None:
                raise ValueError(f"serial qurilma COMn ko'rinishida bo'lsin: {device!r}")
        return normalised


class PluginManifest(_Frozen):
    name: str = Field(pattern=NAME_PATTERN)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+([.+-][0-9A-Za-z.+-]+)?$")
    description: str = Field(default="", max_length=300)
    mode: Literal["inprocess", "subprocess"] = "inprocess"
    heavy: bool = False
    memory_limit_mb: int = Field(default=256, ge=64, le=4096)
    permissions: Permissions = Permissions()

    @model_validator(mode="after")
    def _heavy_runs_in_subprocess(self) -> Self:
        if self.heavy and self.mode != "subprocess":
            raise ValueError("heavy = true plagin faqat mode = 'subprocess' bilan ishlaydi")
        return self


def load_manifest(plugin_dir: Path) -> PluginManifest:
    """`plugin_dir/plugin.toml` ni o'qiydi. Papka nomi `name` bilan bir xil bo'lishi shart."""
    manifest_file = plugin_dir / MANIFEST_FILE
    try:
        with manifest_file.open("rb") as fh:
            raw = tomllib.load(fh)
    except FileNotFoundError as exc:
        raise ManifestError(f"{MANIFEST_FILE} topilmadi: {plugin_dir}") from exc
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ManifestError(f"{manifest_file} o'qilmadi: {exc}") from exc
    try:
        manifest = PluginManifest.model_validate(raw)
    except ValidationError as exc:
        raise ManifestError(f"{manifest_file} yaroqsiz: {exc}") from exc
    if manifest.name != plugin_dir.name:
        raise ManifestError(
            f"papka nomi ({plugin_dir.name!r}) manifestdagi name ({manifest.name!r}) bilan mos emas"
        )
    return manifest
