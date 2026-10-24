"""T15 — GUI tutun testi (QT_QPA_PLATFORM=offscreen): oyna ochiladi, har sahifaga
o'tiladi, har tugma bosiladi va javob beradi (holat satri yoki dialog).

⚠ offscreen'da shrift bazasi bo'sh bo'lishi mumkin — ko'rinish sifati faqat haqiqiy
ekranda baholanadi (§18.2 A6)."""

from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import SIGNAL, QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from app import dialog  # noqa: E402
from core.buyurtma import Zarbxona  # noqa: E402
from core.ombor import ombor_och, ombor_yarat  # noqa: E402

HOZIR = 1_800_000_000_000


@pytest.fixture(scope="module")
def ilova():
    """Ilovadagidek: avtomatik GC o'chiq, yig'ish faqat asosiy oqimda (app/gc_nazorat.py)."""
    import gc

    from app import gc_nazorat
    from app.theme import mavzuni_qol
    a = QApplication.instance() or QApplication([])
    mavzuni_qol(a)
    t = gc_nazorat.ornat(a)
    yield a
    t.stop()
    QCoreApplication.processEvents()
    gc.collect()
    gc.disable()          # conftest siyosati: sessiya oxirigacha o'chiq


class Dialoglar:
    def __init__(self, tmp, sert_yoli):
        self.chaqiriqlar: list[tuple] = []
        self.tmp, self.sert_yoli = tmp, sert_yoli
        self.fayl_och_javob = str(sert_yoli)

    def ornat(self, mp):
        for nom in ("xabar", "xato"):
            mp.setattr(dialog, nom, self._yoz(nom))
        mp.setattr(dialog, "tasdiq", self._qaytar("tasdiq", True))
        mp.setattr(dialog, "fayl_och", lambda *a: self._q("fayl_och", self.fayl_och_javob))
        mp.setattr(dialog, "fayl_saqla",
                   lambda o, s, nom, f: self._q("fayl_saqla", str(self.tmp / nom)))
        mp.setattr(dialog, "papka_tanla", lambda *a: self._q("papka_tanla", str(self.tmp)))
        mp.setattr(dialog, "parol", self._qaytar("parol", None))
        self.parol_javob = None
        mp.setattr(dialog, "parol_almashtirish",
                   lambda *a: self._q("parol_almashtirish", self.parol_javob))

    def _q(self, nom, javob):
        self.chaqiriqlar.append((nom,))
        return javob

    def _yoz(self, nom):
        def f(ota, sarlavha, matn):
            self.chaqiriqlar.append((nom, sarlavha, matn))
        return f

    def _qaytar(self, nom, javob):
        def f(*a):
            self.chaqiriqlar.append((nom,) + a[1:])
            return javob
        return f


def kut(shart, muddat=30.0):
    t = time.monotonic() + muddat
    while time.monotonic() < t:
        QCoreApplication.processEvents()
        if shart():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def oyna(ilova, tmp_path, kalitlar, sertifikat, monkeypatch):
    from app.oyna import Oyna
    sertifikat.yoz(tmp_path / "s.aqcert")
    d = Dialoglar(tmp_path, tmp_path / "s.aqcert")
    d.ornat(monkeypatch)
    z = Zarbxona(tmp_path / "profil", kalitlar[0], soat_ms=lambda: HOZIR)
    o = Oyna(z)
    o.show()
    o.dialoglar = d
    yield o
    o.close()
    assert not o.isVisible()


def bos_va_javob(o, tugma: QPushButton) -> bool:
    """Bosadi; javob — holat satri o'zgardi yoki dialog chaqirildi."""
    o.statusBar().showMessage("")
    n = len(o.dialoglar.chaqiriqlar)
    tugma.click()
    QCoreApplication.processEvents()
    return bool(o.statusBar().currentMessage()) or len(o.dialoglar.chaqiriqlar) > n


def test_t15_toliq_aylanish(oyna):
    o = oyna
    # 1. hamma sahifaga o'tiladi
    for i in range(o.menyu.count()):
        o.menyu.setCurrentRow(i)
        QCoreApplication.processEvents()
        assert o.stek.currentIndex() == i

    # 2. sertifikat import (kalit sahifasi)
    k = o.sahifalar["kalit"]
    assert bos_va_javob(o, k.t_import)
    assert o.z.sertifikat is not None
    assert bos_va_javob(o, k.t_eksport)
    assert (o.dialoglar.tmp / "zarbxona_ochiq_kalit.json").exists()

    # 3. zarb: xato kirish ham javob beradi
    zs = o.sahifalar["zarb"]
    o.sahifaga_ot("zarb")
    zs.summa.setText("")
    assert bos_va_javob(o, zs.t_zarb)
    assert o.dialoglar.chaqiriqlar[-1][0] == "xato"

    # 4. haqiqiy zarb — sekin rejimda, PAUZA/DAVOM/TO'XTATISH bilan
    zs.summa.setText("5 000 017")       # 1000 + 1 + 1 + 1 + ... kupyura
    zs.qulf.setEditText("AQ-RES-GUI")
    zs.toifalar.setText("seed, fuel")
    zs.hajm.setValue(3)
    s = zs.surat
    s.rejim.setCurrentIndex(s.rejim.findData("tezlik"))
    s.tezlik.setValue(200)
    s.N.setValue(0)
    assert "kupyura" in zs.bolinish.text()
    assert "taxminiy vaqt" in s.taxmin.text() and "TAXMINIY" in s.taxmin.text()
    assert bos_va_javob(o, zs.t_zarb)
    assert zs.ishlayapti()
    assert kut(lambda: zs.konveyer.monitor.blockCount() > 3)
    assert not zs.t_zarb.isEnabled() and zs.t_pauza.isEnabled()
    assert bos_va_javob(o, zs.t_pauza)
    assert zs.t_davom.isEnabled() and not zs.t_pauza.isEnabled()
    assert bos_va_javob(o, zs.t_davom)
    assert kut(lambda: len(o.z.jurnal.partiyalar()) >= 2)
    assert bos_va_javob(o, zs.t_toxtat)
    assert kut(lambda: not zs.ishlayapti())
    assert kut(lambda: zs.t_zarb.isEnabled())
    matn = zs.konveyer.monitor.toPlainText()
    assert "partiya yopildi" in matn and "Merkle ildizi" in matn and "TO'XTATILDI" in matn
    assert "muhr 72 B" in matn
    assert "haqiqiy tezlik" in zs.konveyer.holat.text()
    assert zs.grafik.tezlik.namunalar and zs.grafik.cpu.namunalar      # 3.2 jonli grafiklar

    # 5. buyurtmalar: davom ettirish (cheklovsiz — tez tugaydi), bekor qilish
    s.rejim.setCurrentIndex(s.rejim.findData("cheklovsiz"))
    bs = o.sahifalar["buyurtmalar"]
    o.sahifaga_ot("buyurtmalar")
    bs.jadval.selectRow(0)
    assert bs.t_davom.isEnabled()
    assert bos_va_javob(o, bs.t_davom)
    assert kut(lambda: not zs.ishlayapti(), 120)
    b = o.z.jurnal.buyurtmalar()[0]
    assert b.holat == "tugadi" and b.bajarilgan_summa == 5_000_017
    assert bos_va_javob(o, bs.t_yangila)
    # yangi buyurtma yaratib bekor qilamiz
    o.z.buyurtma_yarat(100, "AQ-RES-GUI")
    bs.yangila()
    bs.jadval.selectRow(0)
    assert bos_va_javob(o, bs.t_bekor)
    assert o.z.jurnal.buyurtmalar()[0].holat == "bekor"

    # 6. partiyalar sahifasi — har tugma
    ps = o.sahifalar["partiyalar"]
    o.sahifaga_ot("partiyalar")
    ps.jadval.selectRow(0)
    for t in (ps.t_eksport, ps.t_isbot, ps.t_qayta, ps.t_belgila):
        assert bos_va_javob(o, t), t.text()
    assert list(o.dialoglar.tmp.glob("*.aqbatch"))
    assert list(o.dialoglar.tmp.glob("isbot-*.json"))
    assert o.z.jurnal.partiyalar()[-1].topshirilgan_ms == HOZIR
    # aetherq_core yo'q — aniq xabar (bulutda shunday)
    assert bos_va_javob(o, ps.t_topshir)
    ps.avto.setChecked(True)
    QCoreApplication.processEvents()
    assert not ps.avto.isChecked() or ps.ishchi is not None
    # tanlovsiz bosish ham javob beradi
    ps.jadval.clearSelection()
    ps.jadval.setCurrentCell(-1, -1)
    assert bos_va_javob(o, ps.t_eksport)

    # 7. tekshiruv sahifasi + buzish demosi
    ts = o.sahifalar["tekshiruv"]
    o.sahifaga_ot("tekshiruv")
    assert bos_va_javob(o, ts.t_jurnal)
    assert kut(lambda: ts.t_jurnal.isEnabled())
    assert "TOZA" in ts.natija_sarlavha.text()
    ts.tur.setCurrentIndex(ts.tur.findData("imzo"))
    assert bos_va_javob(o, ts.t_buz)
    assert "muammo" in ts.natija_sarlavha.text() and "[imzo]" in ts.natija.toPlainText()
    assert bos_va_javob(o, ts.t_tikla)
    assert "TOZA" in ts.natija_sarlavha.text()
    o.dialoglar.fayl_och_javob = str(o.z.partiya_papka / o.z.jurnal.partiyalar()[0].fayl)
    assert bos_va_javob(o, ts.t_fayl)
    assert "TOZA" in ts.natija_sarlavha.text()

    # 8. boshqaruv paneli
    bp = o.sahifalar["boshqaruv"]
    o.sahifaga_ot("boshqaruv")
    for t in (bp.t_yangila, bp.t_zarb):
        assert bos_va_javob(o, t)
    assert o.stek.currentWidget() is zs

    # 9. hech bir sahifada «jim» qolgan yoqilgan tugma yo'qligini umumiy tekshirish
    for kalit, sahifa in o.sahifalar.items():
        for t in sahifa.findChildren(QPushButton):
            assert t.receivers(SIGNAL("clicked(bool)")) > 0, (kalit, t.text())


def test_t15_kirish_dialogi(ilova, tmp_path, monkeypatch):
    from app.kirish import KirishDialogi
    d = KirishDialogi(tmp_path / "p", ombor_n=4096)
    assert d.yangi
    d.parol1.setText("uzun-parol-1")
    d.parol2.setText("boshqa-parol")
    d.tugma.click()
    assert "mos emas" in d.xabar.text() and d.zarbxona is None
    d.parol2.setText("uzun-parol-1")
    d.tugma.click()
    assert d.zarbxona is not None
    d.zarbxona.yop()
    d2 = KirishDialogi(tmp_path / "p")
    assert not d2.yangi and "-" in d2.izoh.text()
    d2.parol1.setText("noto'g'ri-parol")
    d2.tugma.click()
    assert "parol noto'g'ri" in d2.xabar.text()
    d2.parol1.setText("uzun-parol-1")
    d2.tugma.click()
    assert d2.zarbxona is not None
    # ikkinchi nusxa — profil band
    d3 = KirishDialogi(tmp_path / "p")
    d3.parol1.setText("uzun-parol-1")
    d3.tugma.click()
    assert "band" in d3.xabar.text()
    d2.zarbxona.yop()


def test_ombor_yozish_va_ochish(tmp_path):
    sk = ombor_yarat(tmp_path / "k.json", "parol-12345", n=4096)
    assert ombor_och(tmp_path / "k.json", "parol-12345").public_key().public_bytes_raw() == \
        sk.public_key().public_bytes_raw()
    assert not (tmp_path / "k.json.tmp").exists()


def test_14_kalit_sahifasi_parol_va_zaxira(ilova, tmp_path, kalitlar, sertifikat, monkeypatch):
    """1.4: parolni o'zgartirish, zaxira nusxa, ogohlantirish — GUI orqali."""
    from app.kirish import KirishDialogi
    from app.oyna import Oyna
    from core.ibtido import ochiq_kalit
    d = Dialoglar(tmp_path, tmp_path / "s.aqcert")
    d.ornat(monkeypatch)
    papka = tmp_path / "p"
    ombor_yarat(papka / "kalit.json", "eski-parol-1", n=4096)
    k = KirishDialogi(papka)
    k.parol1.setText("eski-parol-1")
    k.tugma.click()
    z = k.zarbxona
    o = Oyna(z)
    o.dialoglar = d
    ks = o.sahifalar["kalit"]
    o.sahifaga_ot("kalit")
    # bekor qilindi
    assert bos_va_javob(o, ks.t_parol)
    # takror mos emas
    d.parol_javob = ("eski-parol-1", "yangi-parol-2", "boshqa")
    assert bos_va_javob(o, ks.t_parol) and d.chaqiriqlar[-1][0] == "xato"
    # eski noto'g'ri
    d.parol_javob = ("xato-parol-0", "yangi-parol-2", "yangi-parol-2")
    assert bos_va_javob(o, ks.t_parol) and d.chaqiriqlar[-1][0] == "xato"
    # muvaffaqiyat
    d.parol_javob = ("eski-parol-1", "yangi-parol-2", "yangi-parol-2")
    assert bos_va_javob(o, ks.t_parol) and d.chaqiriqlar[-1][0] == "xabar"
    assert ochiq_kalit(ombor_och(papka / "kalit.json", "yangi-parol-2")) == z.pk
    # zaxira
    assert bos_va_javob(o, ks.t_zaxira)
    zaxira = tmp_path / "zarbxona_kalit_zaxira.json"
    assert zaxira.exists()
    o.close()

    # zaxiradan boshqa profilga tiklash (login oynasi)
    d.fayl_och_javob = str(zaxira)
    k2 = KirishDialogi(tmp_path / "p2")
    assert k2.yangi and k2.t_tikla.isVisibleTo(k2)
    k2.t_tikla.click()
    assert "parol" in k2.xabar.text() and k2.zarbxona is None
    k2.parol1.setText("notogri-parol")
    k2.t_tikla.click()
    assert "parol noto'g'ri" in k2.xabar.text()
    assert not (tmp_path / "p2" / "kalit.json").exists()
    k2.parol1.setText("yangi-parol-2")
    k2.t_tikla.click()
    assert k2.zarbxona is not None
    assert k2.zarbxona.pk == z.pk
    k2.zarbxona.yop()


def test_14_ishga_tushishda_ogohlantirish(ilova, tmp_path, kalitlar, monkeypatch):
    from app.oyna import Oyna
    from core.sertifikat import KUN_MS, sertifikat_yarat
    zsk, zpk, bsk, bpk = kalitlar
    d = Dialoglar(tmp_path, tmp_path / "s.aqcert")
    d.ornat(monkeypatch)
    s = sertifikat_yarat(bsk, bpk, zpk, bytes(16), "T", 1000, HOZIR - KUN_MS, HOZIR + 3 * KUN_MS)
    s.yoz(tmp_path / "s.aqcert")
    z = Zarbxona(tmp_path / "p", zsk, soat_ms=lambda: HOZIR)
    z.sertifikat_import(tmp_path / "s.aqcert")
    o = Oyna(z)
    o.dialoglar = d
    o.ogohlantirishlarni_korsat()
    assert d.chaqiriqlar[-1][0] == "xabar" and "3 kundan keyin" in d.chaqiriqlar[-1][2]
    o.sahifaga_ot("boshqaruv")
    assert "⚠" in o.sahifalar["boshqaruv"].qiymatlar["sert"].text()
    o.sahifaga_ot("zarb")
    assert "3 kundan keyin" in o.sahifalar["zarb"].vakolat_matn.text()
    o.close()


def test_31_demo_rejimi_gui(ilova, tmp_path, kalitlar, monkeypatch):
    """3.1: demo oynasi — Demo bank sahifasi, zarb, onlayn topshirish demo bankka."""
    from app.oyna import Oyna
    from core.demo_bank import demo_tayyorla
    d = Dialoglar(tmp_path, tmp_path / "s.aqcert")
    d.ornat(monkeypatch)
    z = Zarbxona(tmp_path / "data_demo", kalitlar[0])
    db = demo_tayyorla(z)
    o = Oyna(z, demo_bank=db)
    o.dialoglar = d
    o.show()
    assert o.windowTitle().startswith("[DEMO]")
    ds = o.sahifalar["demo"]
    o.sahifaga_ot("demo")
    assert "iz" in ds.bank.text()
    assert ds.qulflar.rowCount() == 1
    for t in (ds.t_yangila, ds.t_qulf):
        assert bos_va_javob(o, t)
    assert ds.qulflar.rowCount() == 2
    ds.qulf_summa.setText("abc")
    assert bos_va_javob(o, ds.t_qulf) and d.chaqiriqlar[-1][0] == "xato"

    # zarb: qulf ro'yxatida demo qulf avtomatik tanlangan
    zs = o.sahifalar["zarb"]
    o.sahifaga_ot("zarb")
    assert zs.qulf.currentText().startswith("AQ-DEMO-")
    zs.summa.setText("12345")
    zs.hajm.setValue(4)
    zs.surat.rejim.setCurrentIndex(zs.surat.rejim.findData("cheklovsiz"))
    assert bos_va_javob(o, zs.t_zarb)
    assert kut(lambda: not zs.ishlayapti() and zs.t_zarb.isEnabled())
    n = len(z.jurnal.partiyalar())
    assert n >= 2

    # onlayn topshirish — aetherq_core'siz, demo bankka
    ps = o.sahifalar["partiyalar"]
    o.sahifaga_ot("partiyalar")
    assert not ps.broker.isEnabled() and "DEMO" in ps.aq.text()
    assert bos_va_javob(o, ps.t_topshir)
    assert kut(lambda: ps.ishchi is not None and not ps.ishchi.isRunning(), 60)
    QCoreApplication.processEvents()
    assert z.jurnal.topshirilmaganlar() == [], ps.log.toPlainText()
    assert "topshirildi" in ps.log.toPlainText()
    o.sahifaga_ot("demo")
    assert ds.qabul.rowCount() == n

    # sertifikatni qayta berish
    eski = z.sertifikat.cert_id
    assert bos_va_javob(o, ds.t_sert)
    assert z.sertifikat.cert_id != eski and z.sertifikat.bank_public_key == db.pk
    o.close()


@pytest.mark.parametrize("bayroq,kutilgan_kod,demo_bolsin", [
    (["--demo"], 0, True),      # yangi profil — demo tayyorlanadi
    ([], 0, False),             # oddiy rejim — demo bank yo'q
])
def test_31_main_demo_ulanishi(ilova, tmp_path, kalitlar, monkeypatch, bayroq, kutilgan_kod,
                               demo_bolsin):
    import app.kirish
    import app.main
    import app.oyna
    from PySide6.QtWidgets import QDialog
    ochilgan = {}

    class SoxtaKirish:
        def __init__(self, papka):
            self.zarbxona = Zarbxona(papka, kalitlar[0])
            self.tiklash = None

        def exec(self):
            return QDialog.DialogCode.Accepted

    asl_oyna = app.oyna.Oyna

    def oyna(z, demo_bank=None):
        o = asl_oyna(z, demo_bank=demo_bank)
        ochilgan["o"] = o
        return o
    monkeypatch.setattr(app.kirish, "KirishDialogi", SoxtaKirish)
    monkeypatch.setattr(app.oyna, "Oyna", oyna)
    monkeypatch.setattr(QApplication, "exec", lambda self: 0)
    Dialoglar(tmp_path, tmp_path).ornat(monkeypatch)
    kod = app.main.main([*bayroq, "--papka", str(tmp_path / "p")])
    assert kod == kutilgan_kod
    o = ochilgan["o"]
    assert (o.demo_bank is not None) == demo_bolsin
    assert ("demo" in o.sahifalar) == demo_bolsin
    o.close()


def test_oyna_ishlayotgan_oqim_bilan_yopilmaydi(ilova, tmp_path, kalitlar, monkeypatch):
    """Codex review P1: fon oqimi to'xtamasa oyna yopilmaydi (QThread destroyed while
    running bo'lmasin), baza ochiq qoladi; oqim tugagach oyna yopiladi."""
    from PySide6.QtCore import QThread

    from app.oyna import Oyna
    d = Dialoglar(tmp_path, tmp_path)
    d.ornat(monkeypatch)

    class Qaysar(QThread):
        def run(self):
            time.sleep(1.0)          # to'xtatishni e'tiborsiz qoldiradi

    z = Zarbxona(tmp_path / "p", kalitlar[0])
    o = Oyna(z)
    o.dialoglar = d
    o.show()
    o.OQIM_KUTISH_MS = 50
    t = Qaysar()
    o.oqim_qosh(t)
    t.start()
    assert o.close() is False and o.isVisible()
    assert d.chaqiriqlar[-1][0] == "xato" and "fon ishi" in d.chaqiriqlar[-1][2]
    assert z.jurnal.partiyalar() == []          # baza hali ochiq
    assert o.taymer.isActive()
    t.wait(5000)
    assert o.close() is True and not o.isVisible()
    assert o.close() is True                     # takror yopish — xavfsiz


def test_31_main_demo_haqiqiy_profilni_rad_etadi(ilova, tmp_path, kalitlar, sertifikat,
                                                 monkeypatch):
    import app.kirish
    import app.main
    from PySide6.QtWidgets import QDialog
    papka = tmp_path / "data"
    z0 = Zarbxona(papka, kalitlar[0], soat_ms=lambda: HOZIR)
    sertifikat.yoz(tmp_path / "s.aqcert")
    z0.sertifikat_import(tmp_path / "s.aqcert")
    z0.yop()

    class SoxtaKirish:
        def __init__(self, p):
            self.zarbxona = Zarbxona(p, kalitlar[0])
            self.tiklash = None

        def exec(self):
            return QDialog.DialogCode.Accepted
    monkeypatch.setattr(app.kirish, "KirishDialogi", SoxtaKirish)
    d = Dialoglar(tmp_path, tmp_path)
    d.ornat(monkeypatch)
    assert app.main.main(["--demo", "--papka", str(papka)]) == 1
    assert d.chaqiriqlar[-1][0] == "xato" and "haqiqiy bank" in d.chaqiriqlar[-1][2]
    assert not (papka / "demo_bank").exists()
    Zarbxona(papka, kalitlar[0]).yop()        # qulf ozod qilingan


def test_33_ikki_kishilik_tasdiq_gui(ilova, tmp_path, kalitlar, sertifikat, monkeypatch):
    """3.3: tasdiqchini ro'yxatdan o'tkazish, katta buyurtma zarbda tasdiq so'raydi,
    Buyurtmalar sahifasidan tasdiqlash, chegarani o'zgartirish."""
    from app.oyna import Oyna
    d = Dialoglar(tmp_path, tmp_path / "s.aqcert")
    d.ornat(monkeypatch)
    parollar = []
    monkeypatch.setattr(dialog, "parol",
                        lambda *a: d._q("parol", parollar.pop(0) if parollar else None))
    sertifikat.yoz(tmp_path / "s.aqcert")
    z = Zarbxona(tmp_path / "p", kalitlar[0], soat_ms=lambda: HOZIR)
    z.sertifikat_import(tmp_path / "s.aqcert")
    o = Oyna(z)
    o.dialoglar = d
    o.show()
    ks = o.sahifalar["kalit"]
    o.sahifaga_ot("kalit")
    tk = ks.tasdiq
    assert "O'chiq" in tk.holat_matn.text() and not tk.t_chegara.isEnabled()
    # ro'yxat: parollar mos emas → xato; keyin muvaffaqiyat
    tk.chegara.setText("1 000 000")
    parollar[:] = ["tasdiqchi-parol-1", "boshqa-parol-22"]
    assert bos_va_javob(o, tk.t_royxat) and d.chaqiriqlar[-1][0] == "xato"
    assert not z.tasdiq.yoqilgan
    parollar[:] = ["tasdiqchi-parol-1", "tasdiqchi-parol-1"]
    assert bos_va_javob(o, tk.t_royxat) and d.chaqiriqlar[-1][0] == "xabar"
    assert z.tasdiq.chegara() == 1_000_000 and "Yoqilgan" in tk.holat_matn.text()
    assert not tk.t_royxat.isEnabled() and tk.t_chegara.isEnabled()

    # zarb: 2 mln — tasdiq so'raladi; parol berilmasa zarb boshlanmaydi
    zs = o.sahifalar["zarb"]
    o.sahifaga_ot("zarb")
    zs.summa.setText("2 000 000")
    zs.qulf.setEditText("AQ-RES-2")
    zs.hajm.setValue(1000)
    zs.surat.rejim.setCurrentIndex(zs.surat.rejim.findData("cheklovsiz"))
    parollar[:] = []
    assert bos_va_javob(o, zs.t_zarb)
    assert not zs.ishlayapti() and "tasdiq berilmadi" in o.statusBar().currentMessage()
    b = z.jurnal.buyurtmalar()[0]
    assert z.tasdiq.holat(b) == "kutilmoqda"

    # Buyurtmalar: noto'g'ri parol → xato; to'g'ri → tasdiqlangan; davom → zarb
    bs = o.sahifalar["buyurtmalar"]
    o.sahifaga_ot("buyurtmalar")
    bs.jadval.selectRow(0)
    assert bs.t_tasdiq.isEnabled() and bs.jadval.item(0, 2).text() == "kutilmoqda"
    parollar[:] = ["xato-parol-000"]
    assert bos_va_javob(o, bs.t_tasdiq) and d.chaqiriqlar[-1][0] == "xato"
    parollar[:] = ["tasdiqchi-parol-1"]
    assert bos_va_javob(o, bs.t_tasdiq)
    assert z.tasdiq.holat(z.jurnal.buyurtma(b.buyurtma_id)) == "tasdiqlangan"
    bs.jadval.selectRow(0)
    assert not bs.t_tasdiq.isEnabled()
    assert bos_va_javob(o, bs.t_davom)
    assert kut(lambda: not zs.ishlayapti() and zs.t_zarb.isEnabled(), 60)
    assert z.jurnal.buyurtma(b.buyurtma_id).holat == "tugadi"

    # zarbda darhol tasdiqlash (to'g'ri parol)
    o.sahifaga_ot("zarb")
    zs.summa.setText("1 500 000")
    parollar[:] = ["tasdiqchi-parol-1"]
    assert bos_va_javob(o, zs.t_zarb)
    assert kut(lambda: not zs.ishlayapti() and zs.t_zarb.isEnabled(), 60)
    assert z.jurnal.buyurtmalar()[0].holat == "tugadi"

    # chegarani o'zgartirish
    o.sahifaga_ot("kalit")
    tk.chegara.setText("5000000")
    parollar[:] = ["xato-parol-000"]
    assert bos_va_javob(o, tk.t_chegara) and d.chaqiriqlar[-1][0] == "xato"
    parollar[:] = ["tasdiqchi-parol-1"]
    assert bos_va_javob(o, tk.t_chegara) and z.tasdiq.chegara() == 5_000_000
    o.close()


def test_34_35_hisobot_pdf_va_qr(ilova, tmp_path, kalitlar, sertifikat, monkeypatch):
    from app.oyna import Oyna
    from core.isbot import isbot_tekshir
    from core.surat import Surat
    d = Dialoglar(tmp_path, tmp_path / "s.aqcert")
    d.ornat(monkeypatch)
    sertifikat.yoz(tmp_path / "s.aqcert")
    z = Zarbxona(tmp_path / "p", kalitlar[0], soat_ms=lambda: HOZIR)
    z.sertifikat_import(tmp_path / "s.aqcert")
    b = z.buyurtma_yarat(12_345, "AQ-RES-1", "", Surat(rejim="cheklovsiz"), partiya_hajmi=4)
    z.buyurtmani_bajar(b.buyurtma_id)
    o = Oyna(z)
    o.dialoglar = d
    o.show()
    bs = o.sahifalar["buyurtmalar"]
    o.sahifaga_ot("buyurtmalar")
    bs.jadval.selectRow(0)
    assert bos_va_javob(o, bs.t_hisobot)
    pdf = tmp_path / f"hisobot-{b.buyurtma_id}.pdf"
    assert pdf.read_bytes()[:5] == b"%PDF-" and pdf.stat().st_size > 2000
    # regressiya: matn sahifa bo'ylab to'g'ri masshtabda (1200 dpi xatosida mitti edi)
    QtPdf = pytest.importorskip("PySide6.QtPdf")
    from PySide6.QtCore import QSize
    hujjat = QtPdf.QPdfDocument()
    hujjat.load(str(pdf))
    rasm = hujjat.render(0, QSize(450, 636))
    qora = sum(1 for x in range(225, 440, 3) for y in range(20, 300, 3)       # fon shaffof
               if rasm.pixelColor(x, y).alpha() > 128 and rasm.pixelColor(x, y).lightness() < 128)
    assert qora > 50, qora
    ps = o.sahifalar["partiyalar"]
    o.sahifaga_ot("partiyalar")
    ps.jadval.selectRow(0)
    ps.indeks.setValue(2)
    assert bos_va_javob(o, ps.t_isbot)
    j = next(tmp_path.glob("isbot-*-2.json"))
    assert isbot_tekshir(j.read_text(encoding="utf-8"), z.pk)[0]
    pytest.importorskip("segno")
    assert bos_va_javob(o, ps.t_qr)
    assert next(tmp_path.glob("isbot-*-2.png")).read_bytes()[:4] == b"\x89PNG"
    ps.indeks.setValue(99)
    assert bos_va_javob(o, ps.t_qr) and d.chaqiriqlar[-1][0] == "xato"
    o.close()


def test_4x_pico_sozlash_kirish_va_zarb(ilova, tmp_path, kalitlar, sertifikat, monkeypatch):
    """4.x: kalit.json → Pico (soxta) ga ko'chirish, PIN bilan kirish, tugma banneri,
    holat, chiqishda qulflash, fayl kalitiga qaytish."""
    from app.kirish import KirishDialogi
    from app.oyna import Oyna
    from core.pico.qurilma import PicoImzolovchi
    from core.pico.ulanish import sozlama_oqi
    d = Dialoglar(tmp_path, tmp_path / "s.aqcert")
    d.ornat(monkeypatch)
    papka = tmp_path / "p"
    ombor_yarat(papka / "kalit.json", "fayl-parol-1", n=4096, urug=bytes(range(1, 33)))
    sertifikat.yoz(tmp_path / "s.aqcert")
    port = f"soxta:{tmp_path / 'flash.json'}"
    javob = {"port": port, "rejim": "import", "pin": "4321", "pin2": "4321",
             "parol": "fayl-parol-1"}
    monkeypatch.setattr(dialog, "pico_sozlash", lambda *a: dict(javob))

    z = Zarbxona(papka, ombor_och(papka / "kalit.json", "fayl-parol-1"), soat_ms=lambda: HOZIR)
    z.sertifikat_import(tmp_path / "s.aqcert")
    o = Oyna(z)
    o.dialoglar = d
    o.sahifaga_ot("kalit")
    pk_karta = o.sahifalar["kalit"].pico
    assert pk_karta.t_sozla.isVisibleTo(pk_karta) and not pk_karta.t_holat.isVisibleTo(pk_karta)
    assert bos_va_javob(o, pk_karta.t_sozla)            # qisqa PIN — rad
    assert d.chaqiriqlar[-1][0] == "xato" and "PIN" in d.chaqiriqlar[-1][2]
    javob.update(pin="pico-pin-77", pin2="pico-pin-77")
    pk_karta.t_sozla.click()
    assert kut(lambda: pk_karta.ish is not None and pk_karta.ish.isFinished())
    assert kut(lambda: d.chaqiriqlar[-1][0] == "xabar")
    assert "Kalit o'sha" in d.chaqiriqlar[-1][2]
    s = sozlama_oqi(papka)
    assert s.public_key == z.pk and s.port == port
    o.close()

    # kirish: Pico rejimi
    k = KirishDialogi(papka)
    assert k.pico is not None and not k.parol2.isVisibleTo(k) and "Pico" in k.izoh.text()
    k.parol1.setText("xato-pin-00")
    k.tugma.click()
    assert "PIN noto'g'ri" in k.xabar.text() and "qolgan urinish: 4" in k.xabar.text()
    k.parol1.setText("pico-pin-77")
    k.tugma.click()
    z = k.zarbxona
    assert isinstance(z.imz, PicoImzolovchi) and z.pk == s.public_key
    z.soat_ms = lambda: HOZIR
    o = Oyna(z)
    o.dialoglar = d
    kutishlar = []
    o.pico_kutish.connect(kutishlar.append)
    b = z.buyurtma_yarat(12_345, "AQ-RES-PICO", "", None, partiya_hajmi=5)
    from core.surat import Surat
    r = z.buyurtmani_bajar(b.buyurtma_id, surat=Surat(rejim="cheklovsiz"))
    QCoreApplication.processEvents()
    assert r.holat == "tugadi", r.xabar
    assert kutishlar[0].startswith("RUXSAT") and kutishlar[-1] is None
    assert not o.pico_banner.isVisibleTo(o)
    ks = o.sahifalar["kalit"]
    o.sahifaga_ot("kalit")
    assert not ks.pico.t_sozla.isVisibleTo(ks.pico) and "Pico" in ks.izoh.text()
    ks.pico.t_holat.click()
    assert kut(lambda: "ruxsat faol" in ks.pico.natija.text(), 10), ks.pico.natija.text()
    qurilma = z.imz.t.q
    # fayl kalitiga qaytish (kalit.json bor)
    assert bos_va_javob(o, ks.pico.t_qaytish)
    assert sozlama_oqi(papka) is None
    o.close()
    assert qurilma.sk is None                        # chiqishda Pico qulflandi


def test_gc_faqat_asosiy_oqimda(ilova):
    """PYSIDE-810: avtomatik GC o'chiq; asosiy oqimdagi taymer halqalarni yig'adi."""
    import gc

    from app import gc_nazorat

    class Halqa:
        pass
    t = gc_nazorat.ornat(ilova, oraliq_ms=10)
    try:
        assert not gc.isenabled()
        h = Halqa()
        h.o = h
        import weakref
        w = weakref.ref(h)
        del h
        assert w() is not None                      # avtomatik yig'ilmadi
        assert kut(lambda: w() is None, 5)          # taymer asosiy oqimda yig'di
    finally:
        t.stop()
