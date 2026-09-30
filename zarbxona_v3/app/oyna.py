"""Asosiy oyna: chap menyu + sahifalar. `closeEvent` tartibi (§16.5):
avval taymer va oqimlar to'xtatilib kutiladi, KEYIN baza yopiladi."""

from __future__ import annotations

from PySide6.QtCore import QSize, QThread, QTimer, Slot
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow,
                               QStackedWidget, QWidget)

from app import dialog
from app.sahifalar.boshqaruv import BoshqaruvSahifasi
from app.sahifalar.buyurtmalar import BuyurtmalarSahifasi
from app.sahifalar.demo_bank import DemoBankSahifasi
from app.sahifalar.kalit import KalitSahifasi
from app.sahifalar.partiyalar import PartiyalarSahifasi
from app.sahifalar.qanday import QandaySahifasi
from app.sahifalar.tekshiruv import TekshiruvSahifasi
from app.sahifalar.zarb import ZarbSahifasi
from app.theme import ikonka
from core.buyurtma import TiklashHisoboti, Zarbxona
from core.ibtido import iz
from core.konstanta import VERSIYA

MENYU = [("boshqaruv", "Boshqaruv paneli", BoshqaruvSahifasi),
         ("zarb", "Zarb", ZarbSahifasi),
         ("buyurtmalar", "Buyurtmalar", BuyurtmalarSahifasi),
         ("partiyalar", "Partiyalar", PartiyalarSahifasi),
         ("tekshiruv", "Tekshiruv", TekshiruvSahifasi),
         ("kalit", "Kalit va sertifikat", KalitSahifasi),
         ("qanday", "Qanday ishlaydi", QandaySahifasi)]


class Oyna(QMainWindow):
    OQIM_KUTISH_MS = 15000

    def __init__(self, z: Zarbxona, demo_bank=None):
        super().__init__()
        self.z = z
        self.demo_bank = demo_bank
        self._yopildi = False
        self.oqimlar: list[QThread] = []
        belgi = "[DEMO] " if demo_bank else ""
        self.setWindowTitle(f"{belgi}AETHER-Q Zarbxona v{VERSIYA} — {iz(z.pk)}")
        self.setWindowIcon(ikonka())
        self.resize(1180, 780)

        ich = QWidget()
        q = QHBoxLayout(ich)
        q.setContentsMargins(0, 0, 0, 0)
        q.setSpacing(0)
        self.menyu = QListWidget()
        self.menyu.setObjectName("menyu")
        self.menyu.setFixedWidth(210)
        self.stek = QStackedWidget()
        self.sahifalar: dict[str, object] = {}
        self.menyu_royxati = MENYU + ([("demo", "Demo bank", DemoBankSahifasi)]
                                      if demo_bank else [])
        for kalit, nom, cls in self.menyu_royxati:
            it = QListWidgetItem(nom)
            it.setSizeHint(QSize(0, 40))
            self.menyu.addItem(it)
            s = cls(self)
            self.sahifalar[kalit] = s
            self.stek.addWidget(s)
        q.addWidget(self.menyu)
        q.addWidget(self.stek, 1)
        self.setCentralWidget(ich)
        self.menyu.currentRowChanged.connect(self.sahifa_almashdi)
        self.menyu.setCurrentRow(0)

        self.taymer = QTimer(self)
        self.taymer.setInterval(3000)
        self.taymer.timeout.connect(self.davriy)
        self.taymer.start()
        if demo_bank:
            b = QLabel("  DEMO REJIMI — haqiqiy bank emas, sessiya shifrlanmaydi  ")
            b.setObjectName("demo_belgi")
            self.statusBar().addPermanentWidget(b)
        self.holat("tayyor")

    # --- kontekst (sahifalar uchun) ------------------------------------------------

    def holat(self, matn: str) -> None:
        self.statusBar().showMessage(matn)

    def oqim_qosh(self, t: QThread) -> None:
        self.oqimlar.append(t)
        t.finished.connect(self._oqim_tugadi)

    @Slot()
    def _oqim_tugadi(self) -> None:
        self.oqimlar = [t for t in self.oqimlar if t.isRunning()]

    def sahifaga_ot(self, kalit: str) -> None:
        self.menyu.setCurrentRow([m[0] for m in self.menyu_royxati].index(kalit))

    def hammasini_yangila(self) -> None:
        for s in self.sahifalar.values():
            s.yangila()

    @Slot(int)
    def sahifa_almashdi(self, i: int) -> None:
        self.stek.setCurrentIndex(i)
        self.stek.currentWidget().yangila()

    @Slot()
    def davriy(self) -> None:
        w = self.stek.currentWidget()
        if getattr(w, "davriy_yangilansin", False):
            w.yangila()

    def ogohlantirishlarni_korsat(self) -> None:
        q = self.z.ogohlantirishlar()
        if q:
            self.holat("⚠ " + q[0])
            dialog.xabar(self, "Ogohlantirish", "\n\n".join(q))

    def tiklashni_korsat(self, t: TiklashHisoboti | None) -> None:
        if t is None or t.bosh:
            return
        matn = t.matn()
        if t.davom_taklifi:
            matn += "\n\nTugallanmagan buyurtmani «Buyurtmalar» sahifasida davom ettiring."
        dialog.xabar(self, "Ishga tushishda tiklash", matn)
        if t.davom_taklifi:
            self.sahifaga_ot("buyurtmalar")

    # --- yopish ------------------------------------------------------------------------

    def closeEvent(self, e) -> None:
        zarb = self.sahifalar["zarb"]
        if zarb.ishlayapti() and not dialog.tasdiq(
                self, "Chiqish", "Zarb davom etmoqda. To'xtatib chiqilsinmi?\n"
                                 "Joriy partiya yozilmaydi, buyurtma keyin davom etadi."):
            e.ignore()
            return
        if self._yopildi:
            e.accept()
            return
        self.taymer.stop()
        for s in self.sahifalar.values():
            if hasattr(s, "toxtat"):
                s.toxtat()
        # Tarmoq kutishlari ~0,2 s da to'xtatishni sezadi; baribir oqim tugamasa oyna
        # YOPILMAYDI — aks holda Qt «QThread: Destroyed while thread is still running»
        # bilan yiqiladi va baza oqim ostidan yopiladi.
        for t in list(self.oqimlar):
            t.wait(self.OQIM_KUTISH_MS)
        tirik = [t for t in self.oqimlar if t.isRunning()]
        if tirik:
            e.ignore()
            self.taymer.start()
            self.holat("fon ishlari hali to'xtamoqda — birozdan keyin qayta yoping")
            dialog.xato(self, "Chiqish", f"{len(tirik)} ta fon ishi hali tugamadi (masalan, "
                        "tarmoq javobini kutyapti). Ular to'xtatildi — bir necha soniyadan "
                        "keyin oynani qayta yoping.")
            return
        self._yopildi = True
        self.z.yop()      # oqimlardan KEYIN
        e.accept()
