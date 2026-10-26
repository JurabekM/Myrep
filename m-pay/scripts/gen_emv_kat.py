#!/usr/bin/env python3
"""M-Pay Test Scheme KAT vektorlari generatori — Rust'dan MUSTAQIL implementatsiya.

Faqat `docs/specs/emv-profile.md` asosida yozilgan (Rust kodidan ko'chirilmagan) va
Python `cryptography` kutubxonasining AES-CMAC'idan foydalanadi. Rust testi
(`crates/mpay-crypto/tests/emv_kat.rs`) shu fayldagi har bir oraliq qiymatni tekshiradi —
ikki mustaqil implementatsiya mos kelishi sxema to'g'ri amalga oshirilganini ko'rsatadi.

Ishga tushirish:
    python scripts/gen_emv_kat.py > testvectors/emv-kat.json

Barcha kalitlar FIKTIV test qiymatlari; PAN'lar M-Pay test BIN diapazonidan.
"""

import json
import sys

from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.cmac import CMAC


def cmac(key: bytes, data: bytes) -> bytes:
    c = CMAC(algorithms.AES(key))
    c.update(data)
    return c.finalize()


def kdf(key: bytes, label: bytes, context: bytes) -> bytes:
    # SP 800-108r1 counter: [i]_8 || Label || 0x00 || Context || [L]_16, L = 128
    return cmac(key, b"\x01" + label + b"\x00" + context + (128).to_bytes(2, "big"))


def luhn_digit(payload: str) -> str:
    total = 0
    for i, ch in enumerate(reversed(payload)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def bcd(value: int, nbytes: int) -> bytes:
    s = str(value).rjust(nbytes * 2, "0")
    assert len(s) == nbytes * 2
    return bytes.fromhex(s)


def pdol_data(t: dict) -> bytes:
    return (
        bcd(t["amount_minor"], 6)
        + bcd(t["other_amount_minor"], 6)
        + bcd(t["country"], 2)
        + bytes.fromhex(t["tvr"])
        + bcd(t["currency"], 2)
        + bytes.fromhex(t["date_yymmdd"])
        + bcd(t["txn_type"], 1)
        + bytes.fromhex(t["un"])
    )


AIP = bytes.fromhex("0080")


def case(name, imk_hex, dpan_prefix, psn, luk_seq, atc, cvr, terminal, arc):
    imk = bytes.fromhex(imk_hex)
    dpan = dpan_prefix + luhn_digit(dpan_prefix)
    mk_ctx = bytes([len(dpan)]) + dpan.encode() + bytes([psn])
    mk = kdf(imk, b"MPAY-TOKEN-MK", mk_ctx)
    luk = kdf(mk, b"MPAY-LUK", luk_seq.to_bytes(4, "big"))
    sk = kdf(luk, b"MPAY-SK-AC", atc.to_bytes(2, "big"))
    iad = bytes([0x01, 0x01]) + luk_seq.to_bytes(4, "big") + bytes([cvr, 0x00])
    pdol = pdol_data(terminal)
    assert len(pdol) == 29
    cdol = pdol + AIP + atc.to_bytes(2, "big") + iad
    assert len(cdol) == 41
    arqc = cmac(sk, cdol)[:8]
    arpc = cmac(sk, arqc + arc.encode())[:4]
    return {
        "name": name,
        "imk": imk_hex,
        "dpan": dpan,
        "psn": psn,
        "mk_context": mk_ctx.hex(),
        "token_master_key": mk.hex(),
        "luk_seq": luk_seq,
        "luk": luk.hex(),
        "atc": atc,
        "session_key": sk.hex(),
        "terminal": terminal,
        "pdol_data": pdol.hex(),
        "iad": iad.hex(),
        "cdol": cdol.hex(),
        "arqc": arqc.hex(),
        "arc": arc,
        "arpc": arpc.hex(),
    }


def main() -> None:
    t1 = {
        "amount_minor": 1_250_000,
        "other_amount_minor": 0,
        "country": 860,
        "tvr": "0000000000",
        "currency": 860,
        "date_yymmdd": "261023",
        "txn_type": 0,
        "un": "a1b2c3d4",
    }
    t2 = dict(t1, amount_minor=99, un="00000001", tvr="0000008000")
    t3 = dict(t1, amount_minor=999_999_999_999, other_amount_minor=5_000, date_yymmdd="280229", un="ffffffff")
    vectors = {
        "scheme": "MPAY-AES128-CMAC-V1",
        "generator": "scripts/gen_emv_kat.py (Python cryptography, Rust'dan mustaqil)",
        "cases": [
            case("basic", "000102030405060708090a0b0c0d0e0f", "990077000000123", 0, 1, 1, 0x80, t1, "00"),
            case("decline-arc", "000102030405060708090a0b0c0d0e0f", "990077000000123", 0, 1, 2, 0x80, t2, "05"),
            case("max-values", "fedcba9876543210f0e1d2c3b4a59687", "990099999999999", 1, 0xFFFFFFFF, 0xFFFF, 0x00, t3, "Q1"),
        ],
    }
    json.dump(vectors, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
