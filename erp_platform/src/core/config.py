# -*- coding: utf-8 -*-
"""
Konfiguratsiya tizimi.

config.yaml fayli birinchi ishga tushishda avtomatik generatsiya qilinadi.
Barcha sozlamalar DEFAULTS bilan chuqur birlashtiriladi (deep merge), shuning
uchun eski config fayllar yangi versiyalarda ham buzilmasdan ishlayveradi.
"""
from __future__ import annotations

import copy
import secrets
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - run.py auto-installer buni oldini oladi
    yaml = None

#: Standart sozlamalar — config.yaml shu asosda yaratiladi.
DEFAULTS: dict[str, Any] = {
    "app": {
        "name": "UzERP",
        "version": "1.0.0",
        "language": "uz",
        "currency": "UZS",
        "company_name": "Mening kompaniyam",
        "secret_key": "",  # birinchi ishga tushishda generatsiya qilinadi
    },
    "server": {
        "host": "127.0.0.1",
        "port": 8000,
        "debug": False,
    },
    "database": {
        "engine": "auto",  # auto | sqlite | postgresql
        "sqlite_path": "data/erp.db",
        "postgresql": {
            "host": "localhost",
            "port": 5432,
            "dbname": "uzerp",
            "user": "postgres",
            "password": "",
        },
    },
    "security": {
        "session_timeout_minutes": 30,
        "max_login_attempts": 5,
        "lockout_minutes": 15,
        "password_min_length": 8,
        "rate_limit_per_minute": 120,
    },
    "backup": {
        "auto_backup": True,
        "interval_hours": 24,
        "keep_last": 30,
    },
    "inventory": {
        "allow_negative_stock": False,  # True — ombor minusga tushishiga ruxsat
    },
    "accounting": {
        "vat_rate": 12.0,           # QQS stavkasi (O'zbekiston, %)
        "income_tax_rate": 12.0,    # Jismoniy shaxslar daromad solig'i (%)
        "pension_rate": 0.1,        # INPS badal stavkasi (%)
        "fiscal_year_start": "01-01",
    },
    "ui": {
        "theme": "dark",
        "page_size": 25,
    },
    "integrations": {
        # API kalitlari IXTIYORIY — bo'sh bo'lsa adapter "sozlanmagan"
        # holatda ishlaydi (so'rov tayyorlaydi, lekin yubormaydi).
        "telegram": {"token": "", "chat_id": ""},
        "email": {"smtp_host": "", "smtp_port": 587, "username": "",
                  "password": "", "sender": ""},
        "sms": {"provider": "eskiz", "token": "", "sender": "UzERP"},
        "click": {"merchant_id": "", "service_id": "", "secret_key": ""},
        "payme": {"merchant_id": "", "key": ""},
        "uzum": {"merchant_id": "", "secret_key": ""},
    },
    "logging": {
        "level": "INFO",
        "keep_days": 30,
    },
}

_HEADER = """\
# ============================================================
# UzERP konfiguratsiya fayli (avtomatik yaratilgan).
# O'zgartirishdan keyin dasturni qayta ishga tushiring.
# ============================================================
"""


def _deep_merge(base: dict, override: dict) -> dict:
    """Ikkita lug'atni rekursiv birlashtiradi (override ustunlik qiladi)."""
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Config:
    """
    Ilova konfiguratsiyasi.

    Nuqtali yo'l orqali qiymat olish mumkin::

        config.get("server.port")          # -> 8000
        config.get("app.secret_key")
    """

    def __init__(self, data: dict[str, Any], path: Path | None = None) -> None:
        self._data = data
        self._path = path

    # ------------------------------------------------------------------ #
    #  Yaratish / yuklash
    # ------------------------------------------------------------------ #

    @classmethod
    def ensure(cls, path: Path) -> "Config":
        """
        config.yaml faylini yuklaydi; mavjud bo'lmasa — DEFAULTS asosida
        yaratadi (secret_key avtomatik generatsiya qilinadi).
        """
        if yaml is None:
            raise RuntimeError(
                "PyYAML o'rnatilmagan. O'rnatish: pip install PyYAML"
            )
        if path.exists():
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            data = _deep_merge(DEFAULTS, raw)
            cfg = cls(data, path)
            if not cfg.get("app.secret_key"):
                cfg.set("app.secret_key", secrets.token_hex(32))
                cfg.save()
            return cfg

        data = copy.deepcopy(DEFAULTS)
        data["app"]["secret_key"] = secrets.token_hex(32)
        cfg = cls(data, path)
        cfg.save()
        return cfg

    def save(self) -> None:
        """Joriy sozlamalarni config.yaml ga yozadi."""
        if self._path is None or yaml is None:
            return
        text = _HEADER + yaml.safe_dump(
            self._data, allow_unicode=True, sort_keys=False, default_flow_style=False
        )
        self._path.write_text(text, encoding="utf-8")

    # ------------------------------------------------------------------ #
    #  O'qish / yozish
    # ------------------------------------------------------------------ #

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Nuqtali yo'l bo'yicha qiymatni qaytaradi (masalan ``server.port``)."""
        node: Any = self._data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted_key: str, value: Any) -> None:
        """Nuqtali yo'l bo'yicha qiymatni o'rnatadi (saqlash uchun save() chaqiring)."""
        parts = dotted_key.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def as_dict(self) -> dict[str, Any]:
        """Sozlamalarning nusxasini qaytaradi (himoya uchun deepcopy)."""
        return copy.deepcopy(self._data)
