"""Ma'lumotlar papkasi va xavfsiz yo'l birlashtirish."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ENV_DATA_DIR = "SRV1_DATA_DIR"
APP_DIR_NAME = "SRV_1"


class PathTraversalError(ValueError):
    """So'ralgan yo'l ruxsat etilgan papkadan tashqariga chiqadi."""


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


def safe_join(base: Path, *parts: str) -> Path:
    """`base` ichidagi yo'lni qaytaradi; tashqariga chiqsa `PathTraversalError`."""
    for part in parts:
        _check_part(part)
    resolved_base = base.resolve()
    candidate = resolved_base.joinpath(*parts).resolve()
    if not candidate.is_relative_to(resolved_base):
        raise PathTraversalError(f"yo'l ruxsat etilgan papkadan tashqarida: {'/'.join(parts)}")
    return candidate


_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"COM{n}" for n in range(1, 10)}
    | {f"LPT{n}" for n in range(1, 10)}
)


def _check_part(part: str) -> None:
    # ':' — disk harfi (C:foo) va NTFS muqobil oqimlari (a.txt:stream) ni yopadi.
    if not part or "\x00" in part or ":" in part:
        raise PathTraversalError(f"yaroqsiz yo'l bo'lagi: {part!r}")
    for component in part.replace("\\", "/").split("/"):
        _check_component(component)


def _check_component(component: str) -> None:
    if component in ("", ".", ".."):
        return  # '..' ni yakuniy `is_relative_to` tekshiruvi hal qiladi
    # Windows oxiridagi nuqta/bo'shliqni jimgina olib tashlaydi: "a.txt." == "a.txt".
    if component[-1] in ". ":
        raise PathTraversalError(f"nom nuqta yoki bo'shliq bilan tugaydi: {component!r}")
    # Qurilma nomlari kengaytma bilan ham qurilma bo'lib qoladi: "NUL.txt".
    if component.split(".", 1)[0].rstrip(" ").upper() in _RESERVED_NAMES:
        raise PathTraversalError(f"Windows qurilma nomi: {component!r}")
