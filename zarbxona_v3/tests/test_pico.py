"""4.x — Pico imzo kaliti: protokol, qurilma qoidalari (soxta Pico) va zarbxona bilan
to'liq halqa. Ichki dastur (`firmware/pico_hsm`) shu qoidalarga bo'ysunadi."""

from __future__ import annotations

import secrets
import struct
import zlib

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.buyurtma import Zarbxona
from core.ibtido import imzo_togri, kalit_urugdan, ochiq_kalit
from core.partiya import imzo_xabari
from core.pico import protokol as P
from core.pico import saqlash as S
from core.pico.qurilma import PicoImzolovchi
from core.pico.soxta import SoxtaPico, SoxtaTashuvchi, avto_tugma
from core.pico.ulanish import PicoSozlama, sozlama_oqi, sozlama_yoz, ulan
from core.protokol import mint_auth_imzo, mint_auth_xesh
from core.surat import Surat
from core.tekshiruv import faylni_tekshir, jurnalni_tekshir
from core.zanjir import bosh_xabari

PIN = "123456"
URUG = bytes(range(1, 33))          # conftest'dagi zarbxona kaliti — sertifikat mos keladi
HOZIR = 1_800_000_000_000
TEZ = Surat(rejim="cheklovsiz")


class Tugma:
    """Boshqariladigan tugma: navbatdagi javoblar, bosilishlar ro'yxati."""

    def __init__(self, *javoblar: str):
        self.javoblar = list(javoblar)
        self.matnlar: list[str] = []

    def __call__(self, matn: str) -> str:
        self.matnlar.append(matn)
        return self.javoblar.pop(0) if self.javoblar else "ha"


class Soat:
    def __init__(self):
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def qurilma(tmp_path=None, **kw):
    q = SoxtaPico(tmp_path / "flash.json" if tmp_path else None, pin_iter=64, **kw)
    t = SoxtaTashuvchi(q)
    xabarlar: list[str] = []
    return q, t, PicoImzolovchi(t, kutish_xabari=xabarlar.append, oddiy_kutish=5), xabarlar


# --- ramka ----------------------------------------------------------------------------


def test_ramka_aylanib_keladi_va_axlatdan_sinxronlanadi():
    r = P.Ramka(P.IMZO_BOSH, 513, P.maydonlar(b"abc", b"", b"\x00" * 300))
    o = P.Oquvchi()
    chiqdi = []
    for b in [b"\xffAQ\x07", r.bayt()[:5], r.bayt()[5:], b"axlat", r.bayt()]:
        chiqdi += o.qosh(b)
    assert [(x.kod, x.seq, x.yuk) for x in chiqdi] == [(r.kod, r.seq, r.yuk)] * 2
    assert P.ajrat(chiqdi[0].yuk) == [b"abc", b"", b"\x00" * 300]


def test_crc_xato_ramka_tashlanadi():
    b = bytearray(P.Ramka(P.SALOM, 1).bayt())
    b[-1] ^= 1
    o = P.Oquvchi()
    assert o.qosh(bytes(b)) == [] and o.buzilgan == 1
    assert len(o.qosh(P.Ramka(P.SALOM, 2).bayt())) == 1


def test_maydon_kesilgan_rad():
    with pytest.raises(P.RamkaXatosi):
        P.ajrat(b"\x05\x00abc")
    with pytest.raises(P.RamkaXatosi):
        P.ajrat(b"\x01")


@settings(max_examples=300, deadline=None)
@given(st.binary(max_size=400))
def test_oquvchi_ixtiyoriy_baytda_yiqilmaydi(b):
    o = P.Oquvchi()
    for r in o.qosh(b):
        assert len(r.yuk) <= P.MAX_YUK


@settings(max_examples=150, deadline=None)
@given(st.integers(0, 0x3F), st.binary(max_size=200))
def test_qurilma_ixtiyoriy_buyruqqa_javob_beradi(kod, yuk):
    """Har qanday yuk — javob (OK yoki xato kodi), istisno emas, kalit o'zgarmaydi."""
    q = SoxtaPico(None, tugma=avto_tugma(javob="yoq"), pin_iter=8)
    j = q.bajar(P.Ramka(kod, 1, yuk), lambda m: None)
    assert j and j[0] in (P.OK, *P.XATO_MATNI)
    assert q.yozuv is None or j[0] == P.OK


def test_soxta_tashuvchi_buzilgan_ramkaga_xato_qaytaradi():
    q, t, pico, _ = qurilma()
    b = bytearray(P.Ramka(P.SALOM, 7).bayt())
    b[-2] ^= 0xFF
    t.yoz(bytes(b))
    o = P.Oquvchi()
    r = o.qosh(t.oqi(2))
    assert r and r[0].kod == P.XATO_RAMKA and r[0].yuk[0] == P.X_FORMAT
    assert pico.salom().versiya.startswith("soxta-pico")       # keyin ham ishlaydi


# --- saqlash (flash) ------------------------------------------------------------------


def test_saqlash_vektori_va_pin():
    """Ichki dastur shu vektorni takrorlashi kerak (firmware/pico_hsm/test)."""
    y = S.shifrla(URUG, b"123456", bytes(16), iter_=S.PIN_ITER)
    assert S.och(y, b"123456") == URUG
    assert S.och(y, b"123457") is None
    assert y.ct.hex() == S.shifrla(URUG, b"123456", bytes(16)).ct.hex()     # deterministik
    assert len(y.tag) == 16 and y.ct != URUG


# --- qurilma qoidalari ------------------------------------------------------------------


def test_kalit_yaratish_qulf_va_pin(tmp_path):
    tugma = Tugma()
    q, t, pico, xabar = qurilma(tmp_path, tugma=tugma)
    s = pico.salom()
    assert not s.kalit_bor and not s.ochiq and s.qolgan_urinish == P.MAX_URINISH
    pk = pico.kalit_yarat(PIN)
    assert len(pk) == 1952 and tugma.matnlar == ["YANGI KALIT yaratish"]
    assert xabar == ["YANGI KALIT yaratish", None]         # KUTMOQDA, keyin «tugadi»
    with pytest.raises(P.PicoXatosi) as e:
        pico.kalit_yarat(PIN)
    assert e.value.kod == P.X_KALIT_BOR
    pico.qulfla()
    with pytest.raises(P.PicoXatosi) as e:
        pico.bosh_imzosi(1, bytes(32))
    assert e.value.kod == P.X_QULFLANGAN
    with pytest.raises(P.PicoXatosi) as e:
        pico.pin_och("000000")
    assert e.value.kod == P.X_PIN and e.value.qoshimcha == [bytes([P.MAX_URINISH - 1])]
    assert pico.pin_och(PIN) == pk
    assert pico.salom().qolgan_urinish == P.MAX_URINISH         # to'g'ri PIN hisobni tiklaydi
    # flash'da urug' ochiq holda YO'Q
    assert URUG.hex() not in (tmp_path / "flash.json").read_text()


def test_kalit_qurilmadan_chiqmaydi_va_quvvat_uzilsa_qulflanadi(tmp_path):
    q, t, pico, _ = qurilma(tmp_path)
    pk = pico.kalit_yarat(PIN)
    t.sugur()
    q2 = SoxtaPico(tmp_path / "flash.json", pin_iter=64)          # qayta ulandi
    pico2 = PicoImzolovchi(SoxtaTashuvchi(q2), kutilgan_pk=pk, oddiy_kutish=5)
    s = pico2.salom()
    assert s.kalit_bor and not s.ochiq and s.pk == b""
    assert pico2.pin_och(PIN) == pk
    # hech bir buyruq javobida urug' yo'q
    for kod in (P.SALOM, P.HOLAT):
        assert URUG not in b"".join(pico2.sorov(kod))


def test_pin_kop_marta_xato_kalit_ochadi(tmp_path):
    q, t, pico, _ = qurilma(tmp_path)
    pico.kalit_yarat(PIN)
    pico.qulfla()
    for i in range(P.MAX_URINISH - 1):
        with pytest.raises(P.PicoXatosi) as e:
            pico.pin_och("999999")
        assert e.value.kod == P.X_PIN
    with pytest.raises(P.PicoXatosi) as e:
        pico.pin_och("999999")
    assert e.value.kod == P.X_OCHIRILDI
    assert not pico.salom().kalit_bor
    assert not SoxtaPico(tmp_path / "flash.json").yozuv        # flash'dan ham o'chgan


def test_urinish_hisobi_quvvat_uzilishiga_chidamli(tmp_path):
    """Hisob tekshiruvdan OLDIN yoziladi: xato PIN'dan keyin quvvatni uzish yordam bermaydi."""
    q, t, pico, _ = qurilma(tmp_path)
    pico.kalit_yarat(PIN)
    pico.qulfla()
    with pytest.raises(P.PicoXatosi):
        pico.pin_och("999999")
    q2 = SoxtaPico(tmp_path / "flash.json", pin_iter=64)
    assert q2.yozuv.urinish == 1


def test_import_ochiq_kalitni_saqlaydi():
    _, _, pico, _ = qurilma()
    pk = pico.kalit_import(PIN, URUG)
    assert pk == ochiq_kalit(kalit_urugdan(URUG)) and pico.salom().import_qilingan


@pytest.mark.parametrize("pin", ["12345", "x" * 65])
def test_pin_uzunligi(pin):
    _, _, pico, _ = qurilma()
    with pytest.raises(P.PicoXatosi) as e:
        pico.kalit_yarat(pin)
    assert e.value.kod == P.X_FORMAT


def test_ruxsat_byudjeti_va_muddati():
    soat = Soat()
    tugma = Tugma()
    q, t, pico, _ = qurilma(tugma=tugma, soat=soat)
    pk = pico.kalit_import(PIN, URUG)
    args = (bytes(32), bytes(16), 3, 600, "AQ-RES", HOZIR)
    with pytest.raises(P.PicoXatosi) as e:
        pico.partiya_imzosi(*args)
    assert e.value.kod == P.X_RUXSAT_YOQ
    pico.ruxsat_muddati_s = 60
    pico.ruxsat("B-1", 1000)
    assert tugma.matnlar[-1] == "RUXSAT: buyurtma B-1 · 1000 so'm"
    imzo = pico.partiya_imzosi(*args)
    assert imzo_togri(pk, imzo, imzo_xabari(*args))
    h = pico.holat()
    assert h.ruxsat_faol and h.byudjet == 400 and h.imzolar == 1
    with pytest.raises(P.PicoXatosi) as e:
        pico.partiya_imzosi(bytes(32), bytes(16), 1, 500, "AQ-RES", HOZIR)
    assert e.value.kod == P.X_BYUDJET and e.value.qoshimcha == [P.u128(400)]
    soat.t += 61
    with pytest.raises(P.PicoXatosi) as e:
        pico.partiya_imzosi(bytes(32), bytes(16), 1, 100, "AQ-RES", HOZIR)
    assert e.value.kod == P.X_RUXSAT_YOQ


@pytest.mark.parametrize("javob,kod", [("rad", P.X_RAD), ("yoq", P.X_TUGMA_YOQ)])
def test_tugma_rad_yoki_bosilmadi(javob, kod):
    _, _, pico, _ = qurilma(tugma=Tugma("ha", javob))
    pico.kalit_import(PIN, URUG)
    with pytest.raises(P.PicoXatosi) as e:
        pico.ruxsat("B-1", 10)
    assert e.value.kod == kod
    assert not pico.holat().ruxsat_faol


def test_jurnal_boshi_tartibi_va_ruxsatsiz_tugma():
    tugma = Tugma()
    _, _, pico, _ = qurilma(tugma=tugma)
    pk = pico.kalit_import(PIN, URUG)
    n = len(tugma.matnlar)
    imzo = pico.bosh_imzosi(5, b"\x01" * 32)                 # ruxsatsiz — tugma so'raladi
    assert imzo_togri(pk, imzo, bosh_xabari(5, b"\x01" * 32))
    assert tugma.matnlar[n:] == ["Jurnal boshi #5 (ruxsatsiz)"]
    pico.bosh_imzosi(5, b"\x02" * 32)                        # o'sha tartib — qayta urinish
    with pytest.raises(P.PicoXatosi) as e:
        pico.bosh_imzosi(4, b"\x03" * 32)
    assert e.value.kod == P.X_TARTIB
    pico.ruxsat("B", 1)
    n = len(tugma.matnlar)
    pico.bosh_imzosi(6, bytes(32))
    assert len(tugma.matnlar) == n                           # ruxsat ichida — tugmasiz


def test_mint_auth_imzosi(kalitlar):
    _, _, pico, _ = qurilma()
    pk = pico.kalit_import(PIN, URUG)
    bpk, nonce, cid = kalitlar[3], secrets.token_bytes(32), bytes(range(16))
    imzo = mint_auth_imzo(pico, bpk, nonce, cid)
    assert imzo_togri(pk, imzo, mint_auth_xesh(bpk, nonce, cid))


def test_kalit_ochirish_pin_va_tugma_bilan():
    _, _, pico, _ = qurilma(tugma=Tugma("ha", "rad"))
    pico.kalit_import(PIN, URUG)
    with pytest.raises(P.PicoXatosi) as e:
        pico.kalit_ochir(PIN)
    assert e.value.kod == P.X_RAD and pico.salom().kalit_bor
    pico.kalit_ochir(PIN)
    assert not pico.salom().kalit_bor


def test_buzuq_qurilma_imzosi_qabul_qilinmaydi():
    q, _, pico, _ = qurilma()
    pico.kalit_import(PIN, URUG)
    q.sk = kalit_urugdan(bytes(32))            # qurilma ichida kalit almashtirildi
    with pytest.raises(P.PicoXatosi) as e:
        pico.mint_auth_imzosi(bytes(1952), b"n", bytes(16))
    assert "YAROQSIZ" in str(e.value)


def test_boshqa_pico_rad_etiladi(tmp_path):
    _, _, pico, _ = qurilma()
    pico.kalit_import(PIN, URUG)
    boshqa = PicoImzolovchi(SoxtaTashuvchi(pico.t.q), kutilgan_pk=bytes(1952), oddiy_kutish=5)
    with pytest.raises(P.PicoXatosi, match="BOSHQA Pico"):
        boshqa.salom()


def test_javob_kelmasa_aloqa_xatosi():
    class Jim:
        nomi = "jim"

        def yoz(self, b): pass
        def oqi(self, k): return b""
        def tozala(self): pass
        def yop(self): pass
    p = PicoImzolovchi(Jim(), oddiy_kutish=0.3)
    with pytest.raises(P.PicoXatosi) as e:
        p.salom()
    assert e.value.kod == P.X_ALOQA


def test_kech_javob_seq_bilan_otkaziladi():
    """Oldingi so'rovning kech javobi joriy so'rovga aralashmaydi."""
    _, t, pico, _ = qurilma()
    eski = P.Ramka(P.SALOM | P.JAVOB_BIT, 1, P.xato_yuki(P.X_ICHKI)).bayt()

    class Aralash:
        nomi = "aralash"
        birinchi = True

        def yoz(self, b): t.yoz(b)

        def oqi(self, k):
            if self.birinchi:
                self.birinchi = False
                return eski
            return t.oqi(k)

        def tozala(self): pass
        def yop(self): pass
    pico.t = Aralash()
    pico._seq = 5
    assert pico.salom().versiya.startswith("soxta")


# --- zarbxona bilan to'liq halqa ---------------------------------------------------------


@pytest.fixture
def pico_zarbxona(tmp_path, sertifikat):
    tugma = Tugma()
    q, t, pico, xabar = qurilma(tmp_path, tugma=tugma)
    pico.kalit_import(PIN, URUG)
    z = Zarbxona(tmp_path / "profil", pico, soat_ms=lambda: HOZIR)
    sertifikat.yoz(tmp_path / "s.aqcert")
    z.sertifikat_import(tmp_path / "s.aqcert")
    yield z, q, t, pico, tugma
    z.yop()


def test_pico_bilan_toliq_zarb(pico_zarbxona):
    z, q, t, pico, tugma = pico_zarbxona
    n = len(tugma.matnlar)
    b = z.buyurtma_yarat(23_456, "AQ-RES-PICO", "", TEZ, partiya_hajmi=4)
    r = z.buyurtmani_bajar(b.buyurtma_id)
    assert r.holat == "tugadi", r.xabar
    assert len(r.partiyalar) > 1
    assert tugma.matnlar[n:] == [f"RUXSAT: buyurtma {b.buyurtma_id} · 23456 so'm"]  # BIR marta
    for y in z.jurnal.partiyalar():
        h, _ = faylni_tekshir(z.partiya_papka / y.fayl, z.pk, z.sertifikat)
        assert h.ok, h.matn()
    h = jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat)
    assert h.ok, h.matn()
    assert pico.holat().byudjet == 0          # ruxsat aynan buyurtma summasicha edi


def test_tugma_rad_etilsa_buyurtma_pauza_va_davom(pico_zarbxona):
    z, q, t, pico, tugma = pico_zarbxona
    b = z.buyurtma_yarat(5_000, "AQ-RES", "", TEZ, partiya_hajmi=1)
    tugma.javoblar = ["rad"]
    r = z.buyurtmani_bajar(b.buyurtma_id)
    assert r.holat == "pauza" and "RAD" in r.xabar and not r.partiyalar
    r = z.buyurtmani_bajar(b.buyurtma_id)
    assert r.holat == "tugadi"


def test_pico_sugurilsa_partiya_yozilmaydi_va_davom_etadi(tmp_path, pico_zarbxona):
    z, q, t, pico, tugma = pico_zarbxona
    b = z.buyurtma_yarat(5000 * 6, "AQ-RES", "", TEZ, partiya_hajmi=2)

    def hodisa(tur, d):
        if tur == "partiya_yopildi" and len(z.jurnal.partiyalar()) == 1:
            t.sugur()                       # birinchi partiyadan keyin USB uzildi
    r = z.buyurtmani_bajar(b.buyurtma_id, hodisa=hodisa)
    assert r.holat == "pauza" and "imzo olinmadi" in r.xabar
    assert len(z.jurnal.partiyalar()) == 1
    assert not list(z.partiya_papka.glob("*.yarim"))
    # qayta ulash: yangi tashuvchi, PIN
    q2 = SoxtaPico(tmp_path / "flash.json", pin_iter=64)
    pico2 = PicoImzolovchi(SoxtaTashuvchi(q2), kutilgan_pk=z.pk, oddiy_kutish=5)
    pico2.pin_och(PIN)
    z.yop()
    z2 = Zarbxona(z.papka, pico2, soat_ms=lambda: HOZIR)
    try:
        r = z2.buyurtmani_bajar(b.buyurtma_id)
        assert r.holat == "tugadi", r.xabar
        assert jurnalni_tekshir(z2.jurnal, z2.partiya_papka, z2.pk, z2.sertifikat).ok
    finally:
        z2.yop()


def test_ruxsat_tugasa_pauza(pico_zarbxona):
    z, q, t, pico, tugma = pico_zarbxona
    soat = Soat()
    q.soat = soat
    b = z.buyurtma_yarat(5000 * 4, "AQ-RES", "", TEZ, partiya_hajmi=1)

    def hodisa(tur, d):
        if tur == "partiya_yopildi":
            soat.t += pico.ruxsat_muddati_s + 1
    r = z.buyurtmani_bajar(b.buyurtma_id, hodisa=hodisa)
    assert r.holat == "pauza" and "ruxsat" in r.xabar.lower()
    assert len(r.partiyalar) == 1
    r = z.buyurtmani_bajar(b.buyurtma_id)
    assert r.holat == "tugadi"


# --- sozlama va ulanish ------------------------------------------------------------------


def test_sozlama_va_soxta_port_bilan_ulanish(tmp_path):
    papka = tmp_path / "p"
    papka.mkdir()
    assert sozlama_oqi(papka) is None
    s = PicoSozlama(port=f"soxta:{tmp_path / 'flash.json'}")
    pico = ulan(s)
    pk = pico.kalit_yarat(PIN)
    s.public_key, s.seriya = pk, pico.salom().seriya
    pico.yop()
    sozlama_yoz(papka, s)
    s2 = sozlama_oqi(papka)
    assert s2.public_key == pk and s2.seriya == s.seriya and s2.port == s.port
    pico = ulan(s2)
    assert pico.pin_och(PIN) == pk
    s2.seriya = bytes(8)
    with pytest.raises(P.PicoXatosi, match="BOSHQA"):
        ulan(s2)


def test_ramka_formati_hujjatga_mos():
    """docs/PICO_PROTOKOL.md dagi misol ramka: SALOM, seq=1."""
    b = P.Ramka(P.SALOM, 1).bayt()
    assert b[:8] == b"AQ\x01\x01\x01\x00\x00\x00"
    assert struct.unpack("<I", b[8:])[0] == zlib.crc32(b[:8])
    assert b.hex() == "4151010101000000" + struct.pack("<I", zlib.crc32(b[:8])).hex()


def test_hamma_partiya_yozilgan_buyurtma_ruxsat_soramaydi(pico_zarbxona):
    """Uzilish oxirgi partiyadan keyin, «tugadi» belgisidan oldin bo'lgan: qolgan summa 0 —
    Pico'dan 0 so'mlik ruxsat so'ralmaydi (aks holda buyurtma abadiy pauzada qolardi)."""
    z, q, t, pico, tugma = pico_zarbxona
    b = z.buyurtma_yarat(5_000, "AQ-RES", "", TEZ, partiya_hajmi=1)
    assert z.buyurtmani_bajar(b.buyurtma_id).holat == "tugadi"
    z.jurnal.buyurtma_holat(b.buyurtma_id, "faol")      # «tugadi» yozilmay qolgan holat
    n = len(tugma.matnlar)
    r = z.buyurtmani_bajar(b.buyurtma_id)
    assert r.holat == "tugadi" and len(tugma.matnlar) == n
