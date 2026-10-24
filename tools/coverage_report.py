"""lcov.info dan papka bo'yicha qamrov hisoboti.

Ishlatish:
    flutter test --coverage
    python tools/coverage_report.py lib/core/money --min 95

`--min` berilsa va qamrov undan past bo'lsa, chiqish kodi 1 (CI uchun).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import PurePosixPath

GENERATED = (".g.dart", ".freezed.dart", ".pigeon.dart")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", help="masalan: lib/core/money")
    parser.add_argument("--lcov", default="coverage/lcov.info")
    parser.add_argument("--min", type=float, default=None)
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()

    prefix = args.prefix.replace("\\", "/").rstrip("/") + "/"
    stats: dict[str, list[int]] = {}
    missed: dict[str, list[int]] = {}
    current = None
    with open(args.lcov, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if line.startswith("SF:"):
                path = line[3:].replace("\\", "/")
                idx = path.find("lib/")
                current = path[idx:] if idx >= 0 else path
            elif line.startswith("DA:") and current:
                if not current.startswith(prefix) or current.endswith(GENERATED):
                    continue
                if any(x in current for x in args.exclude):
                    continue
                number, hits = (int(v) for v in line[3:].split(",")[:2])
                total, hit = stats.setdefault(current, [0, 0])
                stats[current] = [total + 1, hit + (hits > 0)]
                if hits == 0:
                    missed.setdefault(current, []).append(number)

    if not stats:
        print(f"{prefix}: lcov'da fayl topilmadi")
        return 1
    grand_total = grand_hit = 0
    for path, (total, hit) in sorted(stats.items()):
        grand_total += total
        grand_hit += hit
        name = PurePosixPath(path).name
        print(f"  {name:32} {hit:4}/{total:<4} {100 * hit / total:5.1f}%  "
              f"qoplanmagan qatorlar: {missed.get(path, [])}")
    pct = 100 * grand_hit / grand_total
    print(f"JAMI {prefix}: {grand_hit}/{grand_total} = {pct:.1f}%")
    if args.min is not None and pct < args.min:
        print(f"Qamrov {args.min}% dan past!")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
