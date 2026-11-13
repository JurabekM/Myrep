"""Zarbxona v3 spetsifikatsiyasi uchun namunaviy vektorlar (KAT).

Manba — zarbxona_v2 (Rust `aetherq_mint` va haqiqiy `aqbank` bilan
bayt-ma-bayt mosligi testlarda isbotlangan). Qo'shimcha: har bir partiya
qiymati shu yerda Rust ma'lumotnomasi bilan ham solishtiriladi.

Ishga tushirish (AETHER-Q venv'ida):
    python kat_yarat.py      (kat/zarbxona_kat_v1.json ga yozadi)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

V2 = Path(r"C:\Users\comp_2.1\Desktop\WORKPAD\PYS\zarbxona_v2")
AQ = Path(r"C:\Users\comp_2.1\Downloads\claude_cowork\.claude\worktrees"
          r"\aether-q-v5-1-review-e33212\aetherq_bank")
sys.path[:0] = [str(V2), str(AQ)]

import aetherq_core as aq  # noqa: E402

from core import protokol  # noqa: E402
from core.asos import (L_CHEKLOV, L_ID, L_KONVERT, L_NAZORAT, XAZINA,  # noqa: E402
                       nominallarga_bol, teg_xesh)
from core.kalit import ombor_och, ombor_yarat  # noqa: E402
from core.kupyura import Sarlavha, konvert_kaliti, nazorat_kaliti, note_id_hisobla  # noqa: E402
from core.merkle import ildiz, isbotlar, qavatlar  # noqa: E402
from core.partiya import imzo_xabari, zarb  # noqa: E402
from core.sertifikat import Sertifikat, cheklov_json, cheklov_xeshi  # noqa: E402


def h(b: bytes) -> str:
    return b.hex()


def ketma(n: int, boshi: int = 0) -> bytes:
    return bytes((boshi + i) % 256 for i in range(n))


kat: dict = {"format": "ZARBXONA-KAT", "version": 1,
             "izoh": "Barcha baytlar hex. Manba: zarbxona_v2 (Rust aetherq_mint bilan tasdiqlangan)."}

# --- 1. ibtidolar ----------------------------------------------------------
k32 = ketma(32)
kat["primitivlar"] = {
    "sha3_256": [{"in": h(b""), "out": h(aq.sha3_256(b""))},
                 {"in": h(b"abc"), "out": h(aq.sha3_256(b"abc"))}],
    "kmac256": [
        {"key": h(k32), "data": h(b"salom"), "custom": h(L_ID), "len": 32,
         "out": h(aq.kmac256(k32, b"salom", 32, L_ID))},
        {"key": h(k32), "data": h(b""), "custom": h(b""), "len": 64,
         "out": h(aq.kmac256(k32, b"", 64, b""))},
    ],
    "hkdf_expand_sha3_256": [
        {"prk": h(k32), "info": h(L_KONVERT + ketma(32, 100)), "len": 44,
         "out": h(aq.hkdf_expand(k32, L_KONVERT + ketma(32, 100), 44))},
        {"prk": h(k32), "info": h(b""), "len": 80,
         "out": h(aq.hkdf_expand(k32, b"", 80))},
    ],
    "chacha20poly1305": [
        {"key": h(k32), "nonce": h(ketma(12, 7)), "plaintext": h(b"AETHER-Q"),
         "aad": h(b"sarlavha"),
         "out": h(aq.aead_seal(k32, ketma(12, 7), b"AETHER-Q", b"sarlavha"))},
    ],
    "tagged_hash_be32": [
        {"label": h(b"AETHER-Q-CBDC/CONSTRAINTS/v1"), "parts": [h(b'{"a":1}')],
         "out": h(teg_xesh(b"AETHER-Q-CBDC/CONSTRAINTS/v1", b'{"a":1}'))},
        {"label": h(b"L"), "parts": [h(b""), h(b"xy")],
         "out": h(teg_xesh(b"L", b"", b"xy"))},
    ],
}

# --- 2. ML-DSA-65 ----------------------------------------------------------
urug = ketma(32, 42)
shaxs = aq.Identity.from_seed(urug)
xabar = b"AETHER-Q zarbxona KAT"
imzo = shaxs.sign(xabar)
assert aq.verify(shaxs.public_key, imzo, xabar)
kat["ml_dsa_65"] = {
    "izoh": "FIPS 204 ML-DSA-65, KeyGen urug'i (xi) 32 bayt, sof rejim, kontekst bo'sh. "
            "Imzo tasodifiy (hedged) — baytlar solishtirilmaydi, faqat verify tekshiriladi.",
    "seed": h(urug),
    "public_key": h(shaxs.public_key),
    "public_key_sha3": h(aq.sha3_256(shaxs.public_key)),
    "message": h(xabar),
    "signature": h(imzo),
    "fingerprint": "-".join(aq.sha3_256(shaxs.public_key).hex().upper()[i * 4:i * 4 + 4]
                            for i in range(6)),
}

# --- 3. kalit ombori -------------------------------------------------------
ombor = ombor_yarat(shaxs, "kat-parol-123", n=1 << 12)
assert ombor_och(ombor, "kat-parol-123").public_key == shaxs.public_key
kat["kalit_ombori"] = {"parol": "kat-parol-123", "fayl": json.loads(ombor),
                       "kutilgan_seed": h(urug)}

# --- 4. cheklov ------------------------------------------------------------
c1 = cheklov_json(["seed", "FUEL"], 1_800_000_000_000)
c2 = cheklov_json([], None, 250, "AQ-TAX-01")
kat["cheklov"] = [
    {"kirish": {"toifalar": ["seed", "FUEL"], "muddat_ms": 1_800_000_000_000},
     "json": c1, "xesh": h(cheklov_xeshi(c1))},
    {"kirish": {"soliq_bps": 250, "soliq_hisobi": "AQ-TAX-01"},
     "json": c2, "xesh": h(cheklov_xeshi(c2))},
    {"kirish": {}, "json": "", "xesh": h(cheklov_xeshi(""))},
]

# --- 5. sertifikat ---------------------------------------------------------
bank = aq.Identity.from_seed(ketma(32, 200))
sert = Sertifikat(sert_id=ketma(16, 50), bank_kaliti=bank.public_key,
                  zarbxona_kaliti=shaxs.public_key, nomi="KAT vakolati",
                  limit=50_000_000, boshlanish_ms=1_700_000_000_000,
                  tugash_ms=1_900_000_000_000, imzo=b"")
sert = Sertifikat(**{**sert.__dict__, "imzo": bank.sign(sert.xabar())})
assert sert.imzo_togri
kat["sertifikat"] = {
    "bank_seed": h(ketma(32, 200)),
    "xabar_digest": h(sert.xabar()),
    "fayl": json.loads(sert.faylga()),
}

# --- 6. partiyalar ---------------------------------------------------------
try:
    import aetherq_mint as ref  # Rust ma'lumotnomasi (bo'lsa — ikkinchi tasdiq)
except ImportError:
    ref = None

partiyalar = []
shakllar = [
    ("bitta", [5000], ""),
    ("uchta_toq", [5000, 1000, 1], ""),
    ("yetti_cheklovli", nominallarga_bol(12_345)[:7], c1),
    ("nominallarga_bol_1234567", nominallarga_bol(1_234_567), c2),
]
for nomi, noms, chek in shakllar:
    pid = ketma(16, 10)
    pk = ketma(32, 20)
    mk = ketma(32, 30)
    vaqt = 1_750_000_000_000
    cx = cheklov_xeshi(chek)
    p = zarb(nominallar=noms, sert_id=sert.sert_id, zarbxona_nomi="KAT",
             zaxira_qulfi="AQ-RES-KAT0001", birinchi_seq=101, cheklov_xeshi=cx,
             cheklov_json=chek, zarb_ms=vaqt, partiya_id=pid, partiya_kaliti=pk, master=mk)
    msg = p.xabar()
    p.imzo = shaxs.sign(msg)
    barglar = [k.sarlavha.barg() for k in p.kupyuralar]
    yozuv = {
        "nomi": nomi,
        "kirish": {"partiya_id": h(pid), "partiya_kaliti": h(pk), "master": h(mk),
                   "zarb_ms": vaqt, "sert_id": h(sert.sert_id), "egasi": XAZINA,
                   "birinchi_seq": 101, "zaxira_qulfi": "AQ-RES-KAT0001",
                   "cheklov_json": chek, "nominallar": noms},
        "cheklov_xeshi": h(cx),
        "ildiz": h(p.ildiz),
        "soni": p.soni,
        "jami": p.jami,
        "imzo_xabari": h(msg),
        "imzo_xabari_sha3": h(aq.sha3_256(msg)),
        "imzo": h(p.imzo),
    }
    # kichik partiyalar uchun har kupyura to'liq; kattasi uchun boshi/oxiri
    indekslar = list(range(p.soni)) if p.soni <= 7 else [0, 1, p.soni // 2, p.soni - 2, p.soni - 1]
    kup = []
    for i in indekslar:
        k = p.kupyuralar[i]
        s = k.sarlavha
        kk, nn = konvert_kaliti(mk, s.note_id)
        kup.append({
            "indeks": i,
            "note_id": h(s.note_id),
            "nazorat_kaliti": h(nazorat_kaliti(pk, s.note_id)),
            "konvert_kalit": h(kk), "konvert_nonce": h(nn),
            "sarlavha_kodi": h(s.kodla()),
            "sarlavha_xeshi": h(s.xesh()),
            "barg": h(s.barg()),
            "yadro_ochiq": h(__import__("core.kupyura", fromlist=["Yadro"]).Yadro(
                nazorat=nazorat_kaliti(pk, s.note_id), zarb_ms=vaqt,
                sert_id=sert.sert_id).kodla()),
            "muhr": h(k.muhr),
            "isbot": [h(x) for x in k.isbot],
        })
    yozuv["kupyuralar"] = kup
    if p.soni > 7:
        yozuv["barglar_sha3"] = h(aq.sha3_256(b"".join(barglar)))
        yozuv["qavatlar_soni"] = len(qavatlar(barglar))

    # ikkinchi tasdiq: Rust ma'lumotnomasi
    if ref is None:
        raise SystemExit("aetherq_mint (Rust ma'lumotnomasi) topilmadi — KAT tasdiqsiz chiqmasin")
    r = ref.mint_batch(noms, threads=1, duty=1.0, batch_id=pid, batch_key=pk, master=mk,
                       cert_id=sert.sert_id, minted_ms=vaqt, reserve_lock="AQ-RES-KAT0001",
                       constraints_hash=cx, first_seq=101, owner=XAZINA)
    assert r.root == p.ildiz, f"{nomi}: Rust ildizi farq qiladi"
    assert r.signing_message == msg, f"{nomi}: Rust imzo xabari farq qiladi"
    for i, (q, k) in enumerate(zip(r.rows(), p.kupyuralar)):
        assert q[0] == k.sarlavha.note_id and q[6] == k.muhr, f"{nomi}/{i}: kupyura farq qiladi"
        assert q[7] == b"".join(k.isbot), f"{nomi}/{i}: isbot farq qiladi"
    yozuv["rust_tasdiq"] = "mos (ildiz, imzo xabari, har kupyura id/muhr/isbot)"
    partiyalar.append(yozuv)
kat["partiyalar"] = partiyalar

# --- 7. protokol -----------------------------------------------------------
chaqiriq = ketma(32, 77)
wk = ketma(32, 90)
w = protokol.Wire(wk)
paket = w.ora(b"yozuv")
kat["protokol"] = {
    "bank_id": {"bank_public_key_sha3": h(aq.sha3_256(bank.public_key)),
                "server_id_hash": h(aq.server_id_hash(bank.public_key)),
                "bank_id": protokol.bank_id(bank.public_key)},
    "mint_auth": {"chaqiriq": h(chaqiriq), "sert_id": h(sert.sert_id),
                  "digest": h(protokol.mint_auth_xulosasi(bank.public_key, chaqiriq,
                                                          sert.sert_id))},
    "wire": {"kalit": h(wk), "yozuv": h(b"yozuv"), "hisoblagich": 1,
             "c2b_paket": h(paket)},
}

# Konsolga emas, faylga UTF-8 da: Windows konsoli cp1251 bilan buzib yozadi.
chiqish = Path(__file__).resolve().parent.parent / "kat" / "zarbxona_kat_v1.json"
chiqish.parent.mkdir(exist_ok=True)
chiqish.write_text(json.dumps(kat, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"yozildi: {chiqish}")
