"""`electronics` plagini: platalar, USB identifikatorlari va sozlama (`electronics.json`)."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

STORE_FILE = "electronics.json"
Tool = Literal["esptool", "avrdude"]
JobState = Literal["idle", "running", "done", "failed", "cancelled"]


@dataclass(frozen=True)
class Board:
    key: str
    title: str
    tool: Tool
    # esptool: `--chip`; avrdude: `-p` (mikrokontroller).
    chip: str
    suffix: str
    # avrdude: `-c` (programmator protokoli) va bootloader tezligi.
    programmer: str = ""
    baudrate: int = 460800
    # esptool: fayl yoziladigan standart manzil.
    offset: str = "0x0"


# ESP32 oilasida ilova 0x10000 da turadi (bootloader va bo'limlar jadvali undan oldin);
# birlashtirilgan (merged) tasvir uchun manzilni 0x0 deb bering.
BOARDS: dict[str, Board] = {
    board.key: board
    for board in (
        Board("esp32", "ESP32", "esptool", "esp32", ".bin", offset="0x10000"),
        Board("esp32s2", "ESP32-S2", "esptool", "esp32s2", ".bin", offset="0x10000"),
        Board("esp32s3", "ESP32-S3", "esptool", "esp32s3", ".bin", offset="0x10000"),
        Board("esp32c3", "ESP32-C3", "esptool", "esp32c3", ".bin", offset="0x10000"),
        Board("esp32c6", "ESP32-C6", "esptool", "esp32c6", ".bin", offset="0x10000"),
        Board("esp8266", "ESP8266", "esptool", "esp8266", ".bin"),
        Board("uno", "Arduino Uno", "avrdude", "atmega328p", ".hex", "arduino", 115200),
        Board("nano", "Arduino Nano", "avrdude", "atmega328p", ".hex", "arduino", 115200),
        Board(
            "nano_old",
            "Arduino Nano (eski bootloader)",
            "avrdude",
            "atmega328p",
            ".hex",
            "arduino",
            57600,
        ),
        Board("mega2560", "Arduino Mega 2560", "avrdude", "atmega2560", ".hex", "wiring", 115200),
    )
}

# (VID, PID yoki None) -> (USB ko'prigi/plata nomi, taxminiy plata kaliti yoki "").
# CH340/CP210x/FTDI — faqat ko'prik: orqasida qaysi plata turgani USB'dan bilinmaydi.
_USB: tuple[tuple[int, int | None, str, str], ...] = (
    (0x2341, 0x0043, "Arduino Uno", "uno"),
    (0x2341, 0x0001, "Arduino Uno", "uno"),
    (0x2341, 0x0042, "Arduino Mega 2560", "mega2560"),
    (0x2341, 0x0010, "Arduino Mega 2560", "mega2560"),
    (0x2341, None, "Arduino", ""),
    (0x2A03, 0x0043, "Arduino Uno", "uno"),
    (0x2A03, 0x0042, "Arduino Mega 2560", "mega2560"),
    (0x2A03, None, "Arduino", ""),
    (0x303A, None, "Espressif USB", ""),
    (0x1A86, 0x7523, "CH340", ""),
    (0x1A86, 0x55D4, "CH9102", ""),
    (0x1A86, None, "WCH (CH34x)", ""),
    (0x10C4, 0xEA60, "CP210x", ""),
    (0x0403, 0x6001, "FTDI FT232R", ""),
    (0x0403, 0x6015, "FTDI FT231X", ""),
    (0x0403, None, "FTDI", ""),
    (0x067B, 0x2303, "PL2303", ""),
)


def identify_usb(vid: int | None, pid: int | None) -> tuple[str, str]:
    """USB identifikatori bo'yicha (nom, taxminiy plata). Noma'lum bo'lsa ikkala satr bo'sh."""
    if vid is None:
        return "", ""
    for known_vid, known_pid, name, board in _USB:
        if vid == known_vid and known_pid in (None, pid):
            return name, board
    return "", ""


def usb_id(vid: int | None, pid: int | None) -> str:
    return "" if vid is None or pid is None else f"{vid:04X}:{pid:04X}"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Config(_Model):
    # Bitta bosqich (zaxira yoki yozish) uchun vaqt chegarasi.
    timeout_s: float = Field(default=300.0, ge=1, le=3600)
    monitor_baudrate: int = Field(default=115200, ge=300, le=2_000_000)
    # Bo'sh bo'lsa standart joylar: `python -m esptool`, `tools/avrdude/avrdude.exe`.
    # To'ldirilsa — buyruqning boshi (dastur va uning doimiy argumentlari).
    esptool: list[str] = Field(default_factory=list[str], max_length=8)
    avrdude: list[str] = Field(default_factory=list[str], max_length=8)


class Store(_Model):
    config: Config = Config()


def load_store(path: Path) -> Store:
    """Fayl yo'q bo'lsa standart sozlama; buzuq bo'lsa xato (jim almashtirilmaydi)."""
    if not path.is_file():
        return Store()
    return Store.model_validate(json.loads(path.read_text(encoding="utf-8")))
