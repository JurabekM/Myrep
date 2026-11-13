"""4.x — imzolovchi: zarbxona kaliti bilan imzo qo'yadigan narsa.

Ikki turi bor:
  * `FaylImzolovchi` — `kalit.json` dagi kalit (maxfiy kalit kompyuter xotirasida);
  * `core.pico.PicoImzolovchi` — Raspberry Pi Pico (kalit qurilmadan chiqmaydi).

Imzolovchi IXTIYORIY baytlarni imzolamaydi: har bir imzo turi o'z maydonlari bilan
keladi va imzolanadigan xabarni imzolovchining O'ZI quradi. Pico shu sabab siyosatni
o'zi tekshira oladi (masalan, operator tugma bilan ruxsat bergan summadan oshmaslik).
Zarbxona kodi kalit o'rniga imzolovchini ham qabul qiladi: `imzolovchi(sk)` ikkalasini
bir xil interfeysga keltiradi.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .ibtido import MaxfiyKalit, imzola, ochiq_kalit
from .partiya import imzo_xabari
from .protokol import mint_auth_xesh
from .zanjir import bosh_xabari


class ImzolovchiXatosi(RuntimeError):
    """Imzo olinmadi: qurilma uzildi, tugma bosilmadi, ruxsat yo'q va h.k.
    `kod` — Pico protokoli xato kodi (fayl imzolovchida 0)."""

    def __init__(self, xabar: str, kod: int = 0):
        super().__init__(xabar)
        self.kod = kod


@runtime_checkable
class Imzolovchi(Protocol):
    nomi: str          # "fayl" | "pico" | "soxta-pico"

    def ochiq_kalit(self) -> bytes: ...

    def ruxsat(self, buyurtma_id: str, summa: int) -> None:
        """Buyurtma uchun imzo ruxsati. Pico'da operator tugmani bosadi va qurilma
        shu summagacha partiya imzolaydi. Faylda — hech narsa qilmaydi."""

    def partiya_imzosi(self, ildiz: bytes, partiya_id: bytes, soni: int, jami: int,
                       zaxira_qulfi: str, zarb_ms: int) -> bytes: ...

    def bosh_imzosi(self, tartib: int, xesh: bytes) -> bytes: ...

    def mint_auth_imzosi(self, bank_pk: bytes, chaqiriq: bytes, cert_id: bytes) -> bytes: ...


class FaylImzolovchi:
    nomi = "fayl"

    def __init__(self, sk: MaxfiyKalit):
        self.sk = sk
        self._pk = ochiq_kalit(sk)

    def ochiq_kalit(self) -> bytes:
        return self._pk

    def ruxsat(self, buyurtma_id: str, summa: int) -> None:
        return None

    def partiya_imzosi(self, ildiz, partiya_id, soni, jami, zaxira_qulfi, zarb_ms) -> bytes:
        return imzola(self.sk, imzo_xabari(ildiz, partiya_id, soni, jami, zaxira_qulfi,
                                           zarb_ms))

    def bosh_imzosi(self, tartib: int, xesh: bytes) -> bytes:
        return imzola(self.sk, bosh_xabari(tartib, xesh))

    def mint_auth_imzosi(self, bank_pk: bytes, chaqiriq: bytes, cert_id: bytes) -> bytes:
        return imzola(self.sk, mint_auth_xesh(bank_pk, chaqiriq, cert_id))


def imzolovchi(sk) -> Imzolovchi:
    """Kalit obyekti yoki tayyor imzolovchi → imzolovchi."""
    if isinstance(sk, MaxfiyKalit):
        return FaylImzolovchi(sk)
    if isinstance(sk, Imzolovchi):
        return sk
    raise TypeError(f"imzolovchi emas: {type(sk).__name__}")
