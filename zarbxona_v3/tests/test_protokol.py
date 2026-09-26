"""T11 (protokol SoxtaFabrika + soxta bank bilan), T12 (wire), T13 (avto-topshirish)."""

from __future__ import annotations

import pytest

from core.buyurtma import Zarbxona
from core.ibtido import kalit_urugdan, ochiq_kalit
from core.kanal import XotiraKanali
from core.partiya import ZarbKirishi, nominallarga_bol, zarb_qil
from core.protokol import B2C, C2B, ProtokolXatosi, Wire, kodla, och, qator_kodla, qator_och
from core.sertifikat import sertifikat_yarat
from core.sessiya import SessiyaXatosi, SoxtaFabrika
from core.surat import BekorQilindi, Surat
from core.topshirish import (KUTISH_MAX, RAD, AvtoTopshiruvchi, BankXatosi, Mijoz,
                             TarmoqXatosi)
from soxta_bank import BankHolati, SoxtaBank

HOZIR = 1_800_000_000_000


@pytest.fixture
def bank(sertifikat):
    h = BankHolati()
    h.sertlar[sertifikat.cert_id] = sertifikat
    h.qulflar["AQ-RES-1"] = 10_000_000
    return h


def ulanish(kalitlar, sertifikat, holat, **kw):
    mk, bk = XotiraKanali.juft()
    b = SoxtaBank(bk, kalitlar[3], holat, **kw)
    m = Mijoz(mk, SoxtaFabrika(), sertifikat, kalitlar[0], muddat=3, hs_muddat=3)
    return m, b, mk


def partiya(kalitlar, sertifikat, nominallar, seq=1, qulf="AQ-RES-1", cheklov=""):
    return zarb_qil(ZarbKirishi(nominallar, sertifikat.cert_id, qulf, seq, cheklov,
                                mint_label=sertifikat.label), kalitlar[0], zarb_ms=HOZIR)


def test_qator_kodlash():
    from core.kupyura import Qator
    q = Qator(3, b"\x01" * 32, 50, "AQ-TREASURY", 9, b"\x02" * 16, bytes(32), b"\x03" * 72,
              b"\x04" * 64)
    r = qator_kodla(q)
    assert len(r) == 8 and r[1] == 50 and r[2] == "AQ-TREASURY"
    assert qator_och(r, 3) == q
    with pytest.raises(ProtokolXatosi):
        qator_och(r[:7], 0)
    with pytest.raises(ProtokolXatosi):
        kodla({"v": 1, "x": "a" * 1_048_576})


def test_t11_toliq_halqa(kalitlar, sertifikat, bank):
    m, b, _ = ulanish(kalitlar, sertifikat, bank, hodisa_yubor=True)
    v = m.ulan()
    assert v["remaining"] == sertifikat.limit_amount and v["chunk_notes"] == 250
    p = partiya(kalitlar, sertifikat, nominallarga_bol(1_234_567) + [1] * 400)  # 656 kupyura
    bolaklar = []
    r = m.partiya_topshir(p, jarayon=lambda i, n: bolaklar.append(i))
    assert r["note_count"] == 656 and r["total"] == 1_234_967
    assert bolaklar == [250, 500, 656] and b.bolaklar == 3
    assert bank.chiqarilgan[sertifikat.cert_id] == 1_234_967
    m.yop()
    b.join(3)
    assert b.oplar == ["mint_auth", "batch_begin", "batch_chunk", "batch_chunk",
                       "batch_chunk", "batch_commit", "bye"]
    assert b.xato is None


def test_t11_takroriy_topshirish_idempotent(kalitlar, sertifikat, bank):
    p = partiya(kalitlar, sertifikat, [5000, 5])
    m, b, _ = ulanish(kalitlar, sertifikat, bank)
    m.ulan()
    m.partiya_topshir(p)
    assert m.partiya_topshir(p) == {"allaqachon": True}
    m.yop()
    assert bank.chiqarilgan[sertifikat.cert_id] == 5005   # ikki marta hisoblanmadi


def test_t11_bekor_qilishda_abort(kalitlar, sertifikat, bank):
    p = partiya(kalitlar, sertifikat, [1] * 600)
    m, b, _ = ulanish(kalitlar, sertifikat, bank)
    m.ulan()
    n = [0]

    def bekor():
        n[0] += 1
        return n[0] > 1
    with pytest.raises(BekorQilindi):
        m.partiya_topshir(p, bekormi=bekor)
    assert b.abort_soni == 1 and not bank.qabul
    # sessiya tirik: keyingi partiya topshiriladi
    assert m.partiya_topshir(p)["note_count"] == 600
    m.yop()


def test_t11_bank_rad_etadi_va_abort(kalitlar, sertifikat, bank):
    p = partiya(kalitlar, sertifikat, [5000], qulf="YOQ-QULF")
    m, b, _ = ulanish(kalitlar, sertifikat, bank)
    m.ulan()
    with pytest.raises(BankXatosi) as e:
        m.partiya_topshir(p)
    assert e.value.code == "bank_error" and "qulf" in e.value.matn
    assert not bank.qabul
    m.yop()


def test_t11_notogri_mint_auth(kalitlar, sertifikat, bank):
    boshqa = kalit_urugdan(b"\x09" * 32)
    mk, bk = XotiraKanali.juft()
    b = SoxtaBank(bk, kalitlar[3], bank)
    m = Mijoz(mk, SoxtaFabrika(), sertifikat, boshqa, muddat=3, hs_muddat=3)
    with pytest.raises(BankXatosi) as e:
        m.ulan()
    assert e.value.code == "unauthorized"


def test_t11_id_mos_kelmasligi(kalitlar, sertifikat, bank):
    m, b, _ = ulanish(kalitlar, sertifikat, bank, notogri_id=True)
    m.ulan()
    with pytest.raises(ProtokolXatosi):
        m.partiya_topshir(partiya(kalitlar, sertifikat, [5]))


def test_t11_bank_kaliti_pinlangan(kalitlar, sertifikat, bank):
    """Boshqa bank (boshqa kalit) — handshake rad etiladi."""
    mk, bk = XotiraKanali.juft()
    begona = ochiq_kalit(kalit_urugdan(b"\x07" * 32))
    SoxtaBank(bk, begona, bank)
    m = Mijoz(mk, SoxtaFabrika(), sertifikat, kalitlar[0], muddat=3, hs_muddat=3)
    with pytest.raises(SessiyaXatosi):
        m.ulan()


def test_t11_javob_kelmasa_tarmoq_xatosi(kalitlar, sertifikat, bank):
    m, b, _ = ulanish(kalitlar, sertifikat, bank, javobsiz_op="batch_commit")
    m.muddat = 0.3
    m.ulan()
    with pytest.raises(TarmoqXatosi):
        m.partiya_topshir(partiya(kalitlar, sertifikat, [5]))


def test_t12_wire_tashlaydi_sessiya_tirik(kalitlar, sertifikat, bank):
    m, b, mk = ulanish(kalitlar, sertifikat, bank, dublikat=True)
    m.ulan()
    w = m.wire
    # begona paketlar: soxta teg, qisqa, noto'g'ri sehr, eski hisoblagich
    mk.aralash(b"AQW1" + bytes(8) + bytes(16) + b"soxta")
    mk.aralash(b"qisqa")
    mk.aralash(b"XXXX" + bytes(30))
    begona = Wire(b"\x00" * 32, yuborish=B2C, qabul=C2B)
    mk.aralash(begona.ora(b"\x17{}"))
    p = partiya(kalitlar, sertifikat, [5000, 1000, 500])
    assert m.partiya_topshir(p)["note_count"] == 3
    # dublikatlar (har javob ikki marta) + 4 ta begona — hammasi jim tashlandi
    assert w.tashlangan >= 4 + 3
    m.yop()


def test_t12_wire_birlik():
    k = bytes(range(32))
    a, b = Wire(k), Wire(k, yuborish=B2C, qabul=C2B)
    p1, p2 = a.ora(b"bir"), a.ora(b"ikki")
    assert b.ech(p2) == b"ikki"
    assert b.ech(p1) is None            # eski hisoblagich
    assert b.ech(p2) is None            # dublikat
    buz = bytearray(a.ora(b"uch"))
    buz[-1] ^= 1
    assert b.ech(bytes(buz)) is None    # teg mos emas
    assert b.ech(b"AQW1") is None       # qisqa
    assert b.tashlangan == 4
    assert b.ech(a.ora(b"to'rt")) == "to'rt".encode()   # sessiya tirik
    # yo'nalish: o'z paketimizni qaytarib olmaymiz
    assert Wire(k).ech(Wire(k).ora(b"x")) is None


def test_t12_xabar_formati():
    assert och(b'{"v":1,"op":"x"}')["op"] == "x"
    for b in (b"{}", b"[1]", b"\xff", b'{"v":2}'):
        with pytest.raises(ProtokolXatosi):
            och(b)


# --- T13 avto-topshirish ----------------------------------------------------------


@pytest.fixture
def profil(tmp_path, kalitlar, sertifikat):
    z = Zarbxona(tmp_path / "p", kalitlar[0], soat_ms=lambda: HOZIR)
    sertifikat.yoz(tmp_path / "s.aqcert")
    z.sertifikat_import(tmp_path / "s.aqcert")
    yield z
    z.yop()


def test_t13_avto_tarmoq_xatosida_qayta_urinadi(profil, kalitlar, sertifikat, bank):
    z = profil
    b = z.buyurtma_yarat(5000 * 5, "AQ-RES-1", "", Surat(rejim="cheklovsiz"), partiya_hajmi=2)
    z.buyurtmani_bajar(b.buyurtma_id)
    assert len(z.jurnal.topshirilmaganlar()) == 3
    urinish = [0]
    banklar = []

    def mijoz_yarat():
        urinish[0] += 1
        mk, bk = XotiraKanali.juft()
        if urinish[0] <= 2:           # birinchi ikkita — bank javob bermaydi
            return Mijoz(mk, SoxtaFabrika(), sertifikat, kalitlar[0], muddat=0.2,
                         hs_muddat=0.2)
        banklar.append(SoxtaBank(bk, kalitlar[3], bank))
        return Mijoz(mk, SoxtaFabrika(), sertifikat, kalitlar[0], muddat=3, hs_muddat=3)

    a = AvtoTopshiruvchi(z.jurnal, z.partiya_papka, mijoz_yarat, soat_ms=lambda: HOZIR)
    assert a.bir_aylanish() == "tarmoq"
    assert z.jurnal.topshirilmaganlar()[0].topshirish_xatosi.startswith("tarmoq")
    assert a.keyingi_kutish() == 5
    assert a.bir_aylanish() == "tarmoq"
    assert a.keyingi_kutish() == 10
    assert a.bir_aylanish() == "bajarildi"
    assert z.jurnal.topshirilmaganlar() == []
    assert all(y.topshirish_xatosi is None for y in z.jurnal.partiyalar())
    # seq tartibida
    assert [x.hex() for x in bank.qabul_tartibi] == [y.partiya_id for y in z.jurnal.partiyalar()]
    assert a.bir_aylanish() == "bosh"
    for _ in range(10):
        a.keyingi_kutish()
    assert a.keyingi_kutish() == KUTISH_MAX


def test_t13_bank_rad_etsa_keyingilari_yuborilmaydi(profil, kalitlar, sertifikat, bank):
    z = profil
    bank.qulflar["AQ-RES-1"] = 5000 * 2          # faqat birinchi partiyaga yetadi
    b = z.buyurtma_yarat(5000 * 5, "AQ-RES-1", "", Surat(rejim="cheklovsiz"), partiya_hajmi=2)
    z.buyurtmani_bajar(b.buyurtma_id)
    oplar = []

    def mijoz_yarat():
        mk, bk = XotiraKanali.juft()
        sb = SoxtaBank(bk, kalitlar[3], bank)
        oplar.append(sb)
        return Mijoz(mk, SoxtaFabrika(), sertifikat, kalitlar[0], muddat=3, hs_muddat=3)

    a = AvtoTopshiruvchi(z.jurnal, z.partiya_papka, mijoz_yarat, soat_ms=lambda: HOZIR)
    assert a.bir_aylanish() == "rad"
    ys = z.jurnal.partiyalar()
    assert ys[0].topshirilgan_ms == HOZIR
    assert ys[1].topshirilgan_ms is None and ys[1].topshirish_xatosi.startswith(RAD)
    assert ys[2].topshirilgan_ms is None and ys[2].topshirish_xatosi is None
    oplar[0].join(3)
    assert oplar[0].oplar.count("batch_begin") == 2      # uchinchisi yuborilmadi
    # keyingi aylanish ham yubormaydi — operator qaroriga qadar
    assert a.bir_aylanish() == "rad" and len(oplar) == 1
    # operator: qulfni kengaytirdi va qayta urinishni bosdi
    bank.qulflar["AQ-RES-1"] += 20_000
    z.jurnal.topshirish_xatosi(ys[1].partiya_id, None)
    assert a.bir_aylanish() == "bajarildi"
    assert z.jurnal.topshirilmaganlar() == []
