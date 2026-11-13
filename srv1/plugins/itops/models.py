"""`itops` plagini sozlamasi (`itops.json`) va umumiy xato turi."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

STORE_FILE = "itops.json"
DEFAULT_PORTS = (22, 80, 443, 445, 502, 1883, 3389, 8080)


class ItopsError(Exception):
    """Amal bajarilmadi; `status` — klientga qaytadigan HTTP kodi."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _default_ports() -> list[int]:
    return list(DEFAULT_PORTS)


class Config(_Model):
    scan_ports: list[int] = Field(default_factory=_default_ports, min_length=1, max_length=32)
    scan_timeout_s: float = Field(default=0.6, ge=0.05, le=5)
    scan_concurrency: int = Field(default=128, ge=1, le=512)
    # Faqat sinov uchun: 127.0.0.0/8 ni skanerlashga ruxsat.
    scan_loopback: bool = False
    # Zaxira: 5 maydonli cron (bo'sh — jadvalsiz), saqlanadigan nusxalar soni.
    backup_cron: str = Field(default="0 3 * * *", max_length=64)
    backup_keep: int = Field(default=7, ge=1, le=365)
    # Bo'sh — plaginning `backups` papkasi; aks holda manifestdagi `paths` ichidagi papka.
    backup_destination: str = Field(default="", max_length=512)
    backup_projects: bool = False
    backup_logs: bool = False


class Store(_Model):
    config: Config = Config()


def load_store(path: Path) -> Store:
    """Fayl yo'q bo'lsa standart sozlama; buzuq bo'lsa xato (jim almashtirilmaydi)."""
    if not path.is_file():
        return Store()
    return Store.model_validate(json.loads(path.read_text(encoding="utf-8")))
