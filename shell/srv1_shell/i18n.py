"""Tarjima: joriy til, matn tanlash, son va hajm formatlash."""

from collections.abc import Mapping

from srv1_shell.translations import DEFAULT_LANGUAGE, LANGUAGE_NAMES, TEXTS

_COMMA_DECIMAL = frozenset({"uz", "ru"})
_UNITS: dict[str, tuple[str, str, str, str]] = {
    "uz": ("B", "KB", "MB", "GB"),
    "ru": ("Б", "КБ", "МБ", "ГБ"),
    "en": ("B", "KB", "MB", "GB"),
}


class I18n:
    def __init__(self, language: str = DEFAULT_LANGUAGE) -> None:
        self.language = language if language in LANGUAGE_NAMES else DEFAULT_LANGUAGE

    def t(self, key: str, **values: object) -> str:
        """Kalit bo'yicha matn. Noma'lum kalit — kalitning o'zi (xato ko'zga tashlansin)."""
        variants = TEXTS.get(key)
        if variants is None:
            return key
        template = variants.get(self.language) or variants[DEFAULT_LANGUAGE]
        return template.format(**values) if values else template

    def pick(self, text: str | Mapping[str, str]) -> str:
        """Plagin bergan matn: satr yoki `{til: matn}`."""
        if isinstance(text, str):
            return text
        for candidate in (self.language, "en", DEFAULT_LANGUAGE):
            if candidate in text:
                return text[candidate]
        return next(iter(text.values()), "")

    def number(self, value: float, digits: int = 1) -> str:
        text = f"{value:.{digits}f}"
        return text.replace(".", ",") if self.language in _COMMA_DECIMAL else text

    def size(self, size_bytes: float) -> str:
        """Hajm: 1024 asosida, bitta kasr xonasi bilan."""
        b, kb, mb, gb = _UNITS[self.language]
        if size_bytes < 1024:
            return f"{round(size_bytes)} {b}"
        if size_bytes >= 1024**3:
            return f"{self.number(size_bytes / 1024**3)} {gb}"
        if size_bytes >= 1024**2:
            return f"{self.number(size_bytes / 1024**2)} {mb}"
        return f"{self.number(size_bytes / 1024, 0)} {kb}"

    def percent(self, value: float) -> str:
        return f"{self.number(value)} %"
