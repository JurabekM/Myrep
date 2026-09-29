"""Boshqaruv paneli: sertifikat holati, limit, chiqarilgan, qolgan, topshirilmagan;
faol buyurtma; oxirgi partiyalar."""

from __future__ import annotations

import time

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QPushButton

from app.vidjetlar import Karta, Sahifa, jadval, jadval_toldir, som, son, yorliq


def vaqt(ms: int | None) -> str:
    return "—" if not ms else time.strftime("%Y-%m-%d %H:%M", time.localtime(ms / 1000))


class BoshqaruvSahifasi(Sahifa):
    sarlavha_matni = "Boshqaruv paneli"
    davriy_yangilansin = True

    def __init__(self, ctx):
        super().__init__(ctx)
        g = QGridLayout()
        g.setSpacing(12)
        self.qiymatlar = {}
        for i, (k, nom) in enumerate([("sert", "Sertifikat"), ("limit", "Limit"),
                                      ("chiq", "Chiqarilgan"), ("qolgan", "Qolgan limit"),
                                      ("topsh", "Topshirilmagan partiya"),
                                      ("kup", "Jami kupyura")]):
            k_ = Karta(nom)
            lb = yorliq("—", "katta")
            k_.qosh(lb)
            self.qiymatlar[k] = lb
            g.addWidget(k_, i // 3, i % 3)
        self.qosh(g)

        self.faol = Karta("Faol buyurtma")
        self.faol_matn = yorliq("", "xira")
        self.faol.qosh(self.faol_matn)
        q = QHBoxLayout()
        self.t_zarb = QPushButton("Zarb sahifasiga o'tish")
        self.t_zarb.clicked.connect(self.zarbga_ot)
        self.t_yangila = QPushButton("Yangilash")
        self.t_yangila.clicked.connect(self.yangila_bos)
        q.addWidget(self.t_zarb)
        q.addWidget(self.t_yangila)
        q.addStretch(1)
        self.faol.qosh(q)
        self.qosh(self.faol)

        k = Karta("Oxirgi partiyalar")
        self.jadval = jadval(["Partiya", "Seq", "Kupyura", "Summa", "Zarb vaqti",
                              "Topshirilgan"])
        k.qosh(self.jadval)
        self.qosh(k)
        self.oxiri()

    @Slot()
    def zarbga_ot(self) -> None:
        self.ctx.sahifaga_ot("zarb")
        self.holat("Zarb sahifasi")

    @Slot()
    def yangila_bos(self) -> None:
        self.yangila()
        self.holat("boshqaruv paneli yangilandi")

    def yangila(self) -> None:
        z = self.ctx.z
        s = z.sertifikat
        if s is None:
            self.qiymatlar["sert"].setText("<span style='color:#F87171'>yo'q</span>")
            for k in ("limit", "chiq", "qolgan"):
                self.qiymatlar[k].setText("—")
        else:
            m = s.muammo(z.pk, z.soat_ms())
            ogoh = s.ogohlantirish(z.soat_ms())
            rang = "#F87171" if m else ("#FBBF24" if ogoh else "#4ADE80")
            kun = f" · ⚠ {ogoh.split(' (')[0]}" if ogoh else ""
            self.qiymatlar["sert"].setText(
                f"<span style='color:{rang}'>{m or 'yaroqli'}</span><br>"
                f"<span style='font-size:12px;color:#98A0B3'>{s.label}{kun}</span>")
            self.qiymatlar["limit"].setText(som(s.limit_amount))
            self.qiymatlar["chiq"].setText(som(z.chiqarilgan()))
            self.qiymatlar["qolgan"].setText(som(z.qolgan_limit()))
        st = z.jurnal.jami_statistika()
        t = st["topshirilmagan"]
        self.qiymatlar["topsh"].setText(
            f"<span style='color:{'#FBBF24' if t else '#4ADE80'}'>{t}</span>")
        self.qiymatlar["kup"].setText(f"{son(st['kupyura'])}<br><span style='font-size:12px;"
                                      f"color:#98A0B3'>{st['partiya']} partiyada</span>")
        faol = z.jurnal.buyurtmalar(("faol", "pauza"))
        if faol:
            self.faol_matn.setText("<br>".join(
                f"<b>{b.buyurtma_id}</b> · {b.holat} · {som(b.summa)} · "
                f"{b.bajarilgan_kupyura}/{b.kupyura_soni} kupyura "
                f"({b.bajarilgan_kupyura * 100 // max(1, b.kupyura_soni)} %)" for b in faol))
        else:
            self.faol_matn.setText("faol buyurtma yo'q")
        ys = z.jurnal.partiyalar()[-15:][::-1]
        jadval_toldir(self.jadval, [[y.partiya_id[:12], f"{y.birinchi_seq}..{y.oxirgi_seq}",
                                     y.soni, som(y.jami), vaqt(y.zarb_ms),
                                     vaqt(y.topshirilgan_ms) if y.topshirilgan_ms else
                                     ("xato" if y.topshirish_xatosi else "yo'q")] for y in ys])
