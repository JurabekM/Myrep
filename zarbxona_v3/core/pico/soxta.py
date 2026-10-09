"""Soxta Pico — kompyuterda ishlaydigan qurilma modeli.

Ichki dastur (`firmware/pico_hsm/`) bilan bir xil qoidalar: testlar, apparatsiz demo va
ichki dasturning o'zini solishtirish uchun ETALON. Kalit «flash»i — JSON fayl (yoki
xotira); tugma — `tugma(matn) -> "ha" | "rad" | "yoq"` funksiyasi.

HAQIQIY HIMOYA EMAS: kalit shu kompyuterning o'zida turadi.
"""

from __future__ import annotations

import json
import os
import queue
import secrets
import threading
import time
from collections.abc import Callable
from pathlib import Path

from ..ibtido import imzola, kalit_urugdan, ochiq_kalit
from ..konstanta import ML_DSA_PK_UZ, PARTIYA_ID_UZ, SERT_ID_UZ
from ..partiya import imzo_xabari
from ..protokol import mint_auth_xesh
from ..zanjir import bosh_xabari
from . import protokol as P
from . import saqlash as S

QURILMA_VERSIYASI = "soxta-pico 1.0"
IMKONIYATLAR = 0x01          # bit0: IMZO_PARTIYA/BOSH/MINT_AUTH (ML-DSA-65)

Tugma = Callable[[str], str]


def avto_tugma(kechikish: float = 0.0, javob: str = "ha") -> Tugma:
    def bos(_matn: str) -> str:
        if kechikish:
            time.sleep(kechikish)
        return javob
    return bos


class SoxtaPico:
    def __init__(self, flash: Path | None = None, *, tugma: Tugma | None = None,
                 soat: Callable[[], float] = time.monotonic, seriya: bytes | None = None,
                 pin_iter: int = S.PIN_ITER):
        self.flash_yoli = Path(flash) if flash else None
        self.tugma = tugma or avto_tugma()
        self.soat = soat
        self.pin_iter = pin_iter
        self.yozuv: S.KalitYozuvi | None = None
        self.seriya = seriya or secrets.token_bytes(P.SERIYA_UZ)
        self._flash_oqi()
        # RAM — quvvat uzilsa yo'qoladi
        self.urug: bytearray | None = None
        self.sk = None
        self.ruxsat: dict | None = None
        self.oxirgi_tartib = -1
        self.imzolar = 0
        self.flash_yozuvlari = 0      # flash yeyilishini kuzatish uchun

    # --- «flash» ----------------------------------------------------------------------

    def _flash_oqi(self) -> None:
        if not (self.flash_yoli and self.flash_yoli.exists()):
            return
        d = json.loads(self.flash_yoli.read_text(encoding="utf-8"))
        self.seriya = bytes.fromhex(d["seriya"])
        if d.get("kalit"):
            k = d["kalit"]
            self.yozuv = S.KalitYozuvi(bytes.fromhex(k["salt"]), bytes.fromhex(k["ct"]),
                                       bytes.fromhex(k["tag"]), k["urinish"], k["import"])

    def _flash_yoz(self) -> None:
        self.flash_yozuvlari += 1
        if not self.flash_yoli:
            return
        y = self.yozuv
        d = {"seriya": self.seriya.hex(), "kalit": None if y is None else {
            "salt": y.salt.hex(), "ct": y.ct.hex(), "tag": y.tag.hex(), "urinish": y.urinish,
            "import": y.import_}}
        self.flash_yoli.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.flash_yoli.with_name(self.flash_yoli.name + ".tmp")
        tmp.write_text(json.dumps(d), encoding="utf-8")
        os.replace(tmp, self.flash_yoli)

    # --- holat ------------------------------------------------------------------------

    def quvvat_uzildi(self) -> None:
        """USB sug'urib olindi: RAM tozalanadi, flash qoladi."""
        self._qulfla()

    def _qulfla(self) -> None:
        if self.urug is not None:
            for i in range(len(self.urug)):
                self.urug[i] = 0
        self.urug, self.sk, self.ruxsat, self.oxirgi_tartib = None, None, None, -1

    def _ruxsat_faol(self) -> bool:
        return self.ruxsat is not None and self.soat() < self.ruxsat["tugash"]

    def _holat_bitlari(self) -> int:
        h = 0
        if self.yozuv:
            h |= P.H_KALIT_BOR | (P.H_IMPORT if self.yozuv.import_ else 0)
        if self.sk is not None:
            h |= P.H_OCHIQ
        if self._ruxsat_faol():
            h |= P.H_RUXSAT
        return h

    def _ochiq(self, sk_kerak: bool = True) -> None:
        if self.yozuv is None:
            raise P.PicoXatosi(P.X_KALIT_YOQ)
        if sk_kerak and self.sk is None:
            raise P.PicoXatosi(P.X_QULFLANGAN)

    def _ochil(self, urug: bytes) -> None:
        self._qulfla()
        self.urug = bytearray(urug)
        self.sk = kalit_urugdan(bytes(self.urug))

    # --- tugma ------------------------------------------------------------------------

    def _tasdiq(self, matn: str, xabar_ber: Callable[[str], None]) -> None:
        xabar_ber(matn)
        j = self.tugma(matn)
        if j == "rad":
            raise P.PicoXatosi(P.X_RAD)
        if j != "ha":
            raise P.PicoXatosi(P.X_TUGMA_YOQ)

    # --- buyruqlar --------------------------------------------------------------------

    def bajar(self, r: P.Ramka, xabar_ber: Callable[[str], None]) -> bytes:
        """Bitta buyruq → javob yuki. Xato — xato yuki (istisno tashlanmaydi)."""
        try:
            f = P.ajrat(r.yuk)
            ishlov = self._ISHLOV.get(r.kod)
            if ishlov is None:
                raise P.PicoXatosi(P.X_NOMALUM)
            return P.javob_yuki(P.OK, *ishlov(self, f, xabar_ber))
        except P.PicoXatosi as e:
            return P.xato_yuki(e.kod, str(e), *e.qoshimcha)
        except (P.RamkaXatosi, ValueError, IndexError):
            return P.xato_yuki(P.X_FORMAT)

    @staticmethod
    def _soni(f: list[bytes], n: int) -> None:
        if len(f) != n:
            raise P.RamkaXatosi("maydonlar soni")

    @staticmethod
    def _pin(b: bytes) -> bytes:
        if not P.PIN_MIN <= len(b) <= P.PIN_MAX:
            raise P.PicoXatosi(P.X_FORMAT, f"PIN {P.PIN_MIN}..{P.PIN_MAX} bayt bo'lsin")
        return b

    def _salom(self, f, _x):
        self._soni(f, 0)
        pk = ochiq_kalit(self.sk) if self.sk is not None else b""
        qolgan = P.MAX_URINISH - self.yozuv.urinish if self.yozuv else P.MAX_URINISH
        return (QURILMA_VERSIYASI.encode(), P.u32(IMKONIYATLAR), P.u8(self._holat_bitlari()),
                pk, self.seriya, P.u8(qolgan))

    def _kalit_ornat(self, pin: bytes, urug: bytes, import_: bool) -> list[bytes]:
        y = S.shifrla(urug, pin, secrets.token_bytes(S.SALT_UZ), self.pin_iter)
        y.import_ = import_
        self.yozuv = y
        self._flash_yoz()
        self._ochil(urug)
        return [ochiq_kalit(self.sk)]

    def _kalit_yarat(self, f, x):
        self._soni(f, 2)
        pin = self._pin(f[0])
        if len(f[1]) != P.ENTROPIYA_UZ:
            raise P.RamkaXatosi("entropiya")
        if self.yozuv is not None:
            raise P.PicoXatosi(P.X_KALIT_BOR)
        self._tasdiq("YANGI KALIT yaratish", x)
        return self._kalit_ornat(pin, S.yangi_urug(secrets.token_bytes(32), f[1]), False)

    def _kalit_import(self, f, x):
        self._soni(f, 2)
        pin = self._pin(f[0])
        if len(f[1]) != S.URUG_UZ:
            raise P.RamkaXatosi("urug'")
        if self.yozuv is not None:
            raise P.PicoXatosi(P.X_KALIT_BOR)
        self._tasdiq("Mavjud kalitni IMPORT qilish", x)
        return self._kalit_ornat(pin, f[1], True)

    def _pin_tekshir(self, pin: bytes) -> bytes:
        """Urinish hisobi tekshiruvdan OLDIN flash'ga yoziladi: quvvatni uzib hisobni
        chetlab o'tib bo'lmaydi."""
        y = self.yozuv
        assert y is not None
        y.urinish += 1
        self._flash_yoz()
        urug = S.och(y, pin, self.pin_iter)
        if urug is None:
            if y.urinish >= P.MAX_URINISH:
                self.yozuv = None
                self._qulfla()
                self._flash_yoz()
                raise P.PicoXatosi(P.X_OCHIRILDI)
            raise P.PicoXatosi(P.X_PIN, "", [P.u8(P.MAX_URINISH - y.urinish)])
        y.urinish = 0
        self._flash_yoz()
        return urug

    def _pin_och(self, f, _x):
        self._soni(f, 1)
        pin = self._pin(f[0])
        self._ochiq(sk_kerak=False)
        self._ochil(self._pin_tekshir(pin))
        return []

    def _qulfla_b(self, f, _x):
        self._soni(f, 0)
        self._qulfla()
        return []

    def _kalit_ochir(self, f, x):
        self._soni(f, 1)
        pin = self._pin(f[0])
        self._ochiq(sk_kerak=False)
        self._pin_tekshir(pin)
        self._tasdiq("Kalitni O'CHIRISH", x)
        self.yozuv = None
        self._qulfla()
        self._flash_yoz()
        return []

    def _ruxsat_b(self, f, x):
        self._soni(f, 3)
        self._ochiq()
        bid = f[0]
        summa, muddat = P.son(f[1], 16), P.son(f[2], 4)
        if not bid or len(bid) > P.MAX_BUYURTMA_ID_UZ or summa <= 0 \
                or not 1 <= muddat <= P.MAX_RUXSAT_S:
            raise P.RamkaXatosi("ruxsat maydonlari")
        self._tasdiq(f"RUXSAT: buyurtma {bid.decode('utf-8', 'replace')} · {summa} so'm", x)
        self.ruxsat = {"byudjet": summa, "tugash": self.soat() + muddat, "buyurtma": bid}
        return []

    def _holat(self, f, _x):
        self._soni(f, 0)
        faol = self._ruxsat_faol()
        byudjet = self.ruxsat["byudjet"] if faol else 0
        qolgan = int(self.ruxsat["tugash"] - self.soat()) if faol else 0
        return (P.u8(self._holat_bitlari()), P.u128(byudjet), P.u32(max(0, qolgan)),
                P.u32(self.imzolar))

    def _imzo(self, xabar: bytes) -> list[bytes]:
        self.imzolar += 1
        return [imzola(self.sk, xabar)]

    def _imzo_partiya(self, f, _x):
        self._soni(f, 6)
        self._ochiq()
        ildiz, pid = f[0], f[1]
        soni, jami, zarb_ms = P.son(f[2], 8), P.son(f[3], 16), P.son(f[5], 8)
        qulf = f[4]
        if len(ildiz) != 32 or len(pid) != PARTIYA_ID_UZ or soni < 1 or jami < 1 \
                or not qulf or len(qulf) > P.MAX_QULF_UZ:
            raise P.RamkaXatosi("partiya maydonlari")
        if not self._ruxsat_faol():
            raise P.PicoXatosi(P.X_RUXSAT_YOQ)
        if jami > self.ruxsat["byudjet"]:
            raise P.PicoXatosi(P.X_BYUDJET, "", [P.u128(self.ruxsat["byudjet"])])
        self.ruxsat["byudjet"] -= jami
        return self._imzo(imzo_xabari(ildiz, pid, soni, jami, qulf.decode("utf-8"), zarb_ms))

    def _imzo_bosh(self, f, x):
        self._soni(f, 2)
        self._ochiq()
        tartib = P.son(f[0], 8)
        if len(f[1]) != 32:
            raise P.RamkaXatosi("xesh")
        if tartib < self.oxirgi_tartib:
            raise P.PicoXatosi(P.X_TARTIB)
        if not self._ruxsat_faol():
            self._tasdiq(f"Jurnal boshi #{tartib} (ruxsatsiz)", x)
        self.oxirgi_tartib = tartib
        return self._imzo(bosh_xabari(tartib, f[1]))

    def _imzo_mint_auth(self, f, _x):
        self._soni(f, 3)
        self._ochiq()
        if len(f[0]) != ML_DSA_PK_UZ or not 1 <= len(f[1]) <= P.MAX_CHAQIRIQ_UZ \
                or len(f[2]) != SERT_ID_UZ:
            raise P.RamkaXatosi("mint_auth maydonlari")
        return self._imzo(mint_auth_xesh(f[0], f[1], f[2]))

    _ISHLOV = {P.SALOM: _salom, P.KALIT_YARAT: _kalit_yarat, P.KALIT_IMPORT: _kalit_import,
               P.PIN_OCH: _pin_och, P.QULFLA: _qulfla_b, P.RUXSAT: _ruxsat_b,
               P.HOLAT: _holat, P.KALIT_OCHIR: _kalit_ochir, P.IMZO_PARTIYA: _imzo_partiya,
               P.IMZO_BOSH: _imzo_bosh, P.IMZO_MINT_AUTH: _imzo_mint_auth}


class SoxtaTashuvchi:
    """`SoxtaPico` ni bayt oqimi orqasiga qo'yadi — xuddi USB serial kabi. Qurilma o'z
    oqimida ishlaydi: tugma kutilayotganda xost KUTMOQDA xabarini oladi."""

    nomi = "soxta-pico"

    def __init__(self, qurilma: SoxtaPico):
        self.q = qurilma
        self._kirish: queue.Queue[bytes | None] = queue.Queue()
        self._chiqish = bytearray()
        self._shart = threading.Condition()
        self._oquvchi = P.Oquvchi()
        self.uzilgan = False
        self._ip = threading.Thread(target=self._ishla, name="soxta-pico", daemon=True)
        self._ip.start()

    def _chiqar(self, b: bytes) -> None:
        with self._shart:
            self._chiqish += b
            self._shart.notify_all()

    def _ishla(self) -> None:
        while True:
            d = self._kirish.get()
            if d is None:
                return
            n0 = self._oquvchi.buzilgan
            for r in self._oquvchi.qosh(d):
                def xabar(m: str, seq=r.seq) -> None:
                    self._chiqar(P.Ramka(P.KUTMOQDA, seq, P.maydonlar(m.encode())).bayt())
                yuk = self.q.bajar(r, xabar)
                self._chiqar(P.Ramka(r.kod | P.JAVOB_BIT, r.seq, yuk).bayt())
            if self._oquvchi.buzilgan > n0:
                self._chiqar(P.Ramka(P.XATO_RAMKA, 0, P.xato_yuki(P.X_FORMAT)).bayt())

    def yoz(self, b: bytes) -> None:
        if self.uzilgan:
            raise OSError("soxta Pico uzilgan")
        self._kirish.put(bytes(b))

    def oqi(self, kutish: float) -> bytes:
        oxiri = time.monotonic() + kutish
        with self._shart:
            while not self._chiqish:
                if self.uzilgan:
                    raise OSError("soxta Pico uzilgan")
                q = oxiri - time.monotonic()
                if q <= 0:
                    return b""
                self._shart.wait(q)
            b = bytes(self._chiqish)
            self._chiqish.clear()
            return b

    def tozala(self) -> None:
        with self._shart:
            self._chiqish.clear()

    def sugur(self) -> None:
        """USB'ni sug'urish: aloqa uziladi, qurilma RAM'i tozalanadi."""
        self.uzilgan = True
        self.q.quvvat_uzildi()
        with self._shart:
            self._shart.notify_all()

    def yop(self) -> None:
        self._kirish.put(None)
