# -*- coding: utf-8 -*-
"""
Professional logging tizimi.

To'rtta alohida log oqimi yuritiladi (barchasi aylanuvchi — RotatingFileHandler):

* ``logs/app.log``      — umumiy tizim loglari
* ``logs/error.log``    — faqat xatolar (ERROR+)
* ``logs/audit.log``    — audit trail (kim, nima, qachon)
* ``logs/security.log`` — xavfsizlik hodisalari (login, blokirovka, ruxsat rad etildi)
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
_BACKUP_COUNT = 5

_configured = False


def setup_logging(logs_dir: Path, level: str = "INFO") -> logging.Logger:
    """
    Loggerlarni sozlaydi va asosiy ``uzerp`` loggerini qaytaradi.

    Bir necha marta chaqirilsa ham handlerlar takrorlanmaydi (idempotent).
    """
    global _configured
    root = logging.getLogger("uzerp")
    if _configured:
        return root

    logs_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    def _file_handler(filename: str, lvl: int = logging.DEBUG) -> RotatingFileHandler:
        handler = RotatingFileHandler(
            logs_dir / filename,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        handler.setLevel(lvl)
        return handler

    # Umumiy va xatolar oqimi
    root.addHandler(_file_handler("app.log"))
    root.addHandler(_file_handler("error.log", logging.ERROR))

    # Konsol (qisqa ma'lumot uchun)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(logging.WARNING)
    root.addHandler(console)

    # Audit va security alohida fayllarga yoziladi, app.log ga aralashmaydi
    for name, filename in (("uzerp.audit", "audit.log"), ("uzerp.security", "security.log")):
        lg = logging.getLogger(name)
        lg.setLevel(logging.INFO)
        lg.propagate = False
        lg.addHandler(_file_handler(filename))

    _configured = True
    return root


def get_logger(name: str = "uzerp") -> logging.Logger:
    """Nomlangan loggerni qaytaradi (``uzerp.*`` ierarxiyasida)."""
    if name.startswith("uzerp"):
        return logging.getLogger(name)
    return logging.getLogger(f"uzerp.{name}")
