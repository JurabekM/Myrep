# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: `python tools/exe_yig.py` (yoki `pyinstaller zarbxona.spec`).
# Bitta papkada ikki dastur, umumiy kutubxonalar bilan:
#   Zarbxona.exe      — oynali GUI (konsol oynasi ochilmaydi)
#   zarbxona-cli.exe  — konsol: holat/zarb/davom/tasdiqla/tekshir va --selftest
# data/ va selftest_natija.txt .exe yonida yaratiladi (app/yollar.py).
from pathlib import Path

ILDIZ = Path(SPECPATH)
IKONKA = str(ILDIZ / "app" / "assets" / "zarbxona.ico")

a = Analysis(
    [str(ILDIZ / "run.py")],
    pathex=[str(ILDIZ)],
    datas=[(str(ILDIZ / "app" / "assets"), "app/assets")],
    hiddenimports=["app.cli", "app.selftest", "segno"],
    excludes=["tkinter", "pytest", "hypothesis", "Crypto", "PySide6.QtWebEngineCore",
              "PySide6.QtQml", "PySide6.QtQuick", "PySide6.Qt3DCore"],
    noarchive=False,
)
pyz = PYZ(a.pure)

gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Zarbxona", console=False,
          icon=IKONKA, upx=False)
cli = EXE(pyz, a.scripts, [], exclude_binaries=True, name="zarbxona-cli", console=True,
          icon=IKONKA, upx=False)
coll = COLLECT(gui, cli, a.binaries, a.datas, name="Zarbxona", upx=False)
