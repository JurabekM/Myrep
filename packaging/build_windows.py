"""Windows uchun exe va installer yig'adi.

    python packaging/build_windows.py            # exe + installer
    python packaging/build_windows.py --exe-only # faqat exe

Nuitka o'rniga PyInstaller tanlandi: PySide6 + SQLAlchemy + cryptography
to'plamida PyInstaller'ning hook'lari tayyor va build ancha tez. Natija
ikkalasida ham bitta papka + installer.

Yig'ilgandan keyin **majburiy** tekshiruv bajariladi: exe ishga tushirilib,
`--check` rejimida holat so'raladi. "Build muvaffaqiyatli" degani "dastur
ishlaydi" degani emas — bu ikki xil narsa.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DIST = _ROOT / "dist"
_BUILD = _ROOT / "packaging" / "out"
_APP_NAME = "DistribOS AI"
_EXE_NAME = "DistribOS"
_VERSION = "1.0.0"

#: Inno Setup kompilyatori (odatiy o'rnatish joyi).
_ISCC = Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print(f"  $ {' '.join(str(part) for part in command[:4])} …")
    result = subprocess.run(command, cwd=cwd or _ROOT, text=True)
    if result.returncode != 0:
        raise SystemExit(f"Buyruq {result.returncode} kodi bilan tugadi")


def build_exe() -> Path:
    """PyInstaller bilan bitta papkali build."""
    print("[1/4] exe yig'ilmoqda…")

    if _DIST.exists():
        shutil.rmtree(_DIST)
    _BUILD.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", _EXE_NAME,
        # Bitta fayl EMAS: bitta faylli build har ishga tushishda o'zini
        # vaqtinchalik papkaga ochadi — 3 soniya chegarasiga sig'maydi va
        # antivirus uni shubhali deb belgilaydi.
        "--onedir",
        "--windowed",
        "--distpath", str(_DIST),
        "--workpath", str(_BUILD / "work"),
        "--specpath", str(_BUILD),
        "--paths", str(_ROOT / "apps" / "desktop" / "src"),
        # Kontraktlar va spetsifikatsiyalar ilova ichida kerak.
        "--add-data", f"{_ROOT / 'contracts'};contracts",
        "--hidden-import", "distribos.persistence.models",
        "--hidden-import", "distribos.aether_q.vendor",
        # Kerak bo'lmagan og'ir Qt modullari — installer hajmi uchun.
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtWebEngineWidgets",
        "--exclude-module", "PySide6.Qt3DCore",
        "--exclude-module", "PySide6.QtMultimedia",
        "--exclude-module", "PySide6.QtQuick3D",
        "--exclude-module", "PySide6.QtCharts",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "pytest",
        str(_ROOT / "run.py"),
    ]
    run(command)

    exe = _DIST / _EXE_NAME / f"{_EXE_NAME}.exe"
    if not exe.exists():
        raise SystemExit(f"exe topilmadi: {exe}")

    size = sum(f.stat().st_size for f in (_DIST / _EXE_NAME).rglob("*") if f.is_file())
    print(f"      tayyor: {exe}  ({size / 1024 / 1024:.1f} MB)")
    return exe


def smoke_test(exe: Path) -> None:
    """Yig'ilgan exe HAQIQATAN ishga tushishini tekshiradi.

    ## Nega exe REPO TASHQARISIGA ko'chiriladi

    Bu test avval `dist/` ichidan bajarilardi va MUVAFFAQIYATLI o'tardi —
    lekin faqat TASODIFAN: `dist/` repo ichida, shuning uchun resurs
    yo'lini noto'g'ri hisoblagan kod ham to'g'ri faylga tushardi.
    O'rnatilgan dastur boshqa papkada bo'lgani uchun sinardi.

    Endi exe vaqtinchalik papkaga ko'chiriladi — ya'ni test haqiqiy
    o'rnatish sharoitini takrorlaydi.

    ## Nega natija faylan o'qiladi

    `--windowed` build'da `sys.stdout` yo'q, va ko'tarilgan istisno
    PyInstaller'ning MODAL dialogiga aylanadi — tashqaridan bu
    "osilib qoldi" bo'lib ko'rinadi. Shuning uchun `--check` natijani
    `status.txt` ga ham yozadi va biz shuni o'qiymiz.
    """
    print("[2/4] yig'ilgan exe sinovdan o'tkazilmoqda…")

    import os
    import tempfile

    staging = Path(tempfile.mkdtemp(prefix="distribos-smoke-"))
    portable = staging / "app"
    shutil.copytree(exe.parent, portable)
    home = staging / "home"

    environment = {**os.environ, "DISTRIBOS_HOME": str(home)}
    target = portable / exe.name

    started = time.monotonic()
    try:
        result = subprocess.run(
            [str(target), "--check"], capture_output=True, text=True,
            env=environment, timeout=180,
        )
        return_code = result.returncode
        output = (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired:
        raise SystemExit(
            "exe --check javob bermadi (180 s). Ehtimol ishga tushishda "
            "istisno bo'lgan va u ko'rinmas dialogga aylangan. "
            f"Jurnal: {home / 'logs' / 'distribos.log'}"
        ) from None
    elapsed = time.monotonic() - started

    status_file = home / "logs" / "status.txt"
    if status_file.exists():
        output += "\n" + status_file.read_text(encoding="utf-8", errors="replace")

    if return_code != 0 or "AETHER-Q" not in output:
        log = home / "logs" / "distribos.log"
        if log.exists():
            print(log.read_text(encoding="utf-8", errors="replace")[-2000:])
        print(output[-2000:])
        raise SystemExit(f"exe --check muvaffaqiyatsiz (kod {return_code})")

    print(f"      repo tashqarisida ishga tushdi ({elapsed:.1f} s)")
    for line in status_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            print(f"      | {line.rstrip()}")

    if elapsed > 3.0:
        print(f"      OGOHLANTIRISH: ishga tushish {elapsed:.1f} s — maqsad 3 s")

    shutil.rmtree(staging, ignore_errors=True)


def build_installer(exe: Path) -> Path | None:
    """Inno Setup bilan installer yig'adi."""
    print("[3/4] installer yig'ilmoqda…")

    if not _ISCC.exists():
        print(f"      O'TKAZIB YUBORILDI: Inno Setup topilmadi ({_ISCC})")
        return None

    script = _ROOT / "packaging" / "distribos.iss"
    run([str(_ISCC), f"/DAppVersion={_VERSION}", str(script)])

    installer = _DIST / f"DistribOS-Setup-{_VERSION}.exe"
    if not installer.exists():
        raise SystemExit(f"installer topilmadi: {installer}")
    print(f"      tayyor: {installer}  ({installer.stat().st_size / 1024 / 1024:.1f} MB)")
    return installer


def write_manifest(exe: Path, installer: Path | None) -> Path:
    """Chiqarilgan fayllar va ularning nazorat yig'indilari."""
    print("[4/4] reliz manifesti yozilmoqda…")

    def digest(path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    artefacts = [{"name": exe.name, "path": str(exe.relative_to(_ROOT)),
                  "sha256": digest(exe), "size_bytes": exe.stat().st_size}]
    if installer is not None:
        artefacts.append({
            "name": installer.name, "path": str(installer.relative_to(_ROOT)),
            "sha256": digest(installer), "size_bytes": installer.stat().st_size,
        })

    manifest = {
        "product": _APP_NAME,
        "version": _VERSION,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "aether_protocol": "5.1",
        "artefacts": artefacts,
        "note": (
            "Nazorat yig'indilarini tarqatishdan oldin e'lon qiling. "
            "Ochiq broker bilan yig'ilgan build 'production-secure' deb "
            "belgilanmaydi."
        ),
    }
    path = _DIST / "release-manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"      tayyor: {path}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="DistribOS AI Windows build")
    parser.add_argument("--exe-only", action="store_true", help="installer yig'ilmasin")
    parser.add_argument("--skip-test", action="store_true", help="smoke testni o'tkazib yubor")
    arguments = parser.parse_args()

    print(f"DistribOS AI {_VERSION} — Windows build\n")

    exe = build_exe()
    if not arguments.skip_test:
        smoke_test(exe)

    installer = None if arguments.exe_only else build_installer(exe)
    write_manifest(exe, installer)

    print("\nBAJARILDI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
