"""Partiyalar: jadval, fayl eksport, onlayn topshirish, avto-topshirish, isbot eksporti."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (QCheckBox, QFormLayout, QHBoxLayout, QLineEdit, QPlainTextEdit,
                               QPushButton, QSpinBox)

from app import dialog
from app.ishchilar import TopshirishIshchisi
from app.sahifalar.boshqaruv import vaqt
from app.theme import mono_shrift
from app.vidjetlar import Karta, Sahifa, jadval, jadval_toldir, som, tanlangan_kalit, yorliq
from core.merkle import isbot_ajrat
from core.partiya import FaylXatosi, partiya_oqi
from core.sessiya import AETHERQ_YOQ, aetherq_core_bormi


class PartiyalarSahifasi(Sahifa):
    sarlavha_matni = "Partiyalar"
    davriy_yangilansin = True

    def __init__(self, ctx):
        super().__init__(ctx)
        self.ishchi: TopshirishIshchisi | None = None
        k = Karta()
        self.jadval = jadval(["Partiya", "Buyurtma", "Seq", "Kupyura", "Summa", "Zarb vaqti",
                              "Davomiylik", "Topshirildi", "Oxirgi xato"])
        k.qosh(self.jadval)
        q = QHBoxLayout()
        self.t_eksport = QPushButton("Faylni eksport qilish")
        self.t_belgila = QPushButton("Topshirildi deb belgilash")
        self.t_qayta = QPushButton("Xatoni tozalash (qayta urinish)")
        for w, fn in ((self.t_eksport, self.eksport_bos), (self.t_belgila, self.belgila_bos),
                      (self.t_qayta, self.qayta_bos)):
            w.clicked.connect(fn)
            q.addWidget(w)
        q.addStretch(1)
        k.qosh(q)
        iq = QHBoxLayout()
        self.indeks = QSpinBox()
        self.indeks.setRange(0, 99_999)
        self.indeks.setPrefix("kupyura #")
        self.t_isbot = QPushButton("Merkle isbotini JSON ga eksport")
        self.t_isbot.clicked.connect(self.isbot_bos)
        iq.addWidget(self.indeks)
        iq.addWidget(self.t_isbot)
        iq.addStretch(1)
        k.qosh(iq)
        self.qosh(k)

        o = Karta("Onlayn topshirish (MQTT + AETHER-Q sessiyasi)")
        f = QFormLayout()
        z = self.ctx.z
        self.broker = QLineEdit(z.jurnal.sozlama("broker", "broker.hivemq.com"))
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(int(z.jurnal.sozlama("port", "1883")))
        f.addRow("Broker", self.broker)
        f.addRow("Port", self.port)
        o.qosh(f)
        self.aq = yorliq("" if aetherq_core_bormi() else f"⚠ {AETHERQ_YOQ}.", "ogoh")
        o.qosh(self.aq)
        tq = QHBoxLayout()
        self.t_topshir = QPushButton("Topshirilmaganlarni hozir topshirish")
        self.t_topshir.setObjectName("asosiy")
        self.avto = QCheckBox("Avto-topshirish (fonda, seq tartibida)")
        self.t_toxtat = QPushButton("To'xtatish")
        self.t_topshir.clicked.connect(self.topshir_bos)
        self.avto.toggled.connect(self.avto_ozgardi)
        self.t_toxtat.clicked.connect(self.toxtat_bos)
        tq.addWidget(self.t_topshir)
        tq.addWidget(self.avto)
        tq.addWidget(self.t_toxtat)
        tq.addStretch(1)
        o.qosh(tq)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(400)
        self.log.setFont(mono_shrift(9))
        self.log.setMinimumHeight(140)
        o.qosh(self.log)
        self.qosh(o)
        self.oxiri()
        self._tugmalar()

    def yangila(self) -> None:
        ys = self.ctx.z.jurnal.partiyalar()[::-1]
        tanlangan = tanlangan_kalit(self.jadval)
        jadval_toldir(self.jadval, [[
            y.partiya_id[:12], y.buyurtma_id or "—", f"{y.birinchi_seq}..{y.oxirgi_seq}",
            y.soni, som(y.jami), vaqt(y.zarb_ms), f"{y.davomiylik_ms / 1000:.1f} s",
            vaqt(y.topshirilgan_ms) if y.topshirilgan_ms else "yo'q",
            y.topshirish_xatosi or ""] for y in ys], [y.partiya_id for y in ys])
        if tanlangan:
            for i, y in enumerate(ys):
                if y.partiya_id == tanlangan:
                    self.jadval.selectRow(i)

    def _tanlangan(self):
        pid = tanlangan_kalit(self.jadval)
        if not pid:
            dialog.xato(self, "Partiya", "Avval jadvaldan partiyani tanlang.")
        return pid

    def _tugmalar(self) -> None:
        ish = self.ishchi is not None and self.ishchi.isRunning()
        self.t_topshir.setEnabled(not ish)
        self.t_toxtat.setEnabled(ish)

    @Slot()
    def eksport_bos(self) -> None:
        pid = self._tanlangan()
        if not pid:
            return
        y = self.ctx.z.jurnal.partiya(pid)
        papka = dialog.papka_tanla(self, "Partiya faylini qayerga saqlash?")
        if not papka:
            self.holat("eksport bekor qilindi")
            return
        shutil.copy2(self.ctx.z.partiya_papka / y.fayl, Path(papka) / y.fayl)
        self.holat(f"eksport qilindi: {Path(papka) / y.fayl}")
        dialog.xabar(self, "Eksport", f"{y.fayl} → {papka}\nUni bankka fayl orqali bering, "
                     "keyin «Topshirildi deb belgilash» ni bosing.")

    @Slot()
    def belgila_bos(self) -> None:
        pid = self._tanlangan()
        if not pid:
            return
        if not dialog.tasdiq(self, "Belgilash", "Bank bu partiyani qabul qilganini "
                             "tasdiqlaysizmi?"):
            self.holat("belgilash bekor qilindi")
            return
        self.ctx.z.jurnal.topshirildi(pid, self.ctx.z.soat_ms())
        self.holat(f"partiya {pid[:12]} topshirildi deb belgilandi")
        self.yangila()

    @Slot()
    def qayta_bos(self) -> None:
        pid = self._tanlangan()
        if not pid:
            return
        self.ctx.z.jurnal.topshirish_xatosi(pid, None)
        self.holat(f"partiya {pid[:12]}: xato tozalandi, keyingi urinishda qayta yuboriladi")
        self.yangila()

    @Slot()
    def isbot_bos(self) -> None:
        pid = self._tanlangan()
        if not pid:
            return
        y = self.ctx.z.jurnal.partiya(pid)
        try:
            p = partiya_oqi(self.ctx.z.partiya_papka / y.fayl)
        except FaylXatosi as e:
            dialog.xato(self, "Isbot", str(e))
            return
        i = self.indeks.value()
        if i >= p.soni:
            dialog.xato(self, "Isbot", f"Partiyada {p.soni} ta kupyura bor (0..{p.soni - 1}).")
            return
        q = p.qatorlar[i]
        d = {"format": "AETHER-Q-CBDC-NOTE-PROOF", "version": 1, "batch_id": pid,
             "root": p.ildiz.hex(), "note_count": p.soni, "leaf_index": i,
             "note": {"note_id": q.note_id.hex(), "denomination": q.nominal, "owner": q.egasi,
                      "seq": q.seq, "constraints_hash": q.cheklov_xeshi.hex()},
             "leaf": q.barg().hex(), "proof": [x.hex() for x in isbot_ajrat(q.isbot)],
             "batch_signature": p.imzo.hex(), "total": p.jami, "reserve_lock": p.zaxira_qulfi,
             "minted_ms": p.zarb_ms}
        yol = dialog.fayl_saqla(self, "Isbotni saqlash", f"isbot-{pid[:12]}-{i}.json",
                                "JSON (*.json)")
        if not yol:
            self.holat("isbot eksporti bekor qilindi")
            return
        Path(yol).write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        self.holat(f"isbot saqlandi: {yol}")

    # --- onlayn ------------------------------------------------------------------------

    def _ishga(self, avto: bool) -> bool:
        if not aetherq_core_bormi():
            dialog.xato(self, "Onlayn topshirish", AETHERQ_YOQ)
            self.holat(AETHERQ_YOQ)
            return False
        if self.ctx.z.sertifikat is None:
            dialog.xato(self, "Onlayn topshirish", "Sertifikat yo'q — bank kaliti noma'lum.")
            return False
        if self.ishchi is not None and self.ishchi.isRunning():
            self.holat("topshiruvchi allaqachon ishlayapti")
            return False
        self.ctx.z.jurnal.sozlama_yoz("broker", self.broker.text().strip())
        self.ctx.z.jurnal.sozlama_yoz("port", str(self.port.value()))
        self.ishchi = TopshirishIshchisi(self.ctx.z, self.broker.text().strip(),
                                         self.port.value(), avto)
        self.ishchi.log.connect(self.log_satr)
        self.ishchi.tugadi.connect(self.ish_tugadi)
        self.ishchi.finished.connect(self._tugmalar)
        self.ctx.oqim_qosh(self.ishchi)
        self.ishchi.start()
        self._tugmalar()
        return True

    @Slot()
    def topshir_bos(self) -> None:
        if self._ishga(False):
            self.holat("onlayn topshirish boshlandi")

    @Slot(bool)
    def avto_ozgardi(self, yoq: bool) -> None:
        if yoq:
            if not self._ishga(True):
                self.avto.blockSignals(True)
                self.avto.setChecked(False)
                self.avto.blockSignals(False)
            else:
                self.holat("avto-topshirish yoqildi")
        else:
            self.toxtat()
            self.holat("avto-topshirish o'chirildi")

    @Slot()
    def toxtat_bos(self) -> None:
        self.toxtat()
        self.holat("topshiruvchi to'xtatilmoqda…")

    def toxtat(self) -> None:
        if self.ishchi is not None and self.ishchi.isRunning():
            self.ishchi.toxtat()

    @Slot(str)
    def log_satr(self, s: str) -> None:
        self.log.appendPlainText(s)

    @Slot(str)
    def ish_tugadi(self, holat: str) -> None:
        self.log.appendPlainText(f"— {holat} —")
        self.holat(f"topshirish: {holat}")
        self.avto.blockSignals(True)
        self.avto.setChecked(False)
        self.avto.blockSignals(False)
        self._tugmalar()
        self.yangila()
