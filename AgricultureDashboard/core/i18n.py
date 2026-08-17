"""Lightweight i18n for UI chrome. Default language is Uzbek (latin)."""
from __future__ import annotations

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "uz": {},  # Uzbek strings are the keys themselves.
    "en": {
        "Bosh sahifa": "Home",
        "Xarita": "Map",
        "Analitika": "Analytics",
        "Ob-havo": "Weather",
        "Bozor": "Market",
        "Sug'orish": "Irrigation",
        "Moliya": "Finance",
        "Sun'iy yo'ldosh": "Satellite",
        "Machine Learning": "Machine Learning",
        "AI Yordamchi": "AI Assistant",
        "Hisobotlar": "Reports",
        "Administrator": "Administrator",
        "Sozlamalar": "Settings",
        "Chiqish": "Log out",
        "Qidiruv": "Search",
        "Kirish": "Sign in",
        "Offlayn rejim": "Offline mode",
        "Onlayn": "Online",
    },
    "ru": {
        "Bosh sahifa": "Главная",
        "Xarita": "Карта",
        "Analitika": "Аналитика",
        "Ob-havo": "Погода",
        "Bozor": "Рынок",
        "Sug'orish": "Орошение",
        "Moliya": "Финансы",
        "Sun'iy yo'ldosh": "Спутник",
        "Machine Learning": "Машинное обучение",
        "AI Yordamchi": "AI Ассистент",
        "Hisobotlar": "Отчёты",
        "Administrator": "Администратор",
        "Sozlamalar": "Настройки",
        "Chiqish": "Выход",
        "Qidiruv": "Поиск",
        "Kirish": "Вход",
        "Offlayn rejim": "Оффлайн режим",
        "Onlayn": "Онлайн",
    },
}

LANGUAGES = {"uz": "O'zbekcha", "en": "English", "ru": "Русский"}


def translate(text: str, language: str = "uz") -> str:
    """Translate a UI string; unknown keys fall back to the Uzbek original."""
    return _TRANSLATIONS.get(language, {}).get(text, text)
