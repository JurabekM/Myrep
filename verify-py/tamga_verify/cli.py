"""python -m tamga_verify <jurnal.jsonl> [--checkpoints <fayl>] [--key <ochiq-kalit.json>] [--payloads <papka>]

Chiqish kodi: 0 — butun, 1 — buzilish, 2 — foydalanish/o'qish xatosi (Rust `tamga-verify` bilan bir xil).
"""

import argparse
import json
import sys
from pathlib import Path

from .verify import PublicKey, VerifyError, payload_opens, verify_all, verify_log


def _read(path: str, code: str = "E_PARSE") -> str:
    raw = Path(path).read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as e:
        line = raw[: e.start].count(b"\n")
        raise VerifyError(code, line, "UTF-8 emas") from None


def _check_payloads(log_text: str, folder: Path) -> list[str]:
    """Dalil to'plamidagi `payloads/manifest.json`: har payload jurnaldagi majburiyatga mosligi."""
    records = {json.loads(l)["seq"]: json.loads(l) for l in log_text.splitlines() if l}
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    problems = []
    for item in manifest["payloads"]:
        rec = records.get(item["seq"], {})
        ref = rec.get("tool", {}).get("input") if item["field"] == "input" else rec.get("result")
        data = (folder / item["file"]).read_bytes()
        if not ref or not payload_opens(ref, bytes.fromhex(item["salt"]), data):
            problems.append(f"#{item['seq']} {item['field']}: payload jurnaldagi digest bilan mos emas")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tamga-verify-py", description="TAMGA Record 0.1 mustaqil verifikatori")
    ap.add_argument("log")
    ap.add_argument("--checkpoints")
    ap.add_argument("--key")
    ap.add_argument("--payloads", help="dalil to'plamidagi payloads/ papkasi")
    ap.add_argument("--json", action="store_true", help="natijani JSON ko'rinishida chiqarish")
    a = ap.parse_args(argv)
    if bool(a.checkpoints) != bool(a.key):
        print("xato: --checkpoints va --key birga beriladi (kalit operatordan olinadi, spec §10)", file=sys.stderr)
        return 2
    try:
        log = _read(a.log)
        if a.checkpoints:
            pk = PublicKey.from_json(json.loads(Path(a.key).read_text(encoding="utf-8")))
            cps = _read(a.checkpoints, "E_CKPT_FORMAT")
            # L-2: checkpoint fayli berilgan, lekin bo'sh, jurnal esa bo'sh emas — imzo chetlab o'tilmasin.
            if not cps.strip() and log.strip():
                raise VerifyError("E_CKPT_FORMAT", 0, "checkpoint fayli bo'sh, jurnal esa bo'sh emas")
            rep = verify_all(log, cps, pk)
        else:
            rep = verify_log(log)
        problems = _check_payloads(log, Path(a.payloads)) if a.payloads else []
    except VerifyError as e:
        if a.json:
            print(json.dumps({"ok": False, "code": e.code, "index": e.index, "detail": e.detail}))
        else:
            print(f"BUZILISH: {e.code} — indeks {e.index}: {e.detail}")
        return 1
    except (OSError, ValueError) as e:
        print(f"xato: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"ok": not problems, "records": len(rep.hashes), "checkpoints": len(rep.checkpoints), "keys": rep.keys, "key_warnings": rep.key_warnings, "payload_problems": problems}))
    else:
        sealed = max((c["size"] for c in rep.checkpoints), default=0)
        print(f"OK: `{rep.log}` jurnali butun — {len(rep.hashes)} yozuv, {len(rep.checkpoints)} ta checkpoint (Ed25519 + ML-DSA-65), muhrlangan: {sealed}.")
        if not a.checkpoints:
            print("Eslatma: checkpoint'siz faqat ichki izchillik tekshiriladi; oxirini kesish sezilmaydi.")
        if len(rep.keys) > 1:
            print("Kalitlar zanjiri (spec §7.5): " + " → ".join(rep.keys))
        for w in rep.warnings + rep.key_warnings:
            print(f"ogohlantirish: {w}")
        for p in problems:
            print(f"PAYLOAD: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
