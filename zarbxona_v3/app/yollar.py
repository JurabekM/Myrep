"""Dastur papkasi: manbadan ishga tushirilganda — loyiha ildizi; PyInstaller bilan
paketlanganda — .exe yonidagi papka (data/, selftest_natija.txt shu yerda bo'ladi,
kutubxonaning ichki _internal/ papkasida emas)."""

from __future__ import annotations

import sys
from pathlib import Path


def dastur_papkasi() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent
