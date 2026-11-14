"""Paket matni bilan ishlash: xavfsiz ko'rinish va ochiq uzatilgan sirlarni topish."""

import re

PAYLOAD_SCAN_BYTES = 4096

# TLS yozuvi: tur (20–23), versiya 3.x — shifrlangan, ichidan sir qidirish ma'nosiz.
_TLS_TYPES = frozenset({0x14, 0x15, 0x16, 0x17})

# Faqat «nom = qiymat» ko'rinishi: `User-Agent` yoki `keep-alive` kabi sarlavhalar tushmaydi.
_ASSIGNMENT = re.compile(
    rb"(?i)(?<![A-Za-z0-9_])"
    rb"(pass(?:word|wd)?|pwd|secret|token|api[_-]?key|access[_-]?key)"
    rb"[\"']?\s*[=:]\s*[\"']?[^\s&\"']"
)
_AUTH_HEADER = re.compile(rb"(?im)^authorization:\s*(basic|bearer|digest)\s+\S")
# FTP / POP3: parol alohida buyruq bilan ochiq matnda yuboriladi.
_PASS_COMMAND = re.compile(rb"(?m)^PASS \S")


def looks_encrypted(payload: bytes) -> bool:
    return len(payload) >= 3 and payload[0] in _TLS_TYPES and payload[1] == 0x03


def find_secret(payload: bytes) -> str:
    """Ochiq matnda uzatilgan sirning **turi** (`password`, `authorization`, ...) yoki `""`.

    Qiymatning o'zi hech qayerga qaytarilmaydi.
    """
    if not payload or looks_encrypted(payload):
        return ""
    head = payload[:PAYLOAD_SCAN_BYTES]
    found = _ASSIGNMENT.search(head)
    if found is not None:
        return found.group(1).decode("ascii").lower().replace("-", "_")
    if _AUTH_HEADER.search(head) is not None:
        return "authorization"
    if _PASS_COMMAND.search(head) is not None:
        return "pass_command"
    return ""


def printable(payload: bytes, limit: int) -> str:
    """Baytlarni konsol va jadval uchun xavfsiz satrga aylantiradi (ko'pi bilan `limit` bayt).

    Bosiladigan ASCII o'zicha qoladi; tab, CR, LF — `\\t`, `\\r`, `\\n`; qolgani — `\\xNN`.
    """
    parts: list[str] = []
    for byte in payload[:limit]:
        if 32 <= byte <= 126 and byte != 0x5C:
            parts.append(chr(byte))
        elif byte == 0x5C:
            parts.append("\\\\")
        elif byte == 0x09:
            parts.append("\\t")
        elif byte == 0x0A:
            parts.append("\\n")
        elif byte == 0x0D:
            parts.append("\\r")
        else:
            parts.append(f"\\x{byte:02x}")
    if len(payload) > limit:
        parts.append("…")
    return "".join(parts)
