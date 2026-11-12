"""IoT sozlamalari; `iot.json` da saqlanadi."""

import ipaddress
import json
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

STORE_FILE = "iot.json"
NAME_PATTERN = r"^[a-z][a-z0-9_-]{0,31}$"
TOPIC_MAX = 256

RegisterKind = Literal["holding", "input", "coil", "discrete"]
DataType = Literal["uint16", "int16", "uint32", "int32", "float32", "bool"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"


class MqttConfig(_Model):
    enabled: bool = True
    # true — Mosquitto'ni plagin o'zi ishga tushiradi; false — tashqi brokerga ulanadi.
    manage_broker: bool = True
    host: str = "127.0.0.1"
    port: int = Field(default=1883, ge=1, le=65535)
    # Broker tinglaydigan manzil (faqat manage_broker = true bo'lganda).
    listen_host: str = "127.0.0.1"
    allow_non_loopback: bool = False
    username: str = Field(default="", max_length=64, pattern=r"^[^:\s]*$")
    password: str = Field(default="", max_length=128)
    subscriptions: list[str] = Field(default_factory=lambda: ["srv1/#"])

    @model_validator(mode="after")
    def _network_exposure_needs_flag_and_password(self) -> Self:
        if self.manage_broker and not _is_loopback(self.listen_host):
            if not self.allow_non_loopback:
                raise ValueError(
                    f"listen_host={self.listen_host!r} loopback emas; "
                    "allow_non_loopback = true qiling"
                )
            if not self.username or len(self.password) < 8:
                raise ValueError(
                    "tarmoqqa ochiq broker uchun username va kamida 8 belgili password shart"
                )
        return self


class Register(_Model):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    address: int = Field(ge=0, le=65535)
    kind: RegisterKind = "holding"
    type: DataType = "uint16"
    scale: float = 1.0

    @model_validator(mode="after")
    def _bits_are_bool(self) -> Self:
        is_bit = self.kind in ("coil", "discrete")
        if is_bit != (self.type == "bool"):
            raise ValueError("coil/discrete uchun type = 'bool', registrlar uchun son turi kerak")
        return self


class ModbusDevice(_Model):
    name: str = Field(pattern=NAME_PATTERN)
    transport: Literal["tcp", "rtu"] = "tcp"
    host: str = Field(default="127.0.0.1", max_length=255)
    port: int = Field(default=502, ge=1, le=65535)
    serial_port: str = ""
    baudrate: int = Field(default=9600, ge=300, le=921600)
    unit: int = Field(default=1, ge=0, le=255)
    interval_s: float = Field(default=5.0, ge=0.1, le=3600)
    timeout_s: float = Field(default=2.0, ge=0.1, le=30)
    registers: list[Register] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def _rtu_needs_port(self) -> Self:
        if self.transport == "rtu" and not self.serial_port:
            raise ValueError("rtu uchun serial_port kerak")
        if len({register.key for register in self.registers}) != len(self.registers):
            raise ValueError("registr kalitlari takrorlanmasin")
        return self


class Store(_Model):
    mqtt: MqttConfig = MqttConfig()
    modbus: list[ModbusDevice] = Field(default_factory=list[ModbusDevice])
    retention_days: float = Field(default=30.0, ge=0.001, le=3650)


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
