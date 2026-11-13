"""3.1 — DEMO bank: to'liq halqa (sertifikat → zarb → onlayn topshirish → qabul),
holat saqlanishi, idempotentlik va haqiqiy profilni himoyalash."""

from __future__ import annotations

import pytest

from core.buyurtma import Zarbxona
from core.demo_bank import DEMO_BELGI, DemoBank, DemoXatosi, demo_tayyorla
from core.surat import Surat
from core.tekshiruv import jurnalni_tekshir
from core.topshirish import RAD, AvtoTopshiruvchi

TEZ = Surat(rejim="cheklovsiz")


@pytest.fixture
def profil(tmp_path, kalitlar):
    z = Zarbxona(tmp_path / "data_demo", kalitlar[0])
    yield z
    z.yop()


def avto(z, db):
    return AvtoTopshiruvchi(z.jurnal, z.partiya_papka,
                            lambda: db.mijoz(z.sk, z.sertifikat), soat_ms=z.soat_ms)


def test_demo_tayyorla_yangi_profil(profil):
    db = demo_tayyorla(profil)
    s = profil.sertifikat
    assert s is not None and s.bank_public_key == db.pk and s.label.startswith(DEMO_BELGI)
    assert s.muammo(profil.pk) is None
    assert len(db.qulflar()) == 1
    assert DemoBank.bormi(profil.papka)
    # qayta chaqirish — yangi sertifikat yoki qulf ochmaydi
    db2 = demo_tayyorla(profil)
    assert profil.sertifikat.cert_id == s.cert_id and db2.pk == db.pk
    assert len(db2.qulflar()) == 1


def test_toliq_halqa_va_saqlanish(profil):
    z = profil
    db = demo_tayyorla(z)
    qulf = next(iter(db.qulflar()))
    b = z.buyurtma_yarat(1_234_567, qulf, "", TEZ, partiya_hajmi=100)   # 256 kupyura
    assert z.buyurtmani_bajar(b.buyurtma_id).holat == "tugadi"
    assert avto(z, db).bir_aylanish() == "bajarildi"
    assert z.jurnal.topshirilmaganlar() == []
    assert db.chiqarilgan(z.sertifikat.cert_id) == 1_234_567
    assert len(db.qabul_qilinganlar()) == 3
    assert db.qulflar()[qulf] == 50_000_000 - 1_234_567
    assert jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat).ok

    # bank «qayta ishga tushdi» — holat diskdan o'qiladi
    db2 = DemoBank(db.papka)
    assert db2.pk == db.pk and len(db2.qabul_qilinganlar()) == 3
    # jurnalda belgini yo'qotsak ham (javob yo'qolgan holat) — takror idempotent
    for y in z.jurnal.partiyalar():
        z.jurnal._xom_yangila("UPDATE partiyalar SET topshirilgan_ms=NULL WHERE partiya_id=?",
                              (y.partiya_id,))
    assert avto(z, db2).bir_aylanish() == "bajarildi"
    assert z.jurnal.topshirilmaganlar() == []
    assert db2.chiqarilgan(z.sertifikat.cert_id) == 1_234_567     # ikki marta hisoblanmadi


def test_qulf_yetmasa_bank_rad_etadi(profil):
    z = profil
    db = demo_tayyorla(z)
    kichik = db.qulf_och(5000)
    b = z.buyurtma_yarat(5000 * 2, kichik, "", TEZ, partiya_hajmi=1)
    z.buyurtmani_bajar(b.buyurtma_id)
    assert avto(z, db).bir_aylanish() == "rad"
    ys = z.jurnal.partiyalar()
    assert ys[0].topshirilgan_ms is not None
    assert ys[1].topshirish_xatosi.startswith(RAD) and "qulf" in ys[1].topshirish_xatosi


def test_haqiqiy_sertifikatli_profil_demoga_aylanmaydi(tmp_path, kalitlar, sertifikat):
    z = Zarbxona(tmp_path / "data", kalitlar[0], soat_ms=lambda: 1_800_000_000_000)
    try:
        sertifikat.yoz(tmp_path / "s.aqcert")
        z.sertifikat_import(tmp_path / "s.aqcert")
        with pytest.raises(DemoXatosi):
            demo_tayyorla(z)
        assert not DemoBank.bormi(z.papka)
        assert z.sertifikat.cert_id == sertifikat.cert_id
    finally:
        z.yop()


def test_partiyali_profil_demoga_aylanmaydi(tmp_path, kalitlar, sertifikat, profil):
    z = profil
    sertifikat.yoz(tmp_path / "s.aqcert")
    z.sertifikat_import(tmp_path / "s.aqcert")
    z.soat_ms = lambda: 1_800_000_000_000
    z.buyurtmani_bajar(z.buyurtma_yarat(5, "Q", "", TEZ).buyurtma_id)
    z.sertifikat = None                           # sertifikat fayli yo'qolgan bo'lsa ham
    with pytest.raises(DemoXatosi):
        demo_tayyorla(z)


def test_main_demo_default_papka():
    from app.main import ILDIZ, argumentlar
    a = argumentlar(["--demo"])
    assert a.demo and a.papka is None       # main() uni ILDIZ/data_demo qiladi
    assert (ILDIZ / "data_demo").name == "data_demo"
