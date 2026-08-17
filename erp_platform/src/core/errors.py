# -*- coding: utf-8 -*-
"""
Biznes xatolari ierarxiyasi.

Barcha xabarlar foydalanuvchiga ko'rsatishga mo'ljallangan (o'zbek tilida).
Web/API/GUI qatlamlari bu xatolarni tutib, chiroyli ko'rinishda chiqaradi.
"""
from __future__ import annotations


class UzERPError(Exception):
    """Barcha biznes xatolarning asosi."""


class ValidationError(UzERPError):
    """Kiritilgan ma'lumot yaroqsiz (bo'sh nom, manfiy narx va h.k.)."""


class NotFoundError(UzERPError):
    """So'ralgan yozuv topilmadi."""


class InsufficientStockError(UzERPError):
    """Omborda mahsulot yetarli emas."""


class StateError(UzERPError):
    """Hujjat holati amalga ruxsat bermaydi (masalan, bekor qilingan hujjatni tasdiqlash)."""


class PermissionDeniedError(UzERPError):
    """Foydalanuvchi rolida bu amal uchun ruxsat yo'q."""
