"""Buyurtmalar: ro'yxat, holat, progress, davom ettirish/bekor qilish."""

from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QHBoxLayout, QPushButton

from app import dialog
from app.sahifalar.boshqaruv import vaqt
from app.vidjetlar import Karta, Sahifa, jadval, jadval_toldir, som, tanlangan_kalit, yorliq
from core.buyurtma import BuyurtmaXatosi
from core.cheklov import cheklov_tavsif
from core.surat import Surat

HOLAT_NOMI = {"faol": "faol", "pauza": "pauza", "tugadi": "tugadi ✓", "bekor": "bekor"}


class BuyurtmalarSahifasi(Sahifa):
    sarlavha_matni = "Buyurtmalar"

    def __init__(self, ctx):
        super().__init__(ctx)
        k = Karta()
        self.jadval = jadval(["Buyurtma", "Holat", "Summa", "Progress", "Partiya hajmi",
                              "Zaxira qulfi", "Cheklov", "Sur'at", "Yaratilgan"])
        self.jadval.itemSelectionChanged.connect(self.tanlandi)
        k.qosh(self.jadval)
        q = QHBoxLayout()
        self.t_davom = QPushButton("Davom ettirish")
        self.t_davom.setObjectName("asosiy")
        self.t_bekor = QPushButton("Bekor qilish")
        self.t_bekor.setObjectName("xavfli")
        self.t_yangila = QPushButton("Yangilash")
        for w, fn in ((self.t_davom, self.davom_bos), (self.t_bekor, self.bekor_bos),
                      (self.t_yangila, self.yangila_bos)):
            w.clicked.connect(fn)
            q.addWidget(w)
        q.addStretch(1)
        k.qosh(q)
        self.izoh = yorliq("Davom ettirishda «Zarb» sahifasidagi joriy sur'at sozlamasi "
                           "ishlatiladi. Nominallar summadan deterministik qayta hisoblanadi — "
                           "buyurtma keyingi kupyuradan davom etadi.", "xira")
        k.qosh(self.izoh)
        self.qosh(k)
        self.oxiri()

    def yangila(self) -> None:
        bs = self.ctx.z.jurnal.buyurtmalar()
        jadval_toldir(self.jadval, [[
            b.buyurtma_id, HOLAT_NOMI.get(b.holat, b.holat), som(b.summa),
            f"{b.bajarilgan_kupyura}/{b.kupyura_soni} "
            f"({b.bajarilgan_kupyura * 100 // max(1, b.kupyura_soni)} %)",
            b.partiya_hajmi, b.zaxira_qulfi, cheklov_tavsif(b.cheklov),
            Surat.json_dan(b.surat).rejim, vaqt(b.yaratilgan_ms)] for b in bs],
            [b.buyurtma_id for b in bs])
        self.tanlandi()

    @Slot()
    def tanlandi(self) -> None:
        bid = tanlangan_kalit(self.jadval)
        b = self.ctx.z.jurnal.buyurtma(bid) if bid else None
        ochiq = b is not None and b.holat in ("faol", "pauza")
        self.t_davom.setEnabled(ochiq)
        self.t_bekor.setEnabled(ochiq)

    @Slot()
    def yangila_bos(self) -> None:
        self.yangila()
        self.holat("buyurtmalar yangilandi")

    @Slot()
    def davom_bos(self) -> None:
        bid = tanlangan_kalit(self.jadval)
        if not bid:
            dialog.xato(self, "Buyurtma", "Avval jadvaldan buyurtmani tanlang.")
            return
        self.ctx.sahifaga_ot("zarb")
        self.ctx.sahifalar["zarb"].ishga_tushir(bid)

    @Slot()
    def bekor_bos(self) -> None:
        bid = tanlangan_kalit(self.jadval)
        if not bid:
            dialog.xato(self, "Buyurtma", "Avval jadvaldan buyurtmani tanlang.")
            return
        zarb = self.ctx.sahifalar["zarb"]
        if zarb.ishlayapti() and zarb.ishchi.buyurtma_id == bid:
            dialog.xato(self, "Buyurtma", "Bu buyurtma hozir zarb qilinmoqda — avval to'xtating.")
            return
        if not dialog.tasdiq(self, "Bekor qilish", f"Buyurtma {bid} bekor qilinsinmi?\n"
                             "Zarb qilingan partiyalar qoladi, qolgani chiqarilmaydi."):
            self.holat("bekor qilish rad etildi")
            return
        try:
            self.ctx.z.buyurtma_bekor(bid)
        except BuyurtmaXatosi as e:
            dialog.xato(self, "Buyurtma", str(e))
            return
        self.holat(f"buyurtma {bid} bekor qilindi")
        self.yangila()
