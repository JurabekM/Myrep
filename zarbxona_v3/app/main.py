"""Kirish nuqtasi: `python run.py`, `python -m app.main`, `python app/main.py`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ILDIZ = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):        # `python app/main.py`
    sys.path.insert(0, str(ILDIZ))

from core.konstanta import VERSIYA  # noqa: E402


def argumentlar(argv=None) -> argparse.Namespace:
    a = argparse.ArgumentParser(prog="zarbxona", description="AETHER-Q Zarbxona v3")
    a.add_argument("--papka", type=Path, default=ILDIZ / "data",
                   help="profil papkasi (default: dastur yonidagi data/)")
    a.add_argument("--selftest", action="store_true", help="Qt'siz o'z-o'zini sinash")
    a.add_argument("--version", action="version", version=f"Zarbxona {VERSIYA}")
    return a.parse_args(argv)


def main(argv=None) -> int:
    for oqim in (sys.stdout, sys.stderr):
        try:
            oqim.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = argumentlar(argv)
    if args.selftest:
        from app.selftest import selftest
        return selftest(ILDIZ / "selftest_natija.txt")

    from PySide6.QtWidgets import QApplication, QDialog

    from app.kirish import KirishDialogi
    from app.oyna import Oyna
    from app.theme import ikonka, mavzuni_qol

    ilova = QApplication.instance() or QApplication(sys.argv)
    ilova.setApplicationName("Zarbxona")
    mavzuni_qol(ilova)
    ilova.setWindowIcon(ikonka())
    d = KirishDialogi(args.papka)
    if d.exec() != QDialog.DialogCode.Accepted or d.zarbxona is None:
        return 0
    oyna = Oyna(d.zarbxona)
    oyna.show()
    oyna.tiklashni_korsat(d.tiklash)
    oyna.ogohlantirishlarni_korsat()
    return ilova.exec()


if __name__ == "__main__":
    raise SystemExit(main())
