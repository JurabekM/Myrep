"""Kontent siyosati testi uchun taqiqlangan ibora xeshi.

Ishlatish:
    python tools/denylist_hash.py "ibora" ["ibora 2" ...]

Har ibora uchun `test/design/source_policy_test.dart` dagi `_forbidden`
ro'yxatiga qo'shiladigan qator chiqadi: `(so'zlar soni, belgilar soni,
'sha256')`. Ibora repoda ochiq matnda saqlanmaydi.

Normallashtirish Dart testi bilan bir xil: kichik harf, `ʻ ʼ ‘ ’ \\`` → `'`,
so'zlar (harf, raqam, apostrof) bitta bo'shliq bilan qo'shiladi. Moslik so'z
boshidan: «namuna» ibora «namunaviy» ni ham ushlaydi.
"""

from __future__ import annotations

import hashlib
import re
import sys

_APOSTROPHES = re.compile("[ʻʼ‘’`]")
# So'z harf yoki raqamdan boshlanadi; ichida va oxirida apostrof bo'lishi
# mumkin (o'zingizga, obro'). Dart: `[\p{L}\p{N}]+(?:'[\p{L}\p{N}]*)*`.
_WORD = re.compile(r"[^\W_]+(?:'[^\W_]*)*")


def normalize(phrase: str) -> str:
    text = _APOSTROPHES.sub("'", phrase.lower())
    return " ".join(m.group(0) for m in _WORD.finditer(text))


def entry(phrase: str) -> tuple[int, int, str]:
    norm = normalize(phrase)
    if not norm:
        raise ValueError(f"bo'sh ibora: {phrase!r}")
    digest = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    return len(norm.split(" ")), len(norm), digest


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    for phrase in argv:
        words, length, digest = entry(phrase)
        print(f"  ({words}, {length}, '{digest}'),")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
