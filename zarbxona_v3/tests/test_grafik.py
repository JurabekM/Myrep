"""3.2 — jonli grafiklar: o'q shkalasi, chizish, hover, ishchining o'lchov namunalari."""

from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.grafik import JonliGrafik, chiroyli_oq, qiymat_matni  # noqa: E402
from core.buyurtma import Zarbxona  # noqa: E402
from core.surat import Surat  # noqa: E402


@pytest.fixture(scope="module")
def ilova():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("v,kutilgan", [(22, (30, 10)), (27.5, (30, 10)), (4.4, (6, 2)),
                                        (110, (150, 50)), (0.5, (0.6, 0.2))])
def test_chiroyli_oq(v, kutilgan):
    ymax, qadam = chiroyli_oq(v)
    assert ymax == pytest.approx(kutilgan[0]) and qadam == pytest.approx(kutilgan[1])
    assert ymax >= v
    assert 2 <= round(ymax / qadam) <= 6          # 3–7 ta belgi, butun qadamlar


def test_qiymat_matni():
    assert qiymat_matni(25, "%") == "25 %"
    assert qiymat_matni(20.0, "/s") == "20"
    assert qiymat_matni(19.83, "/s") == "19.8"
    assert qiymat_matni(38700, "/s") == "38 700"


def test_grafik_chiziladi_va_hover(ilova):
    g = JonliGrafik("Tezlik, kupyura/s", "/s", "#3987e5", "nishon")
    g.resize(480, 220)
    bosh = g.grab()                                           # bo'sh holat ham chiziladi
    assert not bosh.isNull()
    for i, (v, h) in enumerate([(20, "ish"), (0, "sovutish"), (18, "ish"), (0, "pauza"),
                                (21, "ish")]):
        g.qosh(float(i + 1), v, h, 20.0)
    assert g.y_max() == 30 and g.chegara == 20
    rasm = g.grab().toImage()
    assert not rasm.isNull()
    # chiziq rangi haqiqatan chizilgan
    ranglar = {rasm.pixelColor(x, y).name() for x in range(0, 480, 2) for y in range(0, 220, 2)}
    assert "#3987e5" in ranglar
    i = g.eng_yaqin(g.width() - 70)                           # o'ng chekkaga yaqin
    assert i == 4
    m = g.tooltip_matni(3)
    assert "0" in m and "pauza" in m and "nishon" in m
    g.tozala()
    assert not g.namunalar and g.chegara is None


def test_ishchi_namunalari_haqiqiy_zarbda(ilova, tmp_path, kalitlar, sertifikat):
    """Sekin zarb: namunalarda o'lchangan tezlik nishon atrofida, sovutish va pauza holatlari."""
    from app.ishchilar import ZarbIshchisi
    sertifikat.yoz(tmp_path / "s.aqcert")
    z = Zarbxona(tmp_path / "p", kalitlar[0], soat_ms=lambda: 1_800_000_000_000)
    try:
        z.sertifikat_import(tmp_path / "s.aqcert")
        s = Surat(rejim="tezlik", tezlik=40, byudjet=1.0, N=30, X=0.6)
        b = z.buyurtma_yarat(5000 * 90, "Q", "", s, partiya_hajmi=45)
        w = ZarbIshchisi(z, b.buyurtma_id, s)
        w.namuna_oraliq = 0.25
        namunalar = []
        w.namuna.connect(namunalar.append)
        tugadi = []
        w.tugadi.connect(tugadi.append)
        w.start()
        t = time.monotonic()
        pauza_berildi = False
        while not tugadi and time.monotonic() - t < 30:
            QCoreApplication.processEvents()
            if not pauza_berildi and time.monotonic() - t > 1.0:
                w.pauza(True)
                pauza_berildi = time.monotonic()
            if pauza_berildi is not True and pauza_berildi and time.monotonic() - pauza_berildi > 0.8:
                w.pauza(False)
                pauza_berildi = True
            time.sleep(0.01)
        w.wait(5000)
        QCoreApplication.processEvents()
    finally:
        z.yop()
    assert tugadi and tugadi[0].holat == "tugadi"
    holatlar = {n["holat"] for n in namunalar}
    assert {"ish", "sovutish", "pauza"} <= holatlar, holatlar
    assert all(n["nishon"] == pytest.approx(40) for n in namunalar[1:])
    ish = [n["tezlik"] for n in namunalar if n["holat"] == "ish" and n["tezlik"] > 0]
    assert ish and max(ish) < 40 * 1.6               # lenta tezligidan «portlash» yo'q
    assert all(0 <= n["cpu"] < 2 for n in namunalar)
    ts = [n["t"] for n in namunalar]
    assert ts == sorted(ts)
