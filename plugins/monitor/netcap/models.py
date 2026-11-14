"""Tarmoq kuzatuvi sozlamasi (`netcap.json`). Plagin tomoni: ishchi jarayon buni import qilmaydi."""

import json
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from .engine import normalize_ip

CONFIG_FILE = "netcap.json"
MAX_EXCLUDED = 500

# BPF ifodasi ushlash kutubxonasiga (libpcap) beriladi, buyruq qatoriga emas; baribir
# faqat ifodada uchraydigan belgilar qabul qilinadi.
BPF_PATTERN = r"^[A-Za-z0-9 .:/()\[\]!=<>&|_-]*$"


def _check_excluded(value: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(normalize_ip(item) for item in value))


class NetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Oxirgi tanlangan interfeys (ushlash qayta ishga tushganda shu ishlatiladi).
    interface: str = Field(default="", max_length=200)
    bpf_filter: str = Field(default="", max_length=200, pattern=BPF_PATTERN)
    # Paket ichidagi matnning boshi (256 belgi) bazaga yozilsinmi. Ochiq uzatilgan
    # parollar ham shu matnda bo'lishi mumkin — shuning uchun standart holatda o'chiq.
    store_payload: bool = False
    # Tashqi IP manzillar `ip-api.com` dan so'ralsinmi (HTTP, uchinchi tomon).
    geo: bool = False
    excluded: Annotated[tuple[str, ...], AfterValidator(_check_excluded)] = Field(
        default=(), max_length=MAX_EXCLUDED
    )
    suspicious_ports: tuple[Annotated[int, Field(ge=1, le=65535)], ...] = Field(
        default=(23, 4444, 5555, 6667, 31337), max_length=100
    )
    scan_ports: int = Field(default=15, ge=3, le=1000)
    scan_window_s: float = Field(default=10.0, ge=1, le=600)
    # Bazada saqlanadigan paket yozuvlari soni (eskilari o'chiriladi).
    max_packets: int = Field(default=20_000, ge=100, le=200_000)
    worker_memory_mb: int = Field(default=200, ge=96, le=1024)

    def worker_options(self, interface: str) -> dict[str, object]:
        """Ishchi jarayonga beriladigan sozlama (`engine.Options.from_json`)."""
        return {
            "interface": interface,
            "bpf_filter": self.bpf_filter,
            "store_payload": self.store_payload,
            "geo": self.geo,
            "excluded": list(self.excluded),
            "suspicious_ports": list(self.suspicious_ports),
            "scan_ports": self.scan_ports,
            "scan_window_s": self.scan_window_s,
        }


def load_config(path: Path) -> NetConfig:
    """Fayl yo'q bo'lsa standart sozlama; buzuq bo'lsa xato (jim almashtirilmaydi)."""
    if not path.is_file():
        return NetConfig()
    return NetConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_config(path: Path, config: NetConfig) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(config.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(path)
