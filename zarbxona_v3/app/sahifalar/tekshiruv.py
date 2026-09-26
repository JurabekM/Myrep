"""Tekshiruv: faylni yoki butun jurnalni tekshirish; buzib ko'rish demosi (§12)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPlainTextEdit, QPushButton

from app import dialog
from app.ishchilar import FonIsh
from app.theme import mono_shrift
from app.vidjetlar import Karta, Sahifa, yorliq
from core.buzish import TURLAR, Buzuvchi, BuzishXatosi
from core.tekshiruv import Hisobot, faylni_tekshir, jurnalni_tekshir


def _jurnal_ishi(z):
    return jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat)


class TekshiruvSahifasi(Sahifa):
    sarlavha_matni = "Tekshiruv"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.ish: FonIsh | None = None
        self.buzuvchi = Buzuvchi(ctx.z.partiya_papka, ctx.z.jurnal)
        k = Karta("Tekshirish")
        k.qosh(yorliq("Partiya noldan qayta hisoblanadi: tartib, nominal, cheklov, muhr, "
                      "Merkle ildizi (hamma bargdan), isbotlar, ML-DSA imzo, sertifikat va "
                      "limit. Jurnal tekshiruvi fayllarni jurnal bilan solishtiradi.", "xira"))
        q = QHBoxLayout()
        self.t_fayl = QPushButton("Faylni tekshirish…")
        self.t_jurnal = QPushButton("Butun jurnalni tekshirish")
        self.t_jurnal.setObjectName("asosiy")
        self.t_fayl.clicked.connect(self.fayl_bos)
        self.t_jurnal.clicked.connect(self.jurnal_bos)
        q.addWidget(self.t_fayl)
        q.addWidget(self.t_jurnal)
        q.addStretch(1)
        k.qosh(q)
        self.natija_sarlavha = yorliq("hali tekshirilmadi", "xira")
        k.qosh(self.natija_sarlavha)
        self.natija = QPlainTextEdit()
        self.natija.setReadOnly(True)
        self.natija.setFont(mono_shrift(9))
        self.natija.setMinimumHeight(200)
        k.qosh(self.natija)
        self.qosh(k)

        d = Karta("Buzib ko'rish demosi")
        d.qosh(yorliq("Fayl yoki jurnal ataylab buziladi — tekshiruv buni topishi kerak. "
                      "«Tiklash» asl baytlarni qaytaradi. Buzish qiymati har doim joriy "
                      "qiymatdan farq qiladi.", "xira"))
        bq = QHBoxLayout()
        self.partiya = QComboBox()
        self.tur = QComboBox()
        for k_, v in TURLAR.items():
            self.tur.addItem(v, k_)
        self.t_buz = QPushButton("Buzish")
        self.t_buz.setObjectName("xavfli")
        self.t_tikla = QPushButton("Tiklash")
        self.t_buz.clicked.connect(self.buz_bos)
        self.t_tikla.clicked.connect(self.tikla_bos)
        bq.addWidget(self.partiya, 1)
        bq.addWidget(self.tur, 1)
        bq.addWidget(self.t_buz)
        bq.addWidget(self.t_tikla)
        d.qosh(bq)
        self.buzish_holat = yorliq("", "ogoh")
        d.qosh(self.buzish_holat)
        self.qosh(d)
        self.oxiri()

    def yangila(self) -> None:
        joriy = self.partiya.currentData()
        self.partiya.clear()
        for y in self.ctx.z.jurnal.partiyalar()[::-1]:
            self.partiya.addItem(f"{y.partiya_id[:12]} · seq {y.birinchi_seq}..{y.oxirgi_seq}",
                                 y.partiya_id)
        i = self.partiya.findData(joriy)
        if i >= 0:
            self.partiya.setCurrentIndex(i)
        self.t_tikla.setEnabled(self.buzuvchi.buzilgan)

    def korsat(self, h: Hisobot, nima: str) -> None:
        if h.ok:
            self.natija_sarlavha.setObjectName("ok")
            self.natija_sarlavha.setText(f"✓ {nima}: TOZA")
        elif not h.tekshirildi and not h.muammolar:
            self.natija_sarlavha.setObjectName("ogoh")
            self.natija_sarlavha.setText(f"{nima}: TEKSHIRILMADI")
        else:
            self.natija_sarlavha.setObjectName("xavf")
            self.natija_sarlavha.setText(f"✗ {nima}: {len(h.muammolar)} ta muammo")
        self.natija_sarlavha.style().unpolish(self.natija_sarlavha)
        self.natija_sarlavha.style().polish(self.natija_sarlavha)
        self.natija.setPlainText(h.matn())
        self.holat(f"tekshiruv ({nima}): {'toza' if h.ok else 'muammo bor'}")

    @Slot()
    def fayl_bos(self) -> None:
        yol = dialog.fayl_och(self, "Partiya fayli", "Partiya (*.aqbatch);;Hammasi (*)")
        if not yol:
            self.holat("fayl tanlanmadi")
            return
        z = self.ctx.z
        h, _ = faylni_tekshir(Path(yol), z.pk, z.sertifikat)
        self.korsat(h, Path(yol).name)

    @Slot()
    def jurnal_bos(self) -> None:
        if self.ish is not None and self.ish.isRunning():
            self.holat("tekshiruv allaqachon ishlayapti")
            return
        self.natija_sarlavha.setText("tekshirilmoqda…")
        self.holat("jurnal tekshirilmoqda…")
        self.t_jurnal.setEnabled(False)
        self.ish = FonIsh(self.ctx.z, _jurnal_ishi)
        self.ish.natija.connect(self.jurnal_natija)
        self.ctx.oqim_qosh(self.ish)
        self.ish.start()

    @Slot(object)
    def jurnal_natija(self, r) -> None:
        self.t_jurnal.setEnabled(True)
        if isinstance(r, Exception):
            h = Hisobot()
            h.qosh("jurnal", "xato", str(r))
            r = h
        self.korsat(r, "jurnal")

    @Slot()
    def buz_bos(self) -> None:
        pid = self.partiya.currentData()
        if not pid:
            dialog.xato(self, "Buzish", "Jurnalda partiya yo'q — avval zarb qiling.")
            return
        zarb = self.ctx.sahifalar["zarb"]
        if zarb.ishlayapti():
            dialog.xato(self, "Buzish", "Zarb ketayotganda demo o'tkazilmaydi.")
            return
        try:
            t = self.buzuvchi.buz(self.tur.currentData(), pid)
        except BuzishXatosi as e:
            dialog.xato(self, "Buzish", str(e))
            return
        self.buzish_holat.setText(f"BUZILDI: {t}. Endi «Butun jurnalni tekshirish» — "
                                  "keyin «Tiklash».")
        self.korsat(_jurnal_ishi(self.ctx.z), "buzilgan jurnal")
        self.t_tikla.setEnabled(True)

    @Slot()
    def tikla_bos(self) -> None:
        n = self.buzuvchi.tikla()
        self.buzish_holat.setText(f"tiklandi ({n} ob'ekt)" if n else "tiklash kerak emas")
        self.korsat(_jurnal_ishi(self.ctx.z), "tiklangan jurnal")
        self.t_tikla.setEnabled(False)
