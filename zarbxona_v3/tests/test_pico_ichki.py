"""4.x — Pico ICHKI DASTURI (firmware/pico_hsm, C) ni etalon bilan solishtirish.

Ichki dastur yadrosi kompyuter uchun yig'iladi (`-DAQ_HOST=ON` → `pico_hsm_host`):
USB o'rnida stdin/stdout, flash o'rnida fayl. Shu testlar ikkala qurilmada — Python
etaloni (`SoxtaPico`) va C ichki dasturda — BIR XIL ishlaydi; qo'shimcha ravishda:
  * C dagi SHA3/SHAKE/PIN KDF Python bilan bayt-ma-bayt mos (flash yozuvini Python ochadi);
  * C dagi ML-DSA-65 kaliti va imzolari `cryptography` bilan mos;
  * tasodifiy buyruqlarga ikkalasi bir xil holat kodi qaytaradi (differensial fuzz);
  * stek va arena RP2040 ga sig'adi.

Binar yo'li: `AQ_PICO_HOST` muhit o'zgaruvchisi. Yo'q bo'lsa — testlar o'tkazib yuboriladi
(CI'da yig'iladi va yoqiladi).
"""

from __future__ import annotations

import os
import secrets
import subprocess
import threading
import time
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from core.buyurtma import Zarbxona
from core.ibtido import imzo_togri, kalit_urugdan, ochiq_kalit
from core.partiya import imzo_xabari
from core.pico import protokol as P
from core.pico import saqlash as S
from core.pico.qurilma import PicoImzolovchi
from core.pico.soxta import SoxtaPico, SoxtaTashuvchi
from core.protokol import mint_auth_xesh
from core.surat import Surat
from core.tekshiruv import faylni_tekshir, jurnalni_tekshir
from core.zanjir import bosh_xabari

BINAR = os.environ.get("AQ_PICO_HOST")
pytestmark = pytest.mark.skipif(not (BINAR and Path(BINAR).exists()),
                                reason="AQ_PICO_HOST (pico_hsm_host) yig'ilmagan")

PIN = "123456"
URUG = bytes(range(1, 33))
HOZIR = 1_800_000_000_000


class ProtsessTashuvchi:
    """`pico_hsm_host` — xuddi USB serial kabi bayt oqimi."""

    nomi = "ichki-dastur"

    def __init__(self, flash: Path, tugma: str = "", stek: bool = False):
        env = {**os.environ, "AQ_FLASH": str(flash), "AQ_TUGMA": tugma}
        if stek:
            env["AQ_STEK"] = "1"
        self.p = subprocess.Popen([BINAR], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, env=env)
        self._b = bytearray()
        self._shart = threading.Condition()
        self._ip = threading.Thread(target=self._oqi_ip, daemon=True)
        self._ip.start()

    def _oqi_ip(self) -> None:
        while True:
            d = self.p.stdout.read1(65536)
            with self._shart:
                if not d:
                    self._shart.notify_all()
                    return
                self._b += d
                self._shart.notify_all()

    def yoz(self, b: bytes) -> None:
        self.p.stdin.write(b)
        self.p.stdin.flush()

    def oqi(self, kutish: float) -> bytes:
        oxiri = time.monotonic() + kutish
        with self._shart:
            while not self._b:
                q = oxiri - time.monotonic()
                if q <= 0 or self.p.poll() is not None:
                    return b""
                self._shart.wait(q)
            b = bytes(self._b)
            self._b.clear()
            return b

    def tozala(self) -> None:
        with self._shart:
            self._b.clear()

    def yop(self) -> str:
        if self.p.stdin:
            self.p.stdin.close()
        self.p.wait(10)
        return self.p.stderr.read().decode()


class Tugma:
    def __init__(self, *javoblar):
        self.javoblar = list(javoblar)

    def __call__(self, _m):
        return self.javoblar.pop(0) if self.javoblar else "ha"


@pytest.fixture(params=["etalon", "ichki"])
def qurilma(request, tmp_path):
    """Qurilma yasovchi: `yasa(tugma="ha,rad")` → PicoImzolovchi; `qayta()` — quvvatni
    uzib qayta ulash (flash qoladi, RAM tozalanadi)."""
    tur = request.param
    ochiqlar = []

    class Q:
        nomi = tur
        flash = tmp_path / ("flash.json" if tur == "etalon" else "flash.bin")

        def yasa(self, tugma: str = "") -> PicoImzolovchi:
            if tur == "etalon":
                t = SoxtaTashuvchi(SoxtaPico(self.flash, tugma=Tugma(*filter(None,
                                                                         tugma.split(",")))))
            else:
                t = ProtsessTashuvchi(self.flash, tugma)
            ochiqlar.append(t)
            return PicoImzolovchi(t, oddiy_kutish=20)

    yield Q()
    for t in ochiqlar:
        t.yop()


def kod(f, *a):
    with pytest.raises(P.PicoXatosi) as e:
        f(*a)
    return e.value.kod


# --- ikkala qurilmada bir xil qoidalar -------------------------------------------------


def test_import_kalit_va_imzolar_cryptography_bilan_mos(qurilma, kalitlar):
    p = qurilma.yasa()
    pk = p.kalit_import(PIN, URUG)
    assert pk == ochiq_kalit(kalit_urugdan(URUG))        # FIPS 204 keygen mos
    s = p.salom()
    assert s.kalit_bor and s.ochiq and s.import_qilingan and len(s.seriya) == 8
    p.ruxsat_muddati_s = 600
    p.ruxsat("B-1", 10_000)
    a = (os.urandom(32), os.urandom(16), 7, 9_999, "AQ-RES-ÜZ", HOZIR)
    assert imzo_togri(pk, p.partiya_imzosi(*a), imzo_xabari(*a))
    x = os.urandom(32)
    assert imzo_togri(pk, p.bosh_imzosi(3, x), bosh_xabari(3, x))
    bpk, n, c = kalitlar[3], os.urandom(48), os.urandom(16)
    assert imzo_togri(pk, p.mint_auth_imzosi(bpk, n, c), mint_auth_xesh(bpk, n, c))
    h = p.holat()
    assert h.ruxsat_faol and h.byudjet == 1 and h.imzolar == 3 and 590 <= h.qolgan_s <= 600


def test_yaratish_pin_qulf_va_ochirish(qurilma):
    p = qurilma.yasa()
    assert not p.salom().kalit_bor
    assert kod(p.pin_och, PIN) == P.X_KALIT_YOQ
    assert kod(p.kalit_yarat, "12345") == P.X_FORMAT
    pk = p.kalit_yarat(PIN)
    assert kod(p.kalit_yarat, PIN) == P.X_KALIT_BOR
    assert kod(p.kalit_import, PIN, URUG) == P.X_KALIT_BOR
    p.qulfla()
    assert not p.salom().ochiq and p.salom().pk == b""
    assert kod(p.ruxsat, "B", 5) == P.X_QULFLANGAN
    with pytest.raises(P.PicoXatosi) as e:
        p.pin_och("000000")
    assert e.value.kod == P.X_PIN and e.value.qoshimcha == [bytes([4])]
    assert p.pin_och(PIN) == pk
    assert p.salom().qolgan_urinish == P.MAX_URINISH
    p.kalit_ochir(PIN)
    assert not p.salom().kalit_bor


def test_pin_hisobi_quvvat_uzilishiga_chidamli_va_ochirish(qurilma):
    p = qurilma.yasa()
    p.kalit_import(PIN, URUG)
    for i in range(3):
        assert kod(p.pin_och, "999999") == P.X_PIN
    p.yop()
    p = qurilma.yasa()                                   # quvvat uzildi — flash qoldi
    s = p.salom()
    assert s.kalit_bor and not s.ochiq and s.qolgan_urinish == 2
    assert kod(p.pin_och, "999999") == P.X_PIN
    assert kod(p.pin_och, "999999") == P.X_OCHIRILDI
    assert not p.salom().kalit_bor
    p.yop()
    assert not qurilma.yasa().salom().kalit_bor          # flash'dan ham o'chgan


def test_ruxsat_byudjet_muddat_va_tugma(qurilma):
    p = qurilma.yasa("ha,rad,yoq")
    p.kalit_import(PIN, URUG)
    a = (bytes(32), bytes(16), 1, 600, "Q", HOZIR)
    assert kod(p.partiya_imzosi, *a) == P.X_RUXSAT_YOQ
    assert kod(p.ruxsat, "B", 1000) == P.X_RAD
    assert kod(p.ruxsat, "B", 1000) == P.X_TUGMA_YOQ
    p.ruxsat_muddati_s = 1
    p.ruxsat("B", 1000)
    p.partiya_imzosi(*a)
    with pytest.raises(P.PicoXatosi) as e:
        p.partiya_imzosi(bytes(32), bytes(16), 1, 401, "Q", HOZIR)
    assert e.value.kod == P.X_BYUDJET and e.value.qoshimcha == [P.u128(400)]
    time.sleep(1.1)
    assert kod(p.partiya_imzosi, bytes(32), bytes(16), 1, 1, "Q", HOZIR) == P.X_RUXSAT_YOQ


def test_jurnal_boshi_tartibi_va_ruxsatsiz_tugma(qurilma):
    xabarlar = []
    p = qurilma.yasa("ha,ha,rad")
    p.kutish_xabari = xabarlar.append
    p.kalit_import(PIN, URUG)
    p.bosh_imzosi(5, bytes(32))
    assert "Jurnal boshi #5 (ruxsatsiz)" in xabarlar
    assert kod(p.bosh_imzosi, 4, bytes(32)) == P.X_TARTIB
    assert kod(p.bosh_imzosi, 6, bytes(32)) == P.X_RAD


def test_katta_summa_128_bit(qurilma):
    """u128 summalar: 2^64 dan katta byudjet va ayirish (Cortex-M0+ da __int128 yo'q)."""
    xabarlar = []
    p = qurilma.yasa()
    p.kutish_xabari = xabarlar.append
    p.kalit_import(PIN, URUG)
    katta = 2**64 + 5
    p.ruxsat("B", katta)
    assert f"RUXSAT: buyurtma B · {katta} so'm" in xabarlar
    p.partiya_imzosi(bytes(32), bytes(16), 1, 2**63, "Q", HOZIR)
    assert p.holat().byudjet == katta - 2**63
    with pytest.raises(P.PicoXatosi) as e:
        p.partiya_imzosi(bytes(32), bytes(16), 1, 2**64, "Q", HOZIR)
    assert e.value.kod == P.X_BYUDJET


@pytest.mark.parametrize("qulf", [" Q", "Q ", "\tQ"])
def test_qulf_chetidagi_bosh_joy_rad(qurilma, qulf):
    p = qurilma.yasa()
    p.kalit_import(PIN, URUG)
    p.ruxsat("B", 10)
    j = P.maydonlar(bytes(32), bytes(16), P.u64(1), P.u128(1), qulf.encode(), P.u64(1))
    with pytest.raises(P.PicoXatosi) as e:
        p.sorov(P.IMZO_PARTIYA, *P.ajrat(j))
    assert e.value.kod == P.X_FORMAT
    assert p.holat().byudjet == 10                          # byudjet yeyilmadi


def test_buzilgan_ramka_va_axlat(qurilma):
    p = qurilma.yasa()
    t = p.t
    t.yoz(b"\x00\x01axlat")
    b = bytearray(P.Ramka(P.SALOM, 9).bayt())
    b[-1] ^= 0x55
    t.yoz(bytes(b))
    o = P.Oquvchi()
    r = []
    oxiri = time.monotonic() + 5
    while not r and time.monotonic() < oxiri:
        r = o.qosh(t.oqi(0.2))
    assert r and r[0].kod == P.XATO_RAMKA and r[0].yuk[0] == P.X_FORMAT
    assert p.salom().qolgan_urinish == P.MAX_URINISH       # keyin ham ishlaydi


def test_zarbxona_bilan_toliq_halqa(qurilma, tmp_path, sertifikat):
    p = qurilma.yasa()
    p.kalit_import(PIN, URUG)
    z = Zarbxona(tmp_path / "profil", p, soat_ms=lambda: HOZIR)
    try:
        sertifikat.yoz(tmp_path / "s.aqcert")
        z.sertifikat_import(tmp_path / "s.aqcert")
        b = z.buyurtma_yarat(12_345, "AQ-RES-ICHKI", "", Surat(rejim="cheklovsiz"),
                             partiya_hajmi=4)
        r = z.buyurtmani_bajar(b.buyurtma_id)
        assert r.holat == "tugadi", r.xabar
        for y in z.jurnal.partiyalar():
            assert faylni_tekshir(z.partiya_papka / y.fayl, z.pk, z.sertifikat)[0].ok
        assert jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat).ok
    finally:
        z.yop()


# --- faqat ichki dastur ---------------------------------------------------------------


@pytest.mark.skipif(not (BINAR and Path(BINAR).exists()), reason="binar yo'q")
def test_flash_yozuvini_python_ochadi(tmp_path):
    """C dagi SHA3-256, SHAKE256 va PIN KDF Python (hashlib) bilan bayt-ma-bayt mos."""
    t = ProtsessTashuvchi(tmp_path / "f.bin")
    p = PicoImzolovchi(t, oddiy_kutish=20)
    p.kalit_import("pin-uchun-sinov", URUG)
    t.yop()
    b = (tmp_path / "f.bin").read_bytes()
    assert len(b) == 256 and b[:4] == b"AQK1" and b[5] == 3 and b[6] == 0
    y = S.KalitYozuvi(b[8:24], b[24:56], b[56:72])
    assert S.och(y, b"pin-uchun-sinov") == URUG
    assert S.och(y, b"pin-uchun-sinoV") is None
    import zlib
    assert int.from_bytes(b[72:76], "little") == zlib.crc32(b[:72])
    assert b[76:] == b"\xff" * 180


@pytest.mark.skipif(not (BINAR and Path(BINAR).exists()), reason="binar yo'q")
def test_kalit_yaratish_tasodifiy_va_flashda_ochiq_emas(tmp_path):
    pk = []
    for i in range(2):
        t = ProtsessTashuvchi(tmp_path / f"f{i}.bin")
        p = PicoImzolovchi(t, oddiy_kutish=20)
        pk.append(p.kalit_yarat(PIN))
        t.yop()
    assert pk[0] != pk[1]


@pytest.mark.skipif(not (BINAR and Path(BINAR).exists()), reason="binar yo'q")
def test_stek_va_arena_rp2040_ga_sigadi(tmp_path, kalitlar):
    """Ichki dastur siklni alohida 32 KB stekda ishlatadi (main_pico.c), ML-DSA buferlari
    arenada (aq_arena.c). x86-64 da o'lchanadi — 64 bitli kodda stek ARM'dagidan ko'proq."""
    t = ProtsessTashuvchi(tmp_path / "f.bin", stek=True)
    p = PicoImzolovchi(t, oddiy_kutish=20)
    p.kalit_yarat(PIN)
    p.qulfla()
    p.pin_och(PIN)
    p.ruxsat("B", 10)
    p.partiya_imzosi(bytes(32), bytes(16), 1, 5, "Q", HOZIR)
    p.mint_auth_imzosi(kalitlar[3], b"n" * 32, bytes(16))
    hisobot = t.yop()
    stek = int(hisobot.split("stek ")[1].split()[0])
    arena = int(hisobot.split("arena ")[1].split()[0])
    print(f"\nichki dastur: stek {stek} B, arena {arena} B")
    assert stek < 24 * 1024, hisobot          # 32 KB stekda zaxira bilan
    assert arena < 24 * 1024, hisobot


# --- differensial fuzz -------------------------------------------------------------------


@pytest.fixture(scope="module")
def juftlik(tmp_path_factory):
    if not (BINAR and Path(BINAR).exists()):
        pytest.skip("binar yo'q")
    d = tmp_path_factory.mktemp("juft")
    t = ProtsessTashuvchi(d / "f.bin")
    q = SoxtaPico(d / "f.json", pin_iter=S.PIN_ITER)
    yield t, q
    t.yop()


def _c_javob(t, ramka: P.Ramka) -> P.Ramka:
    t.tozala()
    t.yoz(ramka.bayt())
    o = P.Oquvchi()
    oxiri = time.monotonic() + 20
    while time.monotonic() < oxiri:
        for r in o.qosh(t.oqi(0.2)):
            if r.seq == ramka.seq and r.kod != P.KUTMOQDA:
                return r
    raise AssertionError("ichki dastur javob bermadi")


KODLAR = st.sampled_from([0, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
                          0x10, 0x11, 0x12, 0x13, 0x3F])


def _maydonli_yuk():
    m = st.lists(st.one_of(st.binary(max_size=40), st.sampled_from(
        [b"", b"123456", b"\x01" * 32, b"\x00" * 16, b"\x05" + b"\x00" * 7,
         b"\x01" + b"\x00" * 15, b"\x0a\x00\x00\x00", b"Q"])), max_size=7)
    return m.map(lambda xs: P.maydonlar(*xs))


@settings(max_examples=250, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(KODLAR, st.one_of(st.binary(max_size=60), _maydonli_yuk()))
def test_differensial_holat_kodlari(juftlik, k, yuk):
    """Tasodifiy buyruq ketma-ketligi: C va etalon har qadamda bir xil holat kodi beradi
    (holatlari ham bir xil o'zgaradi: kalit yaratish, PIN, ruxsat...)."""
    t, q = juftlik
    seq = secrets.randbelow(0xFFFF) + 1
    c = _c_javob(t, P.Ramka(k, seq, yuk))
    py = q.bajar(P.Ramka(k, seq, yuk), lambda m: None)
    assert c.kod == k | P.JAVOB_BIT
    assert c.yuk[:1] == py[:1], (hex(k), yuk.hex(), c.yuk[:80], py[:80])
    if py[0] != P.OK:                                       # xato matni va qo'shimchasi
        assert c.yuk == py, (hex(k), c.yuk, py)
