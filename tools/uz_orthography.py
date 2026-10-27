"""O'zbek lotin yozuvi imlosini to'g'rilash: oddiy apostrof o'rniga
`ʻ` (U+02BB, oʻ / gʻ) va `ʼ` (U+02BC, tutuq belgisi — maʼlumot, aʼzo).

Ishlatish:
    python tools/uz_orthography.py            # ARB (uz) ni o'zgartiradi
    python tools/uz_orthography.py --check    # o'zgartirmaydi, topilsa 1 qaytaradi
    python tools/uz_orthography.py --dart FAYL...  # Dart test fayllaridagi matnlar

Qoidalar (faqat harflar orasida):
    o' / O' / g' / G'  ->  oʻ / Oʻ / gʻ / Gʻ
    boshqa harf + ' + harf  ->  harf + ʼ + harf
"""

from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

OKINA = "ʻ"  # ʻ
TUTUQ = "ʼ"  # ʼ
LETTER = r"A-Za-zÀ-ÿ"

# Dart manbasida `\'` (qochirilgan apostrof) ham hisobga olinadi.
_OG = re.compile(rf"([oOgG])\\?['‘’`](?=[{LETTER}])")
_OTHER = re.compile(rf"([{LETTER}])\\?['’`](?=[{LETTER}])")


# So'z oxiridagi oʻ/gʻ («Obroʻ», «moʻ»): oldida harf bo'lsa. Faqat sof
# matn (ARB, kontent JSON) uchun — Dart manbasida yopuvchi qo'shtirnoq bilan
# adashtirilishi mumkin.
_OG_FINAL = re.compile(rf"(?<=[{LETTER}])([oOgG])['‘’`](?![{LETTER}])")


def fix(text: str, *, plain: bool = False) -> str:
    text = _OG.sub(lambda m: m.group(1) + OKINA, text)
    if plain:
        text = _OG_FINAL.sub(lambda m: m.group(1) + OKINA, text)
    return _OTHER.sub(lambda m: m.group(1) + TUTUQ, text)


def fix_arb(path: Path, check: bool) -> int:
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)
    changed = 0
    for key, value in data.items():
        if key.startswith("@") or not isinstance(value, str):
            continue
        new = fix(value, plain=True)
        if new != value:
            changed += 1
            data[key] = new
    if changed and not check:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",  # Windows'da CRLF yozilmasin
        )
    return changed


def main() -> int:
    args = sys.argv[1:]
    check = "--check" in args
    if "--dart" in args:
        total = 0
        for name in args[args.index("--dart") + 1:]:
            p = Path(name)
            src = p.read_text(encoding="utf-8")
            new = fix(src)
            if new != src:
                total += 1
                if not check:
                    p.write_text(new, encoding="utf-8", newline="\n")
        print(f"dart fayllar: {total} ta o'zgardi")
        return 1 if check and total else 0
    n = fix_arb(Path("lib/app/l10n/arb/app_uz.arb"), check)
    print(f"app_uz.arb: {n} ta matn {'tuzatilishi kerak' if check else 'tuzatildi'}")
    return 1 if check and n else 0


if __name__ == "__main__":
    sys.exit(main())
