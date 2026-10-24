"""«Ikki kishilik tasdiq» kartasi (Kalit va sertifikat sahifasida)."""

from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton

from app import dialog
from app.vidjetlar import Karta, som, yorliq
from core.ibtido import iz
from core.tasdiq import DEFAULT_CHEGARA, XAVFSIZ_CHEGARA, TasdiqXatosi


def summa_oqi(matn: str) -> int | None:
    t = matn.replace(" ", "").replace("_", "")
    return int(t) if t.isdigit() and int(t) > 0 else None


class TasdiqKarta(Karta):
    def __init__(self, ctx):
        super().__init__("Ikki kishilik tasdiq")
        self.ctx = ctx
        self.qosh(yorliq("Chegaradan katta buyurtmani IKKINCHI operator (tasdiqchi) o'z kaliti "
                         "va paroli bilan tasdiqlamaguncha zarb boshlanmaydi. Chegarani ham "
                         "faqat tasdiqchi o'zgartira oladi. Tasdiqchi parolini birinchi operator "
                         "bilmasligi kerak.", "xira"))
        self.holat_matn = yorliq("")
        self.qosh(self.holat_matn)
        q = QHBoxLayout()
        self.chegara = QLineEdit(f"{DEFAULT_CHEGARA}")
        self.chegara.setPlaceholderText("chegara, so'm")
        self.t_royxat = QPushButton("Tasdiqchini ro'yxatdan o'tkazish…")
        self.t_chegara = QPushButton("Chegarani o'zgartirish…")
        self.t_royxat.clicked.connect(self.royxat_bos)
        self.t_chegara.clicked.connect(self.chegara_bos)
        q.addWidget(self.chegara)
        q.addWidget(self.t_royxat)
        q.addWidget(self.t_chegara)
        q.addStretch(1)
        self.qosh(q)

    def yangila(self) -> None:
        t = self.ctx.z.tasdiq
        pk = t.tasdiqchi_pk()
        self.t_royxat.setEnabled(pk is None)
        self.t_chegara.setEnabled(pk is not None)
        if pk is None:
            self.holat_matn.setText("O'chiq — tasdiqchi ro'yxatdan o'tmagan. Har buyurtma bitta "
                                    "operator bilan zarb qilinadi.")
            return
        ch = t.chegara()
        buzilgan = (" <span style='color:#F87171'>(chegara imzosi yaroqsiz — har buyurtma "
                    "tasdiq talab qiladi)</span>" if ch == XAVFSIZ_CHEGARA else "")
        self.holat_matn.setText(f"<span style='color:#4ADE80'>Yoqilgan</span> · tasdiqchi izi "
                                f"<code>{iz(pk)}</code> · chegara <b>{som(ch)}</b>{buzilgan}")

    def _xabar(self, m: str) -> None:
        self.ctx.holat(m)

    @Slot()
    def royxat_bos(self) -> None:
        ch = summa_oqi(self.chegara.text())
        if ch is None:
            dialog.xato(self, "Ikki kishilik tasdiq", "Chegarani musbat butun son bilan kiriting.")
            return
        p1 = dialog.parol(self, "Tasdiqchi", "Tasdiqchi paroli (IKKINCHI operator kiritadi, "
                                             "kamida 8 belgi):")
        if not p1:
            self._xabar("tasdiqchi ro'yxatdan o'tkazilmadi")
            return
        p2 = dialog.parol(self, "Tasdiqchi", "Parolni takrorlang:")
        if p1 != p2:
            dialog.xato(self, "Tasdiqchi", "Parollar mos emas.")
            return
        try:
            pk = self.ctx.z.tasdiq.tasdiqchi_yarat(p1, ch)
        except TasdiqXatosi as e:
            dialog.xato(self, "Tasdiqchi", str(e))
            return
        self._xabar(f"tasdiqchi ro'yxatdan o'tdi: {iz(pk)}")
        dialog.xabar(self, "Tasdiqchi", f"Tasdiqchi kaliti yaratildi.\nIz: {iz(pk)}\nChegara: "
                     f"{som(ch)}\n\nBundan katta buyurtmalar tasdiqchi imzosini talab qiladi.")
        self.ctx.hammasini_yangila()

    @Slot()
    def chegara_bos(self) -> None:
        ch = summa_oqi(self.chegara.text())
        if ch is None:
            dialog.xato(self, "Chegara", "Chegarani musbat butun son bilan kiriting.")
            return
        p = dialog.parol(self, "Chegara", f"Yangi chegara: {som(ch)}.\nTasdiqchi paroli:")
        if not p:
            self._xabar("chegara o'zgartirilmadi")
            return
        try:
            self.ctx.z.tasdiq.chegara_ornat(ch, p)
        except TasdiqXatosi as e:
            dialog.xato(self, "Chegara", str(e))
            return
        self._xabar(f"tasdiq chegarasi: {som(ch)}")
        self.ctx.hammasini_yangila()
