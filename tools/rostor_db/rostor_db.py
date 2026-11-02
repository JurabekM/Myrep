"""ROSTOR-2 offlayn bazasini yig'ish va imzolash vositasi (developer kompyuterida ishlaydi).

Buyruqlar:
  keygen  — imzolash kalitlarini yaratadi (repo TASHQARISIGA) va ochiq kalitlarni
            Kotlin'dagi DbKeys.kt ga yozadi.
  build   — registry/registry.json dan imzolangan bundle yasaydi:
            app/android/app/src/main/assets/db/rostor-db.bundle.json
  kat     — Kotlin unit testlari uchun test vektorlari (sobit test kalitlari bilan).
  verify  — bundle'ni Python'da mustaqil tekshiradi.

Kriptografiya ROSTOR-1 bilan bir xil: Ed25519 || ML-DSA-65 (cryptography>=46, OpenSSL).
Imzolanadigan xabar: b"ROSTOR-2/db-manifest" || kanonik_JSON(manifest).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import mldsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app" / "android" / "app" / "src"
BUNDLE_PATH = APP / "main" / "assets" / "db" / "rostor-db.bundle.json"
KEYS_KT = APP / "main" / "kotlin" / "uz" / "rostor" / "rostor2" / "db" / "DbKeys.kt"
KAT_PATH = APP / "test" / "resources" / "db-kat.json"
REGISTRY = ROOT / "registry" / "registry.json"
DEFAULT_KEY_DIR = Path(os.environ.get("ROSTOR2_KEY_DIR", r"C:\keys\rostor2\db"))

FORMAT = "ROSTOR-2/db-bundle/v1"
DOMAIN = b"ROSTOR-2/db-manifest"


def canonical(obj) -> bytes:
    """ROSTOR-1 JSON_CANONICAL: tartiblangan kalitlar, bo'shliqsiz, ASCII."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha3(*parts: bytes) -> bytes:
    h = hashlib.sha3_256()
    for p in parts:
        h.update(p)
    return h.digest()


def key_id(ed_pk: bytes, ml_pk: bytes) -> str:
    return sha3(ed_pk, ml_pk).hex()[:16]


def hybrid_sign(ed_sk: Ed25519PrivateKey, ml_sk: mldsa.MLDSA65PrivateKey, msg: bytes) -> bytes:
    return ed_sk.sign(msg) + ml_sk.sign(msg)


def hybrid_verify(ed_pk: bytes, ml_pk: bytes, sig: bytes, msg: bytes) -> bool:
    if len(sig) != 64 + 3309:
        return False
    ok_ed = ok_ml = True
    try:
        Ed25519PublicKey.from_public_bytes(ed_pk).verify(sig[:64], msg)
    except InvalidSignature:
        ok_ed = False
    try:
        mldsa.MLDSA65PublicKey.from_public_bytes(ml_pk).verify(sig[64:], msg)
    except InvalidSignature:
        ok_ml = False
    return ok_ed and ok_ml


def make_bundle(payload: bytes, version: int, issued_at: int, ed_sk, ml_sk) -> dict:
    ed_pk = ed_sk.public_key().public_bytes_raw()
    ml_pk = ml_sk.public_key().public_bytes_raw()
    manifest = canonical({
        "v": 1,
        "db_version": version,
        "issued_at": issued_at,
        "payload_len": len(payload),
        "payload_sha3_256": sha3(payload).hex(),
        "key_id": key_id(ed_pk, ml_pk),
    })
    sig = hybrid_sign(ed_sk, ml_sk, DOMAIN + manifest)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    return {"format": FORMAT, "manifest": b64(manifest), "sig": b64(sig), "payload": b64(payload)}


def load_keys(key_dir: Path):
    ed_sk = Ed25519PrivateKey.from_private_bytes((key_dir / "ed25519.seed").read_bytes())
    ml_sk = mldsa.MLDSA65PrivateKey.from_seed_bytes((key_dir / "mldsa65.seed").read_bytes())
    return ed_sk, ml_sk


def write_keys_kt(ed_pk: bytes, ml_pk: bytes, note: str) -> None:
    chunks = [ml_pk.hex()[i:i + 96] for i in range(0, len(ml_pk) * 2, 96)]
    ml_lines = "\n".join(f'        "{c}" +' for c in chunks).rstrip(" +")
    KEYS_KT.write_text(
        f"""package uz.rostor.rostor2.db

import uz.rostor.rostor2.crypto.hexToBytes

/**
 * Baza imzosining ochiq kalitlari (Q5). AVTOMATIK yozilgan: tools/rostor_db/rostor_db.py keygen.
 * {note}
 * key_id = {key_id(ed_pk, ml_pk)}
 */
object DbKeys {{
    val ED25519_PK: ByteArray = "{ed_pk.hex()}".hexToBytes()

    val MLDSA65_PK: ByteArray = (
{ml_lines}
    ).hexToBytes()
}}
""",
        encoding="utf-8",
        newline="\n",
    )


def cmd_keygen(args) -> None:
    key_dir: Path = args.key_dir
    if (key_dir / "ed25519.seed").exists() and not args.force:
        ed_sk, ml_sk = load_keys(key_dir)
        print(f"kalitlar mavjud: {key_dir} (qayta yaratish uchun --force)")
    else:
        key_dir.mkdir(parents=True, exist_ok=True)
        ed_sk = Ed25519PrivateKey.generate()
        ml_sk = mldsa.MLDSA65PrivateKey.generate()
        (key_dir / "ed25519.seed").write_bytes(
            ed_sk.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        )
        (key_dir / "mldsa65.seed").write_bytes(ml_sk.private_bytes_raw())
        print(f"yangi kalitlar yozildi: {key_dir}")
    ed_pk = ed_sk.public_key().public_bytes_raw()
    ml_pk = ml_sk.public_key().public_bytes_raw()
    write_keys_kt(ed_pk, ml_pk, f"Maxfiy kalitlar repo tashqarisida: {key_dir}")
    print(f"DbKeys.kt yangilandi, key_id={key_id(ed_pk, ml_pk)}")


def validate_registry(reg: dict) -> list[str]:
    """Q2/F2 qoidasi: tasdiqlanmagan yozuv bazaga kirmaydi; har yozuvda manba bo'lishi shart."""
    problems = []
    for org in reg.get("organizations", []):
        name = org.get("id", "?")
        if org.get("confidence") not in ("verified", "partial"):
            problems.append(f"{name}: confidence={org.get('confidence')!r}")
        for d in org.get("domains", []):
            if d != d.lower() or d.startswith("www.") or "/" in d:
                problems.append(f"{name}: domen kanonik emas: {d}")
        if org.get("domains") and not org.get("domain_sources"):
            problems.append(f"{name}: domen manbasi yo'q")
        for p in org.get("packages", []):
            if not p.get("source"):
                problems.append(f"{name}: paket manbasi yo'q: {p.get('id')}")
            for c in p.get("cert_sha256", []):
                if len(c) != 64:
                    problems.append(f"{name}: sertifikat izi 64 hex emas: {c}")
        for ph in org.get("phones", []):
            if not ph.get("source"):
                problems.append(f"{name}: telefon manbasi yo'q: {ph.get('number')}")
    return problems


def cmd_build(args) -> None:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    problems = validate_registry(reg)
    if problems:
        print("registry xatolari:\n  " + "\n  ".join(problems))
        sys.exit(2)
    version = int(reg["db_version"])
    payload = canonical(reg)
    ed_sk, ml_sk = load_keys(args.key_dir)
    bundle = make_bundle(payload, version, int(time.time()), ed_sk, ml_sk)
    BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE_PATH.write_text(json.dumps(bundle, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"bundle: {BUNDLE_PATH} (v{version}, payload {len(payload)} bayt, {len(reg.get('organizations', []))} tashkilot)")
    verify_file(BUNDLE_PATH, ed_sk.public_key().public_bytes_raw(), ml_sk.public_key().public_bytes_raw())


def verify_file(path: Path, ed_pk: bytes, ml_pk: bytes) -> None:
    b = json.loads(path.read_text(encoding="utf-8"))
    manifest = base64.b64decode(b["manifest"])
    payload = base64.b64decode(b["payload"])
    assert b["format"] == FORMAT
    assert hybrid_verify(ed_pk, ml_pk, base64.b64decode(b["sig"]), DOMAIN + manifest), "imzo haqiqiy emas"
    m = json.loads(manifest)
    assert m["payload_sha3_256"] == sha3(payload).hex(), "xesh mos emas"
    assert m["key_id"] == key_id(ed_pk, ml_pk)
    print(f"tekshirildi: v{m['db_version']} key_id={m['key_id']}")


def cmd_verify(args) -> None:
    ed_sk, ml_sk = load_keys(args.key_dir)
    verify_file(BUNDLE_PATH, ed_sk.public_key().public_bytes_raw(), ml_sk.public_key().public_bytes_raw())


def cmd_kat(args) -> None:
    """Sobit TEST kalitlari (ishlab chiqarish kaliti emas) bilan Kotlin uchun vektorlar."""
    ed_sk = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    ml_sk = mldsa.MLDSA65PrivateKey.from_seed_bytes(bytes(range(32, 64)))
    ed_pk = ed_sk.public_key().public_bytes_raw()
    ml_pk = ml_sk.public_key().public_bytes_raw()
    payload = canonical({"schema": 1, "db_version": 7, "organizations": [], "note": "KAT"})
    bundle = make_bundle(payload, 7, 1_790_000_000, ed_sk, ml_sk)
    kat = {
        "comment": "ROSTOR-2 KAT: sobit test kalitlari, faqat testlar uchun",
        "ed25519_pk": ed_pk.hex(),
        "mldsa65_pk": ml_pk.hex(),
        "key_id": key_id(ed_pk, ml_pk),
        "bundle": json.dumps(bundle),
        "db_version": 7,
        "payload_sha3_256": sha3(payload).hex(),
    }
    # ROSTOR-1 referens kodining o'zi bilan imzolangan vektor: Kotlin tekshiruvi aynan
    # scutum.crypto.primitives.hybrid_sign chiqishini qabul qilishini isbotlaydi.
    scutum = Path(args.scutum) if args.scutum else None
    if scutum and (scutum / "scutum" / "crypto" / "primitives.py").exists():
        sys.path.insert(0, str(scutum))
        from scutum.crypto import primitives as p1  # type: ignore

        msg = b"ROSTOR-1/apk-attestation" + canonical({"package_name": "uz.rostor.kat", "version_code": 1})
        sig = p1.hybrid_sign(ed_sk, ml_sk, msg)
        kat["rostor1_vector"] = {"msg": msg.hex(), "sig": sig.to_bytes().hex()}
        assert p1.hybrid_verify(ed_pk, ml_pk, sig, msg)
    KAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    KAT_PATH.write_text(json.dumps(kat, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"KAT yozildi: {KAT_PATH} (rostor1_vector={'bor' if 'rostor1_vector' in kat else 'yoq'})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key-dir", type=Path, default=DEFAULT_KEY_DIR)
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen")
    k.add_argument("--force", action="store_true")
    sub.add_parser("build")
    sub.add_parser("verify")
    kt = sub.add_parser("kat")
    kt.add_argument("--scutum", default=str(ROOT.parents[2] / "scutum_q1"))
    args = ap.parse_args()
    {"keygen": cmd_keygen, "build": cmd_build, "verify": cmd_verify, "kat": cmd_kat}[args.cmd](args)


if __name__ == "__main__":
    main()
