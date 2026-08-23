"""Son va pul formatlash — yagona manba.

Nega alohida modul: `Decimal.normalize()` katta yumaloq sonlarni ILMIY
notatsiyaga aylantiradi:

    >>> str(Decimal("40").normalize())
    '4E+1'
    >>> str(Decimal("100").normalize())
    '1E+2'

Foydalanuvchi «qoldiq 4E+1» degan matnni ko'rsa, dastur buzilgan deb
o'ylaydi. Shuning uchun butun kod bazasida `.normalize()` ni to'g'ridan
matnga aylantirish TAQIQLANADI — faqat shu yerdagi funksiyalar.
"""

from __future__ import annotations

from decimal import Decimal


def quantity(value: object) -> str:
    """Miqdorni ortiqcha nollarsiz, lekin ILMIY notatsiyasiz ko'rsatadi.

    >>> quantity("40.000")
    '40'
    >>> quantity("12.500")
    '12.5'
    >>> quantity(0)
    '0'
    """
    if value is None:
        return "0"
    number = Decimal(str(value))
    # `normalize()` ortiqcha nollarni oladi, `format(..., "f")` esa
    # natijani doim oddiy o'nlik shaklda beradi (E+ yo'q).
    return format(number.normalize(), "f")


def money(amount: int | None, currency: str = "UZS") -> str:
    """Tiyindan o'qiladigan matnga.

    Ajratgich — bo'sh joy (o'zbek uslubi), kasr qismi vergul bilan.

    >>> money(150_000_000)
    '1 500 000 UZS'
    >>> money(150_075)
    '1 500,75 UZS'
    """
    value = int(amount or 0)
    whole, fraction = divmod(abs(value), 100)
    sign = "-" if value < 0 else ""
    text = f"{whole:,}".replace(",", " ")
    if fraction:
        return f"{sign}{text},{fraction:02d} {currency}"
    return f"{sign}{text} {currency}"


def percent(value: object, decimals: int = 1) -> str:
    """Foizni ko'rsatadi."""
    number = Decimal(str(value or 0))
    return f"{number:.{decimals}f} %"


def to_tiyin(amount: object) -> int:
    """So'mdagi qiymatni tiyinga aylantiradi (butun son).

    Suzuvchi nuqtadan `Decimal` orqali o'tamiz — `int(12.34 * 100)` ba'zan
    1233 beradi, bu moliyaviy hisobda qabul qilib bo'lmaydigan xato.
    """
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1")))


def from_tiyin(amount: int | None) -> Decimal:
    """Tiyindan so'mga (ko'rsatish uchun)."""
    return Decimal(int(amount or 0)) / Decimal(100)
