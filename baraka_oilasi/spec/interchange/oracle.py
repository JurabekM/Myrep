#!/usr/bin/env python3
"""`.baraka` formati uchun mustaqil oracle (Rust kodidan alohida yozilgan).

Rust (`core/crates/interchange`) va kelajakdagi Dart ilovasi shu vektorlarga mos kelishi shart:
konteyner baytlari (Argon2id + XChaCha20-Poly1305), kanonik JSON va yozuv xeshi,
birlashtirish qarorlari jadvali.

    python3 -I spec/interchange/oracle.py --selftest
    python3 -I spec/interchange/oracle.py --generate spec/interchange/vectors.json
    python3 -I spec/interchange/oracle.py --check spec/interchange/vectors.json

Kerak: `cryptography` (Argon2id va ChaCha20-Poly1305). XChaCha uchun HChaCha20 shu yerda.
"""
import argparse
import base64
import hashlib
import json
import struct
import sys
import unicodedata

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

MAGIC = b"BARAKA-EXPORT\n"
FORMAT_VERSION = 1


# ---- HChaCha20 / XChaCha20-Poly1305 (draft-irtf-cfrg-xchacha) ----

def _rotl(v, n):
    return ((v << n) & 0xFFFFFFFF) | (v >> (32 - n))


def _qr(s, a, b, c, d):
    s[a] = (s[a] + s[b]) & 0xFFFFFFFF; s[d] = _rotl(s[d] ^ s[a], 16)
    s[c] = (s[c] + s[d]) & 0xFFFFFFFF; s[b] = _rotl(s[b] ^ s[c], 12)
    s[a] = (s[a] + s[b]) & 0xFFFFFFFF; s[d] = _rotl(s[d] ^ s[a], 8)
    s[c] = (s[c] + s[d]) & 0xFFFFFFFF; s[b] = _rotl(s[b] ^ s[c], 7)


def hchacha20(key, nonce16):
    s = list(struct.unpack("<4I", b"expand 32-byte k")) + list(struct.unpack("<8I", key)) + list(
        struct.unpack("<4I", nonce16))
    for _ in range(10):
        _qr(s, 0, 4, 8, 12); _qr(s, 1, 5, 9, 13); _qr(s, 2, 6, 10, 14); _qr(s, 3, 7, 11, 15)
        _qr(s, 0, 5, 10, 15); _qr(s, 1, 6, 11, 12); _qr(s, 2, 7, 8, 13); _qr(s, 3, 4, 9, 14)
    return struct.pack("<8I", *(s[0:4] + s[12:16]))


def xchacha_seal(key, nonce24, plaintext, aad):
    sub = hchacha20(key, nonce24[:16])
    return ChaCha20Poly1305(sub).encrypt(b"\x00" * 4 + nonce24[16:], plaintext, aad)


def xchacha_open(key, nonce24, sealed, aad):
    sub = hchacha20(key, nonce24[:16])
    return ChaCha20Poly1305(sub).decrypt(b"\x00" * 4 + nonce24[16:], sealed, aad)


# ---- kanonik JSON va xesh ----

def canonical(v):
    if isinstance(v, bool) or isinstance(v, float):
        raise ValueError("bool/float ruxsat etilmaydi")
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def row_hash(table, row):
    return hashlib.sha256(canonical({"t": table, "r": row}).encode()).hexdigest()


def blob(b):
    return {"b64": base64.b64encode(b).decode()}


# ---- konteyner ----

def kdf_key(password, salt, kdf):
    pw = unicodedata.normalize("NFC", password).encode()
    return Argon2id(salt=salt, length=32, iterations=kdf["tCost"], lanes=kdf["pCost"],
                    memory_cost=kdf["mKib"]).derive(pw)


def header_bytes(kdf, salt, nonce):
    header = {"formatVersion": FORMAT_VERSION, "aead": "xchacha20poly1305",
              "kdf": {"alg": "argon2id", "mKib": kdf["mKib"], "tCost": kdf["tCost"], "pCost": kdf["pCost"]},
              "salt": salt.hex(), "nonce": nonce.hex()}
    # Maydonlar tartibi formatning bir qismi (saralanmaydi): AAD shu baytlar.
    return MAGIC + json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"


def plaintext(meta, rows):
    meta = dict(meta, kind="meta", formatVersion=FORMAT_VERSION, rowCount=len(rows))
    lines = [canonical(meta)] + [canonical({"kind": "row", "table": t, "data": d}) for t, d in rows]
    return ("\n".join(lines) + "\n").encode()


def seal(plain, password, kdf, salt, nonce):
    aad = header_bytes(kdf, salt, nonce)
    return aad + xchacha_seal(kdf_key(password, salt, kdf), nonce, plain, aad)


# ---- birlashtirish qarori ----

def decide(local, base, remote, append_only):
    if local is None:
        return "INSERT"
    if local == remote:
        return "SAME"
    if append_only:
        return "PROTECTED"
    if base is not None and remote == base:
        return "KEEP_LOCAL"
    if base is not None and local == base:
        return "UPDATE"
    return "CONFLICT"


# ---- vektorlar ----

FAST = {"mKib": 64, "tCost": 1, "pCost": 1}

META = {
    "schemaVersion": 8,
    "householdId": "0192a000-0000-7000-8000-000000000001",
    "sourceDeviceId": "0192a000-0000-7000-8000-0000000000d1",
    "sourceDeviceName": "Nilufarning telefoni",
    "exportId": "0192a000-0000-7000-8000-0000000000e1",
    "ackExportId": None,
    "mode": "FULL",
    "exportedAt": "2026-10-16T09:00:00.000Z",
}

ROWS = [
    ("incomes", {"id": "0192a000-0000-7000-8000-0000000000a1", "amount_minor": 800000000, "currency": "UZS",
                 "source": "Taksi", "note": None, "occurred_on": "2026-10-15", "version": 1}),
    ("venture_attachments", {"id": "0192a000-0000-7000-8000-0000000000b1", "file_name": "chek.png",
                             "bytes": blob(b"\x89PNG\r\n\x1a\nchek-rasmi")}),
]


def cases():
    out = []
    plain = plaintext(META, ROWS)
    salt = bytes(range(16))
    nonce = bytes(range(16, 40))
    for name, password in [("kat-ascii", "Baraka-2026!"),
                           ("kat-nfc", "Qo‘rg‘on-é")]:
        sealed = seal(plain, password, FAST, salt, nonce)
        out.append({"id": name, "kind": "container", "password": password, "kdf": FAST,
                    "salt": salt.hex(), "nonce": nonce.hex(),
                    "meta": META, "rows": [{"table": t, "data": d} for t, d in ROWS],
                    "plaintextSha256": hashlib.sha256(plain).hexdigest(),
                    "sealedHex": sealed.hex()})
    hashes = [
        ("hash-income", "incomes", ROWS[0][1]),
        ("hash-blob", "venture_attachments", ROWS[1][1]),
        ("hash-unicode", "members", {"id": "m1", "display_name": "Oʻgʻiloy \"Gulya\"\n", "role": "ADULT",
                                     "deleted_at": None}),
        ("hash-negative", "journal_entries", {"id": "j1", "amount_minor": -150000000, "seq": 3}),
    ]
    for cid, table, row in hashes:
        out.append({"id": cid, "kind": "rowHash", "table": table, "row": row,
                    "canonical": canonical({"t": table, "r": row}), "expected": row_hash(table, row)})
    merge = [(None, None, "r", False), (None, "b", "r", True), ("x", None, "x", False), ("b", "b", "r", False),
             ("l", "b", "b", False), ("l", "b", "r", False), ("l", None, "r", False), ("l", "l", "r", True),
             ("x", "b", "x", True)]
    for i, (l, b, r, a) in enumerate(merge, 1):
        out.append({"id": f"merge-{i:02d}", "kind": "merge", "local": l, "base": b, "remote": r,
                    "appendOnly": a, "expected": decide(l, b, r, a)})
    return {"suite": "interchange", "formatVersion": FORMAT_VERSION, "cases": out}


def selftest():
    # RFC 8439 2.8.2 bilan ChaCha20-Poly1305, draft-xchacha 2.2.1 bilan HChaCha20.
    key = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
    sub = hchacha20(key, bytes.fromhex("000000090000004a0000000031415927"))
    assert sub.hex() == "82413b4227b27bfed30e42508a877d73a0f9e4d58a74a853c12ec41326d3ecdc", sub.hex()
    # XChaCha20-Poly1305 AEAD test vektori (draft-irtf-cfrg-xchacha-03, A.3.1).
    pt = (b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, "
          b"sunscreen would be it.")
    aad = bytes.fromhex("50515253c0c1c2c3c4c5c6c7")
    k = bytes.fromhex("808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f")
    n = bytes.fromhex("404142434445464748494a4b4c4d4e4f5051525354555657")
    ct = xchacha_seal(k, n, pt, aad)
    assert ct[-16:].hex() == "c0875924c1c7987947deafd8780acf49", ct[-16:].hex()
    assert ct[:8].hex() == "bd6d179d3e83d43b", ct[:8].hex()
    assert xchacha_open(k, n, ct, aad) == pt
    data = cases()
    c = data["cases"][0]
    sealed = bytes.fromhex(c["sealedHex"])
    body = len(header_bytes(FAST, bytes.fromhex(c["salt"]), bytes.fromhex(c["nonce"])))
    assert xchacha_open(kdf_key(c["password"], bytes.fromhex(c["salt"]), FAST), bytes.fromhex(c["nonce"]),
                        sealed[body:], sealed[:body]) == plaintext(META, ROWS)
    # Ikki xil yozilgan parol (NFC) bir xil kalit beradi.
    assert kdf_key("é-parol-123", b"0" * 16, FAST) == kdf_key("é-parol-123", b"0" * 16, FAST)
    print("interchange oracle selftest: OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--generate")
    ap.add_argument("--check")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    if a.generate:
        with open(a.generate, "w", encoding="utf-8") as f:
            json.dump(cases(), f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"yozildi: {a.generate}")
    if a.check:
        with open(a.check, encoding="utf-8") as f:
            stored = json.load(f)
        if stored != cases():
            print("interchange oracle check: FARQ BOR", file=sys.stderr)
            sys.exit(1)
        print("interchange oracle check: OK")


if __name__ == "__main__":
    main()
