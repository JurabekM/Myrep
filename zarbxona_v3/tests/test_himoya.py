"""1.3 — soat orqaga ketsa zarb yo'q; 1.5 — partiya sirlari ishdan keyin nol bilan to'ldiriladi."""

from __future__ import annotations

import pytest

import core.partiya as partiya_mod
from core.buyurtma import SOAT_TOLERANS_MS, BuyurtmaXatosi, Zarbxona
from core.ibtido import kalit_urugdan
from core.partiya import ZarbKirishi, zarb_qil
from core.surat import BekorQilindi, Surat

HOZIR = 1_800_000_000_000
TEZ = Surat(rejim="cheklovsiz")


@pytest.fixture
def soat():
    return [HOZIR]


@pytest.fixture
def z(tmp_path, kalitlar, sertifikat, soat):
    sertifikat.yoz(tmp_path / "s.aqcert")
    zx = Zarbxona(tmp_path / "p", kalitlar[0], soat_ms=lambda: soat[0])
    zx.sertifikat_import(tmp_path / "s.aqcert")
    yield zx
    zx.yop()


def test_soat_orqaga_ketsa_buyurtma_va_zarb_yoq(z, soat):
    b = z.buyurtma_yarat(5000 * 4, "Q", "", TEZ, partiya_hajmi=2)
    b2 = z.buyurtma_yarat(10, "Q", "", TEZ)
    assert z.buyurtmani_bajar(b.buyurtma_id).holat == "tugadi"
    # tolerans ichida — ruxsat
    soat[0] = HOZIR - SOAT_TOLERANS_MS + 1_000
    assert z.soat_muammosi() is None
    # bir soat orqaga — yangi buyurtma ham, mavjudini zarb qilish ham yo'q
    soat[0] = HOZIR - 3_600_000
    assert "orqaga" in z.soat_muammosi()
    with pytest.raises(BuyurtmaXatosi, match="orqaga"):
        z.buyurtma_yarat(10, "Q", "", TEZ)
    r = z.buyurtmani_bajar(b2.buyurtma_id)
    assert r.holat == "pauza" and "orqaga" in r.xabar
    # soat to'g'rilandi — davom etadi
    soat[0] = HOZIR + 60_000
    assert z.buyurtmani_bajar(b2.buyurtma_id).holat == "tugadi"


def test_soat_belgisi_qayta_ochilganda_saqlanadi(tmp_path, kalitlar, sertifikat):
    sertifikat.yoz(tmp_path / "s.aqcert")
    z = Zarbxona(tmp_path / "p", kalitlar[0], soat_ms=lambda: HOZIR)
    z.sertifikat_import(tmp_path / "s.aqcert")
    z.buyurtma_yarat(10, "Q", "", TEZ)              # hali partiya yo'q — faqat belgi
    z.yop()
    z = Zarbxona(tmp_path / "p", kalitlar[0], soat_ms=lambda: HOZIR - 86_400_000)
    try:
        assert "orqaga" in z.soat_muammosi()
    finally:
        z.yop()


def test_partiya_sirlari_nol_bilan_toldiriladi(monkeypatch):
    yaratilgan = []
    asl = partiya_mod._sir

    def kuzat(b):
        s = asl(b)
        yaratilgan.append(s)
        return s
    monkeypatch.setattr(partiya_mod, "_sir", kuzat)
    zsk = kalit_urugdan(bytes(range(1, 33)))
    k = ZarbKirishi([5000, 10, 1], bytes(16), "Q", 1)
    tez = zarb_qil(k, zsk, partiya_id=bytes(16), partiya_kaliti=bytes(range(32)),
                   master=bytes(range(32, 64)), zarb_ms=HOZIR)
    assert len(yaratilgan) == 2 and all(s == bytearray(32) for s in yaratilgan)
    # natija sirlar tozalanishidan oldin tayyor bo'lgan — bayt-ma-bayt o'sha
    qayta = zarb_qil(k, zsk, partiya_id=bytes(16), partiya_kaliti=bytes(range(32)),
                     master=bytes(range(32, 64)), zarb_ms=HOZIR)
    assert qayta.ildiz == tez.ildiz


def test_bekor_qilinganda_ham_sirlar_tozalanadi(monkeypatch):
    yaratilgan = []
    asl = partiya_mod._sir
    monkeypatch.setattr(partiya_mod, "_sir", lambda b: yaratilgan.append(asl(b)) or
                        yaratilgan[-1])
    zsk = kalit_urugdan(bytes(range(1, 33)))
    with pytest.raises(BekorQilindi):
        zarb_qil(ZarbKirishi([1] * 10, bytes(16), "Q", 1), zsk,
                 jarayon=lambda i, n: i < 3)
    assert len(yaratilgan) == 2 and all(s == bytearray(32) for s in yaratilgan)
