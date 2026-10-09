from __future__ import annotations

import gc
import json
import sys
from pathlib import Path

import pytest

ILDIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ILDIZ))

from core.ibtido import kalit_urugdan, ochiq_kalit  # noqa: E402
from core.sertifikat import sertifikat_yarat  # noqa: E402

KAT_YOL = ILDIZ / "kat" / "zarbxona_kat_v1.json"


@pytest.fixture(scope="session", autouse=True)
def _gc_faqat_asosiy_oqimda():
    """Avtomatik GC o'chiq: u fon oqimida (zarb ishchisi, soxta Pico...) ishga tushib,
    oldingi testlardan qolgan Qt ob'ektlarini noto'g'ri oqimda yo'q qilmasin (PYSIDE-810;
    PySide6 6.12 da CI'da segfault). Yig'ish — har testdan keyin, asosiy oqimda."""
    gc.disable()
    yield
    gc.enable()


@pytest.fixture(autouse=True)
def _gc_har_testdan_keyin():
    yield
    if "PySide6.QtCore" in sys.modules:
        from PySide6.QtCore import QCoreApplication
        if QCoreApplication.instance() is not None:
            QCoreApplication.processEvents()
    gc.collect()


@pytest.fixture(scope="session")
def kat() -> dict:
    return json.loads(KAT_YOL.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def kalitlar():
    """(zarbxona_sk, zarbxona_pk, bank_sk, bank_pk) — deterministik urug'lardan."""
    zsk = kalit_urugdan(bytes(range(1, 33)))
    bsk = kalit_urugdan(bytes(range(101, 133)))
    return zsk, ochiq_kalit(zsk), bsk, ochiq_kalit(bsk)


@pytest.fixture(scope="session")
def sertifikat(kalitlar):
    zsk, zpk, bsk, bpk = kalitlar
    return sertifikat_yarat(bsk, bpk, zpk, bytes(range(16)), "Test vakolati",
                            50_000_000, 1_700_000_000_000, 4_000_000_000_000)
