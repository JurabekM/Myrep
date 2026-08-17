"""ROSTOR panellarini haqiqiy holatga keltirib skrinshot oladi."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from scutum.gui import MainWindow
from scutum.gui.theme import QSS, apply_palette

OUT = Path(__file__).parent / "rostor_shots"
OUT.mkdir(exist_ok=True)


def grab(win, name: str) -> None:
    QApplication.processEvents()
    win.grab().save(str(OUT / f"{name}.png"))
    print("  saqlandi:", name)


def main() -> int:
    app = QApplication(sys.argv)
    apply_palette(app)
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    QApplication.processEvents()

    def go(i: int) -> None:
        win.nav_group.button(i).setChecked(True)
        win.stack.setCurrentIndex(i)
        QApplication.processEvents()

    # 0 — Institutsiyalar
    go(0)
    inst = win.panels[0]
    inst.sender_box.setCurrentIndex(0)
    inst.check_badge()
    QApplication.processEvents()
    grab(win, "0-institutions-verified")
    inst.sender_box.setCurrentIndex(inst.sender_box.count() - 1)  # Mallory
    inst.check_badge()
    QApplication.processEvents()
    grab(win, "0-institutions-fishing")

    # 1 — Tranzaksiya tasdiqlash
    go(1)
    txn = win.panels[1]
    txn.send_request()
    QApplication.processEvents()
    grab(win, "1-txn-confirm-request")
    txn.respond("APPROVE")
    txn.run_relay_attack()
    QApplication.processEvents()
    grab(win, "1-txn-confirm-relay")

    # 2 — Shaffoflik jurnali
    go(2)
    trans = win.panels[2]
    trans.lookup_edit.setText("Bank X")
    trans.do_lookup()
    QApplication.processEvents()
    grab(win, "2-transparency-found")
    trans.lookup_edit.setText("Bunday institutsiya yoq")
    trans.do_lookup()
    QApplication.processEvents()
    grab(win, "2-transparency-notfound")

    # 3 — Firibgarlik lab
    go(3)
    lab = win.panels[3]
    lab.run_all()
    QApplication.processEvents()
    lab.table.selectRow(1)
    QApplication.processEvents()
    grab(win, "3-fraud-lab")

    print("\nBarcha skrinshotlar:", OUT)
    from PySide6.QtCore import QTimer
    QTimer.singleShot(100, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
