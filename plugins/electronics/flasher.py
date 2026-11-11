"""Proshivka dasturlari: joyini topish va buyruq satrini tuzish (`shell`siz, argv ro'yxati)."""

import os
import re
import sys
from importlib import metadata
from pathlib import Path

from .models import Board, Config

ESP_BAUDRATES = (115200, 230400, 460800, 921600)
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def avrdude_exe() -> Path:
    """`SRV1_AVRDUDE_EXE` yoki repozitoriydagi `tools/avrdude/avrdude.exe`."""
    override = os.environ.get("SRV1_AVRDUDE_EXE")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "tools" / "avrdude" / "avrdude.exe"


def _base_python() -> str:
    # venv'dagi python.exe — ishga tushirgich; haqiqiy interpretator to'g'ridan-to'g'ri chaqiriladi.
    return getattr(sys, "_base_executable", sys.executable)


def tool_prefix(board: Board, config: Config) -> list[str] | None:
    """Buyruqning boshi; dastur topilmasa `None`."""
    if board.tool == "esptool":
        if config.esptool:
            return list(config.esptool)
        return [_base_python(), "-m", "esptool"] if esptool_version() else None
    if config.avrdude:
        return list(config.avrdude)
    exe = avrdude_exe()
    return [str(exe)] if exe.is_file() else None


def esptool_version() -> str:
    try:
        return metadata.version("esptool")
    except metadata.PackageNotFoundError:
        return ""


def tool_env() -> dict[str, str]:
    """Bola jarayon muhiti: yadro sozlamalarisiz, rangsiz va buferlanmagan chiqish bilan."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("SRV1_")}
    if _base_python() != sys.executable:
        env["__PYVENV_LAUNCHER__"] = sys.executable  # asosiy interpretator venv'ni ko'rsin
    env |= {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        "NO_COLOR": "1",
        "TERM": "dumb",
        "COLUMNS": "100",
    }
    return env


def esp_write_command(
    prefix: list[str],
    board: Board,
    port: str,
    file: Path,
    *,
    offset: str,
    baudrate: int,
    erase: bool,
) -> list[str]:
    head = [*prefix, "--chip", board.chip, "--port", port, "--baud", str(baudrate), "write-flash"]
    return [*head, *(["--erase-all"] if erase else []), offset, str(file)]


def esp_backup_command(
    prefix: list[str], board: Board, port: str, target: Path, *, baudrate: int
) -> list[str]:
    """Butun flesh xotirani faylga o'qiydi (`ALL` — hajmni esptool o'zi aniqlaydi)."""
    head = [*prefix, "--chip", board.chip, "--port", port, "--baud", str(baudrate)]
    return [*head, "read-flash", "0", "ALL", str(target)]


def avr_write_command(prefix: list[str], board: Board, port: str, filename: str) -> list[str]:
    """`filename` — ish papkasiga nisbatan nom: `-U` ichida disk harfining `:` belgisi bo'lmasin.

    `-D` — yozishdan oldin butun xotirani o'chirmaslik (bootloader orqali yozishda shart).
    """
    head = [*prefix, "-p", board.chip, "-c", board.programmer, "-P", port]
    return [*head, "-b", str(board.baudrate), "-D", "-U", f"flash:w:{filename}:i"]


def clean_output(text: str) -> list[str]:
    """Bitta chiqish satri: ANSI kodlarisiz, `\\r` bilan yangilangan qismlarga bo'lingan."""
    parts = (part.strip() for part in _ANSI_RE.sub("", text).split("\r"))
    return [part for part in parts if part]
