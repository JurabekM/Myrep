"""Xost tomoni: Pico bilan gaplashadigan imzolovchi (`core.imzolovchi.Imzolovchi`).

Bir nechta oqim (zarb, topshirish, GUI) bir qurilmani ishlatadi — har bir so'rov qulf
ostida bajariladi. Qurilma qaytargan HAR BIR imzo shu yerning o'zida ochiq kalit bilan
tekshiriladi: buzuq yoki almashtirilgan qurilma yaroqsiz imzoni jim o'tkazib yubormaydi.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from ..ibtido import imzo_togri, iz
from ..partiya import imzo_xabari
from ..protokol import mint_auth_xesh
from ..zanjir import bosh_xabari
from . import protokol as P

ODDIY_KUTISH_S = 30.0          # RP2040'da ML-DSA imzosi va PIN KDF sekin bo'lishi mumkin
TUGMA_ZAXIRA_S = 5.0
DEFAULT_RUXSAT_S = 12 * 3600


class Tashuvchi(Protocol):
    nomi: str

    def yoz(self, b: bytes) -> None: ...
    def oqi(self, kutish: float) -> bytes: ...
    def tozala(self) -> None: ...
    def yop(self) -> None: ...


@dataclass
class PicoSalom:
    versiya: str
    imkoniyatlar: int
    holat: int
    pk: bytes
    seriya: bytes
    qolgan_urinish: int

    @property
    def kalit_bor(self) -> bool:
        return bool(self.holat & P.H_KALIT_BOR)

    @property
    def ochiq(self) -> bool:
        return bool(self.holat & P.H_OCHIQ)

    @property
    def import_qilingan(self) -> bool:
        return bool(self.holat & P.H_IMPORT)


@dataclass
class PicoHolati:
    holat: int
    byudjet: int
    qolgan_s: int
    imzolar: int

    @property
    def ruxsat_faol(self) -> bool:
        return bool(self.holat & P.H_RUXSAT)


class PicoImzolovchi:
    """`kutish_xabari(matn)` — qurilma tugmani kutayotganda chaqiriladi (GUI/CLI ko'rsatadi)."""

    def __init__(self, tashuvchi: Tashuvchi, *, kutilgan_pk: bytes | None = None,
                 kutish_xabari: Callable[[str], None] | None = None,
                 ruxsat_muddati_s: int = DEFAULT_RUXSAT_S, oddiy_kutish: float = ODDIY_KUTISH_S):
        self.t = tashuvchi
        self.nomi = getattr(tashuvchi, "nomi", "pico")
        self.kutish_xabari = kutish_xabari      # (matn | None) -> None
        self._kutildi = False
        self.ruxsat_muddati_s = ruxsat_muddati_s
        self.oddiy_kutish = oddiy_kutish
        self._qulf = threading.RLock()
        self._seq = secrets.randbelow(0xFFFF) + 1
        self._oquvchi = P.Oquvchi()
        self._pk: bytes | None = None
        self.kutilgan_pk = kutilgan_pk
        self.oxirgi_salom: PicoSalom | None = None

    # --- transport ----------------------------------------------------------------------

    def _keyingi_seq(self) -> int:
        self._seq = self._seq % 0xFFFF + 1          # 1..65535, 0 — xato ramkalari uchun
        return self._seq

    def sorov(self, kod: int, *maydon: bytes) -> list[bytes]:
        """Buyruq yuboradi, javobni kutadi. OK — maydonlar; aks holda `PicoXatosi`.
        Qurilma tugmani kutgan bo'lsa, oxirida `kutish_xabari(None)` — kutish tugadi."""
        with self._qulf:
            self._kutildi = False
            try:
                return self._sorov(kod, maydon)
            finally:
                if self._kutildi and self.kutish_xabari:
                    self.kutish_xabari(None)

    def _sorov(self, kod: int, maydon: tuple[bytes, ...]) -> list[bytes]:
        seq = self._keyingi_seq()
        try:
            self.t.tozala()
            self._oquvchi = P.Oquvchi()
            self.t.yoz(P.Ramka(kod, seq, P.maydonlar(*maydon)).bayt())
            oxiri = time.monotonic() + self.oddiy_kutish
            while True:
                qoldi = oxiri - time.monotonic()
                if qoldi <= 0:
                    raise P.PicoXatosi(P.X_ALOQA, f"Pico javob bermadi "
                                                  f"({P.BUYRUQ_NOMI.get(kod, kod)})")
                for r in self._oquvchi.qosh(self.t.oqi(min(qoldi, 0.25))):
                    if r.kod == P.XATO_RAMKA:
                        raise P.PicoXatosi(P.X_ALOQA, "Pico buzilgan ramka oldi (USB shovqini?)")
                    if r.seq != seq:
                        continue                     # eski so'rovning kech javobi
                    if r.kod == P.KUTMOQDA:
                        matn = _matn(r.yuk)
                        self._kutildi = True
                        if self.kutish_xabari:
                            self.kutish_xabari(matn)
                        oxiri = max(oxiri, time.monotonic() + P.TUGMA_KUTISH_S
                                    + TUGMA_ZAXIRA_S + self.oddiy_kutish)
                        continue
                    if r.kod != kod | P.JAVOB_BIT:
                        raise P.PicoXatosi(P.X_ALOQA, f"kutilmagan javob kodi {r.kod:#x}")
                    return _javob(r.yuk)
        except OSError as e:
            raise P.PicoXatosi(P.X_ALOQA, f"Pico bilan aloqa uzildi: {e}") from e

    def qayta_ulan(self, tashuvchi: Tashuvchi) -> None:
        """USB qayta ulanganda: yangi port. Qurilma qulflangan bo'ladi — keyin `pin_och`."""
        with self._qulf:
            try:
                self.t.yop()
            except OSError:
                pass
            self.t = tashuvchi

    def yop(self) -> None:
        with self._qulf:
            try:
                self.t.yop()
            except OSError:
                pass

    # --- boshqaruv buyruqlari -----------------------------------------------------------

    def salom(self) -> PicoSalom:
        f = self.sorov(P.SALOM)
        if len(f) != 6:
            raise P.PicoXatosi(P.X_ALOQA, "SALOM javobi buzilgan")
        s = PicoSalom(f[0].decode("utf-8", "replace"), P.son(f[1], 4), P.son(f[2], 1), f[3],
                      f[4], P.son(f[5], 1))
        self.oxirgi_salom = s
        if s.pk:
            self._pk_tekshir(s.pk)
        return s

    def _pk_tekshir(self, pk: bytes) -> None:
        if self.kutilgan_pk is not None and pk != self.kutilgan_pk:
            raise P.PicoXatosi(P.X_ALOQA, f"bu BOSHQA Pico: kalit izi {iz(pk)}, kutilgan "
                                          f"{iz(self.kutilgan_pk)}")
        self._pk = pk

    def kalit_yarat(self, pin: str) -> bytes:
        (pk,) = self.sorov(P.KALIT_YARAT, pin.encode("utf-8"), secrets.token_bytes(32))
        self._pk = pk
        return pk

    def kalit_import(self, pin: str, urug: bytes) -> bytes:
        (pk,) = self.sorov(P.KALIT_IMPORT, pin.encode("utf-8"), bytes(urug))
        self._pk = pk
        return pk

    def pin_och(self, pin: str) -> bytes:
        self.sorov(P.PIN_OCH, pin.encode("utf-8"))
        s = self.salom()
        if not s.pk:
            raise P.PicoXatosi(P.X_ALOQA, "PIN qabul qilindi, lekin ochiq kalit kelmadi")
        return s.pk

    def qulfla(self) -> None:
        self.sorov(P.QULFLA)

    def kalit_ochir(self, pin: str) -> None:
        self.sorov(P.KALIT_OCHIR, pin.encode("utf-8"))
        self._pk = None

    def holat(self) -> PicoHolati:
        f = self.sorov(P.HOLAT)
        return PicoHolati(P.son(f[0], 1), P.son(f[1], 16), P.son(f[2], 4), P.son(f[3], 4))

    # --- Imzolovchi ---------------------------------------------------------------------

    def ochiq_kalit(self) -> bytes:
        if self._pk is None:
            s = self.salom()
            if not s.pk:
                raise P.PicoXatosi(P.X_QULFLANGAN if s.kalit_bor else P.X_KALIT_YOQ)
        assert self._pk is not None
        return self._pk

    def ruxsat(self, buyurtma_id: str, summa: int) -> None:
        self.sorov(P.RUXSAT, buyurtma_id.encode("utf-8")[:P.MAX_BUYURTMA_ID_UZ],
                   P.u128(summa), P.u32(self.ruxsat_muddati_s))

    def _imzo(self, javob: list[bytes], xabar: bytes) -> bytes:
        if len(javob) != 1 or not imzo_togri(self.ochiq_kalit(), javob[0], xabar):
            raise P.PicoXatosi(P.X_ALOQA, "Pico qaytargan imzo YAROQSIZ — qurilma buzuq yoki "
                                          "almashtirilgan")
        return javob[0]

    def partiya_imzosi(self, ildiz, partiya_id, soni, jami, zaxira_qulfi, zarb_ms) -> bytes:
        q = zaxira_qulfi.strip()
        j = self.sorov(P.IMZO_PARTIYA, bytes(ildiz), bytes(partiya_id), P.u64(soni),
                       P.u128(jami), q.encode("utf-8"), P.u64(zarb_ms))
        return self._imzo(j, imzo_xabari(ildiz, partiya_id, soni, jami, q, zarb_ms))

    def bosh_imzosi(self, tartib: int, xesh: bytes) -> bytes:
        j = self.sorov(P.IMZO_BOSH, P.u64(tartib), bytes(xesh))
        return self._imzo(j, bosh_xabari(tartib, xesh))

    def mint_auth_imzosi(self, bank_pk: bytes, chaqiriq: bytes, cert_id: bytes) -> bytes:
        j = self.sorov(P.IMZO_MINT_AUTH, bytes(bank_pk), bytes(chaqiriq), bytes(cert_id))
        return self._imzo(j, mint_auth_xesh(bank_pk, chaqiriq, cert_id))


def _matn(yuk: bytes) -> str:
    try:
        f = P.ajrat(yuk)
        return f[0].decode("utf-8", "replace") if f else ""
    except P.RamkaXatosi:
        return ""


def _javob(yuk: bytes) -> list[bytes]:
    if not yuk:
        raise P.PicoXatosi(P.X_ALOQA, "bo'sh javob")
    try:
        f = P.ajrat(yuk[1:])
    except P.RamkaXatosi as e:
        raise P.PicoXatosi(P.X_ALOQA, f"javob buzilgan: {e}") from e
    if yuk[0] != P.OK:
        matn = f[0].decode("utf-8", "replace") if f else ""
        raise P.PicoXatosi(yuk[0], matn, f[1:])
    return f
