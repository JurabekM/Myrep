"""Identifikatorlar va mantiqiy vaqt.

`event_id` UUIDv7 (RFC 9562): birinchi 48 bit — Unix millisekund, qolgani
tasodifiy. Bu bizga ikkita narsani beradi:

* global noyoblik (markaziy generator kerak emas — serversiz tizimda shart);
* **vaqt bo'yicha tartiblanish** — indeks bo'ylab ketma-ket yoziladi, ya'ni
  bir million hodisali event log'da ham B-tree parchalanmaydi.
"""

from __future__ import annotations

import os
import secrets
import time
import uuid
from dataclasses import dataclass


def uuid7() -> uuid.UUID:
    """RFC 9562 UUIDv7 — vaqt bo'yicha tartiblanadigan noyob ID.

    Python 3.13 da standart kutubxonada yo'q, shuning uchun o'zimiz
    quramiz (bu identifikator, kriptografik primitiv emas).
    """
    unix_ms = time.time_ns() // 1_000_000
    rand = secrets.token_bytes(10)
    raw = bytearray(unix_ms.to_bytes(6, "big") + rand)
    raw[6] = (raw[6] & 0x0F) | 0x70          # versiya 7
    raw[8] = (raw[8] & 0x3F) | 0x80          # RFC 4122 variant
    return uuid.UUID(bytes=bytes(raw))


def uuid7_str() -> str:
    return str(uuid7())


def timestamp_from_uuid7(value: uuid.UUID) -> int:
    """UUIDv7 ichidan Unix millisekundni chiqaradi."""
    return int.from_bytes(value.bytes[:6], "big")


def new_device_id() -> bytes:
    """16 baytli qurilma identifikatori — tenant ichida opaque."""
    return secrets.token_bytes(16)


def new_tenant_id() -> bytes:
    """16 baytli tenant identifikatori.

    DIQQAT: bu korxona nomidan hosil qilinmaydi. Topikda ishlatiladigan
    `opaque_tenant_id` shu qiymatning hash'i — ochiq matnda korxona nomi
    hech qachon chiqmaydi (topshiriq §8).
    """
    return secrets.token_bytes(16)


@dataclass(frozen=True, order=True, slots=True)
class HybridTimestamp:
    """Gibrid mantiqiy soat (HLC).

    Nega oddiy `datetime` yetmaydi: qurilmalar soati farq qiladi (clock
    skew). HLC fizik vaqtni saqlaydi, lekin sabab-oqibat tartibini ham
    kafolatlaydi — ikki qurilma hodisalari deterministik solishtiriladi.

    Solishtirish tartibi: (wall_ms, counter, device_id) — oxirgisi
    teng bo'lgan holatlarni deterministik uzadi.
    """

    wall_ms: int
    counter: int
    device_id: str

    def encode(self) -> str:
        return f"{self.wall_ms:013d}.{self.counter:05d}.{self.device_id}"

    @classmethod
    def decode(cls, text: str) -> HybridTimestamp:
        wall, counter, device = text.split(".", 2)
        return cls(int(wall), int(counter), device)


class HybridClock:
    """HLC generatori. Bitta qurilma uchun bitta nusxa."""

    def __init__(self, device_id: str, *, max_drift_ms: int = 5 * 60 * 1000) -> None:
        self._device_id = device_id
        self._wall_ms = 0
        self._counter = 0
        self._max_drift_ms = max_drift_ms

    def now(self) -> HybridTimestamp:
        physical = time.time_ns() // 1_000_000
        if physical > self._wall_ms:
            self._wall_ms, self._counter = physical, 0
        else:
            # Soat orqaga ketdi yoki bir ms ichida bir necha hodisa —
            # hisoblagich bilan monotonlikni saqlaymiz.
            self._counter += 1
        return HybridTimestamp(self._wall_ms, self._counter, self._device_id)

    def observe(self, remote: HybridTimestamp) -> HybridTimestamp:
        """Kelgan hodisa tamg'asini hisobga oladi (HLC qoidasi).

        Juda uzoq kelajakdagi tamg'a QABUL QILINMAYDI: buzilgan yoki
        soati noto'g'ri qurilma butun mesh soatini oldinga surib
        yubormasligi kerak.
        """
        physical = time.time_ns() // 1_000_000
        if remote.wall_ms > physical + self._max_drift_ms:
            # Chetlangan tamg'ani e'tiborsiz qoldiramiz, lekin hodisani
            # rad etmaymiz — bu biznes ma'lumot, uni yo'qotib bo'lmaydi.
            remote = HybridTimestamp(physical, remote.counter, remote.device_id)

        highest = max(physical, self._wall_ms, remote.wall_ms)
        if highest == self._wall_ms == remote.wall_ms:
            self._counter = max(self._counter, remote.counter) + 1
        elif highest == self._wall_ms:
            self._counter += 1
        elif highest == remote.wall_ms:
            self._counter = remote.counter + 1
        else:
            self._counter = 0
        self._wall_ms = highest
        return HybridTimestamp(self._wall_ms, self._counter, self._device_id)


def idempotency_key(*parts: str | bytes | int) -> str:
    """Buyruq uchun idempotentlik kaliti.

    Bir xil buyruq qayta yuborilsa (masalan foydalanuvchi ikki marta
    bosdi yoki tarmoq qayta urindi) — bir xil kalit chiqadi va biznes
    natijasi ikki marta qo'llanmaydi.
    """
    import hashlib

    digest = hashlib.sha3_256()
    for part in parts:
        if isinstance(part, str):
            digest.update(part.encode("utf-8"))
        elif isinstance(part, int):
            digest.update(str(part).encode("ascii"))
        else:
            digest.update(part)
        digest.update(b"\x1f")  # maydon ajratgich
    return digest.hexdigest()


def opaque_tenant_topic_id(tenant_id: bytes) -> str:
    """Topikda ishlatiladigan tenant identifikatori.

    Korxona nomi, telefon yoki boshqa ma'lumot topikka CHIQMAYDI
    (topshiriq §8). Bu qiymat `tenant_id` ning domain-ajratilgan hash'i.
    """
    import hashlib

    digest = hashlib.sha3_256(b"DistribOS/topic/tenant/v1" + tenant_id).digest()
    return digest[:16].hex()


def device_topic_id(device_id: bytes) -> str:
    """Topikda ishlatiladigan qurilma identifikatori (opaque)."""
    import hashlib

    digest = hashlib.sha3_256(b"DistribOS/topic/device/v1" + device_id).digest()
    return digest[:8].hex()


def mask_identifier(value: bytes | str, keep: int = 4) -> str:
    """Diagnostika va log uchun maskalangan identifikator."""
    text = value.hex() if isinstance(value, bytes) else value
    if len(text) <= keep:
        return "*" * len(text)
    return text[:keep] + "…" + "*" * 4


def random_hex(size: int = 8) -> str:
    return os.urandom(size).hex()
