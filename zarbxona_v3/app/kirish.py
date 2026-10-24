"""Birinchi ochilish: kalit yo'q — yaratish (parol ikki marta); bor — iz va parol.
4.x: profil Pico rejimida (`imzolovchi.json`) bo'lsa — Pico'ga ulanish va PIN."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QVBoxLayout)

from app import dialog
from app.theme import tanga
from app.vidjetlar import Karta, yorliq
from core.buyurtma import BandXatosi, TiklashHisoboti, Zarbxona
from core.ibtido import iz
from core.konstanta import VERSIYA
from core.ombor import (MIN_PAROL, OmborXatosi, ombor_ochiq_kalit, ombor_och, ombor_tikla,
                        ombor_yarat)
from core.pico.protokol import PicoXatosi
from core.pico.ulanish import PicoSozlama, sozlama_oqi, ulan


class KirishDialogi(QDialog):
    def __init__(self, papka: Path, ombor_n: int | None = None):
        super().__init__()
        self.papka = Path(papka)
        self.kalit_yoli = self.papka / "kalit.json"
        self.ombor_n = ombor_n
        self.zarbxona: Zarbxona | None = None
        self.tiklash: TiklashHisoboti | None = None
        self.pico: PicoSozlama | None = None
        pico_xato = None
        try:
            self.pico = sozlama_oqi(self.papka)
        except PicoXatosi as e:
            pico_xato = str(e)
        self.yangi = self.pico is None and not self.kalit_yoli.exists()
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

        k = Karta("Pico imzo kaliti" if self.pico else
                  "Yangi zarbxona kaliti" if self.yangi else "Zarbxona kaliti")
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
        tq = QHBoxLayout()
        self.t_tikla = QPushButton("Zaxiradan tiklash…")
        self.t_tikla.clicked.connect(self.zaxiradan)
        self.t_tikla.setVisible(self.yangi)
        tq.addWidget(self.t_tikla)
        tq.addStretch(1)
        tq.addWidget(self.tugma)
        q.addLayout(tq)

        if pico_xato:
            self.xabar.setText(pico_xato)
        if self.pico:
            self.parol2.hide()
            self.parol1.setPlaceholderText("Pico PIN")
            iz_ = iz(self.pico.public_key) if self.pico.public_key else "?"
            self.izoh.setText(f"Profil: {self.papka}<br>Imzolovchi: Raspberry Pi Pico "
                              f"(port {self.pico.port})<br>Kalit izi: <b style='font-family:"
                              f"monospace'>{iz_}</b><br>Pico'ni USB'ga ulang va PIN kiriting.")
        elif self.yangi:
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
    def zaxiradan(self) -> None:
        """Mavjud kalitni zaxira faylidan tiklash — parol birinchi maydonga yoziladi."""
        self.xabar.setText("")
        if not self.parol1.text():
            self.xabar.setText("avval zaxira parolini birinchi maydonga yozing")
            return
        yol = dialog.fayl_och(self, "Kalit zaxirasi", "JSON (*.json);;Hammasi (*)")
        if not yol:
            return
        try:
            sk = ombor_tikla(Path(yol), self.kalit_yoli, self.parol1.text())
            self._kir(sk)
        except (OmborXatosi, BandXatosi) as e:
            self.xabar.setText(str(e))

    def _pico_xabar(self, matn: str | None) -> None:
        """Pico tugmani kutmoqda (masalan, eski jurnal zanjirini imzolash)."""
        self.xabar.setText(f"⏳ Pico tugmasini bosing: {matn}" if matn else "")
        QApplication.processEvents()

    def _pico_kirish(self, pin: str) -> None:
        assert self.pico is not None
        self.xabar.setText("Pico'ga ulanmoqda…")
        QApplication.processEvents()
        pico = None
        try:
            pico = ulan(self.pico, kutish_xabari=self._pico_xabar)
            pico.pin_och(pin)
            self.xabar.setText("")
            self._kir(pico)
        except (PicoXatosi, OmborXatosi, BandXatosi) as e:
            if pico is not None:
                pico.yop()
            matn = str(e)
            if isinstance(e, PicoXatosi) and e.qoshimcha:
                matn += f" — qolgan urinish: {e.qoshimcha[0][0]}"
            self.xabar.setText(matn)

    def _kir(self, sk) -> None:
        self.zarbxona = Zarbxona(self.papka, sk)
        self.tiklash = self.zarbxona.tiklash()
        self.accept()

    @Slot()
    def kirish(self) -> None:
        p1 = self.parol1.text()
        self.xabar.setText("")
        if self.pico:
            self._pico_kirish(p1)
            return
        try:
            if self.yangi:
                if p1 != self.parol2.text():
                    self.xabar.setText("parollar mos emas")
                    return
                kw = {"n": self.ombor_n} if self.ombor_n else {}
                sk = ombor_yarat(self.kalit_yoli, p1, **kw)
            else:
                sk = ombor_och(self.kalit_yoli, p1)
            self._kir(sk)
        except (OmborXatosi, BandXatosi) as e:
            self.xabar.setText(str(e))
