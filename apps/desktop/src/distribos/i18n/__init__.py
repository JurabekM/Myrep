"""Lokalizatsiya — uz-Latn (asosiy) va rus tili.

## Nima uchun Kirill yo'q

Topshiriqda uz-Kirill ham so'ralgan edi, lekin buyurtma bergan tomon
buni keyinchalik olib tashladi: faqat uz-Latn (asosiy, o'zgarmas) va
rus tili kerak.

## Arxitektura — nega "kalit" emas, matnning o'zi

Ko'p i18n tizimi alohida kalit talab qiladi (`tr("orders.title")`).
Bu loyihada YUZLAB literal o'zbekcha satr allaqachon yozilgan
(`presentation/pages/*.py` bo'ylab). Ularning har biriga sun'iy kalit
o'ylab topish katta, xatoga moyil qayta ishlash bo'lardi va ikki
manbani (kod + kalit lug'ati) sinxronlashda tez orada chalkashardi.

Shuning uchun `gettext` uslubi tanlandi: **kalit — o'zbekcha matnning
O'ZI**. `tr("Saqlash")` — "Saqlash" ham chaqiruv, ham lug'at kaliti.
Afzalliklari:

* kodni o'qish qiyinlashmaydi — `tr("Saqlash")` va `"Saqlash"` deyarli
  bir xil ko'rinadi;
* tarjima YO'Q bo'lsa — ASL O'ZBEKCHA MATN ko'rsatiladi, bo'sh joy yoki
  `KeyError` emas (fail-safe, foydalanuvchi hech qachon bo'sh tugma
  ko'rmaydi);
* qaysi matnlar hali tarjima qilinmaganini topish oson: `ru.json` da
  yo'q qatorlarni qidirish kifoya.

Kamchiligi: bir xil o'zbekcha so'z ikki xil kontekstda ikki xil
rus tarjimasiga muhtoj bo'lsa — muammo. Bu loyihada hozircha bunday
holat yo'q (ekranlar orasida ma'no chalkashmaydi); agar chiqsa,
kontekst prefiksi (`tr("Holat|Faol")`) qo'shiladi.

## Ishga tushirish

```python
from distribos.i18n import tr, set_locale

set_locale("ru")
label = tr("Saqlash")   # -> "Сохранить"
```

Til o'zgarishi **qayta ishga tushirishni talab qiladi** — allaqachon
qurilgan widget'lar o'zini avtomatik qayta chizmaydi (Qt'ning to'liq
`retranslateUi` mexanizmi bu loyiha hajmida ortiqcha murakkablik
bo'lardi). `set_locale()` shuni aniq talab qiladi: keyingi ishga
tushirishda kuchga kiradi.
"""

from __future__ import annotations

import json
import logging

from distribos.infrastructure.resources import resource_path

logger = logging.getLogger(__name__)

#: Qo'llab-quvvatlanadigan tillar. Kirill YO'Q — ataylab.
SUPPORTED_LOCALES: tuple[str, ...] = ("uz-Latn", "ru")

#: Asosiy til — manba matnlari shu tilda yozilgan, tarjima fayli yo'q.
DEFAULT_LOCALE = "uz-Latn"

#: Foydalanuvchiga ko'rsatiladigan til nomlari (til tanlov ro'yxati uchun).
LOCALE_NAMES: dict[str, str] = {
    "uz-Latn": "O'zbekcha",
    "ru": "Русский",
}

_current_locale: str = DEFAULT_LOCALE
_translations: dict[str, str] = {}


class UnsupportedLocaleError(ValueError):
    """Noma'lum til so'ralgan."""


def set_locale(locale: str) -> None:
    """Joriy tilni o'rnatadi va tarjima faylini yuklaydi.

    Noma'lum til so'ralsa RAD ETILADI (fail-closed) — jimgina asosiy
    tilga o'tish o'rniga xato ko'tariladi, chunki bu odatda chaqiruvchi
    kodda yozuv xatosi (masalan `"ru-RU"` "ru" o'rniga).
    """
    global _current_locale, _translations
    if locale not in SUPPORTED_LOCALES:
        raise UnsupportedLocaleError(
            f"Noma'lum til: {locale!r}. Qo'llab-quvvatlanadi: {SUPPORTED_LOCALES}"
        )
    _current_locale = locale
    _translations = {} if locale == DEFAULT_LOCALE else _load_translations(locale)


def current_locale() -> str:
    return _current_locale


def _load_translations(locale: str) -> dict[str, str]:
    path = resource_path("i18n", f"{locale}.json")
    if not path.exists():
        logger.warning("Tarjima fayli topilmadi: %s", path)
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Tarjima faylini o'qib bo'lmadi: %s", path)
        return {}
    if not isinstance(data, dict):
        logger.error("Tarjima fayli noto'g'ri shaklda: %s", path)
        return {}
    return {str(k): str(v) for k, v in data.items()}


def tr(text: str) -> str:
    """Matnni joriy tilga tarjima qiladi.

    Tarjima topilmasa — ASL MATN qaytadi. Bu funksiya HECH QACHON
    xato ko'tarmaydi va HECH QACHON bo'sh satr qaytarmaydi — UI
    doimo to'liq matn ko'rsatishi kerak, hatto tarjima yetishmasa ham.
    """
    if not text or _current_locale == DEFAULT_LOCALE:
        return text
    return _translations.get(text, text)


def missing_translations(locale: str, texts: set[str]) -> set[str]:
    """`texts` ichida `locale` tarjimasi yo'q qatorlar.

    Sinov va CI uchun: yangi qo'shilgan matn tarjimasiz qolib
    ketmasligini tekshiradi.
    """
    if locale == DEFAULT_LOCALE:
        return set()
    translated = _load_translations(locale)
    return {t for t in texts if t not in translated}


__all__ = [
    "DEFAULT_LOCALE",
    "LOCALE_NAMES",
    "SUPPORTED_LOCALES",
    "UnsupportedLocaleError",
    "current_locale",
    "missing_translations",
    "set_locale",
    "tr",
]
