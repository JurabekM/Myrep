"""Kanonik kodlash.

Spec §4 muammosi (Y-5): hujjat "kanonik CBOR (tavsiya) YOKI qat'iy kanonik JSON"
deydi, ayni paytda AAD "byte-for-byte bir xil" bo'lishini talab qiladi. Ikkala
talab bir vaqtda bajarilmaydi. Simulyator ikkala kodlashni ham qo'llab-quvvatlaydi
va rejimlar mos kelmaganda nima bo'lishini ko'rsatadi.

HARDENED rejimda faqat `CBOR_DETERMINISTIC` (RFC 8949 §4.2.1) ruxsat etiladi.
"""
from __future__ import annotations

import json
from enum import Enum
from typing import Any

import cbor2


class Encoding(str, Enum):
    CBOR_DETERMINISTIC = "cbor-det"   # RFC 8949 §4.2.1 Core Deterministic
    JSON_CANONICAL = "json-canon"     # sorted keys, no spaces, base64url bytes


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (bytes, bytearray)):
        import base64

        return "b64:" + base64.urlsafe_b64encode(bytes(obj)).decode().rstrip("=")
    raise TypeError(f"JSON uchun qo'llab-quvvatlanmaydigan tur: {type(obj)!r}")


def encode(obj: Any, encoding: Encoding = Encoding.CBOR_DETERMINISTIC) -> bytes:
    """Obyektni kanonik baytlarga aylantiradi."""
    if encoding is Encoding.CBOR_DETERMINISTIC:
        return cbor2.dumps(obj, canonical=True)
    if encoding is Encoding.JSON_CANONICAL:
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=_json_default,
        ).encode("utf-8")
    raise ValueError(f"noma'lum kodlash: {encoding}")


def decode(raw: bytes, encoding: Encoding = Encoding.CBOR_DETERMINISTIC) -> Any:
    if encoding is Encoding.CBOR_DETERMINISTIC:
        return cbor2.loads(raw)
    if encoding is Encoding.JSON_CANONICAL:
        return json.loads(raw.decode("utf-8"))
    raise ValueError(f"noma'lum kodlash: {encoding}")


def is_deterministic(raw: bytes, encoding: Encoding = Encoding.CBOR_DETERMINISTIC) -> bool:
    """Baytlar haqiqatan kanonikmi — qayta kodlab solishtiradi.

    Bu tekshiruv AAD ni qabul qilishdan oldin bajarilishi kerak, aks holda
    server maydonlarni qayta-serializatsiya qilib imzoni "ko'chira" oladi.
    """
    try:
        return encode(decode(raw, encoding), encoding) == raw
    except Exception:
        return False
