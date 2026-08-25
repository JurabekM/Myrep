"""DistribOS AI — ishga tushirish nuqtasi.

    python run.py            # grafik ilova
    python run.py --check    # grafik muhitsiz holat tekshiruvi
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "apps" / "desktop" / "src"))

from distribos.main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
