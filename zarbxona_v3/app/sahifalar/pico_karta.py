"""4.x — «Imzolovchi (Pico)» kartasi: Pico'ni sozlash, holati, qayta ulash, faylga qaytish.

Pico bilan har bir amal FON oqimida: qurilma tugmani 30 s gacha kutishi mumkin, oyna
qotib qolmasin.
"""

from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QHBoxLayout, QPushButton

from app import dialog
from app.ishchilar import Fonda
from app.vidjetlar import Karta, som, yorliq
from core.ibtido import iz
from core.ombor import OmborXatosi, ombor_urug
from core.pico import protokol as P
from core.pico.qurilma import PicoImzolovchi
from core.pico.ulanish import (PicoSozlama, portlar, sozlama_ochir, sozlama_oqi, sozlama_yoz,
                               tashuvchi_och, ulan)


class PicoKarta(Karta):
    def __init__(self, ctx):
        super().__init__("Imzolovchi — Raspberry Pi Pico (HSM)")
        self.ctx = ctx
        self.ish: Fonda | None = None
        self.matn = yorliq("")
        self.qosh(self.matn)
        self.natija = yorliq("", "xira")
        self.qosh(self.natija)
        q = QHBoxLayout()
        self.t_sozla = QPushButton("Pico'ni sozlash…")
        self.t_holat = QPushButton("Pico holati")
        self.t_ulash = QPushButton("Qayta ulash (PIN)…")
        self.t_qaytish = QPushButton("Fayl kalitiga qaytish…")
        for t, f in ((self.t_sozla, self.sozla_bos), (self.t_holat, self.holat_bos),
                     (self.t_ulash, self.ulash_bos), (self.t_qaytish, self.qaytish_bos)):
            t.clicked.connect(f)
            q.addWidget(t)
        q.addStretch(1)
        self.qosh(q)

    @property
    def pico(self) -> PicoImzolovchi | None:
        imz = self.ctx.z.imz
        return imz if isinstance(imz, PicoImzolovchi) else None

    def yangila(self) -> None:
        p = self.pico
        band = self.ish is not None and self.ish.isRunning()
        for t in (self.t_sozla, self.t_holat, self.t_ulash, self.t_qaytish):
            t.setEnabled(not band)
        self.t_sozla.setVisible(p is None)
        for t in (self.t_holat, self.t_ulash, self.t_qaytish):
            t.setVisible(p is not None)
        if p is None:
            kutilmoqda = self._sozlama()
            self.matn.setText(
                "Hozir: <b>kalit.json</b> — imzo paytida maxfiy kalit kompyuter xotirasida "
                "bo'ladi. Pico'da kalit qurilmadan CHIQMAYDI, har buyurtma Pico tugmasi bilan "
                "tasdiqlanadi va Pico tasdiqlangan summadan ortig'ini imzolamaydi."
                + ("<br><span style='color:#FBBF24'>Pico sozlangan — dasturni qayta oching."
                   "</span>" if kutilmoqda else ""))
            return
        s = p.oxirgi_salom
        qism = [f"<span style='color:#4ADE80'>Pico</span> · kalit izi <code>{iz(p.ochiq_kalit())}"
                f"</code>"]
        if s is not None:
            qism.append(f"qurilma {s.versiya} · seriya <code>{s.seriya.hex()}</code>"
                        + (" · kalit IMPORT qilingan" if s.import_qilingan else
                           " · kalit Pico ichida yaratilgan"))
        qism.append("RP2040: flash himoyalanmagan — Pico'ni seyfda saqlang; haqiqiy pul uchun "
                    "Pico 2 (RP2350).")
        self.matn.setText("<br>".join(qism))

    def _sozlama(self) -> PicoSozlama | None:
        try:
            return sozlama_oqi(self.ctx.z.papka)
        except P.PicoXatosi:
            return None

    def _fonda(self, ish, tayyor) -> None:
        self.ish = Fonda(ish)
        self.ish.natija.connect(tayyor)
        self.ctx.oqim_qosh(self.ish)
        self.ish.start()
        self.yangila()

    # --- sozlash ------------------------------------------------------------------------

    @Slot()
    def sozla_bos(self) -> None:
        z = self.ctx.z
        kalit = z.papka / "kalit.json"
        r = dialog.pico_sozlash(self, portlar(), kalit.exists())
        if r is None:
            self.ctx.holat("Pico sozlanmadi")
            return
        pin = r["pin"]
        if pin != r["pin2"]:
            dialog.xato(self, "Pico", "PIN'lar mos emas.")
            return
        if not P.PIN_MIN <= len(pin.encode("utf-8")) <= P.PIN_MAX:
            dialog.xato(self, "Pico", f"PIN {P.PIN_MIN}..{P.PIN_MAX} belgi bo'lsin. RP2040 "
                        "flash'i himoyalanmagan — uzunroq PIN (yoki ibora) xavfsizroq.")
            return
        urug = None
        if r["rejim"] == "import":
            try:
                urug = bytearray(ombor_urug(kalit, r["parol"]))
            except OmborXatosi as e:
                dialog.xato(self, "Pico", f"kalit.json ochilmadi: {e}")
                return
        port = r["port"]
        kutish = self.ctx.pico_kutish.emit

        def ish():
            pico = ulan(PicoSozlama(port=port), kutish_xabari=kutish)
            try:
                s = pico.salom()
                if s.kalit_bor:
                    raise P.PicoXatosi(P.X_KALIT_BOR, "bu Pico'da kalit allaqachon bor — boshqa "
                                       "profilniki bo'lishi mumkin. Avval uni o'chiring.")
                pk = (pico.kalit_import(pin, bytes(urug)) if urug is not None
                      else pico.kalit_yarat(pin))
                s = pico.salom()
                pico.qulfla()
                return PicoSozlama(port=port, public_key=pk, seriya=s.seriya)
            finally:
                pico.yop()
                if urug is not None:
                    for i in range(len(urug)):
                        urug[i] = 0
        self.ctx.holat("Pico: tugmani bosing…")
        self._fonda(ish, self._sozlandi)

    @Slot(object)
    def _sozlandi(self, r) -> None:
        self.yangila()
        if isinstance(r, Exception):
            self.natija.setText(f"Pico sozlanmadi: {r}")
            self.ctx.holat(f"Pico sozlanmadi: {r}")
            dialog.xato(self, "Pico", str(r))
            return
        z = self.ctx.z
        sozlama_yoz(z.papka, r)
        yangi = r.public_key != z.pk
        self.natija.setText(f"Pico sozlandi · seriya {r.seriya.hex()} · iz {iz(r.public_key)}")
        self.ctx.holat("Pico sozlandi — dasturni qayta oching")
        dialog.xabar(self, "Pico sozlandi", (
            f"Pico kalit izi: {iz(r.public_key)}\n\n"
            + ("Bu YANGI kalit: bankdan shu kalitga yangi sertifikat oling (ochiq kalitni "
               "eksport qiling). Eski sertifikat bu kalit bilan ishlamaydi.\n\n" if yangi else
               "Kalit o'sha — sertifikat o'zgarmaydi. kalit.json endi faqat shifrlangan "
               "ZAXIRA: uni kompyuterdan olib, seyfda saqlang.\n\n")
            + "Dasturni yoping va qayta oching: kirishda Pico PIN'i so'raladi."))
        self.yangila()

    # --- Pico rejimidagi amallar --------------------------------------------------------

    @Slot()
    def holat_bos(self) -> None:
        p = self.pico
        if p is None:
            return

        def ish():
            return p.salom(), p.holat()
        self._fonda(ish, self._holat_keldi)

    @Slot(object)
    def _holat_keldi(self, r) -> None:
        self.yangila()
        if isinstance(r, Exception):
            self.natija.setText(f"Pico javob bermadi: {r}")
            self.ctx.holat(f"Pico: {r}")
            return
        s, h = r
        self.natija.setText(
            f"{'ochiq' if s.ochiq else 'QULFLANGAN'} · PIN urinishlari {s.qolgan_urinish} · "
            + (f"ruxsat faol: qolgan {som(h.byudjet)}, {h.qolgan_s // 60} daqiqa"
               if h.ruxsat_faol else "faol ruxsat yo'q")
            + f" · ulangandan beri {h.imzolar} imzo")
        self.ctx.holat("Pico holati yangilandi")
        self.yangila()

    @Slot()
    def ulash_bos(self) -> None:
        p = self.pico
        s = self._sozlama()
        if p is None or s is None:
            return
        pin = dialog.parol(self, "Pico", "Pico'ni USB'ga qayta ulang va PIN kiriting:")
        if not pin:
            self.ctx.holat("qayta ulash bekor qilindi")
            return

        def ish():
            p.qayta_ulan(tashuvchi_och(s.port))
            return p.pin_och(pin)
        self._fonda(ish, self._ulandi)

    @Slot(object)
    def _ulandi(self, r) -> None:
        if isinstance(r, Exception):
            matn = str(r)
            if isinstance(r, P.PicoXatosi) and r.qoshimcha:
                matn += f" — qolgan urinish: {r.qoshimcha[0][0]}"
            self.natija.setText(f"Pico ulanmadi: {matn}")
            dialog.xato(self, "Pico", matn)
        else:
            self.natija.setText("Pico qayta ulandi va ochildi")
            self.ctx.holat("Pico qayta ulandi — pauzadagi buyurtmani davom ettiring")
        self.yangila()

    @Slot()
    def qaytish_bos(self) -> None:
        z = self.ctx.z
        if not (z.papka / "kalit.json").exists():
            dialog.xato(self, "Pico", "Profilda kalit.json yo'q: kalit Pico ichida yaratilgan va "
                        "uni EKSPORT qilib bo'lmaydi. Fayl kalitiga qaytish — yangi kalit va "
                        "yangi sertifikat degani.")
            return
        if not dialog.tasdiq(self, "Pico", "Keyingi kirishdan boshlab kalit.json (parol) "
                             "ishlatilsinmi? Pico'dagi kalit o'chirilmaydi."):
            return
        sozlama_ochir(z.papka)
        self.ctx.holat("keyingi kirishda kalit.json ishlatiladi — dasturni qayta oching")
        dialog.xabar(self, "Pico", "Dasturni qayta oching: kirishda kalit.json paroli so'raladi.")
