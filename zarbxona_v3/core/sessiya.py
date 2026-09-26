"""§13.3 — AETHER-Q v5.1 sessiyasi: TASHQI komponent, faqat adapter.

Handshake va yozuv qatlami `aetherq_core` (Rust, PyO3) da. Bu yerda ular
QAYTA YOZILMAYDI. `SoxtaFabrika` — faqat protokolning yuqori qatlamini
sinash uchun; hech qanday xavfsizlik bermaydi.
"""

from __future__ import annotations

from typing import Protocol

from .ibtido import sha3

AETHERQ_YOQ = "onlayn topshirish uchun aetherq_core kerak; fayl orqali topshirish ishlaydi"


class Sessiya(Protocol):
    def seal(self, ochiq: bytes) -> bytes: ...
    def open(self, paket: bytes) -> tuple[int, bytes]: ...


class Handshake(Protocol):
    def start(self) -> bytes: ...
    def recv(self, paket: bytes) -> bytes | None: ...
    @property
    def is_connected(self) -> bool: ...
    def take_session(self) -> Sessiya: ...


class SessiyaFabrikasi(Protocol):
    def mijoz(self, bank_ochiq_kaliti: bytes) -> Handshake: ...


class SessiyaXatosi(Exception):
    pass


# --- haqiqiy ------------------------------------------------------------------


def aetherq_core_bormi() -> bool:
    try:
        import aetherq_core  # noqa: F401
        return True
    except ImportError:
        return False


class AetherQFabrika:
    """Foydalanuvchi mashinasida: `aq.ClientHandshake(bank_pk)` — bank kaliti PINLANGAN."""

    def __init__(self):
        try:
            import aetherq_core
        except ImportError as e:
            raise SessiyaXatosi(AETHERQ_YOQ) from e
        self._aq = aetherq_core

    def mijoz(self, bank_ochiq_kaliti: bytes) -> Handshake:
        return self._aq.ClientHandshake(bytes(bank_ochiq_kaliti))


# --- soxta (faqat testlar) ------------------------------------------------------

_HS1, _HS2 = b"SOXTA-HS1", b"SOXTA-HS2"
_TUR = 0x17


class SoxtaSessiya:
    """Shifrsiz o'rash + tur bayti. XAVFSIZLIK YO'Q."""

    def seal(self, ochiq: bytes) -> bytes:
        return bytes([_TUR]) + ochiq

    def open(self, paket: bytes) -> tuple[int, bytes]:
        if not paket or paket[0] != _TUR:
            raise SessiyaXatosi("soxta sessiya: yozuv turi noto'g'ri")
        return _TUR, paket[1:]


class SoxtaMijozHandshake:
    def __init__(self, bank_pk: bytes):
        self._pin = sha3(bank_pk)
        self._ulandi = False

    def start(self) -> bytes:
        return _HS1

    def recv(self, paket: bytes) -> bytes | None:
        if paket[:len(_HS2)] != _HS2:
            raise SessiyaXatosi("soxta handshake: kutilmagan paket")
        if paket[len(_HS2):] != self._pin:
            raise SessiyaXatosi("bank kaliti pinlangan kalitga mos emas")
        self._ulandi = True
        return None

    @property
    def is_connected(self) -> bool:
        return self._ulandi

    def take_session(self) -> SoxtaSessiya:
        if not self._ulandi:
            raise SessiyaXatosi("handshake tugamagan")
        return SoxtaSessiya()


class SoxtaBankHandshake:
    def __init__(self, bank_pk: bytes):
        self._pk = bank_pk
        self._ulandi = False

    def recv(self, paket: bytes) -> bytes:
        if paket != _HS1:
            raise SessiyaXatosi("soxta handshake: kutilmagan paket")
        self._ulandi = True
        return _HS2 + sha3(self._pk)

    @property
    def is_connected(self) -> bool:
        return self._ulandi

    def take_session(self) -> SoxtaSessiya:
        return SoxtaSessiya()


class SoxtaFabrika:
    def mijoz(self, bank_ochiq_kaliti: bytes) -> SoxtaMijozHandshake:
        return SoxtaMijozHandshake(bank_ochiq_kaliti)
