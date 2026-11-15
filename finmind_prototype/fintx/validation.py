"""Kirish ma'lumotlarini tekshirish.

Qoida: interfeysdan kelgan har bir qiymat ishonchsiz. Xizmat qatlami
(`auth`, `transactions`) bazaga yozishdan oldin shu funksiyalardan o'tkazadi;
baza sxemasidagi CHECK cheklovlari ikkinchi himoya chizig'i.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

from .errors import ValidationError

# --- Foydalanuvchi nomi -----------------------------------------------------

USERNAME_MIN = 3
USERNAME_MAX = 32
_USERNAME_RE = re.compile(r"[a-z0-9][a-z0-9_.-]{2,31}")


def normalize_username(value: object) -> str:
    """Loginni yagona ko'rinishga keltiradi (NFKC, kichik harf) va tekshiradi."""
    if not isinstance(value, str):
        raise ValidationError("Login matn bo'lishi kerak.", "username")
    name = unicodedata.normalize("NFKC", value).strip().lower()
    if _USERNAME_RE.fullmatch(name) is None:
        raise ValidationError(
            f"Login {USERNAME_MIN}–{USERNAME_MAX} belgidan iborat bo'lsin: lotin "
            "harflari, raqamlar va . _ - belgilari; harf yoki raqam bilan boshlansin.",
            "username",
        )
    return name


# --- Parol siyosati ---------------------------------------------------------

PASSWORD_MIN = 12
PASSWORD_MAX = 128  # xeshlash xarajatini cheklaydi (DoS oldini olish)
_MIN_DISTINCT_CHARS = 5

# Uzunlik talabidan o'tib ketadigan, lekin lug'at hujumida birinchi
# sinaladigan parollar. To'liq ro'yxat emas — namunaviy to'siq.
_COMMON_PASSWORDS = frozenset(
    {
        "password1234",
        "password12345",
        "passwordpassword",
        "123456789012",
        "1234567890123",
        "123123123123",
        "qwertyuiop12",
        "qwertyuiopas",
        "qwerty123456",
        "qwertyqwerty",
        "1q2w3e4r5t6y",
        "zaq12wsxcde3",
        "asdfghjklasd",
        "abcdefghijkl",
        "abc123abc123",
        "iloveyou1234",
        "letmein12345",
        "welcome12345",
        "adminadmin12",
        "administrator",
        "parolparol12",
        "uzbekistan123",
        "toshkent1234",
    }
)


def normalize_password(value: str) -> str:
    """Parolni xeshlashdan oldin NFKC ko'rinishiga keltiradi (NIST SP 800-63B)."""
    return unicodedata.normalize("NFKC", value)


def validate_new_password(password: object, username: str) -> str:
    """Yangi parolni siyosatga tekshiradi va normallashtirilgan parolni qaytaradi.

    Majburiy "katta harf + raqam + belgi" qoidasi ataylab yo'q: uzunlik va
    taniqli parollarni rad etish kuchliroq himoya beradi.
    """
    if not isinstance(password, str):
        raise ValidationError("Parol matn bo'lishi kerak.", "password")
    pw = normalize_password(password)
    if len(pw) < PASSWORD_MIN:
        raise ValidationError(f"Parol kamida {PASSWORD_MIN} belgidan iborat bo'lsin.", "password")
    if len(pw) > PASSWORD_MAX:
        raise ValidationError(f"Parol {PASSWORD_MAX} belgidan oshmasin.", "password")
    lowered = pw.lower()
    if len(set(lowered)) < _MIN_DISTINCT_CHARS:
        raise ValidationError("Parol juda oddiy: bir xil belgilar takrorlangan.", "password")
    if lowered in _COMMON_PASSWORDS:
        raise ValidationError("Bu parol juda keng tarqalgan. Boshqasini tanlang.", "password")
    if username and username in lowered:
        raise ValidationError("Parol ichida login bo'lmasin.", "password")
    return pw


# --- Tranzaksiya maydonlari --------------------------------------------------

KIND_INCOME = "income"
KIND_EXPENSE = "expense"
KIND_LABELS = {KIND_INCOME: "Daromad", KIND_EXPENSE: "Xarajat"}

# Kategoriyalar yopiq ro'yxat: bazada kalit, interfeysda o'zbekcha nom.
CATEGORIES: dict[str, dict[str, str]] = {
    KIND_INCOME: {
        "salary": "Maosh",
        "business": "Biznes",
        "investment": "Investitsiya",
        "gift": "Sovg'a",
        "other": "Boshqa",
    },
    KIND_EXPENSE: {
        "food": "Oziq-ovqat",
        "transport": "Transport",
        "housing": "Uy-joy",
        "utilities": "Kommunal to'lovlar",
        "health": "Sog'liq",
        "education": "Ta'lim",
        "clothing": "Kiyim-kechak",
        "leisure": "Ko'ngilochar",
        "other": "Boshqa",
    },
}

NOTE_MAX = 200
MIN_DATE = date(2000, 1, 1)
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def validate_kind(value: object) -> str:
    if value not in KIND_LABELS:
        raise ValidationError("Tranzaksiya turi noto'g'ri.", "kind")
    return str(value)


def validate_category(kind: str, value: object) -> str:
    if not isinstance(value, str) or value not in CATEGORIES[kind]:
        raise ValidationError("Kategoriya ro'yxatdan tanlanishi kerak.", "category")
    return value


def category_label(kind: str, key: str) -> str:
    """Kategoriya kalitining o'zbekcha nomi (noma'lum kalit o'zgarishsiz qaytadi)."""
    return CATEGORIES.get(kind, {}).get(key, key)


def _is_unsafe_char(ch: str) -> bool:
    # C* toifalari: boshqaruv (ESC, \n), format (bidi) va boshqa ko'rinmas belgilar.
    return unicodedata.category(ch).startswith("C")


def validate_note(value: object) -> str:
    """Izoh: ixtiyoriy, qisqa, boshqaruv belgilarisiz.

    Boshqaruv belgilari terminalda ESC ketma-ketligi orqali ekranni
    o'zgartirishi mumkin, shuning uchun ular kirishdayoq rad etiladi.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError("Izoh matn bo'lishi kerak.", "note")
    note = unicodedata.normalize("NFC", value).strip()
    if len(note) > NOTE_MAX:
        raise ValidationError(f"Izoh {NOTE_MAX} belgidan oshmasin.", "note")
    if any(_is_unsafe_char(ch) for ch in note):
        raise ValidationError("Izohda boshqaruv yoki ko'rinmas belgilar bo'lmasin.", "note")
    return note


def parse_date(
    value: object, *, today: date, field: str = "date", allow_future: bool = False
) -> date:
    """`YYYY-MM-DD` sanani tekshiradi.

    Tranzaksiya sanasi kelajakda bo'lishi mumkin emas; davr filtri uchun
    (`allow_future=True`) bu cheklov qo'llanmaydi.
    """
    if isinstance(value, date):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if _DATE_RE.fullmatch(text) is None:
            raise ValidationError(
                "Sana YYYY-MM-DD ko'rinishida bo'lsin (masalan: 2026-11-15).", field
            )
        try:
            parsed = date.fromisoformat(text)
        except ValueError:
            raise ValidationError("Bunday sana mavjud emas.", field) from None
    else:
        raise ValidationError("Sana noto'g'ri.", field)
    if parsed < MIN_DATE:
        raise ValidationError(f"Sana {MIN_DATE.isoformat()} dan oldin bo'lmasin.", field)
    if not allow_future and parsed > today:
        raise ValidationError("Sana kelajakda bo'lishi mumkin emas.", field)
    return parsed


def printable(text: str) -> str:
    """Chiqarishdan oldingi himoya: ko'rinmas belgilar `?` bilan almashtiriladi."""
    return "".join("?" if _is_unsafe_char(ch) else ch for ch in text)
