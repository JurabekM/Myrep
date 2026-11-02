"""ROSTOR-2 firibgarlik hisobotlari — developer vositasi (F3).

Foydalanuvchilar hisobotni o'zlari 102, bank yoki developerga yuboradi. Bu vosita kelgan
.json fayllarni tekshiradi va bir xil firibgar bo'yicha guruhlaydi:

  py tools/rostor_report/rostor_report.py verify <fayl.json> [...]
  py tools/rostor_report/rostor_report.py aggregate <papka> [--out nomzodlar.json]
  py tools/rostor_report/rostor_report.py kat

Signal, hukm emas (ROSTOR-1 §14.2): `aggregate` faqat NOMZOD chiqaradi. Bazaga
(registry/registry.json -> malicious) qo'shishdan oldin har nomzod qo'lda tekshiriladi.
Qurilma kaliti arzon yaratiladi, shuning uchun MIN_K to'liq Sybil-himoya emas (ROSTOR-1 §20).
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rostor_db"))
from rostor_db import hybrid_sign, hybrid_verify, sha3  # noqa: E402

from cryptography.hazmat.primitives.asymmetric import mldsa  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

FORMAT = "ROSTOR-2/fraud-report/v1"
DOMAIN = b"ROSTOR-2/fraud-report"
TARGET_DOMAIN = b"ROSTOR-1/report-target"
ROOT = Path(__file__).resolve().parents[2]
KAT_PATH = ROOT / "app" / "android" / "app" / "src" / "test" / "resources" / "report-kat.json"

# ROSTOR-1 SPEC 1.1 §15.2 normativ konstantalari
BASE_WEIGHT = 1
MIN_K = 5
SCORE_THRESHOLD = 15
RATE_LIMIT_PER_DAY = 10
DECAY_WINDOW_SECS = 90 * 86400


def device_id(ed_pk: bytes, ml_pk: bytes) -> str:
    return sha3(ed_pk, ml_pk).hex()[:32]


def target_hash(target_type: str, value: str) -> str:
    return sha3(TARGET_DOMAIN, target_type.encode(), value.encode()).hex()


def verify(raw: str) -> tuple[bool, str, dict | None]:
    """-> (ok, xato, content). Faqat imzolangan `content` ga ishoniladi; `readable` e'tiborga olinmaydi."""
    try:
        f = json.loads(raw)
    except ValueError:
        return False, "JSON emas", None
    if f.get("format") != FORMAT:
        return False, "noma'lum format", None
    try:
        content = base64.b64decode(f["content"], validate=True)
        sig = base64.b64decode(f["sig"], validate=True)
        ed_pk = base64.b64decode(f["ed25519_pk"], validate=True)
        ml_pk = base64.b64decode(f["mldsa65_pk"], validate=True)
    except (KeyError, ValueError):
        return False, "maydonlar buzilgan", None
    if len(ed_pk) != 32 or len(ml_pk) != 1952 or not hybrid_verify(ed_pk, ml_pk, sig, DOMAIN + content):
        return False, "imzo haqiqiy emas", None
    c = json.loads(content)
    did = device_id(ed_pk, ml_pk)
    if f.get("device_id") != did or c.get("device_id") != did:
        return False, "qurilma ID mos emas", None
    if c.get("v") != 1:
        return False, "hisobot versiyasi qo'llab-quvvatlanmaydi", None
    if c.get("target_value_hash") != target_hash(c.get("target_type", ""), c.get("target_value", "")):
        return False, "target xeshi mos emas", None
    return True, "", c


def cmd_verify(args) -> None:
    bad = 0
    for p in args.files:
        ok, err, c = verify(Path(p).read_text(encoding="utf-8"))
        if ok:
            print(f"OK   {p}: {c['category']} {c['target_type']}={c['target_value']} qurilma={c['device_id'][:12]}")
        else:
            bad += 1
            print(f"XATO {p}: {err}")
    sys.exit(1 if bad else 0)


def aggregate(contents: list[dict], now: int) -> list[dict]:
    """Bir xil (target_type, target_value_hash) bo'yicha guruhlash, ROSTOR-1 §15.2 chegaralari bilan."""
    seen_ids: set[str] = set()
    per_device_day: dict[tuple[str, int], int] = defaultdict(int)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for c in sorted(contents, key=lambda c: c["created_at"]):
        if c["report_id"] in seen_ids or now - c["created_at"] > DECAY_WINDOW_SECS or c["created_at"] > now + 300:
            continue
        seen_ids.add(c["report_id"])
        day = (c["device_id"], c["created_at"] // 86400)
        per_device_day[day] += 1
        if per_device_day[day] > RATE_LIMIT_PER_DAY:
            continue
        groups[(c["target_type"], c["target_value_hash"])].append(c)
    out = []
    for (ttype, thash), rs in groups.items():
        # Bitta qurilma bir firibgar haqida necha marta yozmasin — bir ovoz.
        devices = {r["device_id"] for r in rs}
        score = BASE_WEIGHT * len(devices)
        out.append({
            "target_type": ttype,
            "target_value": rs[0]["target_value"],
            "target_value_hash": thash,
            "distinct_devices": len(devices),
            "score": score,
            "candidate": score >= SCORE_THRESHOLD and len(devices) >= MIN_K,
            "categories": sorted({r["category"] for r in rs}),
            "claimed_orgs": sorted({r["claimed_org"] for r in rs if r.get("claimed_org")}),
            "first_seen": min(r["created_at"] for r in rs),
            "last_seen": max(r["created_at"] for r in rs),
            "report_ids": [r["report_id"] for r in rs],
        })
    return sorted(out, key=lambda g: (-g["candidate"], -g["distinct_devices"], g["target_type"]))


def cmd_aggregate(args) -> None:
    contents, bad = [], 0
    for p in sorted(Path(args.dir).rglob("*.json")):
        ok, err, c = verify(p.read_text(encoding="utf-8"))
        if ok:
            contents.append(c)
        else:
            bad += 1
            print(f"rad etildi {p.name}: {err}")
    groups = aggregate(contents, int(args.now or time.time()))
    for g in groups:
        mark = "NOMZOD" if g["candidate"] else "signal"
        print(f"{mark:7} {g['target_type']:8} {g['target_value']:<28} qurilmalar={g['distinct_devices']} ball={g['score']} {','.join(g['categories'])}")
    print(f"\n{len(contents)} ta haqiqiy hisobot, {bad} ta rad etildi, "
          f"{sum(g['candidate'] for g in groups)} ta nomzod (chegara: {MIN_K} qurilma va {SCORE_THRESHOLD} ball).")
    if args.out:
        Path(args.out).write_text(json.dumps({
            "comment": "Nomzodlar — tasdiqlanmagan. Registry'ga qo'shishdan oldin har birini qo'lda tekshiring.",
            "generated_at": int(time.time()),
            "groups": groups,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"yozildi: {args.out}")


def make_report(content: dict, ed_sk: Ed25519PrivateKey, ml_sk: mldsa.MLDSA65PrivateKey) -> dict:
    ed_pk = ed_sk.public_key().public_bytes_raw()
    ml_pk = ml_sk.public_key().public_bytes_raw()
    raw = json.dumps(content, ensure_ascii=False).encode("utf-8")
    sig = hybrid_sign(ed_sk, ml_sk, DOMAIN + raw)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return {"format": FORMAT, "content": b64(raw), "sig": b64(sig), "ed25519_pk": b64(ed_pk),
            "mldsa65_pk": b64(ml_pk), "device_id": device_id(ed_pk, ml_pk), "readable": "(Python KAT)"}


def cmd_kat(args) -> None:
    """Sobit TEST kalitlari (db-kat bilan bir xil urug'lar) bilan Kotlin uchun vektor."""
    ed_sk = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    ml_sk = mldsa.MLDSA65PrivateKey.from_seed_bytes(bytes(range(32, 64)))
    did = device_id(ed_sk.public_key().public_bytes_raw(), ml_sk.public_key().public_bytes_raw())
    content = {
        "v": 1, "report_id": "00112233445566778899aabbccddeeff", "created_at": 1_790_000_000,
        "category": "T2", "target_type": "phone", "target_value": "+998901234567",
        "target_value_hash": target_hash("phone", "+998901234567"), "claimed_org": "Uzcard",
        "incident_at": None, "amount_uzs": 1500000, "description": "Xavfsizlik xizmati deb SMS kod so'radi",
        "evidence": [{"kind": "call", "value": "+998 90 123 45 67"}], "findings": ["call.no_signal"],
        "reporter_contact": None, "app": {"version": "kat", "db_version": 1}, "device_id": did,
    }
    kat = {
        "comment": "ROSTOR-2 hisobot KAT: sobit test kalitlari, faqat testlar uchun",
        "report": json.dumps(make_report(content, ed_sk, ml_sk)),
        "device_id": did,
        "target_value_hash": content["target_value_hash"],
    }
    ok, err, _ = verify(kat["report"])
    assert ok, err
    KAT_PATH.write_text(json.dumps(kat, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"yozildi: {KAT_PATH} (device_id={did})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify"); v.add_argument("files", nargs="+"); v.set_defaults(fn=cmd_verify)
    a = sub.add_parser("aggregate"); a.add_argument("dir"); a.add_argument("--out"); a.add_argument("--now", type=int)
    a.set_defaults(fn=cmd_aggregate)
    k = sub.add_parser("kat"); k.set_defaults(fn=cmd_kat)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
