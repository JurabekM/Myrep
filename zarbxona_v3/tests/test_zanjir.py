"""1.2 — jurnal xesh-zanjiri: o'zgartirish, o'chirish, kalitsiz qayta hisoblash aniqlanadi."""

from __future__ import annotations

import pytest

from core.buyurtma import Zarbxona
from core.jurnal import ZANJIR_BOSH, ZANJIR_VERSIYA
from core.surat import Surat
from core.tekshiruv import jurnalni_tekshir
from core.zanjir import NOL, bogin_xeshi, bosh_json, bosh_tahlil

HOZIR = 1_800_000_000_000
TEZ = Surat(rejim="cheklovsiz")


@pytest.fixture
def z(tmp_path, kalitlar, sertifikat):
    sertifikat.yoz(tmp_path / "s.aqcert")
    zx = Zarbxona(tmp_path / "p", kalitlar[0], soat_ms=lambda: HOZIR)
    zx.sertifikat_import(tmp_path / "s.aqcert")
    b = zx.buyurtma_yarat(5000 * 8, "AQ-RES-Z", "", TEZ, partiya_hajmi=2)   # 4 partiya
    zx.buyurtmani_bajar(b.buyurtma_id)
    yield zx
    zx.yop()


def tekshir(z):
    return jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat)


def sql(z, q, p=()):
    z.jurnal._xom_yangila(q, p)


def test_zanjir_quriladi_va_toza(z):
    ys = z.jurnal.partiyalar()
    bs = z.jurnal.zanjir_boginlari()
    assert len(ys) == len(bs) == 4
    x = NOL
    for i, (y, b) in enumerate(zip(ys, bs)):
        assert b[0] == i and b[1] == y.partiya_id and b[2] == x.hex()
        x = bogin_xeshi(x, y)
        assert b[3] == x.hex()
    tartib, xesh, _ = bosh_tahlil(z.jurnal.sozlama(ZANJIR_BOSH))
    assert tartib == 4 and xesh == x
    assert tekshir(z).ok


def test_topshirish_belgisi_zanjirni_buzmaydi(z):
    pid = z.jurnal.partiyalar()[0].partiya_id
    z.jurnal.topshirildi(pid, HOZIR)
    z.jurnal.topshirish_xatosi(pid, "tarmoq: sinov")
    assert tekshir(z).ok


@pytest.mark.parametrize("ustun,qiymat", [("jami", 1), ("zaxira_qulfi", "BOSHQA"),
                                          ("buyurtma_id", None), ("zarb_ms", 1)])
def test_yozuvni_ozgartirish_aniqlanadi(z, ustun, qiymat):
    pid = z.jurnal.partiyalar()[1].partiya_id
    sql(z, f"UPDATE partiyalar SET {ustun}=? WHERE partiya_id=?", (qiymat, pid))
    assert "zanjir" in tekshir(z).qoidalar()


def test_orta_yozuvni_zanjiri_bilan_ochirish(z):
    pid = z.jurnal.partiyalar()[1].partiya_id
    sql(z, "DELETE FROM zanjir WHERE partiya_id=?", (pid,))
    sql(z, "DELETE FROM partiyalar WHERE partiya_id=?", (pid,))
    assert "zanjir" in tekshir(z).qoidalar()


def test_oxirgi_yozuvni_ochirish_faqat_imzolangan_bosh_bilan_topiladi(z):
    """Dumni kesish: qolgan zanjir o'zi izchil — faqat imzolangan bosh sezadi."""
    pid = z.jurnal.partiyalar()[-1].partiya_id
    sql(z, "DELETE FROM zanjir WHERE partiya_id=?", (pid,))
    sql(z, "DELETE FROM partiyalar WHERE partiya_id=?", (pid,))
    (z.partiya_papka / f"partiya-{pid[:12]}.aqbatch").unlink()   # izni ham yo'qotadi
    h = tekshir(z)
    assert h.qoidalar() == {"zanjir-bosh"}, h.matn()


def test_kalitsiz_qayta_hisoblash_imzodan_otmaydi(z):
    """Bosqinchi jami ni o'zgartirib, butun zanjirni va bosh xeshini qayta hisoblaydi,
    lekin kalit yo'q — eski imzoni qoldiradi yoki soxta imzo qo'yadi."""
    ys = z.jurnal.partiyalar()
    sql(z, "UPDATE partiyalar SET jami=jami+1 WHERE partiya_id=?", (ys[0].partiya_id,))
    ys = z.jurnal.partiyalar()
    x = NOL
    sql(z, "DELETE FROM zanjir")
    for i, y in enumerate(ys):
        yangi = bogin_xeshi(x, y)
        sql(z, "INSERT INTO zanjir VALUES (?,?,?,?)", (i, y.partiya_id, x.hex(), yangi.hex()))
        x = yangi
    _, _, eski_imzo = bosh_tahlil(z.jurnal.sozlama(ZANJIR_BOSH))
    for imzo in (eski_imzo, bytes(len(eski_imzo))):
        z.jurnal.sozlama_yoz(ZANJIR_BOSH, bosh_json(len(ys), x, imzo))
        h = tekshir(z)
        assert "zanjir-bosh" in h.qoidalar() and "imzo" in h.matn()


def test_zanjir_belgisini_ochirish(z):
    sql(z, "DELETE FROM sozlama WHERE kalit=?", (ZANJIR_VERSIYA,))
    assert "zanjir" in tekshir(z).qoidalar()


def test_eski_jurnal_migratsiyasi(tmp_path, kalitlar, sertifikat):
    """Zanjirsiz eski v3 jurnali: ochilganda bir marta quriladi va toza chiqadi."""
    sertifikat.yoz(tmp_path / "s.aqcert")
    papka = tmp_path / "p"
    zx = Zarbxona(papka, kalitlar[0], soat_ms=lambda: HOZIR)
    zx.sertifikat_import(tmp_path / "s.aqcert")
    zx.buyurtmani_bajar(zx.buyurtma_yarat(5000 * 3, "Q", "", TEZ, partiya_hajmi=1).buyurtma_id)
    for q in ("DELETE FROM zanjir", "DELETE FROM sozlama WHERE kalit='zanjir_bosh'",
              "DELETE FROM sozlama WHERE kalit='zanjir_versiya'"):
        sql(zx, q)
    assert zx.jurnal.zanjir_migratsiya_kerak()
    zx.yop()
    zx = Zarbxona(papka, kalitlar[0], soat_ms=lambda: HOZIR)
    try:
        assert not zx.jurnal.zanjir_migratsiya_kerak()
        assert len(zx.jurnal.zanjir_boginlari()) == 3
        assert tekshir(zx).ok
        # migratsiyadan keyin yangi partiyalar zanjirga ulanadi
        zx.buyurtmani_bajar(zx.buyurtma_yarat(10, "Q", "", TEZ).buyurtma_id)
        assert len(zx.jurnal.zanjir_boginlari()) == 4 and tekshir(zx).ok
        # mavjud (buzilgan) zanjir migratsiya bilan «tuzatilmaydi»
        sql(zx, "DELETE FROM zanjir WHERE tartib=1")
        assert zx.jurnal.zanjir_migratsiya(zx._imzo) == 0
        assert "zanjir" in tekshir(zx).qoidalar()
    finally:
        zx.yop()
