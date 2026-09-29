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
    from app.theme import mavzuni_qol
    a = QApplication.instance() or QApplication([])
    mavzuni_qol(a)
    return a


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
