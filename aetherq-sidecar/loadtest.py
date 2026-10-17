#!/usr/bin/env python3
"""
AETHER-Q sidecar — yuk sinovi.

Avval HAMMA narsani qayta yig'adi (eski binar o'lchanmasligi uchun — bu qadamni o'tkazib yuborish yo'q):
  aq-sidecar (Rust, release) → dist/aq-sidecar.exe
  aqctl, aether_new (Go)      → dist/aqctl.exe, dist/aether_new.exe
  aqload (Go, yuk generatori) → bin/aqload.exe
so'ng aqload'ni ishga tushiradi. Natija: loadtest-out/report.md va report.json.

Ishga tushirish (Windows, Python 3.8+ — faqat stdlib):
    python loadtest.py            # to'liq sinov: 10 000 so'rov, 1000 ulanish, parallellik (bir necha daqiqa)
    python loadtest.py --quick    # tez tekshiruv (≈1 daqiqa), qabul mezoni sifatida hisoblanmaydi
    python loadtest.py -- -conc 32 -hs 2000   # '--' dan keyingi argumentlar aqload'ga uzatiladi
"""

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
EXE = ".exe" if os.name == "nt" else ""


def find_go():
    cand = [os.environ.get("GO"), str(pathlib.Path.home() / "tools" / "go" / "bin" / ("go" + EXE)), shutil.which("go")]
    for c in cand:
        if c and pathlib.Path(c).exists():
            return c
    sys.exit("XATO: Go topilmadi (GO muhit o'zgaruvchisi, ~/tools/go yoki PATH)")


def step(title, cmd, cwd):
    print(f"  {title} ...", flush=True)
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        sys.exit(f"XATO: {title} muvaffaqiyatsiz (kod {r.returncode})")


def build(go):
    print("[yig'ish] eski binar o'lchanmasligi uchun hammasi qayta yig'iladi")
    dist, binp = HERE / "dist", HERE / "bin"
    dist.mkdir(exist_ok=True)
    binp.mkdir(exist_ok=True)
    if os.name == "nt":
        cargo = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "scripts" / "cargo-msvc.ps1"),
                 "build", "--release", "-p", "aq-sidecar"]
    else:
        cargo = ["cargo", "build", "--release", "-p", "aq-sidecar"]
    step("aq-sidecar (Rust, release)", cargo, HERE)
    shutil.copy2(HERE / "target" / "release" / ("aq-sidecar" + EXE), dist / ("aq-sidecar" + EXE))
    step("aqctl (Go)", [go, "build", "-o", str(dist / ("aqctl" + EXE)), "./cmd/aqctl"], HERE / "control")
    step("aether_new (Go)", [go, "build", "-o", str(dist / ("aether_new" + EXE)), "."], HERE / "aether_new")
    step("aqload (Go, yuk generatori)", [go, "build", "-o", str(binp / ("aqload" + EXE)), "."], HERE / "loadtest")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="tez tekshiruv (kichik hajmlar)")
    # '--' dan keyingi argumentlar aqload'ga (argparse.REMAINDER ishlatilmaydi: u --help ni yutib yuboradi).
    argv, extra = sys.argv[1:], []
    if "--" in argv:
        i = argv.index("--")
        argv, extra = argv[:i], argv[i + 1:]
    args = ap.parse_args(argv)

    build(find_go())
    cmd = [str(HERE / "bin" / ("aqload" + EXE)), "-bin", str(HERE / "dist"), "-out", str(HERE / "loadtest-out")]
    if args.quick:
        cmd.append("-quick")
    cmd += extra
    print("\n[sinov]", " ".join(cmd[1:]), "\n", flush=True)
    return subprocess.call(cmd, cwd=str(HERE))


if __name__ == "__main__":
    sys.exit(main())
