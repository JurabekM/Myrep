"""Deterministic Uzbek/Russian text understanding used by the demo AI.

Everything here is pure functions over text, so it is fully unit-testable and
works with no network access.  The OpenAI-compatible provider reuses the same
helpers for language detection and safety checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from app.models.enums import LanguageCode, Sentiment
from app.utils.dates import now
from app.utils.formatting import normalize_phone

_CYRILLIC = re.compile(r"[а-яё]", re.IGNORECASE)
_LATIN = re.compile(r"[a-z]", re.IGNORECASE)

UZ_MARKERS = {
    "salom",
    "assalomu",
    "qancha",
    "narx",
    "bo'sh",
    "bosh",
    "kerak",
    "yozilmoqchi",
    "qabul",
    "rahmat",
    "bugun",
    "ertaga",
    "iltimos",
    "mumkinmi",
    "bormi",
    "menga",
    "siz",
}

# --------------------------------------------------------------------------- #
# Intent keyword dictionaries
# --------------------------------------------------------------------------- #
KEYWORDS: dict[str, dict[str, list[str]]] = {
    "greeting": {
        "uz": ["salom", "assalom", "assalomu alaykum", "hayrli", "xayrli"],
        "ru": ["здравствуй", "привет", "добрый день", "добрый вечер", "доброе утро"],
    },
    "price": {
        "uz": ["narx", "qancha", "necha pul", "qiymati", "narxi", "pul"],
        "ru": ["цена", "сколько стоит", "стоимость", "прайс", "сколько"],
    },
    "booking": {
        "uz": ["yozil", "band qil", "bron", "navbat", "qabulga", "kelmoqchi", "yoziling", "yozing"],
        "ru": ["записать", "запишите", "запись", "бронь", "хочу прийти", "приду", "забронир"],
    },
    "schedule": {
        "uz": ["bo'sh vaqt", "bosh vaqt", "ish vaqti", "qachon", "soat", "necha kunda", "grafik"],
        "ru": ["свободн", "во сколько", "когда", "график", "время работы", "часы работы"],
    },
    "address": {
        "uz": ["manzil", "qayerda", "filial", "joylashgan", "adres"],
        "ru": ["адрес", "где находит", "филиал", "как доехать"],
    },
    "human": {
        "uz": ["operator", "odam bilan", "inson bilan", "menejer", "tirik odam", "javob bering"],
        "ru": ["оператор", "с человеком", "менеджер", "живой человек", "соедините"],
    },
    "objection_price": {
        "uz": ["qimmat", "qimmatroq", "chegirma", "arzonroq", "aksiya bormi"],
        "ru": ["дорого", "дороговато", "скидк", "дешевле", "акция"],
    },
    "negative": {
        "uz": [
            "yomon",
            "shikoyat",
            "aldadingiz",
            "norozi",
            "juda yomon",
            "javob bermadingiz",
            "yoqmadi",
        ],
        "ru": [
            "плохо",
            "жалоба",
            "обманули",
            "ужасно",
            "недоволен",
            "хамство",
            "не понравилось",
            "возмущен",
        ],
    },
    "opt_out": {
        "uz": [
            "yozmang",
            "bezovta qilmang",
            "spam",
            "to'xtating",
            "toxtating",
            "boshqa yozmang",
            "qo'ng'iroq qilmang",
        ],
        "ru": [
            "не пишите",
            "не беспокойте",
            "отпишите",
            "стоп",
            "прекратите",
            "удалите меня",
            "не звоните",
            "больше не",
        ],
    },
    "urgency": {
        "uz": ["bugun", "hozir", "tez", "shoshilinch", "zudlik"],
        "ru": ["сегодня", "сейчас", "срочно", "быстрее", "как можно скорее"],
    },
    "confirm": {
        "uz": ["ha", "mayli", "yaxshi", "roziman", "to'g'ri", "kelaman", "bo'ladi"],
        "ru": ["да", "хорошо", "согласен", "подходит", "приду", "ладно"],
    },
    "decline": {
        "uz": ["yo'q", "kerak emas", "keyinroq", "hozircha yo'q", "o'ylab ko'raman"],
        "ru": ["нет", "не надо", "позже", "подумаю", "не интересует"],
    },
    "thanks": {
        "uz": ["rahmat", "tashakkur"],
        "ru": ["спасибо", "благодарю"],
    },
}

STOP_WORDS = {"va", "bilan", "uchun", "и", "для", "с", "на", "в"}


@dataclass
class Understanding:
    """Result of analysing one customer message."""

    language: str = LanguageCode.UNKNOWN
    intents: set[str] = field(default_factory=set)
    sentiment: str = Sentiment.NEUTRAL
    phone: str | None = None
    name: str | None = None
    requested_datetime: datetime | None = None
    keywords: list[str] = field(default_factory=list)

    def has(self, *intents: str) -> bool:
        """Whether any of the given intents was detected."""
        return any(i in self.intents for i in intents)


def detect_language(text: str, fallback: str = LanguageCode.UNKNOWN) -> str:
    """Detect Uzbek vs Russian using script and marker words."""
    if not text or not text.strip():
        return fallback
    lowered = text.lower()
    cyrillic = len(_CYRILLIC.findall(lowered))
    latin = len(_LATIN.findall(lowered))
    if cyrillic > latin:
        return LanguageCode.RU
    if latin > 0:
        return LanguageCode.UZ
    return fallback


def detect_intents(text: str, language: str) -> set[str]:
    """Return the set of intents whose keywords appear in ``text``."""
    lowered = (text or "").lower()
    lang = language if language in ("uz", "ru") else "uz"
    found: set[str] = set()
    for intent, per_lang in KEYWORDS.items():
        for candidate_lang in {lang, "uz", "ru"}:
            for keyword in per_lang.get(candidate_lang, []):
                if keyword in lowered:
                    found.add(intent)
                    break
            if intent in found:
                break
    return found


def detect_sentiment(text: str, intents: set[str]) -> str:
    """Rule-based sentiment classification."""
    if "negative" in intents or "opt_out" in intents:
        return Sentiment.NEGATIVE
    if "objection_price" in intents:
        return Sentiment.NEGATIVE
    if intents & {"thanks", "confirm", "booking"}:
        return Sentiment.POSITIVE
    return Sentiment.NEUTRAL


_TIME_RE = re.compile(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b")
_HOUR_RE = re.compile(r"\bsoat\s*([01]?\d|2[0-3])\b|\bв\s*([01]?\d|2[0-3])\s*(?:час|ч)?\b")


def extract_datetime(text: str, reference: datetime | None = None) -> datetime | None:
    """Extract a coarse requested date/time such as 'ertaga 15:00'."""
    if not text:
        return None
    ref = reference or now()
    lowered = text.lower()
    day = ref.date()
    if any(word in lowered for word in ("ertaga", "завтра")):
        day = day + timedelta(days=1)
    elif any(word in lowered for word in ("indinga", "послезавтра")):
        day = day + timedelta(days=2)
    elif any(word in lowered for word in ("bugun", "сегодня", "hozir", "сейчас")):
        day = ref.date()
    else:
        if not (_TIME_RE.search(lowered) or _HOUR_RE.search(lowered)):
            return None

    match = _TIME_RE.search(lowered)
    if match:
        return datetime.combine(day, time(int(match.group(1)), int(match.group(2))))
    hour_match = _HOUR_RE.search(lowered)
    if hour_match:
        hour = int(hour_match.group(1) or hour_match.group(2))
        return datetime.combine(day, time(hour, 0))
    if day != ref.date():
        return datetime.combine(day, time(10, 0))
    return None


_NAME_RE = re.compile(
    r"(?:ismim|mening ismim|men\s|меня зовут|моё имя|мое имя)\s+([A-Za-zЎЁА-Яа-яёʻ'`]{3,}(?:\s+[A-Za-zА-Яа-яёЎʻ'`]{3,})?)",
    re.IGNORECASE,
)


def extract_name(text: str) -> str | None:
    """Extract a self-introduced customer name."""
    match = _NAME_RE.search(text or "")
    if not match:
        return None
    candidate = match.group(1).strip()
    if candidate.lower() in STOP_WORDS:
        return None
    return " ".join(part.capitalize() for part in candidate.split())


_PHONE_RE = re.compile(r"(?:\+?998[\s\-]?)?\(?\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")


def extract_phone(text: str) -> str | None:
    """Extract and normalise the first phone number found in the text."""
    match = _PHONE_RE.search(text or "")
    if not match:
        return None
    return normalize_phone(match.group(0))


def keywords_of(text: str, limit: int = 8) -> list[str]:
    """Return significant lowercase words for knowledge base lookup."""
    words = re.findall(r"[\wʻ']+", (text or "").lower(), flags=re.UNICODE)
    result = [w for w in words if len(w) > 3 and w not in STOP_WORDS]
    return result[:limit]


def understand(text: str, fallback_language: str = LanguageCode.UNKNOWN) -> Understanding:
    """Full analysis of one customer message."""
    language = detect_language(text, fallback_language)
    intents = detect_intents(text, language)
    return Understanding(
        language=language,
        intents=intents,
        sentiment=detect_sentiment(text, intents),
        phone=extract_phone(text),
        name=extract_name(text),
        requested_datetime=extract_datetime(text),
        keywords=keywords_of(text),
    )
