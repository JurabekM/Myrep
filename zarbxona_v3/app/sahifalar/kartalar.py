"""Zarb sahifasining kartalari: Konveyer sur'ati (§14.2) va Konveyer monitori (§16.3)."""

from __future__ import annotations

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                               QPlainTextEdit, QProgressBar, QSpinBox)

from app.theme import mono_shrift
from app.vidjetlar import Karta, yorliq
from core.surat import Surat, taxminiy_vaqt, tezlik_matni, vaqt_matni

TAXMINIY_KUPYURA_MS = 0.03     # §14.1 — o'lchanmagan boshlang'ich taxmin
REJIM_NOMI = {"tezlik": "Tezlik (kupyura/s)", "davomiylik": "Davomiylik (daqiqa)",
              "cheklovsiz": "Cheklovsiz (tez, CPU to'la)"}
MONITOR_MAX = 600


class SuratKarta(Karta):
    ozgardi = Signal()

    def __init__(self):
        super().__init__("Konveyer sur'ati")
        f = QFormLayout()
        self.rejim = QComboBox()
        for k, v in REJIM_NOMI.items():
            self.rejim.addItem(v, k)
        self.tezlik = QDoubleSpinBox()
        self.tezlik.setRange(0.01, 100_000)
        self.tezlik.setDecimals(2)
        self.tezlik.setSuffix(" kupyura/s")
        self.davomiylik = QDoubleSpinBox()
        self.davomiylik.setRange(0.1, 7 * 24 * 60)
        self.davomiylik.setSuffix(" daqiqa")
        self.byudjet = QSpinBox()
        self.byudjet.setRange(1, 100)
        self.byudjet.setSuffix(" % CPU")
        self.N = QSpinBox()
        self.N.setRange(0, 100_000)
        self.N.setPrefix("har ")
        self.N.setSuffix(" kupyurada")
        self.X = QDoubleSpinBox()
        self.X.setRange(0, 3600)
        self.X.setSuffix(" s tanaffus")
        sov = QHBoxLayout()
        sov.addWidget(self.N)
        sov.addWidget(self.X)
        f.addRow("Rejim", self.rejim)
        f.addRow("Tezlik", self.tezlik)
        f.addRow("Davomiylik", self.davomiylik)
        f.addRow("Protsessor byudjeti", self.byudjet)
        f.addRow("Sovutish", sov)
        self.qosh(f)
        self.taxmin = yorliq("", "xira")
        self.qosh(self.taxmin)
        self.olchangan_ms: float | None = None
        self.soni = 0
        for w in (self.tezlik, self.davomiylik, self.X):
            w.valueChanged.connect(self._ozgardi)
        for w in (self.byudjet, self.N):
            w.valueChanged.connect(self._ozgardi)
        self.rejim.currentIndexChanged.connect(self._ozgardi)
        self.ornat(Surat())

    def ornat(self, s: Surat) -> None:
        self.rejim.setCurrentIndex(max(0, self.rejim.findData(s.rejim)))
        self.tezlik.setValue(s.tezlik)
        self.davomiylik.setValue(s.davomiylik)
        self.byudjet.setValue(round(s.byudjet * 100))
        self.N.setValue(s.N)
        self.X.setValue(s.X)
        self._ozgardi()

    def surat(self) -> Surat:
        return Surat(rejim=self.rejim.currentData(), tezlik=self.tezlik.value(),
                     davomiylik=self.davomiylik.value(), byudjet=self.byudjet.value() / 100,
                     N=self.N.value(), X=self.X.value())

    def kupyura_soni(self, soni: int) -> None:
        self.soni = soni
        self._ozgardi(signal=False)

    @Slot()
    def _ozgardi(self, *_, signal: bool = True) -> None:
        r = self.rejim.currentData()
        self.tezlik.setEnabled(r == "tezlik")
        self.davomiylik.setEnabled(r == "davomiylik")
        for w in (self.byudjet, self.N, self.X):
            w.setEnabled(r != "cheklovsiz")
        rs = self.surat().ritm_sozlamasi(max(1, self.soni))
        if self.soni:
            ms = self.olchangan_ms or TAXMINIY_KUPYURA_MS
            t = taxminiy_vaqt(rs, self.soni, ms)
            manba = (f"o'lchangan: {self.olchangan_ms:.3f} ms/kupyura" if self.olchangan_ms
                     else f"TAXMINIY ({TAXMINIY_KUPYURA_MS} ms/kupyura, hali o'lchanmagan)")
            self.taxmin.setText(f"{self.soni} kupyura · lenta: {tezlik_matni(rs.tezlik)} · "
                                f"taxminiy vaqt ~{vaqt_matni(t)} ({manba})")
        else:
            self.taxmin.setText(f"lenta: {tezlik_matni(rs.tezlik)} · summani kiriting — "
                                "taxminiy vaqt hisoblanadi")
        if signal:
            self.ozgardi.emit()


class KonveyerKarta(Karta):
    def __init__(self):
        super().__init__("Konveyer")
        self.p_partiya = QProgressBar()
        self.p_partiya.setFormat("partiya: %v / %m")
        self.p_buyurtma = QProgressBar()
        self.p_buyurtma.setFormat("buyurtma: %v / %m")
        self.qosh(self.p_partiya)
        self.qosh(self.p_buyurtma)
        self.holat = yorliq("konveyer bo'sh", "xira")
        self.qosh(self.holat)
        self.monitor = QPlainTextEdit()
        self.monitor.setObjectName("monitor")
        self.monitor.setReadOnly(True)
        self.monitor.setMaximumBlockCount(MONITOR_MAX)   # eskilari tushib ketadi
        self.monitor.setFont(mono_shrift(9))
        self.monitor.setMinimumHeight(260)
        self.qosh(self.monitor)

    def satrlar(self, s: list[str]) -> None:
        self.monitor.appendPlainText("\n".join(s))

    def jarayon(self, d: dict) -> None:
        self.p_partiya.setMaximum(max(1, d["p_soni"]))
        self.p_partiya.setValue(d["p_bajarildi"])
        self.p_buyurtma.setMaximum(max(1, d["b_jami"]))
        self.p_buyurtma.setValue(d["b_bajarildi"])
        cpu = "—" if d["cpu"] is None else f"{d['cpu'] * 100:.1f} %"
        qolgan = "—" if d["qolgan_s"] is None else "~" + vaqt_matni(d["qolgan_s"])
        tz = tezlik_matni(d["tezlik"]) if d["tezlik"] else "o'lchanmoqda…"
        pz = " · PAUZA" if d.get("pauza") else ""
        self.holat.setText(f"{d['b_bajarildi']} / {d['b_jami']} · haqiqiy tezlik {tz} · "
                           f"haqiqiy CPU {cpu} · qolgan {qolgan}{pz}")


class GrafikKarta(Karta):
    """Jonli grafiklar: tezlik va CPU ulushi — IKKI alohida grafik (bitta y-o'q qoidasi)."""

    def __init__(self):
        from PySide6.QtWidgets import QHBoxLayout

        from app.grafik import CPU_RANG, TEZLIK_RANG, JonliGrafik
        super().__init__("Jonli grafiklar (o'lchangan, har ~1 soniya)")
        q = QHBoxLayout()
        q.setSpacing(12)
        self.tezlik = JonliGrafik("Tezlik, kupyura/s", "/s", TEZLIK_RANG, "nishon")
        self.cpu = JonliGrafik("CPU ulushi", "%", CPU_RANG, "byudjet")
        q.addWidget(self.tezlik, 1)
        q.addWidget(self.cpu, 1)
        self.qosh(q)
        self.qosh(yorliq("Kulrang fon — sovutish tanaffusi, sariq fon — pauza, uzuq chiziq — "
                         "sozlangan nishon tezlik va CPU byudjeti. Sichqonchani grafik ustida "
                         "yurgizing — o'sha soniyadagi qiymat chiqadi. Oxirgi qiymat grafik "
                         "o'ng tomonida va holat satrida.", "xira"))

    def tozala(self) -> None:
        self.tezlik.tozala()
        self.cpu.tozala()

    def namuna(self, d: dict) -> None:
        self.tezlik.qosh(d["t"], d["tezlik"], d["holat"], d.get("nishon"))
        b = d.get("byudjet") or 1.0
        self.cpu.qosh(d["t"], d["cpu"] * 100, d["holat"], b * 100 if b < 1 else None)
