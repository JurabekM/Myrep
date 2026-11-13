"""Loyiha ikonkasini (ko'p o'lchamli ICO + 256 px PNG) qayta yaratadi.

    python tools/ikonka_yarat.py
"""

import sys
from pathlib import Path

ILDIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ILDIZ))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.theme import IKONKA, ico_baytlari, tanga  # noqa: E402

if __name__ == "__main__":
    ilova = QApplication.instance() or QApplication(sys.argv)
    IKONKA.parent.mkdir(parents=True, exist_ok=True)
    IKONKA.write_bytes(ico_baytlari())
    tanga(256).save(str(IKONKA.with_suffix(".png")), "PNG")
    print(f"yozildi: {IKONKA} va {IKONKA.with_suffix('.png').name}")
