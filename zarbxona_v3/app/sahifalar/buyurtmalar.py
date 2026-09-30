"""Buyurtmalar: ro'yxat, holat, progress, davom ettirish/bekor qilish."""

from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QHBoxLayout, QPushButton

from app import dialog
from app.sahifalar.boshqaruv import vaqt
from app.vidjetlar import Karta, Sahifa, jadval, jadval_toldir, som, tanlangan_kalit, yorliq
from core.buyurtma import BuyurtmaXatosi
from core.cheklov import cheklov_tavsif
from core.hisobot import buyurtma_hisoboti
from core.surat import Surat
from core.tasdiq import HOLAT_NOMI as TASDIQ_NOMI
from core.tasdiq import TasdiqXatosi


def pdf_yoz(html_matn: str, yol: str) -> None:
    """HTML → PDF (A4) Qt'ning o'zi bilan — qo'shimcha bog'liqlik yo'q."""
    from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument
    from PySide6.QtCore import QMarginsF
    w = QPdfWriter(str(yol))
    w.setResolution(96)          # QTextDocument 96 dpi da o'lchaydi — aks holda matn mitti
    w.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4),
                                QPageLayout.Orientation.Portrait, QMarginsF(15, 15, 15, 15),
                                QPageLayout.Unit.Millimeter))
    w.setTitle("AETHER-Q Zarbxona — buyurtma hisoboti")
    d = QTextDocument()
    d.setHtml(html_matn)
    d.setPageSize(w.pageLayout().paintRectPixels(w.resolution()).size().toSizeF())
    d.print_(w)


def tasdiq_sorov(ota, z, buyurtma_id: str) -> bool:
    """Ikkinchi operatordan parol so'raydi va buyurtmani imzolaydi. True — tasdiqlandi."""
    b = z.jurnal.buyurtma(buyurtma_id)
    p = dialog.parol(ota, "Ikkinchi tasdiq", f"Buyurtma {buyurtma_id} · {som(b.summa)}\n"
                     f"zaxira qulfi {b.zaxira_qulfi}\n\nTASDIQCHI paroli (ikkinchi operator):")
    if not p:
        ota.holat("tasdiq berilmadi — buyurtma kutmoqda («Buyurtmalar» → «Ikkinchi tasdiq»)")
        return False
    try:
        tiz = z.tasdiq.tasdiqla(buyurtma_id, p)
    except TasdiqXatosi as e:
        dialog.xato(ota, "Ikkinchi tasdiq", str(e))
        return False
    ota.holat(f"buyurtma {buyurtma_id} tasdiqlandi · tasdiqchi {tiz}")
    return True


HOLAT_NOMI = {"faol": "faol", "pauza": "pauza", "tugadi": "tugadi ✓", "bekor": "bekor"}


class BuyurtmalarSahifasi(Sahifa):
    sarlavha_matni = "Buyurtmalar"

    def __init__(self, ctx):
        super().__init__(ctx)
        k = Karta()
        self.jadval = jadval(["Buyurtma", "Holat", "Tasdiq", "Summa", "Progress",
                              "Partiya hajmi", "Zaxira qulfi", "Cheklov", "Sur'at",
                              "Yaratilgan"])
        self.jadval.itemSelectionChanged.connect(self.tanlandi)
        k.qosh(self.jadval)
        q = QHBoxLayout()
        self.t_davom = QPushButton("Davom ettirish")
        self.t_davom.setObjectName("asosiy")
        self.t_bekor = QPushButton("Bekor qilish")
        self.t_bekor.setObjectName("xavfli")
        self.t_yangila = QPushButton("Yangilash")
        self.t_tasdiq = QPushButton("Ikkinchi tasdiq…")
        self.t_hisobot = QPushButton("Hisobot (PDF)…")
        for w, fn in ((self.t_davom, self.davom_bos), (self.t_tasdiq, self.tasdiq_bos),
                      (self.t_hisobot, self.hisobot_bos),
                      (self.t_bekor, self.bekor_bos), (self.t_yangila, self.yangila_bos)):
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
        t = self.ctx.z.tasdiq
        jadval_toldir(self.jadval, [[
            b.buyurtma_id, HOLAT_NOMI.get(b.holat, b.holat), TASDIQ_NOMI[t.holat(b)],
            som(b.summa),
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
        self.t_tasdiq.setEnabled(ochiq and self.ctx.z.tasdiq.holat(b) in ("kutilmoqda",
                                                                          "yaroqsiz"))

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
    def tasdiq_bos(self) -> None:
        bid = tanlangan_kalit(self.jadval)
        if not bid:
            dialog.xato(self, "Tasdiq", "Avval jadvaldan buyurtmani tanlang.")
            return
        if tasdiq_sorov(self, self.ctx.z, bid):
            self.yangila()

    @Slot()
    def hisobot_bos(self) -> None:
        bid = tanlangan_kalit(self.jadval)
        if not bid:
            dialog.xato(self, "Hisobot", "Avval jadvaldan buyurtmani tanlang.")
            return
        yol = dialog.fayl_saqla(self, "Hisobotni saqlash", f"hisobot-{bid}.pdf", "PDF (*.pdf)")
        if not yol:
            self.holat("hisobot bekor qilindi")
            return
        pdf_yoz(buyurtma_hisoboti(self.ctx.z, bid), yol)
        self.holat(f"hisobot saqlandi: {yol}")

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
