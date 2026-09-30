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
    a.add_argument("--papka", type=Path, default=None,
                   help="profil papkasi (default: dastur yonidagi data/, --demo da data_demo/)")
    a.add_argument("--demo", action="store_true",
                   help="DEMO rejimi: o'rnatilgan soxta bank bilan to'liq halqa (haqiqiy emas)")
    a.add_argument("--selftest", action="store_true", help="Qt'siz o'z-o'zini sinash")
    a.add_argument("--version", action="version", version=f"Zarbxona {VERSIYA}")
    return a.parse_args(argv)


def main(argv=None) -> int:
    for oqim in (sys.stdout, sys.stderr):
        try:
            oqim.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    royxat = list(sys.argv[1:] if argv is None else argv)
    if royxat and royxat[0] in ("holat", "zarb", "davom", "tasdiqla", "buyurtmalar", "tekshir"):
        from app.cli import main as cli_main      # GUI'siz — Qt yuklanmaydi
        return cli_main(royxat)
    args = argumentlar(argv)
    if args.papka is None:
        args.papka = ILDIZ / ("data_demo" if args.demo else "data")
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
    from core.demo_bank import DemoBank, DemoXatosi, demo_tayyorla
    demo = None
    if args.demo or DemoBank.bormi(args.papka):
        try:
            demo = demo_tayyorla(d.zarbxona)
        except DemoXatosi as e:
            from app import dialog
            dialog.xato(None, "Demo rejimi", str(e))
            d.zarbxona.yop()
            return 1
    oyna = Oyna(d.zarbxona, demo_bank=demo)
    oyna.show()
    oyna.tiklashni_korsat(d.tiklash)
    oyna.ogohlantirishlarni_korsat()
    return ilova.exec()


if __name__ == "__main__":
    raise SystemExit(main())
