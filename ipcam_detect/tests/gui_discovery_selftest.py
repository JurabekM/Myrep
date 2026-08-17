"""gui_discovery_selftest.py — «Kameralarni qidirish» oynasi sinovi.

Soxta RTSP/ONVIF serverlari ko'tariladi (discovery_selftest.py dagilar),
so'ng dialog xuddi foydalanuvchi ishlatgandek boshqariladi: qidirish →
kamerani tanlash → login/parol kiritish → tekshirish → URL ni qabul qilish.

    python tests/gui_discovery_selftest.py
"""

from __future__ import annotations

import sys
import threading
import time
from http.server import HTTPServer
from pathlib import Path
from typing import List

from PyQt6.QtCore import QEventLoop, QTimer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import gui as gui_mod  # noqa: E402
from discovery_selftest import (  # noqa: E402
    GOOD_PATH,
    ONVIF_PORT,
    PASSWORD,
    RTSP_PORT,
    USER,
    FakeRTSPServer,
    ONVIFHandler,
)
from gui_discovery import DiscoveryDialog  # noqa: E402

_results: List[tuple] = []


def check(name: str, cond: bool, info: str = "") -> None:
    _results.append((name, cond, info))
    text = f"{'[OK]  ' if cond else '[FAIL]'} {name}" + (f"  ({info})" if info else "")
    enc = sys.stdout.encoding or "ascii"
    print(text.encode(enc, "replace").decode(enc))


def pump(seconds: float) -> None:
    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    loop.exec()


def wait_until(cond, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pump(0.25)
        if cond():
            return True
    return False


def main() -> int:
    import logging

    logging.basicConfig(level=logging.WARNING)

    rtsp = FakeRTSPServer()
    rtsp.start()
    onvif = HTTPServer(("127.0.0.1", ONVIF_PORT), ONVIFHandler)
    threading.Thread(target=onvif.serve_forever, daemon=True).start()

    app = gui_mod.build_app()
    win = gui_mod.MainWindow()
    win.show()
    pump(0.4)

    print("=" * 68)
    print(" GUI: kameralarni qidirish oynasi")
    print("=" * 68)

    check("asosiy oynada 'qidirish' tugmasi bor",
          hasattr(win, "btn_discover") and win.btn_discover.isEnabled(),
          win.btn_discover.text() if hasattr(win, "btn_discover") else "—")

    dlg = DiscoveryDialog(win, colors=gui_mod.C)
    dlg.show()
    pump(0.3)
    check("dialog ochildi", dlg.isVisible(), f"{dlg.width()}x{dlg.height()}")
    check("lokal tarmoqlar ro'yxatga to'ldi", dlg.cmb_subnet.count() > 0,
          f"{dlg.cmb_subnet.count()} ta")

    # --- qidiruv: faqat lokal soxta serverlar ---
    dlg.chk_onvif.setChecked(False)          # multicast'ni testda ishlatmaymiz
    dlg.cmb_subnet.setCurrentText("127.0.0.1/30")
    dlg.ed_ports.setText(f"{RTSP_PORT},{ONVIF_PORT}")
    dlg.start_discovery()
    check("qidiruv boshlandi (tugmalar bloklandi)",
          not dlg.btn_scan.isEnabled() and dlg.btn_cancel.isEnabled())

    ok = wait_until(lambda: dlg.discover_thread is None, 40)
    check("qidiruv yakunlandi", ok)
    check("jadvalda qurilma paydo bo'ldi", dlg.table.rowCount() >= 1,
          f"{dlg.table.rowCount()} qator")
    check("topilgan IP to'g'ri",
          dlg.table.item(0, 0) is not None and dlg.table.item(0, 0).text() == "127.0.0.1",
          dlg.table.item(0, 0).text() if dlg.table.item(0, 0) else "—")
    check("ochiq portlar ko'rsatildi",
          str(RTSP_PORT) in dlg.table.item(0, 2).text(), dlg.table.item(0, 2).text())
    check("holat 'tekshirilmagan'", "tekshirilmagan" in dlg.table.item(0, 4).text(),
          dlg.table.item(0, 4).text())

    # --- login/parolsiz tekshirish urinishi ---
    dlg.table.selectRow(0)
    pump(0.2)
    check("kamera tanlandi -> tekshirish tugmasi faol", dlg.btn_verify.isEnabled())
    dlg.ed_user.setText("")
    dlg.verify_selected()
    check("loginsiz ogohlantirish chiqdi", "Login" in dlg.lbl_status.text(),
          dlg.lbl_status.text())

    # --- noto'g'ri parol ---
    dlg.ed_user.setText(USER)
    dlg.ed_pass.setText("xato-parol")
    dlg.verify_selected()
    ok = wait_until(lambda: dlg.verify_thread is None, 60)
    check("noto'g'ri parol tekshiruvi tugadi", ok)
    check("noto'g'ri parol xabari to'g'ri",
          "parol" in dlg.lbl_status.text().lower() and not dlg.btn_use.isEnabled(),
          dlg.lbl_status.text())
    check("jadval holati yangilandi", "login/parol" in dlg.table.item(0, 4).text(),
          dlg.table.item(0, 4).text())

    # --- to'g'ri parol ---
    dlg.ed_pass.setText(PASSWORD)
    dlg.verify_selected()
    ok = wait_until(lambda: dlg.verify_thread is None, 60)
    check("to'g'ri parol tekshiruvi tugadi", ok)
    url = dlg.lbl_url.text()
    check("RTSP URL topildi", url.endswith(GOOD_PATH), url)
    check("URL da login/parol bor", USER in url and "@127.0.0.1" in url, url)
    check("«TANLASH» tugmasi faollashdi", dlg.btn_use.isEnabled())
    check("jadvalda '✓ ulanadi'", "ulanadi" in dlg.table.item(0, 4).text(),
          dlg.table.item(0, 4).text())

    # --- parolni ko'rsatish tugmasi ---
    from PyQt6.QtWidgets import QLineEdit

    dlg.btn_eye.setChecked(True)
    check("parolni ko'rsatish ishlaydi",
          dlg.ed_pass.echoMode() == QLineEdit.EchoMode.Normal)
    dlg.btn_eye.setChecked(False)
    check("parol yana yashirildi",
          dlg.ed_pass.echoMode() == QLineEdit.EchoMode.Password)

    # --- skrinshot ---
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    shot = out / "gui_discovery.png"
    dlg.grab().save(str(shot))
    check("skrinshot saqlandi", shot.exists() and shot.stat().st_size > 15000,
          f"{shot.stat().st_size // 1024} KB")

    # --- URL ni asosiy oynaga uzatish ---
    dlg._accept_url()
    check("dialog URL ni qabul qildi", dlg.selected_url == url)
    win.ed_url.setText(dlg.selected_url)
    check("asosiy oynaga URL o'tdi", win.ed_url.text() == url)
    masked = gui_mod._mask_url(url)
    check("parol log uchun maskalanadi",
          masked.startswith(f"rtsp://{USER}:***@") and "P%40rol" not in masked,
          masked)

    dlg.close()
    win.close()
    pump(0.3)
    rtsp.stop()
    onvif.shutdown()

    okc = sum(1 for _, c, _ in _results if c)
    print("\n" + "=" * 68)
    print(f" NATIJA: {okc}/{len(_results)} test o'tdi")
    print(f" Skrinshot: {shot}")
    print("=" * 68)
    for name, cond, info in _results:
        if not cond:
            print(f"  [FAIL] {name} {info}")
    app.quit()
    return 0 if okc == len(_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
