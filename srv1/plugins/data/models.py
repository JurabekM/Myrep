"""`data` plagini sozlamasi va to'plamlar ro'yxati; `data.json` da saqlanadi."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

STORE_FILE = "data.json"
# To'plam nomi SQL'da jadval nomi bo'ladi: FROM sotuvlar
NAME_PATTERN = r"^[a-z][a-z0-9_]{0,47}$"
DatasetState = Literal["importing", "ready", "failed"]
Encoding = Literal["auto", "utf-8", "cp1251"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataConfig(_Model):
    # DuckDB xotira chegarasi (loyiha talabi: 400 MB).
    memory_limit: str = Field(default="400MB", pattern=r"^\d{2,5}(MB|GB)$")
    threads: int = Field(default=2, ge=1, le=16)
    query_timeout_s: float = Field(default=25.0, ge=0.5, le=28)
    max_rows: int = Field(default=1000, ge=10, le=5000)
    temp_limit: str = Field(default="2GB", pattern=r"^\d{1,5}(MB|GB)$")


class Column(_Model):
    name: str
    type: str


class Dataset(_Model):
    name: str = Field(pattern=NAME_PATTERN)
    state: DatasetState = "importing"
    source: str = ""
    rows: int = 0
    columns: list[Column] = Field(default_factory=list[Column])
    size: int = 0
    imported: float = 0.0
    seconds: float = 0.0
    error: str | None = None


class Store(_Model):
    config: DataConfig = DataConfig()
    datasets: list[Dataset] = Field(default_factory=list[Dataset])


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
