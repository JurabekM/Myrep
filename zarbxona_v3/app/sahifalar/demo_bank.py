"""Demo bank sahifasi (faqat DEMO rejimida): bank tomonidan qaralganda nima bo'lyapti —
qabul qilingan partiyalar, zaxira qulflari, sertifikat."""

from __future__ import annotations

import time

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton

from app import dialog
from app.vidjetlar import Karta, Sahifa, jadval, jadval_toldir, som, yorliq
from core.demo_bank import DEMO_LIMIT, DEMO_QULF_SUMMA
from core.ibtido import iz
from core.sertifikat import SertifikatXatosi


class DemoBankSahifasi(Sahifa):
    sarlavha_matni = "Demo bank"
    davriy_yangilansin = True

    def __init__(self, ctx):
        super().__init__(ctx)
        k = Karta("Bu nima?")
        k.qosh(yorliq("Bu <b>haqiqiy bank emas</b>. Zarbxona ichidagi soxta bank u bergan "
                      "sertifikat bilan zarb qilingan partiyalarni qabul qiladi. Qabul "
                      "qoidalari (§11) haqiqiy bankniki bilan bir xil: imzo, Merkle "
                      "ildizi, isbotlar, limit, zaxira qulfi va takroriy partiya tekshiriladi. "
                      "Sessiya shifrlanmaydi, bank kaliti demo papkasida ochiq turadi. Bu faqat "
                      "ko'rsatish va o'qitish uchun.", "xira"))
        self.bank = yorliq("")
        k.qosh(self.bank)
        q = QHBoxLayout()
        self.t_sert = QPushButton("Sertifikatni qayta berish (365 kun)")
        self.t_sert.clicked.connect(self.sert_bos)
        q.addWidget(self.t_sert)
        q.addStretch(1)
        k.qosh(q)
        self.qosh(k)

        qk = Karta("Zaxira qulflari")
        self.qulflar = jadval(["Qulf", "Bo'sh summa"])
        self.qulflar.setMinimumHeight(140)
        qk.qosh(self.qulflar)
        qq = QHBoxLayout()
        self.qulf_summa = QLineEdit(f"{DEMO_QULF_SUMMA}")
        self.qulf_summa.setPlaceholderText("summa")
        self.t_qulf = QPushButton("Yangi zaxira qulfi ochish")
        self.t_qulf.clicked.connect(self.qulf_bos)
        qq.addWidget(self.qulf_summa)
        qq.addWidget(self.t_qulf)
        qq.addStretch(1)
        qk.qosh(qq)
        self.qosh(qk)

        ak = Karta("Bank qabul qilgan partiyalar")
        self.qabul = jadval(["Partiya", "Kupyura", "Summa", "Qabul vaqti"])
        ak.qosh(self.qabul)
        t = QHBoxLayout()
        self.t_yangila = QPushButton("Yangilash")
        self.t_yangila.clicked.connect(self.yangila_bos)
        t.addWidget(self.t_yangila)
        t.addStretch(1)
        ak.qosh(t)
        self.qosh(ak)
        self.oxiri()

    def yangila(self) -> None:
        db, z = self.ctx.demo_bank, self.ctx.z
        if db is None:
            return
        s = z.sertifikat
        chiq = db.chiqarilgan(s.cert_id) if s else 0
        self.bank.setText(
            f"bank kaliti izi: <code>{iz(db.pk)}</code><br>"
            + (f"sertifikat: <b>{s.label}</b> · limit {som(s.limit_amount)} · bank "
               f"hisobida chiqarilgan {som(chiq)}" if s else "sertifikat yo'q"))
        jadval_toldir(self.qulflar, [[k, som(v)] for k, v in db.qulflar().items()])
        jadval_toldir(self.qabul, [[x["batch_id"][:12], x["note_count"], som(x["total"]),
                                    time.strftime("%Y-%m-%d %H:%M:%S",
                                                  time.localtime(x["accepted_ms"] / 1000))]
                                   for x in db.qabul_qilinganlar()])

    @Slot()
    def yangila_bos(self) -> None:
        self.yangila()
        self.holat("demo bank yangilandi")

    @Slot()
    def qulf_bos(self) -> None:
        t = self.qulf_summa.text().replace(" ", "")
        if not t.isdigit() or int(t) <= 0:
            dialog.xato(self, "Zaxira qulfi", "Summani musbat butun son bilan kiriting.")
            return
        nom = self.ctx.demo_bank.qulf_och(int(t))
        self.holat(f"zaxira qulfi ochildi: {nom} · {som(int(t))}")
        self.ctx.hammasini_yangila()

    @Slot()
    def sert_bos(self) -> None:
        z, db = self.ctx.z, self.ctx.demo_bank
        if z.jurnal.buyurtmalar(("faol", "pauza")) and not dialog.tasdiq(
                self, "Sertifikat", "Faol buyurtmalar eski sertifikatga bog'langan va pauzaga "
                "o'tadi. Davom etilsinmi?"):
            self.holat("sertifikat berilmadi")
            return
        s = db.sertifikat_ber(z.pk, DEMO_LIMIT)
        yol = db.papka / "sertifikat.aqcert"
        s.yoz(yol)
        try:
            z.sertifikat_import(yol)
        except SertifikatXatosi as e:
            dialog.xato(self, "Sertifikat", str(e))
            return
        self.holat(f"demo bank yangi sertifikat berdi: {s.cert_id.hex()[:12]}")
        self.ctx.hammasini_yangila()
