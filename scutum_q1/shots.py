"""GUI ni haqiqiy holatga keltirib, har panelning skrinshotini oladi."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from scutum.gui import MainWindow
from scutum.gui.theme import QSS, apply_palette

OUT = Path(__file__).parent / "shots"
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

    panels = {label: p for (label, _), p in zip(
        [(n, c) for n, c in __import__(
            "scutum.gui.main_window", fromlist=["NAV"]).NAV], win.panels)}
    names = list(panels)

    def go(i: int) -> None:
        win.nav_group.button(i).setChecked(True)
        win.stack.setCurrentIndex(i)
        QApplication.processEvents()

    # 1 — umumiy
    go(0); grab(win, "1-overview")

    # 2 — qurilmalar
    go(1); grab(win, "2-devices")

    # 3 — sessiya: handshake + xabarlar
    go(2)
    sp = win.panels[2]
    sp.do_handshake()
    for t in ["Salom Bobur, bu SCUTUM sinovi.",
              "Ikkinchi xabar — ratchet oldinga siljidi."]:
        sp.edit.setText(t); sp.do_send()
    sp.who.setChecked(False); sp._toggle_who()
    sp.edit.setText("Qabul qildim, Alisa. Hammasi joyida."); sp.do_send()
    sp.who.setChecked(True); sp._toggle_who()
    sp.do_pq()
    sp.edit.setText("PQ ratchetdan keyingi xabar."); sp.do_send()
    QApplication.processEvents(); grab(win, "3-session")

    # 4 — ratchet
    go(3); win.panels[3].refresh(); grab(win, "4-ratchet")

    # 5 — S-FILE
    go(4)
    qp = win.panels[4]
    qp.chunk_box.setValue(16)
    qp.size_box.setCurrentIndex(0)
    qp.encrypt_random()
    QApplication.processEvents(); grab(win, "5-sfile")
    qp.tamper()
    QApplication.processEvents(); grab(win, "5b-sfile-tamper")

    # 6 — hujum laboratoriyasi
    go(5)
    ap = win.panels[5]
    ap.start(compare=True)
    while ap._runner and ap._runner.isRunning():
        QApplication.processEvents()
        ap._runner.wait(50)
    QApplication.processEvents()
    ap.table.selectRow(0)
    QApplication.processEvents(); grab(win, "6-attacks")
    ap.table.selectRow(2)
    QApplication.processEvents(); grab(win, "6b-attacks-detail")

    # 7 — inspektor
    go(6)
    ip = win.panels[6]
    ip.refresh()
    if ip.table.rowCount() > 2:
        ip.table.selectRow(2)
    QApplication.processEvents(); grab(win, "7-inspector")

    # 8 — testlar
    go(7)
    tp = win.panels[7]
    tp.start()
    while tp._runner and tp._runner.isRunning():
        QApplication.processEvents()
        tp._runner.wait(50)
    QApplication.processEvents(); grab(win, "8-tests")

    print("\nBarcha skrinshotlar:", OUT)
    QTimer.singleShot(100, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
