"""Pul summalari: tiyingacha aniq, butun sonlarda.

Summalar hech qachon `float` sifatida saqlanmaydi yoki hisoblanmaydi:
1 so'm = 100 tiyin, bazada va hisob-kitobda faqat tiyin (int) yuradi.
"""

from __future__ import annotations

import re
from decimal import Decimal

from .errors import ValidationError

MINOR_PER_UNIT = 100
# Bitta tranzaksiya uchun yuqori chegara: 1 trillion so'm.
MAX_AMOUNT_MINOR = 1_000_000_000_000 * MINOR_PER_UNIT
CURRENCY = "so'm"

# Faqat ASCII raqamlar: `\d` boshqa yozuvlardagi raqamlarni ham qabul qiladi.
_AMOUNT_RE = re.compile(r"([0-9]{1,13})(?:[.,]([0-9]{1,2}))?")
# Minglik ajratuvchi sifatida ruxsat etilgan bo'shliqlar (oddiy, NBSP, tor NBSP).
_GROUP_SPACES = (" ", " ", " ")
_MAX_INPUT_LEN = 32


def parse_amount(text: object) -> int:
    """Foydalanuvchi kiritgan summani tiyinga aylantiradi.

    Qabul qilinadi: `125000`, `125 000`, `125000.5`, `125 000,50`.
    Rad etiladi: manfiy, nol, eksponenta, `NaN`, uchinchi kasr xonasi va
    ASCII bo'lmagan raqamlar.
    """
    if not isinstance(text, str):
        raise ValidationError("Summa matn ko'rinishida kiritilishi kerak.", "amount")
    raw = text.strip()
    if not raw:
        raise ValidationError("Summani kiriting.", "amount")
    if len(raw) > _MAX_INPUT_LEN:
        raise ValidationError("Summa juda uzun.", "amount")
    for space in _GROUP_SPACES:
        raw = raw.replace(space, "")
    match = _AMOUNT_RE.fullmatch(raw)
    if match is None:
        raise ValidationError(
            "Summa noto'g'ri. Faqat musbat son, ko'pi bilan ikki kasr xonasi "
            "(masalan: 125000 yoki 125 000,50).",
            "amount",
        )
    whole, frac = match.group(1), match.group(2) or ""
    minor = int(whole) * MINOR_PER_UNIT + int(frac.ljust(2, "0"))
    if minor <= 0:
        raise ValidationError("Summa noldan katta bo'lishi kerak.", "amount")
    if minor > MAX_AMOUNT_MINOR:
        raise ValidationError(
            f"Summa juda katta (chegara: {format_amount(MAX_AMOUNT_MINOR)} {CURRENCY}).",
            "amount",
        )
    return minor


def format_amount(minor: int, *, signed: bool = False) -> str:
    """Tiyinni `1 250 000,50` ko'rinishida yozadi (manfiy qiymat `-` bilan)."""
    sign = "-" if minor < 0 else ("+" if signed and minor > 0 else "")
    whole, frac = divmod(abs(minor), MINOR_PER_UNIT)
    grouped = f"{whole:,}".replace(",", " ")
    return f"{sign}{grouped},{frac:02d}"


def format_percent(value: Decimal) -> str:
    """Foizni o'zbekcha yozuvda (kasr ajratuvchisi — vergul) qaytaradi: `97,2 %`."""
    return f"{value:f}".replace(".", ",") + " %"
