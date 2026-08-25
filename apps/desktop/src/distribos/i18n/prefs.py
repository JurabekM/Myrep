"""Foydalanuvchi til tanlovini diskda saqlash.

`AppSettings.language` (`infrastructure/config.py`) atayin muhit
o'zgaruvchisidan (`LANGUAGE`) o'qiladi — bu o'rnatuvchi/administrator
uchun. Foydalanuvchi esa Sozlamalar ekranida tilni bosib tanlaydi;
bu tanlov muhit o'zgaruvchisiga YOZILMAYDI (jarayon ichidan o'zgartirib
bo'lmaydi), shuning uchun alohida, kichik faylda saqlanadi va u
`AppSettings.language`dan USTUN turadi.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_FILE_NAME = "language.json"


def load_saved_locale(data_dir: Path) -> str | None:
    """Oldin saqlangan til tanlovi. Yo'q yoki buzuq bo'lsa — `None`."""
    path = data_dir / _FILE_NAME
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Til sozlamasi o'qilmadi: %s", path, exc_info=True)
        return None
    locale = data.get("locale")
    return locale if isinstance(locale, str) else None


def save_locale(data_dir: Path, locale: str) -> None:
    """Til tanlovini saqlaydi. Keyingi ishga tushirishda kuchga kiradi."""
    path = data_dir / _FILE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"locale": locale}, ensure_ascii=False), encoding="utf-8")
