"""KAT'ni MUSTAQIL tekshiruvchi — faqat standart kutubxonalar bilan.

Maqsad: SPEC.md ning o'zi yetarli ekanini isbotlash. Bu fayl zarbxona v2
kodini ham, `aetherq_core` ni ham import qilmaydi; hamma narsa SPEC'dagi
ta'riflardan qaytadan yozilgan.

Talab:  pip install pycryptodome cryptography>=47
Ishga tushirish:  python kat_tekshir.py ../kat/zarbxona_kat_v1.json
"""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
import sys
from base64 import b64encode  # noqa: F401 — protokol qatorlari uchun namuna

from Crypto.Hash import KMAC256
from cryptography.hazmat.primitives.asymmetric import mldsa
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

X = bytes.fromhex


# --- ibtidolar (SPEC §2) ---------------------------------------------------

def sha3(b: bytes) -> bytes:
    return hashlib.sha3_256(b).digest()


def _left(x: int) -> bytes:
    s = x.to_bytes(max(1, (x.bit_length() + 7) // 8), "big")
    return bytes([len(s)]) + s


def _right(x: int) -> bytes:
    s = x.to_bytes(max(1, (x.bit_length() + 7) // 8), "big")
    return s + bytes([len(s)])


def _enc(s: bytes) -> bytes:
    return _left(len(s) * 8) + s


def _pad(x: bytes, w: int = 136) -> bytes:
    z = _left(w) + x
    return z + bytes((-len(z)) % w)


def kmac(key: bytes, data: bytes, custom: bytes, n: int = 32) -> bytes:
    """AQ-KMAC256 (SPEC §2.2): SP 800-185 KMAC256 tuzilmasi, LEKIN cSHAKE
    o'rniga oddiy SHAKE256 (padding 0x1F, standart 0x04 emas).

    Standart KMAC (pycryptodome `Crypto.Hash.KMAC256`) BOSHQA natija beradi —
    pastda bu ataylab tekshiriladi.
    """
    x = _pad(_enc(key)) + data + _right(n * 8)
    return hashlib.shake_256(_pad(_enc(b"KMAC") + _enc(custom)) + x).digest(n)


def kmac_standart(key: bytes, data: bytes, custom: bytes, n: int = 32) -> bytes:
    return KMAC256.new(key=key, data=data, mac_len=n, custom=custom).digest()


def hkdf_expand(prk: bytes, info: bytes, n: int) -> bytes:
    out, t, c = b"", b"", 1
    while len(out) < n:
        t = hmac.new(prk, t + info + bytes([c]), hashlib.sha3_256).digest()
        out += t
        c += 1
    return out[:n]


def aead_seal(k: bytes, nonce: bytes, pt: bytes, aad: bytes) -> bytes:
    return ChaCha20Poly1305(k).encrypt(nonce, pt, aad)


def tagged(label: bytes, *parts: bytes) -> bytes:
    b = b""
    for p in (label, *parts):
        b += len(p).to_bytes(4, "big") + p
    return sha3(b)


def lp(b: bytearray, d: bytes) -> None:
    b += len(d).to_bytes(8, "little") + d


def u64(n: int) -> bytes:
    return n.to_bytes(8, "little")


# --- zarb (SPEC §4-6) ------------------------------------------------------

L_HDR = b"AETHER-Q-CBDC/NOTE-HEADER/v1"
L_ID = b"AETHER-Q-CBDC/NOTE-ID/v1"
L_REST = b"AETHER-Q-CBDC/NOTE-REST/v1"
L_CLAIM = b"AETHER-Q-CBDC/NOTE-CLAIM/v1"
L_ROOT = b"AETHER-Q-CBDC/BATCH-ROOT/v1"
L_CERT = b"AETHER-Q-CBDC/MINT-CERT/v1"
L_CONS = b"AETHER-Q-CBDC/CONSTRAINTS/v1"


def header(nid, nom, owner, seq, bid, ch) -> bytes:
    b = bytearray()
    for d in (L_HDR, nid, u64(nom), owner.encode(), u64(seq), bid, ch):
        lp(b, d)
    return bytes(b)


def node(a, b):
    return sha3(b"\x01" + a + b)


def layers(leaves):
    if not leaves:
        return [[bytes(32)]]
    ls = [list(leaves)]
    while len(ls[-1]) > 1:
        c = ls[-1]
        n = [node(c[i], c[i + 1]) for i in range(0, len(c) - 1, 2)]
        if len(c) % 2:
            n.append(c[-1])
        ls.append(n)
    return ls


def proof(ls, i):
    p = []
    for lay in ls[:-1]:
        s = i + 1 if i % 2 == 0 else i - 1
        if s < len(lay):
            p.append(lay[s])
        i //= 2
    return p


def cons_json(cats=(), exp=None, bps=0, acct=""):
    d = {}
    t = sorted({c.strip().upper() for c in cats if c.strip()})
    if t:
        d["categories"] = t
    if exp:
        d["expires_ms"] = exp
    if bps:
        d["tax_bps"] = bps
        d["tax_account"] = acct
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False) if d else ""


def cons_hash(s):
    return bytes(32) if not s else tagged(L_CONS, s.encode())


# --- tekshiruv -------------------------------------------------------------

xatolar = 0


def teng(nomi, a, b):
    global xatolar
    if a != b:
        xatolar += 1
        print(f"  XATO  {nomi}")
    return a == b


def main(yol: str) -> int:
    k = json.load(open(yol, encoding="utf-8"))
    p = k["primitivlar"]
    for v in p["sha3_256"]:
        teng("sha3", sha3(X(v["in"])).hex(), v["out"])
    for v in p["kmac256"]:
        teng("kmac256", kmac(X(v["key"]), X(v["data"]), X(v["custom"]), v["len"]).hex(), v["out"])
        # Tuzoq qulfi: standart KMAC256 mos kelmasligi SHART (aks holda spec noto'g'ri).
        if kmac_standart(X(v["key"]), X(v["data"]), X(v["custom"]), v["len"]).hex() == v["out"]:
            teng("standart KMAC farq qilishi kerak edi", 0, 1)
    for v in p["hkdf_expand_sha3_256"]:
        teng("hkdf", hkdf_expand(X(v["prk"]), X(v["info"]), v["len"]).hex(), v["out"])
    for v in p["chacha20poly1305"]:
        teng("aead", aead_seal(X(v["key"]), X(v["nonce"]), X(v["plaintext"]),
                               X(v["aad"])).hex(), v["out"])
    for v in p["tagged_hash_be32"]:
        teng("tagged", tagged(X(v["label"]), *[X(x) for x in v["parts"]]).hex(), v["out"])
    print("ibtidolar: tekshirildi")

    m = k["ml_dsa_65"]
    sk = mldsa.MLDSA65PrivateKey.from_seed_bytes(X(m["seed"]))
    pk = sk.public_key().public_bytes_raw()
    teng("ML-DSA seed→pk", pk.hex(), m["public_key"])
    pub = mldsa.MLDSA65PublicKey.from_public_bytes(X(m["public_key"]))
    pub.verify(X(m["signature"]), X(m["message"]))           # istisno = xato
    sig = sk.sign(X(m["message"]))
    assert len(sig) == 3309 and len(pk) == 1952
    print("ML-DSA-65: urug'dan kalit mos, KAT imzosi tasdiqlandi, o'z imzomiz 3309 B")

    ks = k["kalit_ombori"]
    f = ks["fayl"]
    kd = f["kdf"]
    kk = hashlib.scrypt(ks["parol"].encode(), salt=X(kd["salt"]), n=kd["n"], r=kd["r"],
                        p=kd["p"], dklen=32, maxmem=256 * 1024 * 1024)
    seed = ChaCha20Poly1305(kk).decrypt(X(f["nonce"]), X(f["ciphertext"]),
                                        b"AETHER-Q-BANK/KEYSTORE/v1")
    teng("kalit ombori", seed.hex(), ks["kutilgan_seed"])
    print("kalit ombori: ochildi")

    for c in k["cheklov"]:
        kir = c["kirish"]
        s = cons_json(kir.get("toifalar", ()), kir.get("muddat_ms"),
                      kir.get("soliq_bps", 0), kir.get("soliq_hisobi", ""))
        teng("cheklov json", s, c["json"])
        teng("cheklov xesh", cons_hash(s).hex(), c["xesh"])
    print("cheklovlar: tekshirildi")

    s = k["sertifikat"]["fayl"]
    msg = tagged(L_CERT, X(s["mint_public_key"]), X(s["cert_id"]), s["label"].encode(),
                 s["limit_amount"].to_bytes(8, "big"), s["valid_from_ms"].to_bytes(8, "big"),
                 s["valid_until_ms"].to_bytes(8, "big"))
    teng("sertifikat xabari", msg.hex(), k["sertifikat"]["xabar_digest"])
    mldsa.MLDSA65PublicKey.from_public_bytes(X(s["bank_public_key"])).verify(X(s["signature"]), msg)
    print("sertifikat: xabar mos, bank imzosi tasdiqlandi")

    for b in k["partiyalar"]:
        kir = b["kirish"]
        bid, bk, mk = X(kir["partiya_id"]), X(kir["partiya_kaliti"]), X(kir["master"])
        ch = cons_hash(kir["cheklov_json"])
        teng(b["nomi"] + " cheklov", ch.hex(), b["cheklov_xeshi"])
        rows = []
        for i, nom in enumerate(kir["nominallar"]):
            nid = kmac(bk, bid + u64(i), L_ID)
            hdr = header(nid, nom, kir["egasi"], kir["birinchi_seq"] + i, bid, ch)
            claim = kmac(bk, nid, L_CLAIM)
            kn = hkdf_expand(mk, L_REST + nid, 44)
            core = claim + u64(kir["zarb_ms"]) + X(kir["sert_id"])
            seal = aead_seal(kn[:32], kn[32:44], core, sha3(hdr))
            rows.append((nid, hdr, claim, kn, core, seal, sha3(b"\x00" + hdr)))
        ls = layers([r[6] for r in rows])
        root = ls[-1][0]
        teng(b["nomi"] + " ildiz", root.hex(), b["ildiz"])
        total = sum(kir["nominallar"])
        sm = bytearray()
        for d in (L_ROOT, root, bid, u64(len(rows)), total.to_bytes(16, "little"),
                  kir["zaxira_qulfi"].encode(), u64(kir["zarb_ms"])):
            lp(sm, d)
        teng(b["nomi"] + " imzo xabari", bytes(sm).hex(), b["imzo_xabari"])
        for kv in b["kupyuralar"]:
            i = kv["indeks"]
            nid, hdr, claim, kn, core, seal, leaf = rows[i]
            t = f"{b['nomi']}/{i}"
            teng(t + " note_id", nid.hex(), kv["note_id"])
            teng(t + " nazorat", claim.hex(), kv["nazorat_kaliti"])
            teng(t + " konvert", (kn[:32].hex(), kn[32:].hex()),
                 (kv["konvert_kalit"], kv["konvert_nonce"]))
            teng(t + " sarlavha", hdr.hex(), kv["sarlavha_kodi"])
            teng(t + " barg", leaf.hex(), kv["barg"])
            teng(t + " yadro", core.hex(), kv["yadro_ochiq"])
            teng(t + " muhr", seal.hex(), kv["muhr"])
            teng(t + " isbot", [x.hex() for x in proof(ls, i)], kv["isbot"])
        # partiya imzosi zarbxona kaliti bilan
        mldsa.MLDSA65PublicKey.from_public_bytes(X(k["ml_dsa_65"]["public_key"])).verify(
            X(b["imzo"]), bytes(sm))
        print(f"partiya «{b['nomi']}»: {len(rows)} kupyura, ildiz/imzo xabari/kupyuralar mos")

    pr = k["protokol"]
    bpk = X(s["bank_public_key"])
    sid = sha3(b"AETHER-Q-v5.1-SRV-ID" + bpk)
    teng("server_id_hash", sid.hex(), pr["bank_id"]["server_id_hash"])
    teng("bank_id", sid.hex()[:16], pr["bank_id"]["bank_id"])
    ma = pr["mint_auth"]
    teng("mint_auth", tagged(b"AETHER-Q-BANK/MINT-AUTH/v1", bpk, X(ma["chaqiriq"]),
                             X(ma["sert_id"])).hex(), ma["digest"])
    w = pr["wire"]
    rec = X(w["yozuv"])
    n = w["hisoblagich"]
    tag = sha3(b"AETHER-Q-BANK/WIRE/v1" + X(w["kalit"]) + b"c2b" + struct.pack(">Q", n) + rec)[:16]
    teng("wire paket", (b"AQW1" + struct.pack(">Q", n) + tag + rec).hex(), w["c2b_paket"])
    print("protokol: bank_id, mint_auth, wire mos")

    print("NATIJA:", "HAMMASI MOS" if xatolar == 0 else f"{xatolar} ta XATO")
    return 1 if xatolar else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "../kat/zarbxona_kat_v1.json"))
