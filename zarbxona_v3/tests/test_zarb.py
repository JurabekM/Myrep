"""T3 (to'liq sikl), T4 (buzish), T6 (sur'at baytlarni o'zgartirmaydi),
T8 (buyurtma uzilishi), T9 (tiklash), T10 (yagona yozuvchi)."""

from __future__ import annotations

import sqlite3

import pytest

from core.buyurtma import BandXatosi, BuyurtmaXatosi, Zarbxona
from core.buzish import KUTILGAN_QOIDA, TURLAR, Buzuvchi, BuzishXatosi
from core.cheklov import cheklov_json
from core.ibtido import imzo_togri
from core.kupyura import muhrni_och
from core.partiya import (ZarbKirishi, nominallar_bolagi, nominallar_soni, nominallarga_bol,
                          partiya_oqi, partiya_yoz, zarb_qil)
from core.surat import BekorQilindi, Ritm, RitmSozlama, Surat
from core.tekshiruv import faylni_tekshir, jurnalni_tekshir, partiyani_tekshir

TEZ = Surat(rejim="cheklovsiz")
HOZIR = 1_800_000_000_000


@pytest.fixture
def zarbxona(tmp_path, kalitlar, sertifikat):
    zsk = kalitlar[0]
    z = Zarbxona(tmp_path / "profil", zsk, soat_ms=lambda: HOZIR)
    sertifikat.yoz(tmp_path / "s.aqcert")
    z.sertifikat_import(tmp_path / "s.aqcert")
    yield z
    z.yop()


def test_nominallar_bolagi_mos():
    for summa in (1, 7, 1_234_567, 99_999, 5000 * 3 + 1):
        n = nominallarga_bol(summa)
        assert nominallar_soni(summa) == len(n)
        for a in range(0, len(n), 37):
            assert nominallar_bolagi(summa, a, 50) == n[a:a + 50]
    assert len(nominallarga_bol(1_234_567)) == 256


def test_t3_toliq_sikl(zarbxona, kalitlar):
    z = zarbxona
    cj = cheklov_json(["seed"], None, 0, "")
    b = z.buyurtma_yarat(123_456, "AQ-RES-0001", cj, TEZ, partiya_hajmi=10)
    r = z.buyurtmani_bajar(b.buyurtma_id)
    assert r.holat == "tugadi"
    b2 = z.jurnal.buyurtma(b.buyurtma_id)
    assert b2.holat == "tugadi" and b2.bajarilgan_summa == 123_456
    assert b2.bajarilgan_kupyura == nominallar_soni(123_456)
    yozuvlar = z.jurnal.partiyalar()
    assert len(yozuvlar) == -(-b2.kupyura_soni // 10)
    for y in yozuvlar:
        h, p = faylni_tekshir(z.partiya_papka / y.fayl, z.pk, z.sertifikat)
        assert h.ok, h.matn()
        assert p.mint_label == "Test vakolati" and p.cheklov == cj
    h = jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat)
    assert h.ok, h.matn()
    assert z.qolgan_limit() == 50_000_000 - 123_456


def test_bosh_jurnal_tekshirilmadi_toza_emas(tmp_path, kalitlar):
    from core.jurnal import Jurnal
    from core.tekshiruv import Hisobot
    assert not Hisobot().ok                     # hech narsa tekshirilmagan ≠ toza
    j = Jurnal(tmp_path / "j.db")
    h = jurnalni_tekshir(j, tmp_path, kalitlar[1], None)
    assert h.ok  # bo'sh jurnal tekshirildi va unda muammo yo'q
    j.yop()


def test_fayl_ochilmasa_muammo(tmp_path, kalitlar):
    (tmp_path / "x.aqbatch").write_bytes(b"bu sqlite emas")
    h, p = faylni_tekshir(tmp_path / "x.aqbatch", kalitlar[1], None)
    assert p is None and not h.ok and "fayl" in h.qoidalar()


@pytest.mark.parametrize("tur", list(TURLAR))
def test_t4_buzish(zarbxona, tur):
    z = zarbxona
    b = z.buyurtma_yarat(5000 * 3 + 7, "AQ-RES-0002", "", TEZ, partiya_hajmi=100)
    assert z.buyurtmani_bajar(b.buyurtma_id).holat == "tugadi"
    pid = z.jurnal.partiyalar()[0].partiya_id
    assert jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat).ok
    bz = Buzuvchi(z.partiya_papka, z.jurnal)
    tavsif = bz.buz(tur, pid)
    eski, yangi = tavsif.split(": ", 1)[1].split(" → ")
    assert eski != yangi
    h = jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat)
    assert not h.ok
    assert KUTILGAN_QOIDA[tur] in h.qoidalar(), (tur, h.matn())
    bz.tikla()
    assert jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat).ok


def test_t4_nominal_5000_ham_buziladi(zarbxona):
    """v2 xatosi: kupyura allaqachon 5000 bo'lsa «5000 qilish» hech narsani buzmagan."""
    z = zarbxona
    b = z.buyurtma_yarat(5000, "AQ-RES-0003", "", TEZ)
    z.buyurtmani_bajar(b.buyurtma_id)
    y = z.jurnal.partiyalar()[0]
    p = partiya_oqi(z.partiya_papka / y.fayl)
    assert p.qatorlar[0].nominal == 5000
    Buzuvchi(z.partiya_papka, z.jurnal).buz("nominal", y.partiya_id)
    assert partiya_oqi(z.partiya_papka / y.fayl).qatorlar[0].nominal != 5000


def test_buzish_farqsiz_qiymat_rad_etiladi():
    from core.buzish import _farqli
    with pytest.raises(BuzishXatosi):
        _farqli(5, (5,))


def test_t6_surat_baytlarni_ozgartirmaydi(kalitlar):
    zsk = kalitlar[0]
    k = ZarbKirishi(nominallarga_bol(12_345), bytes(16), "AQ-RES-X", 7, "")
    sirlar = dict(partiya_id=bytes(range(16)), partiya_kaliti=bytes(32),
                  master=bytes(range(32)), zarb_ms=HOZIR)
    tez = zarb_qil(k, zsk, **sirlar)
    t = [0.0]
    ritm = Ritm(RitmSozlama(tezlik=2.0, byudjet=0.1, N=3, X=5.0),
                soat=lambda: t[0], uxla=lambda d: t.__setitem__(0, t[0] + d))
    kuzatilgan = []
    sekin = zarb_qil(k, zsk, ritm=ritm, kuzatuv=lambda q, i, n: kuzatilgan.append(i),
                     soat=lambda: t[0], **sirlar)
    assert t[0] > 10                                 # soxta vaqt haqiqatan o'tdi
    assert kuzatilgan == list(range(len(k.nominallar)))
    assert sekin.ildiz == tez.ildiz
    assert sekin.imzo_xabari() == tez.imzo_xabari()
    assert [q.muhr for q in sekin.qatorlar] == [q.muhr for q in tez.qatorlar]
    assert [q.isbot for q in sekin.qatorlar] == [q.isbot for q in tez.qatorlar]


def test_zarb_ms_bitta_va_muhr_ochiladi(kalitlar):
    zsk, zpk = kalitlar[0], kalitlar[1]
    mk = bytes(range(32))
    p = zarb_qil(ZarbKirishi([5, 10, 50], bytes(16), "Q", 1), zsk, master=mk, zarb_ms=HOZIR)
    for q in p.qatorlar:
        yd = muhrni_och(mk, q.note_id, q.muhr, q.kod())
        assert yd is not None and int.from_bytes(yd[32:40], "little") == HOZIR
        # AAD — sarlavha: egasini o'zgartirsak yadro ochilmaydi
        q2 = type(q)(**{**{s: getattr(q, s) for s in q.__slots__}, "egasi": "BOSHQA"})
        assert muhrni_och(mk, q.note_id, q.muhr, q2.kod()) is None
    assert imzo_togri(zpk, p.imzo, p.imzo_xabari())


def test_zarb_kirishi_tekshiruvi(kalitlar):
    from core.partiya import ZarbXatosi
    zsk = kalitlar[0]
    for k in (ZarbKirishi([], bytes(16), "Q", 1), ZarbKirishi([3], bytes(16), "Q", 1),
              ZarbKirishi([5], bytes(16), "  ", 1), ZarbKirishi([5], bytes(16), "Q", 0)):
        with pytest.raises(ZarbXatosi):
            zarb_qil(k, zsk)


def test_limit_va_buyurtma_cheklovlari(zarbxona):
    z = zarbxona
    with pytest.raises(BuyurtmaXatosi):
        z.buyurtma_yarat(50_000_001, "Q", "", TEZ)
    z.buyurtma_yarat(40_000_000, "Q", "", TEZ)
    with pytest.raises(BuyurtmaXatosi):   # boshqa faol buyurtma limitni band qilgan
        z.buyurtma_yarat(10_000_001, "Q", "", TEZ)
    with pytest.raises(BuyurtmaXatosi):
        z.buyurtma_yarat(10, "   ", "", TEZ)


def test_sertifikat_muddati_otsa_pauza(tmp_path, kalitlar, sertifikat):
    vaqt = [HOZIR]
    z = Zarbxona(tmp_path / "p", kalitlar[0], soat_ms=lambda: vaqt[0])
    sertifikat.yoz(tmp_path / "s.aqcert")
    z.sertifikat_import(tmp_path / "s.aqcert")
    b = z.buyurtma_yarat(100, "Q", "", TEZ, partiya_hajmi=1)
    vaqt[0] = sertifikat.valid_until_ms + 1
    r = z.buyurtmani_bajar(b.buyurtma_id)
    assert r.holat == "pauza" and "muddati" in r.xabar
    assert z.jurnal.buyurtma(b.buyurtma_id).holat == "pauza"
    z.yop()


def test_t8_uzilish_va_davom(tmp_path, kalitlar, sertifikat):
    papka = tmp_path / "profil"
    sertifikat.yoz(tmp_path / "s.aqcert")
    summa = 5000 * 20 + 1000 * 3 + 50 + 7    # 20+3+1+1+2 = 27 kupyura
    z = Zarbxona(papka, kalitlar[0], soat_ms=lambda: HOZIR)
    z.sertifikat_import(tmp_path / "s.aqcert")
    b = z.buyurtma_yarat(summa, "AQ-RES-T8", "", TEZ, partiya_hajmi=5)

    # 3-partiya o'rtasida (umumiy 13-kupyura) TO'XTATISH
    sanoq = [0]

    def kuzat(q, i, n):
        sanoq[0] += 1

    r = z.buyurtmani_bajar(b.buyurtma_id, kuzatuv=kuzat, bekormi=lambda: sanoq[0] >= 13)
    assert r.holat == "toxtatildi" and len(r.partiyalar) == 2
    assert not list(z.partiya_papka.glob("*.yarim"))
    assert len(list(z.partiya_papka.glob("*.aqbatch"))) == 2
    z.yop()

    # qayta ochish → davom
    z = Zarbxona(papka, kalitlar[0], soat_ms=lambda: HOZIR)
    t = z.tiklash()
    assert not t.karantin
    b2 = z.jurnal.buyurtma(b.buyurtma_id)
    assert b2.bajarilgan_kupyura == 10 and b2.holat == "pauza"
    r = z.buyurtmani_bajar(b.buyurtma_id)
    assert r.holat == "tugadi"
    ys = z.jurnal.partiyalar()
    seqlar = [(y.birinchi_seq, y.oxirgi_seq) for y in ys]
    assert seqlar[0][0] == 1
    for (a1, b1), (a2, b2_) in zip(seqlar, seqlar[1:]):
        assert a2 == b1 + 1                       # uzluksiz, kesishmaydi
    assert sum(y.jami for y in ys) == summa
    assert sum(y.soni for y in ys) == 27
    assert z.chiqarilgan() <= sertifikat.limit_amount
    assert jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat).ok
    # butun buyurtma nominallari deterministik ro'yxat bilan bir xil
    nom = []
    for y in ys:
        nom += [q.nominal for q in partiya_oqi(z.partiya_papka / y.fayl).qatorlar]
    assert nom == nominallarga_bol(summa)
    z.yop()


def test_faol_buyurtma_avtomatik_davom_etmaydi(tmp_path, kalitlar, sertifikat):
    papka = tmp_path / "p"
    sertifikat.yoz(tmp_path / "s.aqcert")
    z = Zarbxona(papka, kalitlar[0], soat_ms=lambda: HOZIR)
    z.sertifikat_import(tmp_path / "s.aqcert")
    b = z.buyurtma_yarat(500, "Q", "", TEZ)   # 'faol' — jarayon «o'lgan»
    z.yop()
    z = Zarbxona(papka, kalitlar[0], soat_ms=lambda: HOZIR)
    t = z.tiklash()
    assert [x.buyurtma_id for x in t.davom_taklifi] == [b.buyurtma_id]
    assert z.jurnal.partiyalar() == []
    z.yop()


def test_t9_tiklash(zarbxona, kalitlar, sertifikat):
    z = zarbxona
    zsk = kalitlar[0]
    # (a) .yarim o'chiriladi
    (z.partiya_papka / "partiya-abc.aqbatch.yarim").write_bytes(b"yarim")
    # (b) jurnalsiz toza fayl (4-qadamdan keyin, 5-dan oldin uzilish) — buyurtmaga bog'lanadi
    b = z.buyurtma_yarat(5000 * 4, "AQ-RES-T9", "", TEZ, partiya_hajmi=2)
    p = zarb_qil(ZarbKirishi(nominallar_bolagi(b.summa, 0, 2), sertifikat.cert_id,
                             "AQ-RES-T9", z.jurnal.keyingi_seq(), "",
                             mint_label=sertifikat.label), zsk, zarb_ms=HOZIR)
    partiya_yoz(p, z.partiya_papka)
    # (c) buzilgan fayl — karantin
    p2 = zarb_qil(ZarbKirishi([5], sertifikat.cert_id, "Q", 999, ""), zsk, zarb_ms=HOZIR)
    y2 = partiya_yoz(p2, z.partiya_papka)
    db = sqlite3.connect(y2)
    with db:
        db.execute("UPDATE notes SET denomination=10")
    db.close()

    t = z.tiklash()
    assert t.ochirilgan_yarim == ["partiya-abc.aqbatch.yarim"]
    assert t.qabul_qilingan == [p.fayl_nomi()]
    assert [n for n, _ in t.karantin] == [p2.fayl_nomi()]
    assert (z.karantin_papka / p2.fayl_nomi()).exists()      # jim o'chirilmadi
    y = z.jurnal.partiyalar()
    assert len(y) == 1 and y[0].buyurtma_id == b.buyurtma_id
    assert z.jurnal.buyurtma(b.buyurtma_id).bajarilgan_kupyura == 2
    # davom etsa — qolgan 2 kupyura
    assert z.buyurtmani_bajar(b.buyurtma_id).holat == "tugadi"
    assert z.jurnal.buyurtma(b.buyurtma_id).bajarilgan_summa == 20_000
    assert jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat).ok


def test_t10_yagona_yozuvchi(tmp_path, kalitlar):
    z = Zarbxona(tmp_path / "p", kalitlar[0])
    with pytest.raises(BandXatosi):
        Zarbxona(tmp_path / "p", kalitlar[0])
    z.yop()
    Zarbxona(tmp_path / "p", kalitlar[0]).yop()   # ozod qilingandan keyin — ochiladi


def test_tekshiruv_limit_va_vakolat(kalitlar, sertifikat):
    zsk, zpk = kalitlar[0], kalitlar[1]
    p = zarb_qil(ZarbKirishi([5000], sertifikat.cert_id, "Q", 1), zsk, zarb_ms=HOZIR)
    assert partiyani_tekshir(p, zpk, sertifikat).ok
    assert "limit" in partiyani_tekshir(p, zpk, sertifikat, limit_qolgan=100).qoidalar()
    assert "vakolat" in partiyani_tekshir(p, zpk, sertifikat,
                                          hozir_ms=sertifikat.valid_until_ms + 1).qoidalar()
    assert "sertifikat" in partiyani_tekshir(p, zpk, None).qoidalar()


def test_bekor_qilish_cheklovsiz_rejimda(kalitlar):
    zsk = kalitlar[0]
    k = ZarbKirishi([1] * 600, bytes(16), "Q", 1)
    n = [0]

    def bekor():
        n[0] += 1
        return True
    with pytest.raises(BekorQilindi):
        zarb_qil(k, zsk, bekormi=bekor)
    assert n[0] == 1    # 250-kupyurada birinchi marta tekshirildi
