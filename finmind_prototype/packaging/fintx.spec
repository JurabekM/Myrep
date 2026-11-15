# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spetsifikatsiyasi: FinTx desktop + terminal ijro fayllari.

Ishga tushirish (loyiha ildizidan):  pyinstaller --noconfirm packaging/fintx.spec

Natija `dist/FinTx/` papkasi (ikkala ijro fayl bitta kutubxonalar to'plamini
bo'lishadi), macOS'da qo'shimcha ravishda `dist/FinTx.app`.

Imzolash: `MACOS_CODESIGN_IDENTITY` muhit o'zgaruvchisi berilsa, macOS'dagi har bir
ikkilik fayl shu Developer ID bilan, "hardened runtime" yoqilgan holda imzolanadi.
Berilmasa PyInstaller faqat ad-hoc imzo qo'yadi (Apple Silicon'da ishga tushishi
uchun majburiy, lekin Gatekeeper uni ishonchli nashriyotchi deb hisoblamaydi).
"""

import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(ROOT))

from fintx import __version__  # noqa: E402

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

ICON = str(ROOT / "packaging" / ("icon.ico" if IS_WIN else "icon.png"))
IDENTITY = os.environ.get("MACOS_CODESIGN_IDENTITY") or None
ENTITLEMENTS = str(ROOT / "packaging" / "macos" / "entitlements.plist") if IDENTITY else None

# Ilova ichidagi shrift modul yonidan (`fintx/assets/fonts`) qidiriladi.
DATAS = [(str(ROOT / "fintx" / "assets" / "fonts"), "fintx/assets/fonts")]
# Ilova ishlatmaydigan og'ir modullar paketga kirmasin.
EXCLUDES = ["tkinter", "unittest", "pydoc", "PIL"]

gui = Analysis(
    [str(ROOT / "packaging" / "desktop_entry.py")],
    pathex=[str(ROOT)],
    datas=DATAS,
    excludes=EXCLUDES,
)
cli = Analysis(
    [str(ROOT / "packaging" / "cli_entry.py")],
    pathex=[str(ROOT)],
    excludes=[*EXCLUDES, "PySide6", "shiboken6"],
)


def executable(analysis, name, console):
    return EXE(
        PYZ(analysis.pure),
        analysis.scripts,
        [],
        exclude_binaries=True,
        name=name,
        console=console,
        icon=ICON if (IS_WIN or IS_MAC) else None,
        upx=False,  # UPX siqish antiviruslarda yolg'on signal beradi
        codesign_identity=IDENTITY,
        entitlements_file=ENTITLEMENTS,
    )


gui_exe = executable(gui, "FinTx", console=False)
cli_exe = executable(cli, "fintx-cli", console=True)

bundle = COLLECT(
    gui_exe,
    cli_exe,
    gui.binaries,
    gui.datas,
    cli.binaries,
    cli.datas,
    upx=False,
    name="FinTx",
)

if IS_MAC:
    app = BUNDLE(
        bundle,
        name="FinTx.app",
        icon=ICON,
        bundle_identifier="uz.fintx.desktop",
        version=__version__,
        info_plist={
            "CFBundleDisplayName": "FinTx",
            "CFBundleShortVersionString": __version__,
            "CFBundleVersion": __version__,
            "LSApplicationCategoryType": "public.app-category.finance",
            "LSMinimumSystemVersion": "12.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "NSHumanReadableCopyright": "FinTx prototipi",
        },
    )
