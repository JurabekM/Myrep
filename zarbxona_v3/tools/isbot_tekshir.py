"""Kupyura isboti paketini OFLAYN tekshirish (JSON fayl yoki QR'dan o'qilgan matn).

    python tools/isbot_tekshir.py isbot.json
    python tools/isbot_tekshir.py isbot.json --kalit zarbxona_ochiq_kalit.json
    echo '<QR matni>' | python tools/isbot_tekshir.py -

`--kalit` — Kalit sahifasidan eksport qilingan zarbxona ochiq kaliti (to'liq paketda
partiya imzosini ham tekshiradi). Chiqish kodi: 0 — tegishli, 1 — yo'q/buzilgan.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.isbot import isbot_tekshir  # noqa: E402


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("paket", help="JSON fayl yoki '-' (stdin)")
    a.add_argument("--kalit", type=Path, help="zarbxona_ochiq_kalit.json")
    x = a.parse_args(argv)
    matn = sys.stdin.read() if x.paket == "-" else Path(x.paket).read_text(encoding="utf-8")
    pk = bytes.fromhex(json.loads(x.kalit.read_text(encoding="utf-8"))["public_key"]) \
        if x.kalit else None
    ok, izoh = isbot_tekshir(matn.strip(), pk)
    print(("TEGISHLI: " if ok else "RAD: ") + izoh)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
