"""Zarb sahifasi: vakolat, buyurtma, konveyer sur'ati, ZARB/PAUZA/DAVOM/TO'XTATISH, monitor."""

from __future__ import annotations

import time

from PySide6.QtCore import QDateTime, Slot
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDateTimeEdit, QFormLayout, QHBoxLayout,
                               QLineEdit, QPushButton, QSpinBox)

from app import dialog
from app.ishchilar import ZarbIshchisi
from app.sahifalar.kartalar import KonveyerKarta, SuratKarta
from app.vidjetlar import Karta, Sahifa, som, yorliq
from core.buyurtma import BuyurtmaXatosi
from core.cheklov import CheklovXatosi, cheklov_json
from core.partiya import nominallar_soni
from core.surat import Surat


class ZarbSahifasi(Sahifa):
    sarlavha_matni = "Zarb"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.ishchi: ZarbIshchisi | None = None
        self.vakolat = Karta("Vakolat")
        self.vakolat_matn = yorliq("")
        self.vakolat.qosh(self.vakolat_matn)
        self.qosh(self.vakolat)

        b = Karta("Buyurtma")
        f = QFormLayout()
        self.summa = QLineEdit()
        self.summa.setPlaceholderText("masalan 1 234 567")
        self.summa.textChanged.connect(self.summa_ozgardi)
        self.qulf = QComboBox()
        self.qulf.setEditable(True)
        self.qulf.lineEdit().setPlaceholderText("bank bergan reserve_lock, masalan AQ-RES-0001")
        self.toifalar = QLineEdit()
        self.toifalar.setPlaceholderText("vergul bilan: SEED, FUEL (bo'sh — cheklovsiz)")
        mq = QHBoxLayout()
        self.muddat_bor = QCheckBox("muddat")
        self.muddat = QDateTimeEdit(QDateTime.currentDateTime().addYears(1))
        self.muddat.setCalendarPopup(True)
        self.muddat.setEnabled(False)
        self.muddat_bor.toggled.connect(self.muddat.setEnabled)
        mq.addWidget(self.muddat_bor)
        mq.addWidget(self.muddat, 1)
        sq = QHBoxLayout()
        self.soliq = QSpinBox()
        self.soliq.setRange(0, 9999)
        self.soliq.setSuffix(" bps")
        self.soliq_hisob = QLineEdit()
        self.soliq_hisob.setPlaceholderText("soliq hisobi")
        sq.addWidget(self.soliq)
        sq.addWidget(self.soliq_hisob, 1)
        self.hajm = QSpinBox()
        self.hajm.setRange(1, 100_000)
        self.hajm.setValue(500)
        self.hajm.setSuffix(" kupyura / partiya")
        self.hajm.valueChanged.connect(self.summa_ozgardi)
        f.addRow("Summa", self.summa)
        f.addRow("Zaxira qulfi", self.qulf)
        f.addRow("Toifalar", self.toifalar)
        f.addRow("Muddat", mq)
        f.addRow("Soliq", sq)
        f.addRow("Partiya hajmi", self.hajm)
        b.qosh(f)
        self.bolinish = yorliq("", "xira")
        b.qosh(self.bolinish)
        self.qosh(b)

        self.surat = SuratKarta()
        self.surat.ozgardi.connect(self.surat_saqla)
        self.qosh(self.surat)

        t = QHBoxLayout()
        self.t_zarb = QPushButton("ZARB")
        self.t_zarb.setObjectName("asosiy")
        self.t_pauza = QPushButton("PAUZA")
        self.t_davom = QPushButton("DAVOM")
        self.t_toxtat = QPushButton("TO'XTATISH")
        self.t_toxtat.setObjectName("xavfli")
        for w, fn in ((self.t_zarb, self.zarb_bos), (self.t_pauza, self.pauza_bos),
                      (self.t_davom, self.davom_bos), (self.t_toxtat, self.toxtat_bos)):
            w.clicked.connect(fn)
            t.addWidget(w)
        t.addStretch(1)
        self.qosh(t)
        self.konveyer = KonveyerKarta()
        self.qosh(self.konveyer)
        self.oxiri()

        s = self.ctx.z.jurnal.sozlama("surat")
        if s:
            self.surat.ornat(Surat.json_dan(s))
        self.tugmalar()

    # --- holat --------------------------------------------------------------------

    def ishlayapti(self) -> bool:
        return self.ishchi is not None and self.ishchi.isRunning()

    @Slot()
    def tugmalar(self) -> None:
        ish = self.ishlayapti()
        pz = ish and self.ishchi.pauzada_mi
        self.t_zarb.setEnabled(not ish)
        self.t_pauza.setEnabled(ish and not pz)
        self.t_davom.setEnabled(ish and pz)
        self.t_toxtat.setEnabled(ish)

    def yangila(self) -> None:
        z = self.ctx.z
        s = z.sertifikat
        if s is None:
            self.vakolat_matn.setText("<span style='color:#F87171'>Sertifikat yo'q.</span> "
                                      "«Kalit va sertifikat» sahifasida bank vakolatini import "
                                      "qiling.")
        else:
            m = s.muammo(z.pk, z.soat_ms())
            rang = "#F87171" if m else "#4ADE80"
            self.vakolat_matn.setText(
                f"<b>{s.label}</b> · limit {som(s.limit_amount)} · qolgan "
                f"{som(z.qolgan_limit())} · band (faol buyurtmalar) {som(z.band_summa())}<br>"
                f"<span style='color:{rang}'>{m or 'yaroqli'}</span> · amal qiladi "
                f"{time.strftime('%Y-%m-%d', time.localtime(s.valid_until_ms / 1000))} gacha")
        joriy = self.qulf.currentText()
        self.qulf.clear()
        self.qulf.addItems(z.jurnal.oxirgi_qulflar())
        self.qulf.setEditText(joriy)
        self.tugmalar()

    @Slot()
    def summa_ozgardi(self) -> None:
        n = self._summa()
        if n:
            k = nominallar_soni(n)
            self.bolinish.setText(f"{som(n)} → {k} kupyura, "
                                  f"{-(-k // self.hajm.value())} partiya")
            self.surat.kupyura_soni(k)
        else:
            self.bolinish.setText("")
            self.surat.kupyura_soni(0)

    def _summa(self) -> int | None:
        t = self.summa.text().replace(" ", "").replace("_", "")
        return int(t) if t.isdigit() and int(t) > 0 else None

    @Slot()
    def surat_saqla(self) -> None:
        self.ctx.z.jurnal.sozlama_yoz("surat", self.surat.surat().json())

    # --- tugmalar -------------------------------------------------------------------

    @Slot()
    def zarb_bos(self) -> None:
        summa = self._summa()
        if summa is None:
            dialog.xato(self, "Zarb", "Summani musbat butun son bilan kiriting.")
            return
        try:
            muddat = self.muddat.dateTime().toMSecsSinceEpoch() if self.muddat_bor.isChecked() \
                else None
            cj = cheklov_json(self.toifalar.text().split(","), muddat, self.soliq.value(),
                              self.soliq_hisob.text())
            s = self.surat.surat()
            s.tekshir()
            b = self.ctx.z.buyurtma_yarat(summa, self.qulf.currentText(), cj, s,
                                          self.hajm.value())
        except (BuyurtmaXatosi, CheklovXatosi, ValueError) as e:
            dialog.xato(self, "Buyurtma yaratilmadi", str(e))
            self.holat(f"buyurtma yaratilmadi: {e}")
            return
        self.ishga_tushir(b.buyurtma_id)

    def ishga_tushir(self, buyurtma_id: str) -> None:
        if self.ishlayapti():
            dialog.xato(self, "Zarb", "Konveyer band: avval joriy zarbni to'xtating.")
            return
        s = self.surat.surat()
        self.ishchi = ZarbIshchisi(self.ctx.z, buyurtma_id, s)
        self.ishchi.satrlar.connect(self.konveyer.satrlar)
        self.ishchi.jarayon.connect(self.jarayon)
        self.ishchi.tugadi.connect(self.tugadi)
        self.ishchi.finished.connect(self.tugmalar)
        self.ctx.oqim_qosh(self.ishchi)
        self.konveyer.satrlar([f"— buyurtma {buyurtma_id} · sur'at: {s.rejim} —"])
        self.ishchi.start()
        self.holat(f"zarb boshlandi: buyurtma {buyurtma_id}")
        self.tugmalar()

    @Slot(dict)
    def jarayon(self, d: dict) -> None:
        self.konveyer.jarayon(d)
        if d.get("kupyura_ms") and not self.surat.olchangan_ms:
            self.surat.olchangan_ms = d["kupyura_ms"]
            self.surat.kupyura_soni(self.surat.soni)

    @Slot(object)
    def tugadi(self, r) -> None:
        self.konveyer.satrlar([f"— {r.holat.upper()}: {r.xabar.splitlines()[0]} · "
                               f"{len(r.partiyalar)} partiya yozildi —"])
        self.holat(f"zarb: {r.holat} — {r.xabar.splitlines()[0]}")
        if r.holat in ("pauza", "xato"):
            matn = r.xabar + (("\n\n" + r.hisobot.matn()) if r.hisobot else "")
            dialog.xato(self, "Zarb to'xtadi", matn)
        self.tugmalar()
        self.ctx.hammasini_yangila()

    @Slot()
    def pauza_bos(self) -> None:
        if self.ishlayapti():
            self.ishchi.pauza(True)
            self.ishchi.satr_qosh(f"[{time.strftime('%H:%M:%S')}] PAUZA")
            self.holat("pauza — DAVOM bilan davom ettiring")
        self.tugmalar()

    @Slot()
    def davom_bos(self) -> None:
        if self.ishlayapti():
            self.ishchi.pauza(False)
            self.ishchi.satr_qosh(f"[{time.strftime('%H:%M:%S')}] DAVOM")
            self.holat("davom etmoqda")
        self.tugmalar()

    @Slot()
    def toxtat_bos(self) -> None:
        if self.ishlayapti():
            self.ishchi.toxtat()
            self.holat("to'xtatilmoqda… joriy partiya yozilmaydi")
        self.tugmalar()

    def toxtat(self) -> None:
        if self.ishlayapti():
            self.ishchi.toxtat()
