"""docs/PLAY_LISTING.md dagi Play matnlari chegaralarini tekshiradi.

Har `### <sarlavha>` ostidagi ```text bloki bitta maydon. Maydon turi sarlavhadan
aniqlanadi (nom 30, qisqa tavsif 80, to'liq tavsif 4000, «What's new» 500 belgi).
Play belgilarni Unicode kod nuqtalari bo'yicha sanaydi (U+02BB ham bitta belgi).

    python tools/store/check_listing.py [docs/PLAY_LISTING.md]
"""

import re
import sys
from pathlib import Path

LIMITS = [
    (("Nom", "Название", "Title"), 30),
    (("Qisqa tavsif", "Краткое описание", "Short description"), 80),
    (("To'liq tavsif", "Полное описание", "Full description"), 4000),
    (("What's new", "Что нового"), 500),
]
# Play metadata siyosati bo'yicha taqiqlangan uslub belgilari («riba-free» — narx emas).
FORBIDDEN = re.compile(
    r"(№\s*1|#1|\beng yaxshi\b|\bлучш|\bbest\b|(?<![-\w])free\b|\bбесплатн|\bbepul\b)", re.I
)


def limit_for(title: str) -> int | None:
    for names, limit in LIMITS:
        if any(title.startswith(n) for n in names):
            return limit
    return None


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/PLAY_LISTING.md")
    text = path.read_bytes().decode("utf-8")
    lang = "?"
    failed = False
    checked = 0
    for m in re.finditer(r"^## ([^\n]+)$|^### ([^\n]+)\n```text\n(.*?)\n```", text, re.M | re.S):
        if m.group(1):
            lang = m.group(1).strip()
            continue
        title, body = m.group(2).strip(), m.group(3)
        limit = limit_for(title)
        if limit is None:
            print(f"?    {lang} / {title}: chegara noma'lum")
            failed = True
            continue
        n = len(body)
        bad = FORBIDDEN.search(body)
        ok = n <= limit and bad is None and "'" not in body
        failed |= not ok
        checked += 1
        note = f" (taqiqlangan: {bad.group(0)!r})" if bad else ""
        note += " (ASCII ' — U+02BB/U+02BC kerak)" if "'" in body else ""
        print(f"{'OK ' if ok else 'XATO'} {lang} / {title}: {n}/{limit}{note}")
    print(f"{checked} maydon tekshirildi")
    return 1 if failed or checked == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
