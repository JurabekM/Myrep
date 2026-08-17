"""Runtime translation layer (Uzbek / Russian).

Usage::

    from app.ui.i18n import tr, translator
    label.setText(tr("nav.inbox"))
    translator.language_changed.connect(self.retranslate)
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.config import load_config, save_config
from app.ui.i18n.strings import TRANSLATIONS


class Translator(QObject):
    """Holds the active language and notifies widgets when it changes."""

    language_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._language: str = load_config().language

    @property
    def language(self) -> str:
        """Current language code (``uz`` or ``ru``)."""
        return self._language

    def set_language(self, language: str, persist: bool = True) -> None:
        """Switch the interface language and notify every listener."""
        if language not in ("uz", "ru") or language == self._language:
            return
        self._language = language
        if persist:
            config = load_config()
            config.language = language
            save_config(config)
        self.language_changed.emit(language)

    def tr(self, key: str, **kwargs: object) -> str:
        """Translate ``key``; missing keys fall back to the key itself."""
        entry = TRANSLATIONS.get(key)
        if entry is None:
            return key
        text = entry.get(self._language) or entry.get("uz") or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text


#: Application-wide translator instance.
translator = Translator()


def tr(key: str, **kwargs: object) -> str:
    """Shorthand for ``translator.tr``."""
    return translator.tr(key, **kwargs)


def current_language() -> str:
    """Return the active language code."""
    return translator.language
