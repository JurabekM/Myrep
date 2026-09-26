"""Birinchi ochilish: kalit yo'q — yaratish (parol ikki marta); bor — iz va parol."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout)

from app.theme import tanga
from app.vidjetlar import Karta, yorliq
from core.buyurtma import BandXatosi, TiklashHisoboti, Zarbxona
from core.ibtido import iz
from core.konstanta import VERSIYA
from core.ombor import MIN_PAROL, OmborXatosi, ombor_ochiq_kalit, ombor_och, ombor_yarat


class KirishDialogi(QDialog):
    def __init__(self, papka: Path, ombor_n: int | None = None):
        super().__init__()
        self.papka = Path(papka)
        self.kalit_yoli = self.papka / "kalit.json"
        self.ombor_n = ombor_n
        self.zarbxona: Zarbxona | None = None
        self.tiklash: TiklashHisoboti | None = None
        self.yangi = not self.kalit_yoli.exists()
        self.setWindowTitle("Zarbxona — kirish")
        self.setMinimumWidth(460)

        q = QVBoxLayout(self)
        q.setContentsMargins(24, 24, 24, 24)
        bosh = QHBoxLayout()
        rasm = QLabel()
        rasm.setPixmap(tanga(56))
        bosh.addWidget(rasm)
        bosh.addWidget(yorliq(f"AETHER-Q Zarbxona <span style='color:#98A0B3'>v{VERSIYA}"
                              "</span>", "sarlavha"), 1)
        q.addLayout(bosh)

        k = Karta("Yangi zarbxona kaliti" if self.yangi else "Zarbxona kaliti")
        self.izoh = yorliq("", "xira")
        k.qosh(self.izoh)
        self.parol1 = QLineEdit()
        self.parol1.setEchoMode(QLineEdit.EchoMode.Password)
        self.parol1.setPlaceholderText("parol")
        self.parol2 = QLineEdit()
        self.parol2.setEchoMode(QLineEdit.EchoMode.Password)
        self.parol2.setPlaceholderText("parolni takrorlang")
        k.qosh(self.parol1)
        k.qosh(self.parol2)
        self.xabar = yorliq("", "xavf")
        k.qosh(self.xabar)
        q.addWidget(k)

        self.tugma = QPushButton("Kalit yaratish" if self.yangi else "Kirish")
        self.tugma.setObjectName("asosiy")
        self.tugma.clicked.connect(self.kirish)
        self.parol1.returnPressed.connect(self.kirish)
        self.parol2.returnPressed.connect(self.kirish)
        q.addWidget(self.tugma, alignment=Qt.AlignmentFlag.AlignRight)

        if self.yangi:
            self.izoh.setText(f"Profil: {self.papka}\nKalit hali yo'q. ML-DSA-65 kaliti "
                              f"yaratiladi va parol bilan shifrlanadi (kamida {MIN_PAROL} belgi).")
        else:
            self.parol2.hide()
            try:
                self.izoh.setText(f"Profil: {self.papka}\nKalit izi: "
                                  f"<b style='font-family:monospace'>"
                                  f"{iz(ombor_ochiq_kalit(self.kalit_yoli))}</b>")
            except OmborXatosi as e:
                self.izoh.setText(f"Profil: {self.papka}\nKalit fayli o'qilmadi: {e}")

    @Slot()
    def kirish(self) -> None:
        p1 = self.parol1.text()
        self.xabar.setText("")
        try:
            if self.yangi:
                if p1 != self.parol2.text():
                    self.xabar.setText("parollar mos emas")
                    return
                kw = {"n": self.ombor_n} if self.ombor_n else {}
                sk = ombor_yarat(self.kalit_yoli, p1, **kw)
            else:
                sk = ombor_och(self.kalit_yoli, p1)
            self.zarbxona = Zarbxona(self.papka, sk)
            self.tiklash = self.zarbxona.tiklash()
        except (OmborXatosi, BandXatosi) as e:
            self.xabar.setText(str(e))
            return
        self.accept()
