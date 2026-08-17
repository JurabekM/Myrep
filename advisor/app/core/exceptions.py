"""Domen xatolari — barcha qatlamlar shu iyerarxiyadan foydalanadi."""

from __future__ import annotations


class AdvisorError(Exception):
    """Ilovaning bazaviy xatosi."""


class ConfigError(AdvisorError):
    """Konfiguratsiya bilan bog'liq xato."""


class ValidationError(AdvisorError):
    """Kirish ma'lumotlari yaroqsiz."""


class NotFoundError(AdvisorError):
    """Resurs topilmadi."""


class AIProviderError(AdvisorError):
    """Bitta AI provayder chaqiruvi muvaffaqiyatsiz tugadi."""


class AllProvidersFailedError(AIProviderError):
    """Barcha AI provayderlar (bepul API'lar va lokal model) ishlamadi."""


class ScraperError(AdvisorError):
    """Lex.uz yoki boshqa scraping xatosi."""


class DocumentError(AdvisorError):
    """Hujjatdan matn ajratishda xato."""
