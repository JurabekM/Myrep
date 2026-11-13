"""`monitor` plagini sozlamasi (`monitor.json`), o'lchov tuzilmasi va xato turi."""

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

STORE_FILE = "monitor.json"
GB = 1024**3
MB = 1024**2


class MonitorError(Exception):
    """Amal bajarilmadi; `status` — klientga qaytadigan HTTP kodi."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Thresholds(_Model):
    """Ogohlantirish chegaralari. `0` — shu qoida o'chirilgan."""

    # RAM bandligi shu foizga yetsa.
    memory_percent: float = Field(default=90.0, ge=0, le=100)
    # CPU shu foizdan `cpu_minutes` daqiqa uzluksiz past tushmasa.
    cpu_percent: float = Field(default=90.0, ge=0, le=100)
    cpu_minutes: float = Field(default=5.0, ge=0, le=120)
    # Istalgan qattiq diskda bo'sh joy shundan kam bo'lsa.
    disk_free_gb: float = Field(default=10.0, ge=0, le=100_000)


class Config(_Model):
    # O'lchovlar orasi. O'zgartirilsa, plaginni o'chirib-yoqish kerak.
    interval_s: float = Field(default=15.0, ge=0.2, le=3600)
    retention_days: float = Field(default=7.0, gt=0, le=365)
    thresholds: Thresholds = Thresholds()


class Store(_Model):
    config: Config = Config()


def load_store(path: Path) -> Store:
    """Fayl yo'q bo'lsa standart sozlama; buzuq bo'lsa xato (jim almashtirilmaydi)."""
    if not path.is_file():
        return Store()
    return Store.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_store(path: Path, store: Store) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(store.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(path)


@dataclass(frozen=True, slots=True)
class Disk:
    mount: str
    free: int
    total: int


@dataclass(frozen=True, slots=True)
class Sample:
    """Bitta o'lchov. Xotira va disk — baytlarda, CPU va RAM bandligi — foizda."""

    ts: float
    cpu: float
    memory: float
    memory_used: int
    memory_total: int
    srv1_rss: int
    disks: tuple[Disk, ...]
