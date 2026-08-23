"""Resurs fayllarini topish — manba daraxtida ham, paketda ham.

## Nega alohida modul kerak

Manba daraxtida `Path(__file__).parents[N]` bilan repo ildizini topish
ishlaydi. PyInstaller paketida esa fayllar butunlay boshqa joyda yotadi
(`sys._MEIPASS`), va `parents[N]` tasodifiy papkani ko'rsatadi.

Bu xato **eng yomon tarzda** namoyon bo'ladi: dastur to'g'ri yig'iladi,
testlar o'tadi, hatto `dist/` ichidan ishga tushirilganda ham ishlaydi —
chunki `dist/` repo ICHIDA va tasodifan to'g'ri yo'l chiqadi. Faqat
haqiqatan o'rnatilgandan keyin, boshqa papkada, sinadi.

Shuning uchun resurs yo'li BITTA joyda hisoblanadi va paketlash testi
repo tashqarisida bajariladi.
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """Dastur PyInstaller paketi ichida ishlayaptimi."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def resource_root() -> Path:
    """Resurs fayllari joylashgan ildiz papka.

    * paketda — PyInstaller ochgan vaqtinchalik/`_internal` papka;
    * manba daraxtida — repo ildizi.
    """
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]  # noqa: SLF001
    # .../apps/desktop/src/distribos/infrastructure/resources.py
    #  -> parents[5] = repo ildizi
    return Path(__file__).resolve().parents[5]


def resource_path(*parts: str) -> Path:
    """Resurs fayliga to'liq yo'l.

    >>> resource_path("contracts", "events", "registry.json")
    """
    return resource_root().joinpath(*parts)


def require_resource(*parts: str) -> Path:
    """Resursni topadi; yo'q bo'lsa TUSHUNARLI xato beradi.

    Jim `FileNotFoundError` o'rniga aniq sabab: paketda resurs
    yetishmasa, buni build muammosi ekanini darhol bilish kerak.
    """
    path = resource_path(*parts)
    if not path.exists():
        raise FileNotFoundError(
            f"Resurs topilmadi: {path}\n"
            f"(frozen={is_frozen()}, ildiz={resource_root()})\n"
            "Agar bu o'rnatilgan dastur bo'lsa — build'da resurs "
            "qo'shilmagan (`packaging/build_windows.py` dagi --add-data)."
        )
    return path
