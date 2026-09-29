"""Fon ishchilari (QThread). Har oqim o'z SQLite ulanishini O'ZI ochadi (§16.5).

Monitor satrlari to'planib yuboriladi: ≥ 0,15 s oraliqda, bir signalda ≤ 40 satr;
progress signali ≤ 5/s (§16.3) — aks holda oyna qotadi.
"""

from __future__ import annotations

import threading
import time
import traceback
from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from core.buyurtma import BajarishNatijasi, Zarbxona
from core.kanal import MqttKanal
from core.sessiya import AetherQFabrika
from core.surat import Surat
from core.topshirish import AvtoTopshiruvchi, Mijoz

SATR_ORALIQ = 0.15
SATR_MAX = 40
PROGRESS_ORALIQ = 0.2
OLCHASH_KUPYURA = 50


def _soat() -> str:
    return time.strftime("%H:%M:%S")


class ZarbIshchisi(QThread):
    satrlar = Signal(list)
    jarayon = Signal(dict)
    tugadi = Signal(object)

    def __init__(self, z: Zarbxona, buyurtma_id: str, surat: Surat | None = None):
        super().__init__()
        self.z_asl, self.buyurtma_id, self.surat = z, buyurtma_id, surat
        self._toxta = threading.Event()
        self._pauza = threading.Event()
        self._qulf = threading.Lock()
        self._bufer: list[str] = []
        self._oxirgi_satr = 0.0
        self._oxirgi_progress = 0.0
        self._asos = 0
        self._jami = 0
        self._p_soni = 0
        self._p_bajarildi = 0
        self._bosh_devor = 0.0
        self._bosh_cpu = 0.0
        self._bajarildi_sessiya = 0
        self._ish_cpu = 0.0
        self._olchangan_ms: float | None = None
        self._oxirgi_thread = 0.0

    # --- boshqaruv (UI oqimidan) -----------------------------------------------

    def toxtat(self) -> None:
        self._toxta.set()
        self._pauza.clear()

    def pauza(self, yoq: bool) -> None:
        if yoq:
            self._pauza.set()
        else:
            self._pauza.clear()

    def satr_qosh(self, s: str) -> None:
        """UI oqimidan: satr monitorga ishchi buferi ORQALI tushadi — tartib buzilmaydi
        (bufer hali chiqarilmagan kupyura satrlari PAUZA dan oldin turadi)."""
        with self._qulf:
            self._bufer.append(s)

    @property
    def pauzada_mi(self) -> bool:
        return self._pauza.is_set()

    # --- oqim ichida -----------------------------------------------------------

    def _satr(self, s: str) -> None:
        with self._qulf:
            self._bufer.append(s)
        self._chiqar()

    def _chiqar(self, majburiy: bool = False) -> None:
        hozir = time.monotonic()
        if not majburiy and hozir - self._oxirgi_satr < SATR_ORALIQ:
            return
        with self._qulf:
            b, self._bufer = self._bufer, []
        if not b:
            return
        if len(b) > SATR_MAX:
            b = [f"… ({len(b) - (SATR_MAX - 1)} satr o'tkazib yuborildi)"] + b[-(SATR_MAX - 1):]
        self._oxirgi_satr = hozir
        self.satrlar.emit(b)

    def _progress(self, majburiy: bool = False) -> None:
        hozir = time.monotonic()
        if not majburiy and hozir - self._oxirgi_progress < PROGRESS_ORALIQ:
            return
        self._oxirgi_progress = hozir
        devor = hozir - self._bosh_devor
        n = self._bajarildi_sessiya
        tezlik = n / devor if devor > 0 and n else 0.0
        cpu = (time.process_time() - self._bosh_cpu) / devor if devor > 0.5 else None
        qolgan_k = self._jami - (self._asos + self._p_bajarildi)
        self.jarayon.emit({
            "p_bajarildi": self._p_bajarildi, "p_soni": self._p_soni,
            "b_bajarildi": self._asos + self._p_bajarildi, "b_jami": self._jami,
            "tezlik": tezlik, "cpu": cpu, "pauza": self._pauza.is_set(),
            "qolgan_s": qolgan_k / tezlik if tezlik > 0 else None,
            "kupyura_ms": self._olchangan_ms,
        })

    def _kuzatuv(self, q, i: int, soni: int) -> None:
        t = time.thread_time()
        self._ish_cpu += t - self._oxirgi_thread
        self._oxirgi_thread = t
        self._p_bajarildi = i + 1
        self._bajarildi_sessiya += 1
        if self._olchangan_ms is None and self._bajarildi_sessiya >= OLCHASH_KUPYURA:
            self._olchangan_ms = self._ish_cpu * 1000 / self._bajarildi_sessiya
        self._satr(f"[{_soat()}] #{q.seq:<8} {q.nominal:>5} so'm   {q.note_id.hex()[:24]}…"
                   f"  muhr {len(q.muhr)} B  ✓")
        self._progress(i + 1 == soni)

    def _tanaffus(self, x: float) -> None:
        self._satr(f"[{_soat()}] — sovutish rejimi ({x:.1f} soniya) —")

    def _pauzada(self) -> bool:
        # Ritm har 0,1 s da so'raydi — to'plangan satrlar shu yerda ham chiqadi
        self._chiqar()
        self._progress()
        self._oxirgi_thread = time.thread_time()   # uyqu CPU o'lchoviga kirmasin
        return self._pauza.is_set()

    def _hodisa(self, tur: str, d: dict) -> None:
        if tur == "partiya_boshlandi":
            self._asos, self._jami, self._p_soni = d["bajarilgan"], d["jami_kupyura"], d["soni"]
            self._p_bajarildi = 0
            s = d["birinchi_seq"]
            self._satr(f"[{_soat()}] partiya boshlandi · {d['soni']} kupyura · "
                       f"seq {s}..{s + d['soni'] - 1}")
        elif tur == "partiya_yopildi":
            p = d["partiya"]
            self._satr(f"[{_soat()}] partiya yopildi · Merkle ildizi {p.ildiz.hex()[:12]}… · "
                       f"imzo qo'yildi · {p.davomiylik_s:.0f} soniya · {d['fayl']}")
        elif tur == "toxtatildi":
            self._satr(f"[{_soat()}] TO'XTATILDI — partiya yozilmadi")
        elif tur == "tekshiruv_xato":
            self._satr(f"[{_soat()}] O'Z TEKSHIRUVI XATO — fayl yozilmadi")
        self._progress(True)

    def run(self) -> None:
        self._bosh_devor = time.monotonic()
        self._bosh_cpu = time.process_time()
        self._oxirgi_thread = time.thread_time()
        z = None
        natija: object
        try:
            z = self.z_asl.oqim_nusxasi()
            natija = z.buyurtmani_bajar(
                self.buyurtma_id, surat=self.surat, kuzatuv=self._kuzatuv,
                bekormi=self._toxta.is_set, pauzada=self._pauzada, tanaffus=self._tanaffus,
                hodisa=self._hodisa)
        except Exception as e:  # noqa: BLE001
            natija = BajarishNatijasi("xato", f"{e}\n{traceback.format_exc(limit=3)}")
        finally:
            if z is not None:
                z.yop()
        self._chiqar(True)
        self._progress(True)
        self.tugadi.emit(natija)


class TopshirishIshchisi(QThread):
    """Onlayn topshirish: `avto=False` — bitta aylanish; `True` — to'xtatilguncha."""

    log = Signal(str)
    tugadi = Signal(str)

    def __init__(self, z: Zarbxona, broker: str, port: int, avto: bool,
                 mijoz_yarat: Callable[[], Mijoz] | None = None):
        """`mijoz_yarat` berilsa (DEMO bank) — MQTT va aetherq_core o'rniga shu."""
        super().__init__()
        self.z_asl, self.broker, self.port, self.avto = z, broker, port, avto
        self.mijoz_yarat = mijoz_yarat
        self._toxta = threading.Event()

    def toxtat(self) -> None:
        self._toxta.set()

    def _mijoz(self) -> Mijoz:
        if self.mijoz_yarat is not None:
            return self.mijoz_yarat()
        sert = self.z_asl.sertifikat
        fabrika = AetherQFabrika()
        kanal = MqttKanal(self.broker, self.port, sert.bank_public_key)
        self.log.emit(f"broker {self.broker}:{self.port} · sessiya {kanal.sessiya_id}")
        return Mijoz(kanal, fabrika, sert, self.z_asl.sk, log=self.log.emit)

    def run(self) -> None:
        z = None
        holat = "xato"
        try:
            z = self.z_asl.oqim_nusxasi()
            a = AvtoTopshiruvchi(z.jurnal, z.partiya_papka, self._mijoz, log=self.log.emit)
            if self.avto:
                a.ishlat(self._toxta.is_set)
                holat = "avto-topshirish to'xtatildi"
            else:
                holat = a.bir_aylanish(bekormi=self._toxta.is_set)
        except Exception as e:  # noqa: BLE001
            holat = f"xato: {e}"
        finally:
            if z is not None:
                z.yop()
        self.tugadi.emit(holat)


class FonIsh(QThread):
    """Umumiy: `ish(z_nusxa)` fon oqimida, natija signal bilan."""

    natija = Signal(object)

    def __init__(self, z: Zarbxona, ish: Callable[[Zarbxona], object]):
        super().__init__()
        self.z_asl, self.ish = z, ish

    def run(self) -> None:
        z = None
        try:
            z = self.z_asl.oqim_nusxasi()
            r = self.ish(z)
        except Exception as e:  # noqa: BLE001
            r = e
        finally:
            if z is not None:
                z.yop()
        self.natija.emit(r)
