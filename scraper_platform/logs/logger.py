# -*- coding: utf-8 -*-
"""
logs/logger.py
==============
Loyihaning markazlashtirilgan loglash tizimi (loguru asosida).

- Konsolga rangli chiqish
- Fayllarga rotatsiya bilan yozish (logs/app.log, logs/error.log)
- GUI'ga real-time log uzatish uchun maxsus "sink" qo'shish imkoni

Foydalanish:
    from logs.logger import get_logger
    log = get_logger(__name__)
    log.info("Xabar")
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

from loguru import logger

from config.settings import LOGS_DIR, CONFIG


# Standart loguru handlerni olib tashlaymiz va o'zimiznikini qo'shamiz
logger.remove()

# 1) Konsol (rangli)
logger.add(
    sys.stderr,
    level=CONFIG.log_level,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    ),
    colorize=True,
    enqueue=True,  # Ko'p oqimli muhitda xavfsiz
)

# 2) Umumiy log fayli (rotatsiya bilan)
logger.add(
    LOGS_DIR / "app.log",
    level="DEBUG",
    rotation="10 MB",
    retention="10 days",
    compression="zip",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
    enqueue=True,
)

# 3) Faqat xatoliklar fayli
logger.add(
    LOGS_DIR / "error.log",
    level="ERROR",
    rotation="5 MB",
    retention="30 days",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
    enqueue=True,
)


def get_logger(name: str = "scraper") -> "logger":  # type: ignore[valid-type]
    """Berilgan nom bilan bog'langan logger qaytaradi."""
    return logger.bind(name=name)


def add_gui_sink(callback: Callable[[str], Any], level: str = "INFO") -> int:
    """
    GUI'da real-time loglarni ko'rsatish uchun callback qo'shadi.

    Args:
        callback: har bir log xabari uchun chaqiriladigan funksiya (str qabul qiladi).
        level: minimal log darajasi.

    Returns:
        Handler ID (keyinchalik olib tashlash uchun).
    """
    def _sink(message: Any) -> None:
        callback(str(message).rstrip("\n"))

    return logger.add(
        _sink,
        level=level,
        format="{time:HH:mm:ss} | {level: <8} | {message}",
        enqueue=True,
    )


def remove_sink(handler_id: int) -> None:
    """GUI sink'ini olib tashlaydi."""
    try:
        logger.remove(handler_id)
    except ValueError:
        pass


__all__ = ["get_logger", "add_gui_sink", "remove_sink", "logger"]
