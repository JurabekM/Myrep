"""Kalit va sertifikat: kalit izi, sertifikat importi, ochiq kalitni eksport qilish."""

from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QHBoxLayout, QPushButton

from app import dialog
from app.sahifalar.tasdiq_karta import TasdiqKarta
from app.vidjetlar import Karta, Sahifa, som, yorliq
from core.ibtido import iz
from core.ombor import MIN_PAROL, OmborXatosi, ombor_zaxira, parol_almashtir
from core.sertifikat import SertifikatXatosi


def _sana(ms: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ms / 1000))


class KalitSahifasi(Sahifa):
    sarlavha_matni = "Kalit va sertifikat"

    def __init__(self, ctx):
        super().__init__(ctx)
        k = Karta("Zarbxona kaliti (ML-DSA-65)")
        self.iz = yorliq("", "katta")
        k.qosh(self.iz)
        k.qosh(yorliq("Bankka ochiq kalitni bering. Bank sertifikatni aynan shu kalitga "
                      "chiqaradi. Izni bank operatori bilan ko'z bilan solishtiring. Maxfiy "
                      "kalit faqat parol bilan shifrlangan holda kalit.json da turadi.", "xira"))
        q = QHBoxLayout()
        self.t_eksport = QPushButton("Ochiq kalitni eksport qilish…")
        self.t_eksport.clicked.connect(self.eksport_bos)
        self.t_parol = QPushButton("Parolni o'zgartirish…")
        self.t_parol.clicked.connect(self.parol_bos)
        self.t_zaxira = QPushButton("Shifrlangan zaxira nusxa…")
        self.t_zaxira.clicked.connect(self.zaxira_bos)
        for w in (self.t_eksport, self.t_parol, self.t_zaxira):
            q.addWidget(w)
        q.addStretch(1)
        k.qosh(q)
        self.qosh(k)

        s = Karta("Bank sertifikati (vakolat)")
        self.sert = yorliq("")
        s.qosh(self.sert)
        self.ogoh = yorliq("", "ogoh")
        s.qosh(self.ogoh)
        sq = QHBoxLayout()
        self.t_import = QPushButton("Sertifikatni import qilish…")
        self.t_import.setObjectName("asosiy")
        self.t_import.clicked.connect(self.import_bos)
        sq.addWidget(self.t_import)
        sq.addStretch(1)
        s.qosh(sq)
        self.qosh(s)
        self.tasdiq = TasdiqKarta(ctx)
        self.qosh(self.tasdiq)
        self.oxiri()

    def yangila(self) -> None:
        z = self.ctx.z
        self.iz.setText(f"<span style='font-family:monospace'>{iz(z.pk)}</span>")
        self.ogoh.setText("<br>".join("⚠ " + m for m in z.ogohlantirishlar()))
        self.tasdiq.yangila()
        c = z.sertifikat
        if c is None:
            self.sert.setText("Sertifikat import qilinmagan. Bank bergan <b>.aqcert</b> "
                              "faylini tanlang.")
            return
        m = c.muammo(z.pk, z.soat_ms())
        self.sert.setText(
            f"<b>{c.label}</b><br>cert_id: <code>{c.cert_id.hex()}</code><br>"
            f"bank kaliti izi: <code>{iz(c.bank_public_key)}</code> (onlayn ulanishda "
            f"PINLANADI)<br>limit: {som(c.limit_amount)} · chiqarilgan "
            f"{som(z.chiqarilgan())} · qolgan {som(z.qolgan_limit())}<br>"
            f"amal qilish: {_sana(c.valid_from_ms)} — {_sana(c.valid_until_ms)}<br>"
            f"holat: <span style='color:{'#F87171' if m else '#4ADE80'}'>"
            f"{m or 'yaroqli'}</span>")

    @Slot()
    def eksport_bos(self) -> None:
        z = self.ctx.z
        yol = dialog.fayl_saqla(self, "Ochiq kalitni saqlash", "zarbxona_ochiq_kalit.json",
                                "JSON (*.json)")
        if not yol:
            self.holat("eksport bekor qilindi")
            return
        Path(yol).write_text(json.dumps({"algorithm": "ML-DSA-65", "public_key": z.pk.hex(),
                                         "fingerprint": iz(z.pk)}, indent=2),
                             encoding="utf-8")
        self.holat(f"ochiq kalit saqlandi: {yol}")

    @Slot()
    def parol_bos(self) -> None:
        r = dialog.parol_almashtirish(self)
        if r is None:
            self.holat("parol o'zgartirilmadi")
            return
        eski, yangi, takror = r
        if yangi != takror:
            dialog.xato(self, "Parol", "Yangi parollar mos emas.")
            return
        try:
            parol_almashtir(self.ctx.z.papka / "kalit.json", eski, yangi)
        except OmborXatosi as e:
            dialog.xato(self, "Parol", str(e))
            self.holat(f"parol o'zgartirilmadi: {e}")
            return
        self.holat("parol o'zgartirildi")
        dialog.xabar(self, "Parol", "Parol o'zgartirildi. Kalit va uning izi o'zgarmadi.\n"
                     "Eski zaxira nusxalar ESKI parol bilan ochiladi — yangisini oling.")

    @Slot()
    def zaxira_bos(self) -> None:
        yol = dialog.fayl_saqla(self, "Kalit zaxirasi", "zarbxona_kalit_zaxira.json",
                                "JSON (*.json)")
        if not yol:
            self.holat("zaxira bekor qilindi")
            return
        try:
            pk = ombor_zaxira(self.ctx.z.papka / "kalit.json", Path(yol))
        except (OmborXatosi, OSError) as e:
            dialog.xato(self, "Zaxira", str(e))
            return
        self.holat(f"kalit zaxirasi saqlandi: {yol}")
        dialog.xabar(self, "Zaxira", f"Saqlandi: {yol}\nIz: {iz(pk)}\n\nFayl parol bilan "
                     f"shifrlangan. Uni boshqa diskda yoki USB'da saqlang; parolsiz "
                     f"(kamida {MIN_PAROL} belgi) uni ochib bo'lmaydi.")

    @Slot()
    def import_bos(self) -> None:
        yol = dialog.fayl_och(self, "Sertifikat", "Sertifikat (*.aqcert);;Hammasi (*)")
        if not yol:
            self.holat("sertifikat tanlanmadi")
            return
        z = self.ctx.z
        eski = z.sertifikat
        if eski is not None and z.jurnal.buyurtmalar(("faol", "pauza")) and not dialog.tasdiq(
                self, "Sertifikat", "Faol buyurtmalar bor. Yangi sertifikat ularni pauzaga "
                "o'tkazishi mumkin (boshqa cert_id). Davom etilsinmi?"):
            self.holat("import bekor qilindi")
            return
        try:
            c = z.sertifikat_import(Path(yol))
        except SertifikatXatosi as e:
            dialog.xato(self, "Sertifikat rad etildi", str(e))
            self.holat(f"sertifikat rad etildi: {e}")
            return
        self.holat(f"sertifikat import qilindi: {c.label}")
        dialog.xabar(self, "Sertifikat", f"«{c.label}» import qilindi.\nBank kaliti izi: "
                     f"{iz(c.bank_public_key)}")
        self.ctx.hammasini_yangila()
