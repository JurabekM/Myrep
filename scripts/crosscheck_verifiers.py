"""Rust `tamga-verify` va Python `verify-py` hukmlarini haqiqiy jurnallarda va ularning tasodifiy
buzilgan variantlarida solishtiradi. Ikkalasi ham bir xil (natija, kod, indeks) berishi shart.

Ishga tushirish:  py scripts/crosscheck_verifiers.py <tamga-verify.exe> <TAMGA_HOME>...
"""

import json
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def rust(exe: str, log: Path, cps: Path, key: Path) -> tuple:
    out = subprocess.run([exe, str(log), "--checkpoints", str(cps), "--key", str(key)], capture_output=True, text=True, encoding="utf-8").stdout
    m = re.search(r"BUZILISH: (E_\w+) — indeks (\d+)", out)
    return ("FAIL", m.group(1), int(m.group(2))) if m else ("OK", None, None)


def python(log: Path, cps: Path, key: Path) -> tuple:
    out = subprocess.run(
        [sys.executable, "-m", "tamga_verify", str(log), "--checkpoints", str(cps), "--key", str(key), "--json"],
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT / "verify-py",
    ).stdout
    v = json.loads(out)
    return ("OK", None, None) if v["ok"] else ("FAIL", v["code"], v["index"])


def mutations(lines: list[str], rng: random.Random):
    n = len(lines)
    yield "asl", lines
    if n < 3:
        return
    i = rng.randrange(n)
    edited = list(lines)
    edited[i] = edited[i].replace('"seq":', '"seq": ', 1) if rng.random() < 0.3 else edited[i].replace("e", "E", 1)
    yield f"o'zgartirish #{i}", edited
    j = rng.randrange(n)
    yield f"o'chirish #{j}", lines[:j] + lines[j + 1 :]
    k = rng.randrange(n - 1)
    swapped = list(lines)
    swapped[k], swapped[k + 1] = swapped[k + 1], swapped[k]
    yield f"almashtirish #{k}", swapped
    yield "oxirini kesish", lines[: n - 2]


def main() -> int:
    exe, homes = sys.argv[1], [Path(h) for h in sys.argv[2:]]
    rng = random.Random(2026)
    total = mismatches = 0
    for home in homes:
        logs = sorted((home / "logs").glob("*.jsonl"))
        if not logs:
            continue
        log, key = logs[0], home / "public-key.json"
        cps = log.with_suffix(".checkpoints")
        lines = log.read_text(encoding="utf-8").splitlines(keepends=True)
        for label, variant in mutations(lines, rng):
            with tempfile.TemporaryDirectory() as tmp:
                vlog = Path(tmp) / "log.jsonl"
                vlog.write_text("".join(variant), encoding="utf-8", newline="")
                r, p = rust(exe, vlog, cps, key), python(vlog, cps, key)
            total += 1
            same = r == p
            mismatches += not same
            print(f"[{'MOS' if same else 'FARQ'}] {home.name:<10} {label:<18} rust={r} py={p}")
    print(f"\nJAMI: {total} holat, farq: {mismatches}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
