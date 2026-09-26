"""Kalit va sertifikat: kalit izi, sertifikat importi, ochiq kalitni eksport qilish."""

from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QHBoxLayout, QPushButton

from app import dialog
from app.vidjetlar import Karta, Sahifa, som, yorliq
from core.ibtido import iz
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
        q.addWidget(self.t_eksport)
        q.addStretch(1)
        k.qosh(q)
        self.qosh(k)

        s = Karta("Bank sertifikati (vakolat)")
        self.sert = yorliq("")
        s.qosh(self.sert)
        sq = QHBoxLayout()
        self.t_import = QPushButton("Sertifikatni import qilish…")
        self.t_import.setObjectName("asosiy")
        self.t_import.clicked.connect(self.import_bos)
        sq.addWidget(self.t_import)
        sq.addStretch(1)
        s.qosh(sq)
        self.qosh(s)
        self.oxiri()

    def yangila(self) -> None:
        z = self.ctx.z
        self.iz.setText(f"<span style='font-family:monospace'>{iz(z.pk)}</span>")
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
