"""Qurilma ichidagi kalit yozuvi (flash) — PIN bilan himoya. Ichki dastur (C) AYNAN
shu algoritmni bajaradi; `firmware/pico_hsm/` testlari shu fayldagi vektorlar bilan
solishtiriladi.

    k   = SHA3-256(L_PIN || salt || pin);  k = SHA3-256(k || pin) × (PIN_ITER − 1)
    ek  = SHA3-256(L_ENC || k),  mk = SHA3-256(L_MAC || k)
    ct  = urug ⊕ SHAKE256(ek || salt, 32)
    tag = SHA3-256(mk || salt || ct)[:16]

Faqat SHA3 oilasi: Pico'da ML-DSA uchun Keccak baribir bor, boshqa shifr kerak emas.

OGOHLANTIRISH (RP2040): flash'ni BOOTSEL orqali o'qib olish mumkin. Kimdir qurilmani
qo'lga olsa, `PIN_ITER` faqat sekinlashtiradi: qisqa PIN oflayn tez topiladi. Urinishlar
hisobi (`MAX_URINISH`) faqat qurilmaning O'ZIGA qarshi taxminlarni to'xtatadi.
Haqiqiy pul uchun — Pico 2 (RP2350): OTP kalit, secure boot, debug yopiq.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

L_PIN = b"AQ-PICO/PIN/v1"
L_ENC = b"AQ-PICO/ENC/v1"
L_MAC = b"AQ-PICO/MAC/v1"
L_KEYGEN = b"AQ-PICO/KEYGEN/v1"
PIN_ITER = 4096
SALT_UZ = 16
TAG_UZ = 16
URUG_UZ = 32


def _sha3(*q: bytes) -> bytes:
    h = hashlib.sha3_256()
    for x in q:
        h.update(x)
    return h.digest()


def pin_kaliti(pin: bytes, salt: bytes, iter_: int = PIN_ITER) -> bytes:
    k = _sha3(L_PIN, salt, pin)
    for _ in range(iter_ - 1):
        k = _sha3(k, pin)
    return k


def _kalitlar(pin: bytes, salt: bytes, iter_: int) -> tuple[bytes, bytes]:
    k = pin_kaliti(pin, salt, iter_)
    return _sha3(L_ENC, k), _sha3(L_MAC, k)


def _oqim(ek: bytes, salt: bytes) -> bytes:
    return hashlib.shake_256(ek + salt).digest(URUG_UZ)


@dataclass
class KalitYozuvi:
    salt: bytes
    ct: bytes
    tag: bytes
    urinish: int = 0
    import_: bool = False


def shifrla(urug: bytes, pin: bytes, salt: bytes, iter_: int = PIN_ITER) -> KalitYozuvi:
    if len(urug) != URUG_UZ or len(salt) != SALT_UZ:
        raise ValueError("urug' 32, salt 16 bayt bo'lishi kerak")
    ek, mk = _kalitlar(pin, salt, iter_)
    ct = bytes(a ^ b for a, b in zip(urug, _oqim(ek, salt)))
    return KalitYozuvi(salt, ct, _sha3(mk, salt, ct)[:TAG_UZ])


def och(y: KalitYozuvi, pin: bytes, iter_: int = PIN_ITER) -> bytes | None:
    """To'g'ri PIN — urug'; noto'g'ri — `None`."""
    ek, mk = _kalitlar(pin, y.salt, iter_)
    if not hmac.compare_digest(_sha3(mk, y.salt, y.ct)[:TAG_UZ], y.tag):
        return None
    return bytes(a ^ b for a, b in zip(y.ct, _oqim(ek, y.salt)))


def yangi_urug(qurilma_tasodifi: bytes, xost_entropiyasi: bytes) -> bytes:
    """Ikki manba aralashadi: biri yomon bo'lsa ham, ikkinchisi saqlaydi."""
    return _sha3(L_KEYGEN, qurilma_tasodifi, xost_entropiyasi)
