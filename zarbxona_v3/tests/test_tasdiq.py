"""3.3 — ikki kishilik tasdiq: chegara, imzo, soxtalashtirish, xavfsiz tomonga o'tish."""

from __future__ import annotations

import json

import pytest

from core.buyurtma import Zarbxona
from core.ombor import ombor_yarat
from core.surat import Surat
from core.tasdiq import (DEFAULT_CHEGARA, TASDIQ_CHEGARA, XAVFSIZ_CHEGARA, TasdiqXatosi)

HOZIR = 1_800_000_000_000
TEZ = Surat(rejim="cheklovsiz")
PAROL = "tasdiqchi-parol-1"


@pytest.fixture
def z(tmp_path, kalitlar, sertifikat):
    sertifikat.yoz(tmp_path / "s.aqcert")
    zx = Zarbxona(tmp_path / "p", kalitlar[0], soat_ms=lambda: HOZIR)
    zx.sertifikat_import(tmp_path / "s.aqcert")
    yield zx
    zx.yop()


@pytest.fixture
def zt(z):
    z.tasdiq.tasdiqchi_yarat(PAROL, n=4096)
    return z


def test_tasdiqchisiz_ochiq(z):
    assert not z.tasdiq.yoqilgan and z.tasdiq.chegara() is None
    b = z.buyurtma_yarat(40_000_000, "Q", "", TEZ, partiya_hajmi=5000)
    assert z.tasdiq.holat(b) == "kerak emas"
    assert z.buyurtmani_bajar(b.buyurtma_id).holat == "tugadi"


def test_chegaradan_kichik_tasdiqsiz(zt):
    assert zt.tasdiq.chegara() == DEFAULT_CHEGARA
    b = zt.buyurtma_yarat(DEFAULT_CHEGARA - 1, "Q", "", TEZ, partiya_hajmi=5000)
    assert zt.tasdiq.holat(b) == "kerak emas"
    assert zt.buyurtmani_bajar(b.buyurtma_id).holat == "tugadi"


def test_katta_buyurtma_tasdiqsiz_zarb_qilinmaydi(zt):
    b = zt.buyurtma_yarat(DEFAULT_CHEGARA, "Q", "", TEZ, partiya_hajmi=5000)
    assert zt.tasdiq.holat(b) == "kutilmoqda"
    r = zt.buyurtmani_bajar(b.buyurtma_id)
    assert r.holat == "pauza" and "tasdiq" in r.xabar
    assert zt.jurnal.partiyalar() == []                         # hech narsa zarb qilinmadi
    with pytest.raises(TasdiqXatosi, match="parol"):
        zt.tasdiq.tasdiqla(b.buyurtma_id, "notogri-parol")
    iz_ = zt.tasdiq.tasdiqla(b.buyurtma_id, PAROL)
    assert "-" in iz_ and zt.tasdiq.holat(b) == "tasdiqlangan"
    assert zt.buyurtmani_bajar(b.buyurtma_id).holat == "tugadi"


@pytest.mark.parametrize("ustun,qiymat", [("summa", DEFAULT_CHEGARA + 5),
                                          ("zaxira_qulfi", "BOSHQA-QULF"),
                                          ("cheklov", '{"categories":["X"]}')])
def test_tasdiqdan_keyin_buyurtma_ozgarsa_yaroqsiz(zt, ustun, qiymat):
    b = zt.buyurtma_yarat(DEFAULT_CHEGARA, "Q", "", TEZ, partiya_hajmi=5000)
    zt.tasdiq.tasdiqla(b.buyurtma_id, PAROL)
    zt.jurnal._xom_yangila(f"UPDATE buyurtmalar SET {ustun}=? WHERE buyurtma_id=?",
                           (qiymat, b.buyurtma_id))
    b2 = zt.jurnal.buyurtma(b.buyurtma_id)
    assert zt.tasdiq.holat(b2) == "yaroqsiz"
    r = zt.buyurtmani_bajar(b.buyurtma_id)
    assert r.holat == "pauza" and "YAROQSIZ" in r.xabar
    assert zt.jurnal.partiyalar() == []


def test_chegarani_soxtalashtirish_xavfsiz_tomonga(zt):
    # birinchi operator chegarani imzosiz ko'taradi — tizim HAR buyurtmaga tasdiq so'raydi
    zt.jurnal.sozlama_yoz(TASDIQ_CHEGARA, json.dumps({"chegara": 10**12, "imzo": "00"}))
    assert zt.tasdiq.chegara() == XAVFSIZ_CHEGARA
    b = zt.buyurtma_yarat(5, "Q", "", TEZ)
    assert zt.tasdiq.holat(b) == "kutilmoqda"
    zt.jurnal.sozlama_yoz(TASDIQ_CHEGARA, "buzilgan json")
    assert zt.tasdiq.chegara() == XAVFSIZ_CHEGARA


def test_chegarani_faqat_tasdiqchi_ozgartiradi(zt):
    with pytest.raises(TasdiqXatosi):
        zt.tasdiq.chegara_ornat(1_000, "notogri-parol")
    assert zt.tasdiq.chegara() == DEFAULT_CHEGARA
    zt.tasdiq.chegara_ornat(1_000, PAROL)
    assert zt.tasdiq.chegara() == 1_000
    with pytest.raises(TasdiqXatosi):
        zt.tasdiq.chegara_ornat(0, PAROL)


def test_talab_yaratilganda_qotiriladi(zt):
    """Buyurtma yaratilganda tasdiq talab qilingan bo'lsa — chegara keyin ko'tarilsa ham."""
    b = zt.buyurtma_yarat(DEFAULT_CHEGARA, "Q", "", TEZ, partiya_hajmi=5000)
    zt.tasdiq.chegara_ornat(DEFAULT_CHEGARA * 10, PAROL)
    assert zt.tasdiq.holat(b) == "kutilmoqda"


def test_tasdiqchi_bir_marta_va_kalit_almashtirilsa_rad(zt, tmp_path):
    with pytest.raises(TasdiqXatosi, match="allaqachon"):
        zt.tasdiq.tasdiqchi_yarat("boshqa-parol-2", n=4096)
    # tasdiqchi.json ni boshqa (o'sha parolli) kalit bilan almashtirish
    zt.tasdiq.kalit_yoli.unlink()
    ombor_yarat(zt.tasdiq.kalit_yoli, PAROL, n=4096)
    b = zt.buyurtma_yarat(DEFAULT_CHEGARA, "Q", "", TEZ, partiya_hajmi=5000)
    with pytest.raises(TasdiqXatosi, match="mos emas"):
        zt.tasdiq.tasdiqla(b.buyurtma_id, PAROL)


def test_keraksiz_va_tugagan_buyurtma(zt):
    kichik = zt.buyurtma_yarat(5, "Q", "", TEZ)
    with pytest.raises(TasdiqXatosi, match="kerak emas"):
        zt.tasdiq.tasdiqla(kichik.buyurtma_id, PAROL)
    zt.buyurtma_bekor(kichik.buyurtma_id)
    with pytest.raises(TasdiqXatosi, match="holati"):
        zt.tasdiq.tasdiqla(kichik.buyurtma_id, PAROL)
    with pytest.raises(TasdiqXatosi, match="topilmadi"):
        zt.tasdiq.tasdiqla("yoq", PAROL)


def test_qisqa_parol_va_notogri_chegara(z):
    with pytest.raises(TasdiqXatosi):
        z.tasdiq.tasdiqchi_yarat("qisqa", n=4096)
    assert not z.tasdiq.yoqilgan and not z.tasdiq.kalit_yoli.exists()
    with pytest.raises(TasdiqXatosi):
        z.tasdiq.tasdiqchi_yarat(PAROL, chegara=0, n=4096)
