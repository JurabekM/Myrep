"""SCUTUM protokol simulyatori — ishga tushirish nuqtasi.

    python run.py            GUI
    python run.py --tests    faqat testlar (CLI)
    python run.py --attacks  faqat hujum matritsasi (CLI)
"""
from __future__ import annotations

import sys


def _gui() -> int:
    from PySide6.QtWidgets import QApplication

    from scutum.gui import MainWindow
    from scutum.gui.theme import QSS, apply_palette

    app = QApplication(sys.argv)
    app.setApplicationName("SCUTUM simulyatori")
    apply_palette(app)
    app.setStyleSheet(QSS)

    win = MainWindow()
    win.show()
    return app.exec()


def _tests() -> int:
    from scutum.selftest import main

    return main()


def _attacks() -> int:
    from scutum.config import hardened_config, spec_config
    from scutum.sim.attacks import ATTACKS, Outcome, run_attack

    print(f"{'hujum':<36}{'topilma':<9}{'SPEC':<13}{'HARDENED'}")
    print("-" * 74)
    broken = 0
    for key, atk in ATTACKS.items():
        rs = run_attack(key, spec_config())
        rh = run_attack(key, hardened_config())
        broken += rs.outcome == Outcome.BROKEN
        print(f"{atk.title[:35]:<36}{atk.finding:<9}{rs.outcome:<13}{rh.outcome}")
    print("-" * 74)
    print(f"SPEC rejimida buzilgan: {broken}/{len(ATTACKS)}")
    return 0


if __name__ == "__main__":
    if "--tests" in sys.argv:
        raise SystemExit(_tests())
    if "--attacks" in sys.argv:
        raise SystemExit(_attacks())
    raise SystemExit(_gui())
