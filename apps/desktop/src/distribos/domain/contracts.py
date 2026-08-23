"""Hodisa kontraktlarini `contracts/events/registry.json` dan yuklaydi.

Python va Kotlin modellari qo'lda ikki joyda yuritilmaydi — ikkalasi ham
SHU faylni o'qiydi. Nomuvofiqlikni `tests/contract/` qulflaydi.

Validatsiya fail-closed: noma'lum hodisa turi, yetishmayotgan majburiy
maydon yoki noto'g'ri tip — hodisa RAD ETILADI, jimgina o'tkazilmaydi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import cache
from pathlib import Path
from typing import Any


def _registry_path() -> Path:
    """Kontrakt faylining yo'li.

    Paketda va manba daraxtida BOSHQA-BOSHQA joyda yotadi, shuning uchun
    `infrastructure.resources` orqali hisoblanadi (u yerdagi izohga
    qarang — bu tasodifan "ishlaydigan" xato sinfini yopadi).
    """
    from distribos.infrastructure.resources import resource_path

    return resource_path("contracts", "events", "registry.json")


class ContractError(ValueError):
    """Hodisa kontraktga mos emas."""


@dataclass(frozen=True, slots=True)
class EventContract:
    event_type: str
    schema_version: int
    aggregate_type: str
    conflict_strategy: str
    required: tuple[str, ...]
    optional: tuple[str, ...]
    types: dict[str, str]
    line_fields: dict[str, Any] | None = None

    @property
    def known_fields(self) -> frozenset[str]:
        return frozenset(self.required) | frozenset(self.optional)


@dataclass(frozen=True, slots=True)
class ContractRegistry:
    contract_version: int
    envelope_fields: tuple[str, ...]
    events: dict[str, EventContract]
    conflict_strategies: dict[str, str]

    def get(self, event_type: str) -> EventContract:
        contract = self.events.get(event_type)
        if contract is None:
            raise ContractError(
                f"Noma'lum hodisa turi: {event_type!r}. Noma'lum hodisa "
                "qabul qilinmaydi — bu eskirgan yoki soxta klient belgisi."
            )
        return contract

    def validate(self, event_type: str, payload: dict[str, Any], schema_version: int = 1) -> None:
        """Payload'ni kontraktga solishtiradi. Xato bo'lsa `ContractError`."""
        contract = self.get(event_type)

        if schema_version > contract.schema_version:
            raise ContractError(
                f"{event_type}: schema_version={schema_version} biz "
                f"biladigan {contract.schema_version} dan yangi. Ilovani "
                "yangilash kerak — noma'lum sxemani taxmin qilib "
                "qo'llamaymiz."
            )

        missing = [name for name in contract.required if name not in payload]
        if missing:
            raise ContractError(f"{event_type}: majburiy maydonlar yo'q: {missing}")

        unknown = set(payload) - contract.known_fields
        if unknown:
            raise ContractError(
                f"{event_type}: noma'lum maydonlar: {sorted(unknown)}"
            )

        for name, value in payload.items():
            expected = contract.types.get(name)
            if expected is not None and value is not None:
                _check_type(event_type, name, expected, value)

        if contract.line_fields and "lines" in payload:
            _validate_lines(event_type, contract, payload["lines"])


def _validate_lines(event_type: str, contract: EventContract, lines: Any) -> None:
    if not isinstance(lines, list):
        raise ContractError(f"{event_type}: `lines` ro'yxat bo'lishi kerak")
    spec = contract.line_fields or {}
    required = spec.get("required", [])
    known = set(required) | set(spec.get("optional", []))
    types = spec.get("types", {})

    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            raise ContractError(f"{event_type}: lines[{index}] obyekt emas")
        missing = [name for name in required if name not in line]
        if missing:
            raise ContractError(f"{event_type}: lines[{index}] da yo'q: {missing}")
        unknown = set(line) - known
        if unknown:
            raise ContractError(
                f"{event_type}: lines[{index}] noma'lum maydon: {sorted(unknown)}"
            )
        for name, value in line.items():
            expected = types.get(name)
            if expected is not None and value is not None:
                _check_type(f"{event_type}.lines[{index}]", name, expected, value)


def _check_type(context: str, name: str, expected: str, value: Any) -> None:
    """Tip tekshiruvi.

    `money` — BUTUN son (tiyin). Float kelsa rad etiladi: moliyaviy
    qiymatda suzuvchi nuqta yaxlitlash xatosini keltiradi.
    `decimal` — matn sifatida uzatiladi (aynan shu sababdan).
    """
    if expected == "string":
        if not isinstance(value, str):
            raise ContractError(f"{context}.{name}: matn kutildi, {type(value).__name__} keldi")
    elif expected == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ContractError(f"{context}.{name}: butun son kutildi")
    elif expected == "money":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ContractError(
                f"{context}.{name}: pul BUTUN son (tiyin) bo'lishi kerak, "
                f"{type(value).__name__} keldi — float moliyaviy aniqlikni buzadi"
            )
    elif expected == "decimal":
        if isinstance(value, float):
            raise ContractError(
                f"{context}.{name}: `decimal` matn sifatida uzatiladi "
                "(masalan \"12.500\"), float emas"
            )
        try:
            Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ContractError(f"{context}.{name}: son emas: {value!r}") from exc
    elif expected in ("timestamp", "date"):
        if not isinstance(value, str):
            raise ContractError(f"{context}.{name}: ISO-8601 matn kutildi")
    elif expected == "list":
        if not isinstance(value, list):
            raise ContractError(f"{context}.{name}: ro'yxat kutildi")
    elif expected == "map":
        if not isinstance(value, dict):
            raise ContractError(f"{context}.{name}: obyekt kutildi")


@cache
def load_registry(path: Path | None = None) -> ContractRegistry:
    """Kontraktlarni yuklaydi (bir marta, keshlanadi)."""
    source = path or _registry_path()
    if not source.exists():
        raise ContractError(f"Kontrakt fayli topilmadi: {source}")

    raw = json.loads(source.read_text(encoding="utf-8"))
    events = {
        name: EventContract(
            event_type=name,
            schema_version=int(spec["schema_version"]),
            aggregate_type=spec["aggregate_type"],
            conflict_strategy=spec["conflict_strategy"],
            required=tuple(spec.get("required", [])),
            optional=tuple(spec.get("optional", [])),
            types=dict(spec.get("types", {})),
            line_fields=spec.get("line_fields"),
        )
        for name, spec in raw["events"].items()
    }
    return ContractRegistry(
        contract_version=int(raw["contract_version"]),
        envelope_fields=tuple(raw["envelope_fields"]),
        events=events,
        conflict_strategies=dict(raw["conflict_strategies"]),
    )
