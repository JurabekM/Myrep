"""§14 — konveyer sur'ati: v3 ning asosiy xususiyati.

Pul sekin, protsessorni kam band qilib, jonli kuzatuv ostida zarb qilinadi.
`soat` va `uxla` tashqaridan beriladi — testlar soxta soat bilan ishlaydi.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass

ENG_QISQA_UYQU = 0.004   # bundan qisqa uyqu qilinmaydi; qarz keyingi qadamga o'tadi
BOLAK = 0.10             # uzun kutish shunday bo'laklarga bo'linadi

REJIMLAR = ("tezlik", "davomiylik", "cheklovsiz")


class BekorQilindi(Exception):
    """Operator TO'XTATISH bosdi."""


@dataclass
class Surat:
    """§14.2 sozlamalari (profilda saqlanadi)."""

    rejim: str = "tezlik"
    tezlik: float = 8.0          # kupyura/soniya
    davomiylik: float = 10.0     # daqiqa
    byudjet: float = 0.25        # 0 < b ≤ 1
    N: int = 25                  # har N kupyurada sovutish (0 — o'chiq)
    X: float = 2.0               # sovutish, soniya

    def tekshir(self) -> None:
        if self.rejim not in REJIMLAR:
            raise ValueError(f"noma'lum rejim: {self.rejim}")
        if self.rejim == "tezlik" and not self.tezlik > 0:
            raise ValueError("tezlik 0 dan katta bo'lsin")
        if self.rejim == "davomiylik" and not self.davomiylik > 0:
            raise ValueError("davomiylik 0 dan katta bo'lsin")
        if not 0 < self.byudjet <= 1:
            raise ValueError("protsessor byudjeti 0 < b ≤ 1")
        if self.N < 0 or self.X < 0:
            raise ValueError("sovutish parametrlari manfiy bo'lmasin")

    def json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    @classmethod
    def json_dan(cls, s: str | None) -> Surat:
        if not s:
            return cls()
        d = json.loads(s)
        maydonlar = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        return cls(**maydonlar)

    def ritm_sozlamasi(self, soni: int) -> RitmSozlama:
        """Rejimdan amaldagi chegaralar. `soni` — davomiylik rejimi uchun."""
        if self.rejim == "cheklovsiz":
            return RitmSozlama(tezlik=None, byudjet=1.0, N=0, X=0.0)
        tezlik: float | None = self.tezlik
        if self.rejim == "davomiylik":
            tezlik = davomiylikdan_tezlik(soni, self.davomiylik * 60, self.N, self.X)
        return RitmSozlama(tezlik=tezlik, byudjet=self.byudjet, N=self.N, X=self.X)


@dataclass(frozen=True)
class RitmSozlama:
    tezlik: float | None
    byudjet: float
    N: int
    X: float


def davomiylikdan_tezlik(soni: int, davomiylik_s: float, N: int, X: float) -> float:
    tanaffus = (soni // N) * X if N > 0 else 0
    return soni / max(davomiylik_s - tanaffus, davomiylik_s * 0.05)


def taxminiy_vaqt(s: RitmSozlama, soni: int, kupyura_ms: float) -> float:
    t = soni * kupyura_ms / 1000 / s.byudjet
    if s.tezlik:
        t = max(t, soni / s.tezlik)
    if s.N and s.X:
        t += (soni // s.N) * s.X
    return t


def tezlik_matni(t: float | None) -> str:
    """«0 kupyura/s» emas: 1 dan kichik bo'lsa «~har 6 soniyada 1 kupyura»."""
    if t is None:
        return "cheklovsiz"
    if t <= 0:
        return "—"
    if t < 1:
        return f"~har {1 / t:.0f} soniyada 1 kupyura"
    if t < 10:
        return f"{t:.1f} kupyura/s"
    return f"{t:,.0f} kupyura/s".replace(",", " ")


def vaqt_matni(s: float) -> str:
    s = max(0, int(round(s)))
    if s < 60:
        return f"{s} soniya"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m} daq {s:02d} s"
    h, m = divmod(m, 60)
    return f"{h} soat {m:02d} daq"


class Ritm:
    """§14.3 — aynan spec'dagi mantiq, qo'shimcha PAUZA bilan."""

    def __init__(self, s: RitmSozlama,
                 soat: Callable[[], float] = time.perf_counter,
                 uxla: Callable[[float], None] = time.sleep,
                 toxtatildi: Callable[[], bool] | None = None,
                 tanaffus: Callable[[float], None] | None = None,
                 pauzada: Callable[[], bool] | None = None):
        self.s = s
        self.soat, self.uxla = soat, uxla
        self.toxtatildi, self.tanaffus, self.pauzada = toxtatildi, tanaffus, pauzada
        self.boshlangan = soat()
        self.oxirgi = self.boshlangan
        self.ishlagan = 0.0      # sof ish vaqti
        self.uxlagan = 0.0       # jami kutish (tanaffus ham)
        self.tanaffusda = 0.0    # sovutish + pauza — tezlik nishonidan chegiriladi

    def _bekormi(self) -> None:
        if self.toxtatildi and self.toxtatildi():
            raise BekorQilindi()

    def _pauza_kut(self) -> None:
        """Pauzadagi vaqt `tanaffusda` ga qo'shiladi — davomdan keyin portlash yo'q.
        `uxlagan` ga qo'shilmaydi: aks holda byudjet «kredit» berib, keyin CPU to'la yonadi."""
        if not (self.pauzada and self.pauzada()):
            return
        t0 = self.soat()
        while self.pauzada():
            self._bekormi()
            self.uxla(BOLAK)
        self.tanaffusda += self.soat() - t0

    def qadam(self, bajarildi: int) -> None:
        """Har kupyuradan KEYIN chaqiriladi."""
        s = self.s
        hozir = self.soat()
        self.ishlagan += hozir - self.oxirgi
        kerak = 0.0
        if s.byudjet < 1:
            kerak = self.ishlagan * (1 - s.byudjet) / s.byudjet - self.uxlagan
        if s.tezlik is not None:
            nishon = self.boshlangan + self.tanaffusda + bajarildi / s.tezlik
            kerak = max(kerak, nishon - hozir)
        if kerak >= ENG_QISQA_UYQU:
            self._kut(kerak)
        if s.N > 0 and s.X > 0 and bajarildi % s.N == 0:
            if self.tanaffus:
                self.tanaffus(s.X)
            self.tanaffusda += s.X
            self._kut(s.X)
        self._pauza_kut()
        self.oxirgi = self.soat()

    def _kut(self, t: float) -> None:
        """Bo'laklab — TO'XTATISH darhol ishlasin."""
        qolgan = t
        while qolgan > 0:
            self._bekormi()
            self._pauza_kut()
            b = min(qolgan, BOLAK)
            self.uxla(b)
            qolgan -= b
        self.uxlagan += t
