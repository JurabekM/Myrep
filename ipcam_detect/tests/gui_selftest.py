"""gui_selftest.py — GUI ni haqiqatan ishga tushirib avtomatik tekshiradi.

Qo'lda bosib ko'rmasdan: oynani ochadi, test videosi bilan pipeline'ni
boshlaydi, kadr/statistika kelishini kutadi, skrinshot oladi, to'xtatadi va
resurslar bo'shaganini tekshiradi.

    python tests/gui_selftest.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import List

from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import gui as gui_mod  # noqa: E402
from real_model_check import make_video  # noqa: E402

_results: List[tuple] = []
OUT = ROOT / "out"


def _safe(text: str) -> str:
    """Windows konsoli (cp1251) uchun ASCII bo'lmagan belgilarni tozalaydi."""
    enc = sys.stdout.encoding or "ascii"
    return text.encode(enc, errors="replace").decode(enc)


def check(name: str, cond: bool, info: str = "") -> None:
    _results.append((name, cond, info))
    print(_safe(f"{'[OK]  ' if cond else '[FAIL]'} {name}"
                + (f"  ({info})" if info else "")))


def pump(seconds: float) -> None:
    """Qt hodisa siklini `seconds` davomida aylantiradi (bloklamasdan)."""
    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    loop.exec()


def main() -> int:
    model = ROOT / "models" / "yolov8n_640.onnx"
    if not model.exists():
        print(f"Model topilmadi: {model}")
        return 2

    video = os.path.join(tempfile.gettempdir(), "gui_selftest.mp4")
    make_video(video, seconds=6)

    app = gui_mod.build_app()
    win = gui_mod.MainWindow()
    win.show()
    pump(0.6)
    check("oyna ochildi", win.isVisible(), f"{win.width()}x{win.height()}")
    check("dark tema qo'llandi",
          "background: #0f1115" in QApplication.instance().styleSheet())

    # --- sozlamalarni to'ldirish (foydalanuvchi bosgandek) ---
    win.ed_url.setText(video)
    win.cmb_sbackend.setCurrentText("opencv")
    win.ed_model.setText(str(model))
    win.chk_loop.setChecked(True)
    win.sp_every.setValue(3)
    win.sp_target.setValue(15.0)
    win.cmb_resize.setCurrentText("960x540")
    win._check_model()
    check("model banneri yashirin (model bor)", win.banner.isHidden())

    cfg = win.build_config()
    check("konfiguratsiya to'g'ri yig'ildi",
          cfg.stream.url == video and cfg.detector.imgsz == 640
          and cfg.stream.resize_to == (960, 540) and not cfg.show,
          f"detect_every={cfg.detect_every}, tracker={cfg.tracker}")

    # --- ishga tushirish ---
    win.start_pipeline()
    check("START bosilgach STOP faollashdi",
          win.btn_stop.isEnabled() and not win.btn_start.isEnabled())

    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        pump(0.4)
        fps_ready = win.card_fps.value.text() not in ("0", "0.0")
        if win._last_frame is not None and fps_ready:
            break

    check("preview kadri keldi", win._last_frame is not None,
          f"{win._last_frame.shape if win._last_frame is not None else '—'}")
    fps_text = win.card_fps.value.text()
    check("FPS ko'rsatkichi yangilandi",
          fps_text not in ("0", "0.0") and float(fps_text) > 1.0,
          f"FPS={fps_text}")
    check("RAM ko'rsatkichi yangilandi", win.card_ram.value.text() != "0",
          f"RAM={win.card_ram.value.text()} MB")
    check("holat 'Ulangan'", "Ulangan" in win.lbl_state.text(), win.lbl_state.text())

    pump(4.0)  # jadval to'lishi uchun
    check("obyektlar jadvali to'ldi", win.table.rowCount() > 0,
          f"{win.table.rowCount()} sinf: " + ", ".join(
              win.table.item(i, 0).text() for i in range(win.table.rowCount())))
    check("o'qilgan kadrlar hisoblandi", win.lbl_read.text() not in ("0", ""),
          f"o'qildi={win.lbl_read.text()}")
    check("log oynasi to'ldi", len(win.log.toPlainText()) > 0,
          f"{len(win.log.toPlainText().splitlines())} qator")

    # --- skrinshot ---
    OUT.mkdir(parents=True, exist_ok=True)
    shot = OUT / "gui_screenshot.png"
    win.grab().save(str(shot))
    check("skrinshot saqlandi", shot.exists() and shot.stat().st_size > 20000,
          f"{shot.stat().st_size // 1024} KB")

    # --- snapshot tugmasi ---
    win.save_snapshot()
    snaps = list((OUT / "snapshots").glob("snap_*.jpg"))
    check("snapshot tugmasi ishladi", bool(snaps),
          snaps[-1].name if snaps else "—")

    # --- sinf tanlash dialogi ---
    dlg = gui_mod.ClassDialog([0, 2], win)
    dlg.search.setText("person")
    visible = [i for i in range(dlg.list.count()) if not dlg.list.item(i).isHidden()]
    check("sinf dialogi qidiruvi ishlaydi", len(visible) == 1, f"{len(visible)} natija")
    check("tanlangan sinflar saqlandi", dlg.selected() == [0, 2], str(dlg.selected()))
    dlg.close()

    # --- to'xtatish ---
    win.stop_pipeline()
    deadline = time.monotonic() + 15
    while win.worker is not None and time.monotonic() < deadline:
        pump(0.3)
    check("pipeline to'xtadi", win.worker is None)
    check("STOP dan keyin START qaytdi", win.btn_start.isEnabled())

    # --- profil saqlash/yuklash (dialogsiz) ---
    win.presets["__test__"] = win._collect()
    win._apply(win.presets["__test__"])
    check("profil yig'ish/qo'llash ishlaydi", win.ed_url.text() == video)

    win.close()
    pump(0.4)
    try:
        os.remove(video)
    except OSError:
        pass

    ok = sum(1 for _, c, _ in _results if c)
    print("\n" + "=" * 66)
    print(f" GUI NATIJA: {ok}/{len(_results)} test o'tdi")
    print(f" Skrinshot: {shot}")
    print("=" * 66)
    for name, cond, info in _results:
        if not cond:
            print(_safe(f"  [FAIL] {name} {info}"))
    app.quit()
    return 0 if ok == len(_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
