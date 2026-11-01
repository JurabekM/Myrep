#!/usr/bin/env python3
"""Play do'kon matnlari chegaralarini tekshiradi: nom ≤ 30, qisqa tavsif ≤ 80, to'liq ≤ 4000, yangiliklar ≤ 500."""
import sys
from pathlib import Path

LIMITS = {"title.txt": 30, "short_description.txt": 80, "full_description.txt": 4000, "release_notes.txt": 500}


def main() -> int:
    bad = 0
    for lang in sorted((Path(__file__).resolve().parent / "listing").iterdir()):
        for name, limit in LIMITS.items():
            text = (lang / name).read_text(encoding="utf-8").strip()
            ok = 0 < len(text) <= limit
            bad += not ok
            print(f"{'OK ' if ok else 'XATO'} {lang.name:6} {name:24} {len(text):5} / {limit}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
