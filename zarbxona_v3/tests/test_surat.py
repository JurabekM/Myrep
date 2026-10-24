"""T5 — ritm (soxta soat), T7 — haqiqiy vaqt."""

from __future__ import annotations

import time

import pytest

from core.surat import (BOLAK, BekorQilindi, Ritm, RitmSozlama, Surat, davomiylikdan_tezlik,
                        taxminiy_vaqt, tezlik_matni)


class SoxtaSoat:
    def __init__(self):
        self.t = 0.0
        self.uyqular: list[float] = []

    def __call__(self) -> float:
        return self.t

    def uxla(self, d: float) -> None:
        self.uyqular.append(d)
        self.t += d

    def ish(self, d: float) -> None:
        self.t += d


def yur(s: RitmSozlama, soni: int, ish: float, **kw):
    c = SoxtaSoat()
    r = Ritm(s, soat=c, uxla=c.uxla, **kw)
    vaqtlar = []
    for i in range(soni):
        c.ish(ish)
        vaqtlar.append(c.t)          # kupyura tayyor bo'lgan payt
        r.qadam(i + 1)
    return c, r, vaqtlar


def test_tezlik():
    c, r, v = yur(RitmSozlama(10.0, 1.0, 0, 0), 50, 0.001)
    assert c.t == pytest.approx(5.0, abs=0.01)
    oraliq = [b - a for a, b in zip(v, v[1:])]
    assert all(x == pytest.approx(0.1, abs=0.005) for x in oraliq)


def test_byudjet_ish_ulushi():
    c, r, v = yur(RitmSozlama(None, 0.25, 0, 0), 400, 0.01)
    ulush = r.ishlagan / c.t
    assert ulush == pytest.approx(0.25, abs=0.01)


def test_ikki_chegaradan_kattasi():
    # tezlik 1000/s (0,001 s) lekin byudjet 0,5 va ish 0,01 s → byudjet hal qiladi
    c, r, _ = yur(RitmSozlama(1000.0, 0.5, 0, 0), 100, 0.01)
    assert c.t == pytest.approx(2.0, rel=0.02)
    # tezlik 2/s, byudjet 0,5, ish 0,001 → tezlik hal qiladi
    c, r, _ = yur(RitmSozlama(2.0, 0.5, 0, 0), 10, 0.001)
    assert c.t == pytest.approx(5.0, abs=0.01)


def test_qisqa_uyqu_yigiladi():
    # 1000/s, ish 0 → har qadam 1 ms kerak, 4 ms dan qisqa uyqu qilinmaydi
    c, r, _ = yur(RitmSozlama(1000.0, 1.0, 0, 0), 100, 0.0)
    assert all(d >= 0.004 - 1e-12 for d in c.uyqular)
    assert c.t == pytest.approx(0.1, abs=0.005)
    assert len(c.uyqular) < 100


def test_sovutish_va_portlash_yoq():
    """Har oraliq = 1/tezlik, sovutishdan keyingisi = 1/tezlik + X. Portlash yo'q."""
    tanaffuslar = []
    c, r, v = yur(RitmSozlama(4.0, 1.0, 5, 2.0), 20, 0.001, tanaffus=tanaffuslar.append)
    assert tanaffuslar == [2.0] * 4
    oraliq = [b - a for a, b in zip(v, v[1:])]
    for i, x in enumerate(oraliq, start=1):
        kutilgan = 0.25 + (2.0 if i % 5 == 0 else 0)
        assert x == pytest.approx(kutilgan, abs=0.01), (i, x)


def test_uzun_tanaffus_boklaklab_bekor_qilinadi():
    c = SoxtaSoat()
    bekor = [False]

    def uxla(d):
        c.uxla(d)
        if c.t > 1.0:
            bekor[0] = True
    r = Ritm(RitmSozlama(None, 1.0, 1, 3600.0), soat=c, uxla=uxla, toxtatildi=lambda: bekor[0])
    with pytest.raises(BekorQilindi):
        r.qadam(1)
    assert c.t < 1.0 + 2 * BOLAK         # soat kutmadi
    assert max(c.uyqular) <= BOLAK


def test_pauza_portlash_bermaydi():
    c = SoxtaSoat()
    pauza = [False]
    r = Ritm(RitmSozlama(2.0, 1.0, 0, 0), soat=c, uxla=c.uxla, pauzada=lambda: pauza[0])
    v = []
    for i in range(10):
        c.ish(0.001)
        v.append(c.t)
        if i == 4:
            pauza[0] = True
            # pauza «operator tomonidan» 30 soniyadan keyin olinadi
            asl = c.uxla

            def uxla(d, asl=asl):
                asl(d)
                if c.t >= v[-1] + 30:
                    pauza[0] = False
            r.uxla = uxla
        r.qadam(i + 1)
    oraliq = [b - a for a, b in zip(v, v[1:])]
    for i, x in enumerate(oraliq):
        if i == 4:
            assert x >= 30
        else:
            assert x == pytest.approx(0.5, abs=0.01), (i, x)


def test_davomiylik_rejimi():
    s = Surat(rejim="davomiylik", davomiylik=10, N=25, X=2.0)
    rs = s.ritm_sozlamasi(600)
    # 600 kupyura, 24 tanaffus × 2 s = 48 s; 600 / (600 − 48)
    assert rs.tezlik == pytest.approx(600 / 552)
    assert davomiylikdan_tezlik(10, 1.0, 1, 10) == pytest.approx(10 / 0.05)
    c, r, _ = yur(rs, 600, 0.0001)
    assert c.t == pytest.approx(600, rel=0.01)


def test_taxminiy_vaqt_va_matn():
    assert taxminiy_vaqt(RitmSozlama(8.0, 0.25, 25, 2.0), 100, 0.03) == pytest.approx(12.5 + 8)
    assert tezlik_matni(1 / 6) == "~har 6 soniyada 1 kupyura"
    assert "0 kupyura" not in tezlik_matni(0.01)
    assert Surat.json_dan(Surat(rejim="davomiylik", byudjet=0.5).json()).byudjet == 0.5


def test_t7_haqiqiy_vaqt():
    r = Ritm(RitmSozlama(40.0, 1.0, 0, 0))
    t0 = time.perf_counter()
    for i in range(20):
        r.qadam(i + 1)
    assert time.perf_counter() - t0 >= 0.4
