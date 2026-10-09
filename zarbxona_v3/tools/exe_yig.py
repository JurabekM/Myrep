"""Zarbxona'ni Python'siz ishlaydigan papkaga yig'ish (PyInstaller).

    python -m pip install "pyinstaller>=6.10"
    python tools/exe_yig.py

Natija: dist/Zarbxona/ — Zarbxona(.exe) va zarbxona-cli(.exe). Oxirida paketlangan
dastur `--version` va `--selftest` bilan ishga tushirib tekshiriladi.
"""

import os
import subprocess
import sys
from pathlib import Path

ILDIZ = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        import PyInstaller.__main__ as pi
    except ImportError:
        print("PyInstaller o'rnatilmagan: python -m pip install \"pyinstaller>=6.10\"")
        return 1
    pi.run([str(ILDIZ / "zarbxona.spec"), "--noconfirm", "--clean",
            "--distpath", str(ILDIZ / "dist"), "--workpath", str(ILDIZ / "build")])
    papka = ILDIZ / "dist" / "Zarbxona"
    cli = papka / ("zarbxona-cli.exe" if os.name == "nt" else "zarbxona-cli")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for arg in ("--version", "--selftest"):
        r = subprocess.run([str(cli), arg], cwd=papka, capture_output=True, text=True,
                           encoding="utf-8", env=env, timeout=300)
        print(f"$ {cli.name} {arg}  → kod {r.returncode}\n{r.stdout[-600:]}{r.stderr[-600:]}")
        if r.returncode != 0:
            return 1
    print(f"TAYYOR: {papka}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
