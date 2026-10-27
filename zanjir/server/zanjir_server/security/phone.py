"""Telefon raqami: O'zbekiston formati `+998XXXXXXXXX` ga keltiriladi (bo'shliq, chiziqcha, qavslar olib tashlanadi)."""

from __future__ import annotations

import re

_UZ = re.compile(r"\+998[0-9]{9}")


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"[\s\-()]", "", raw.strip())
    if digits.startswith("998") and len(digits) == 12:
        digits = "+" + digits
    return digits if _UZ.fullmatch(digits) else None
