"""Kanonik JSON (RFC 8785 / JCS): kalitlar UTF-16 kod birliklari bo'yicha saralangan, bo'sh joy yo'q,
sonlar ECMAScript formatida, vaqt — UTC ISO-8601 (millisekund), natija UTF-8.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

# JavaScript'da aniq ifodalanadigan eng katta butun son (2^53 − 1).
_MAX_SAFE_INT = 9007199254740991

_ESCAPES = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def canonical_json(value: object) -> str:
    out: list[str] = []
    _write(out, value)
    return "".join(out)


def canonical_json_bytes(value: object) -> bytes:
    return canonical_json(value).encode("utf-8")


def _write(out: list[str], v: object) -> None:
    if v is None:
        out.append("null")
    elif isinstance(v, bool):
        out.append("true" if v else "false")
    elif isinstance(v, str):
        out.append(_string(v))
    elif isinstance(v, int):
        if abs(v) > _MAX_SAFE_INT:
            raise ValueError(f"butun son 2^53 dan katta: {v}")
        out.append(str(v))
    elif isinstance(v, float):
        out.append(_number(v))
    elif isinstance(v, datetime):
        out.append(_string(_iso(v)))
    elif isinstance(v, dict):
        if not all(isinstance(k, str) for k in v):
            raise ValueError("kalit satr bo'lishi kerak")
        keys = sorted(v, key=lambda k: k.encode("utf-16-be"))
        out.append("{")
        for i, k in enumerate(keys):
            if i:
                out.append(",")
            out.append(_string(k))
            out.append(":")
            _write(out, v[k])
        out.append("}")
    elif isinstance(v, list):
        out.append("[")
        for i, item in enumerate(v):
            if i:
                out.append(",")
            _write(out, item)
        out.append("]")
    else:
        raise ValueError(f"JSON'ga o'girib bo'lmaydi: {type(v).__name__}")


def _string(s: str) -> str:
    parts = ['"']
    for ch in s:
        c = ord(ch)
        if 0xD800 <= c <= 0xDFFF:
            raise ValueError("yolg'iz surrogat")
        if ch in _ESCAPES:
            parts.append(_ESCAPES[ch])
        elif c < 0x20:
            parts.append(f"\\u{c:04x}")
        else:
            parts.append(ch)
    parts.append('"')
    return "".join(parts)


def _number(x: float) -> str:
    """ECMAScript `Number.prototype.toString()` (RFC 8785, 3.2.2.3)."""
    if not math.isfinite(x):
        raise ValueError("NaN yoki cheksiz son")
    if x == 0:
        return "0"
    sign = "-" if x < 0 else ""
    # repr — eng qisqa aniq raqamlar ketma-ketligi.
    r = repr(abs(x))
    mantissa, _, exp = r.partition("e")
    whole, _, frac = mantissa.partition(".")
    raw = whole + frac
    leading_zeros = len(raw) - len(raw.lstrip("0"))
    # Qiymat = 0.<digits> · 10^n
    n = len(whole) + (int(exp) if exp else 0) - leading_zeros
    digits = raw.strip("0")
    k = len(digits)
    if k <= n <= 21:
        body = digits + "0" * (n - k)
    elif 0 < n <= 21:
        body = f"{digits[:n]}.{digits[n:]}"
    elif -6 < n <= 0:
        body = "0." + "0" * -n + digits
    else:
        e = n - 1
        mant = digits if k == 1 else f"{digits[0]}.{digits[1:]}"
        body = f"{mant}e{'-' if e < 0 else '+'}{abs(e)}"
    return sign + body


def _iso(t: datetime) -> str:
    if t.utcoffset() != timedelta(0):
        raise ValueError("vaqt UTC bo'lishi kerak")
    return (
        f"{t.year:04d}-{t.month:02d}-{t.day:02d}T{t.hour:02d}:{t.minute:02d}:{t.second:02d}."
        f"{t.microsecond // 1000:03d}Z"
    )
