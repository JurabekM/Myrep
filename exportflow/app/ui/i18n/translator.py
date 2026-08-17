"""Interface translation (Uzbek / Russian / English).

Keys are dotted strings. English is the fallback language, and unknown keys
degrade gracefully to a readable form instead of raising.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.config import SUPPORTED_LANGUAGES
from app.ui.i18n.strings import ENUM_LABELS, TRANSLATIONS

LANGUAGE_NAMES = {"uz": "O‘zbekcha", "ru": "Русский", "en": "English"}


class Translator(QObject):
    """Process-wide translator with a language-changed signal."""

    language_changed = Signal(str)

    def __init__(self, language: str = "uz") -> None:
        super().__init__()
        self._language = language if language in SUPPORTED_LANGUAGES else "uz"

    @property
    def language(self) -> str:
        """Currently active interface language code."""
        return self._language

    def set_language(self, language: str) -> None:
        """Switch the interface language and notify every listener."""
        if language not in SUPPORTED_LANGUAGES or language == self._language:
            return
        self._language = language
        self.language_changed.emit(language)

    def t(self, key: str, **params: object) -> str:
        """Translate a key, formatting ``{placeholders}`` from ``params``."""
        table = TRANSLATIONS.get(self._language, {})
        text = table.get(key)
        if text is None:
            text = TRANSLATIONS["en"].get(key)
        if text is None:
            text = key.rsplit(".", 1)[-1].replace("_", " ").capitalize()
        if params:
            try:
                return text.format(**params)
            except (KeyError, IndexError, ValueError):
                return text
        return text

    def enum(self, group: str, value: str | None) -> str:
        """Translate an enum value such as ``lead_status`` / ``new``."""
        if not value:
            return ""
        table = ENUM_LABELS.get(group, {})
        entry = table.get(value)
        if entry is None:
            return value.replace("_", " ").title()
        return entry.get(self._language) or entry.get("en") or value


#: Singleton instance used across the UI layer.
TR = Translator()


def t(key: str, **params: object) -> str:
    """Shortcut to :meth:`Translator.t` on the shared instance."""
    return TR.t(key, **params)


def te(group: str, value: str | None) -> str:
    """Shortcut to :meth:`Translator.enum` on the shared instance."""
    return TR.enum(group, value)
