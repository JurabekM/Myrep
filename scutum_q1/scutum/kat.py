"""SCUTUM-Q1 v1.1 — Known Answer Test (KAT) vektorlari.

Spec §10 p.1 talabi: "Har kriptografik funksiya uchun rasmiy KAT/test vektorlari".

Bu modul vektorlarni HAM generatsiya qiladi, HAM tekshiradi. Barcha kalitlar
qat'iy urug'lardan chiqariladi, shuning uchun natija har ishga tushirishda bir xil.

Ikki istisno — bular tabiatan tasodifiy:
  * `ML-KEM.Encaps`  — `cryptography` API tasodifiylikni tashqaridan olmaydi;
  * `ML-DSA.Sign`    — FIPS 204 standart rejimi "hedged" (tasodifiy).
Ular bir marta generatsiya qilinib, faylga QOTIRILADI (`pinned`), so'ng
`Decaps` / `Verify` orqali tekshiriladi — bu KAT uchun to'liq yetarli.
Ed25519 (RFC 8032) esa deterministik, shuning uchun imzo to'g'ridan-to'g'ri
solishtiriladi.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .config import PROTOCOL_VERSION, SUITE, ProtocolConfig, hardened_config
from .crypto import canonical
from .crypto.primitives import (
    aead_seal,
    argon2id,
    ed25519_from_raw,
    ed25519_pub,
    ed25519_sign,
    ed25519_verify,
    hkdf_sha512,
    hmac_sha512,
    key_commitment,
    mldsa_from_seed,
    mldsa_pub,
    mldsa_sign,
    mldsa_verify,
    mlkem_decaps,
    mlkem_encaps,
    mlkem_from_seed,
    mlkem_pub,
    sha3_256,
    uint64be,
    x25519_dh,
    x25519_from_raw,
    x25519_pub,
)
from .protocol import merkle
from .protocol.envelope import (
    DIR_INITIATOR,
    Envelope,
    MsgType,
    RatchetHeader,
    file_chunk_nonce,
    message_nonce,
)
from .protocol.handshake import derive_root_key, init_salt, init_transcript
from .protocol.identity import (
    DeviceKeys,
    build_dc,
    dc_bytes,
    device_fingerprint,
)
from .protocol.ratchet import kdf_ck, kdf_rk
from .protocol.sfile import chunk_aad, chunk_key, meta_key, meta_nonce

KAT_PATH = Path(__file__).resolve().parent.parent / "kat" / "scutum-q1-kat.json"
KAT_VERSION = "1.1"

# ---------------------------------------------------------------------------
# Qat'iy parametrlar
# ---------------------------------------------------------------------------
T0 = 1767225600          # 2026-01-01T00:00:00Z
DAY = 86400
SESSION_ID = bytes.fromhex("53435554554d2d51312f4b41542f7331")   # "SCUTUM-Q1/KAT/s1"
TIMESTAMP = T0 + 3600


def _seed(label: str, n: int) -> bytes:
    """Etiketdan deterministik urug'."""
    out = b""
    i = 0
    while len(out) < n:
        out += sha3_256(b"SCUTUM-Q1/KAT/seed", label.encode(), bytes([i]))
        i += 1
    return out[:n]


def _device(name: str) -> DeviceKeys:
    """Butunlay deterministik qurilma."""
    dev = DeviceKeys(
        name=name,
        device_id=_seed(f"{name}/device_id", 16),
        ik_x=x25519_from_raw(_seed(f"{name}/ik_x", 32)),
        ik_ed=ed25519_from_raw(_seed(f"{name}/ik_ed", 32)),
        ik_mldsa=mldsa_from_seed(_seed(f"{name}/ik_mldsa", 32)),
        spk_x=x25519_from_raw(_seed(f"{name}/spk_x", 32)),
        spk_mlkem=mlkem_from_seed(_seed(f"{name}/spk_mlkem", 64)),
        spk_created_at=T0,
        spk_expiry=T0 + 30 * DAY,
        created_at=T0,
        expires_at=T0 + 365 * DAY,
    )
    dev.opks.clear()
    from .protocol.identity import OneTimePreKey

    opk_sk = x25519_from_raw(_seed(f"{name}/opk0", 32))
    opk = OneTimePreKey(_seed(f"{name}/opk0/id", 8), opk_sk, x25519_pub(opk_sk))
    dev.opks[opk.opk_id] = opk
    return dev


def _h(b: bytes) -> str:
    return b.hex()


# ---------------------------------------------------------------------------
# Generatsiya
# ---------------------------------------------------------------------------
def build(pinned: Optional[dict] = None) -> dict:
    """Barcha vektorlarni quradi. `pinned` — oldingi tasodifiy qiymatlar."""
    pinned = pinned or {}
    cfg: ProtocolConfig = hardened_config()
    v: dict[str, Any] = {
        "kat_version": KAT_VERSION,
        "suite": SUITE,
        "protocol_version": PROTOCOL_VERSION,
        "note": "Barcha qiymatlar hex. HARDENED (v1.1) profili ostida.",
    }

    # ------------------------------------------------------------------ §2
    p: dict[str, Any] = {}
    p["sha3_256__abc"] = _h(sha3_256(b"abc"))
    p["sha3_256__empty"] = _h(sha3_256(b""))

    ikm, salt, info = b"\x0b" * 22, bytes(range(0x00, 0x0D)), bytes(range(0xF0, 0xFA))
    p["hkdf_sha512"] = {
        "ikm": _h(ikm), "salt": _h(salt), "info": _h(info), "L": 64,
        "okm": _h(hkdf_sha512(ikm, salt, info, 64)),
    }

    k = _seed("aead/key", 32)
    n = _seed("aead/nonce", 12)
    pt = b"SCUTUM-Q1 KAT plaintext"
    aad = b"SCUTUM-Q1 KAT aad"
    p["chacha20poly1305"] = {
        "key": _h(k), "nonce": _h(n), "plaintext": _h(pt), "aad": _h(aad),
        "ciphertext": _h(aead_seal(k, n, pt, aad)),
    }

    a_raw, b_raw = _seed("x25519/a", 32), _seed("x25519/b", 32)
    a_sk, b_sk = x25519_from_raw(a_raw), x25519_from_raw(b_raw)
    p["x25519"] = {
        "sk_a": _h(a_raw), "pk_a": _h(x25519_pub(a_sk)),
        "sk_b": _h(b_raw), "pk_b": _h(x25519_pub(b_sk)),
        "shared": _h(x25519_dh(a_sk, x25519_pub(b_sk))),
    }

    ed_raw = _seed("ed25519/sk", 32)
    ed_sk = ed25519_from_raw(ed_raw)
    msg = b"SCUTUM-Q1 KAT message"
    p["ed25519"] = {                      # RFC 8032 — deterministik
        "sk": _h(ed_raw), "pk": _h(ed25519_pub(ed_sk)), "msg": _h(msg),
        "sig": _h(ed25519_sign(ed_sk, msg)),
        "deterministic": True,
    }

    kem_seed = _seed("mlkem/seed", 64)
    kem_sk = mlkem_from_seed(kem_seed)
    kem_pk = mlkem_pub(kem_sk)
    prev = pinned.get("primitives", {}).get("ml_kem_768", {})
    if prev.get("ct"):
        ct = bytes.fromhex(prev["ct"])
        ss = mlkem_decaps(kem_sk, ct)
    else:
        ss, ct = mlkem_encaps(kem_pk)
    p["ml_kem_768"] = {
        "sk_seed": _h(kem_seed), "pk": _h(kem_pk), "ct": _h(ct),
        "shared_secret": _h(ss),
        "sizes": {"pk": len(kem_pk), "ct": len(ct), "ss": len(ss)},
        "deterministic": False,
        "check": "Decaps(sk_seed, ct) == shared_secret",
    }

    dsa_seed = _seed("mldsa/seed", 32)
    dsa_sk = mldsa_from_seed(dsa_seed)
    dsa_pk = mldsa_pub(dsa_sk)
    prevd = pinned.get("primitives", {}).get("ml_dsa_65", {})
    sig = (bytes.fromhex(prevd["sig"]) if prevd.get("sig")
           else mldsa_sign(dsa_sk, msg))
    p["ml_dsa_65"] = {
        "sk_seed": _h(dsa_seed), "pk": _h(dsa_pk), "msg": _h(msg), "sig": _h(sig),
        "sizes": {"pk": len(dsa_pk), "sig": len(sig)},
        "deterministic": False,
        "check": "Verify(pk, msg, sig) == true",
    }

    p["argon2id"] = {
        "password": _h(b"correct horse battery staple"),
        "salt": _h(_seed("argon2/salt", 16)),
        "m_kib": 65536, "t": 3, "p": 1, "L": 32,
        "output": _h(argon2id(b"correct horse battery staple",
                              _seed("argon2/salt", 16),
                              memory_kib=65536, time_cost=3,
                              parallelism=1, length=32)),
    }
    v["primitives"] = p

    # ------------------------------------------------------------------ §3
    A, B = _device("A"), _device("B")
    dc_a, dc_b = A.dc(), B.dc()
    v["identity"] = {
        "device_A": {
            "device_id": _h(A.device_id),
            "ik_x25519_pk": _h(A.ik_x_pk),
            "ik_ed25519_pk": _h(A.ik_ed_pk),
            "ik_mldsa65_pk_sha3": _h(sha3_256(A.ik_mldsa_pk)),
            "canonical_dc_sha3": _h(sha3_256(dc_bytes(dc_a, cfg))),
            "canonical_dc_len": len(dc_bytes(dc_a, cfg)),
            "fingerprint": _h(device_fingerprint(dc_a, cfg)),
        },
        "device_B": {
            "device_id": _h(B.device_id),
            "ik_x25519_pk": _h(B.ik_x_pk),
            "spk_x25519_pk": _h(B.spk_x_pk),
            "spk_mlkem768_pk_sha3": _h(sha3_256(B.spk_mlkem_pk)),
            "opk_id": _h(next(iter(B.opks))),
            "opk_pk": _h(next(iter(B.opks.values())).pk),
            "canonical_dc_sha3": _h(sha3_256(dc_bytes(dc_b, cfg))),
            "fingerprint": _h(device_fingerprint(dc_b, cfg)),
        },
        "fingerprint_rule": 'SHA3-256("SCUTUM-Q1/fp" || x25519_pk || ed25519_pk || mldsa65_pk)',
    }

    # ------------------------------------------------------------------ §5
    opk = next(iter(B.opks.values()))
    ek_sk = x25519_from_raw(_seed("A/ephemeral", 32))
    ek_pk = x25519_pub(ek_sk)

    prevh = pinned.get("handshake", {})
    if prevh.get("mlkem_ct"):
        kem_ct = bytes.fromhex(prevh["mlkem_ct"])
        kem_ss = mlkem_decaps(B.spk_mlkem, kem_ct)
    else:
        kem_ss, kem_ct = mlkem_encaps(B.spk_mlkem_pk)

    dh1 = x25519_dh(ek_sk, B.spk_x_pk)
    dh2 = x25519_dh(A.ik_x, B.spk_x_pk)
    dh3 = x25519_dh(ek_sk, dc_b["x25519_pk"])
    dh4 = x25519_dh(ek_sk, opk.pk)
    salt_i = init_salt(dc_a, dc_b, cfg)
    tr = init_transcript(
        ek_pk=ek_pk, spk_x_pk=B.spk_x_pk, mlkem_pk=B.spk_mlkem_pk,
        mlkem_ct=kem_ct, opk_pk=opk.pk, dc_a=dc_a, dc_b=dc_b, cfg=cfg,
    )
    rk0 = derive_root_key(cfg=cfg, dh1=dh1, dh2=dh2, dh3=dh3, dh4=dh4,
                          kem_ss=kem_ss, salt=salt_i, transcript=tr)
    v["handshake"] = {
        "ephemeral_sk": _h(_seed("A/ephemeral", 32)),
        "ephemeral_pk": _h(ek_pk),
        "mlkem_ct": _h(kem_ct),
        "mlkem_shared_secret": _h(kem_ss),
        "dh1_EK_SPK": _h(dh1),
        "dh2_IKA_SPK": _h(dh2),
        "dh3_EK_IKB": _h(dh3),
        "dh4_EK_OPK": _h(dh4),
        "init_salt": _h(salt_i),
        "transcript": _h(tr),
        "ikm_order": "dh1 || dh2 || dh3 || dh4 || mlkem_ss",
        "rk0": _h(rk0),
    }

    # ------------------------------------------------------------------ §6
    dhs_sk = x25519_from_raw(_seed("A/ratchet0", 32))
    dhs_pk = x25519_pub(dhs_sk)
    dh_out = x25519_dh(dhs_sk, B.spk_x_pk)
    rk1, ck0 = kdf_rk(rk0, dh_out)

    chain = []
    ck = ck0
    for i in range(3):
        ck, mk = kdf_ck(cfg, ck, SESSION_ID, i)
        chain.append({"i": i, "mk": _h(mk), "ck_next": _h(ck)})

    _, mk0 = kdf_ck(cfg, ck0, SESSION_ID, 0)
    nonce0 = message_nonce(SESSION_ID, DIR_INITIATOR, 0)
    hdr = RatchetHeader(dh_pk=dhs_pk, pn=0, n=0)
    env = Envelope(
        type=MsgType.MSG,
        sender_device_id=A.device_id,
        recipient_device_id=B.device_id,
        session_id=SESSION_ID,
        message_no=0,
        timestamp=TIMESTAMP,
        header=hdr,
    )
    aad0 = env.aad(cfg)
    body0 = key_commitment(mk0) + aead_seal(mk0, nonce0, b"salom", aad0)
    env.body = body0

    v["ratchet"] = {
        "session_id": _h(SESSION_ID),
        "ratchet_sk": _h(_seed("A/ratchet0", 32)),
        "ratchet_pk": _h(dhs_pk),
        "dh_output": _h(dh_out),
        "kdf_rk": {"rk_in": _h(rk0), "secret": _h(dh_out),
                   "rk_next": _h(rk1), "ck": _h(ck0)},
        "kdf_ck_chain": chain,
        "kdf_ck_rule": "MK = HMAC-SHA-512(CK,0x01)[0:32] ; CK' = HMAC-SHA-512(CK,0x02)[0:32]",
        "message": {
            "plaintext": _h(b"salom"),
            "direction_byte": _h(DIR_INITIATOR),
            "message_no": 0,
            "timestamp": TIMESTAMP,
            "nonce": _h(nonce0),
            "mk": _h(mk0),
            "key_commitment": _h(key_commitment(mk0)),
            "aad": _h(aad0),
            "body": _h(body0),
            "wire": _h(env.to_wire(cfg)),
            "wire_len": len(env.to_wire(cfg)),
        },
    }

    # ------------------------------------------------------------------ §7
    fk = _seed("file/fk", 32)
    file_id = _seed("file/id", 16)
    file_salt = _seed("file/salt", 32)
    chunk_size = 64
    data = bytes((i * 7 + 3) % 256 for i in range(chunk_size * 2 + 17))
    total = (len(data) + chunk_size - 1) // chunk_size

    chunks = []
    leaves = []
    for i in range(total):
        ck_i = chunk_key(fk, file_salt, file_id, i)
        n_i = file_chunk_nonce(file_id, i)
        aad_i = chunk_aad(file_id, i, total, len(data), cfg)
        ct_i = key_commitment(ck_i) + aead_seal(
            ck_i, n_i, data[i * chunk_size:(i + 1) * chunk_size], aad_i)
        leaf = merkle.leaf_hash(i, ct_i, cfg)
        leaves.append(leaf)
        chunks.append({"i": i, "chunk_key": _h(ck_i), "nonce": _h(n_i),
                       "aad": _h(aad_i), "ciphertext_sha3": _h(sha3_256(ct_i)),
                       "ciphertext_len": len(ct_i), "leaf": _h(leaf)})

    tree = merkle.build_tree(leaves, cfg)
    mk_meta = meta_key(fk, file_salt, file_id, cfg)
    name = "hisobot.pdf"
    name_ct = aead_seal(
        mk_meta, meta_nonce(file_id, "name", cfg), name.encode(),
        canonical.encode({"file_id": file_id, "f": "name"}, cfg.encoding))

    v["s_file"] = {
        "fk": _h(fk), "file_id": _h(file_id), "file_salt": _h(file_salt),
        "chunk_size": chunk_size, "plaintext_size": len(data),
        "total_chunks": total, "plaintext_sha3": _h(sha3_256(data)),
        "chunks": chunks,
        "tree_root": _h(tree.tree_root),
        "root_hash": _h(tree.root),
        "root_rule": 'SHA3-256(0x02 || uint64be(total_chunks) || tree_root)',
        "leaf_rule": 'SHA3-256(0x00 || uint64be(i) || ct_i)',
        "node_rule": 'SHA3-256(0x01 || L || R)',
        "meta": {"key": _h(mk_meta),
                 "nonce": _h(meta_nonce(file_id, "name", cfg)),
                 "name": name, "name_enc": _h(name_ct)},
    }

    # ------------------------------------------------------------- domenlar
    v["domain_separators"] = [
        "SCUTUM-Q1/INIT", "SCUTUM-Q1/transcript", "SCUTUM-Q1/init-id",
        "SCUTUM-Q1/RK", "SCUTUM-Q1/MSG", "SCUTUM-Q1/commit",
        "SCUTUM-Q1/prekey", "SCUTUM-Q1/fp",
        "SCUTUM-Q1/FILE/CHUNK", "SCUTUM-Q1/FILE/META",
    ]
    return v


# ---------------------------------------------------------------------------
# Tekshirish
# ---------------------------------------------------------------------------
def verify(vectors: dict) -> list[str]:
    """Vektorlarni qayta hisoblab solishtiradi. -> xatolar ro'yxati (bo'sh = OK)."""
    errs: list[str] = []

    def eq(label: str, got: bytes, want_hex: str) -> None:
        if got.hex() != want_hex:
            errs.append(f"{label}: {got.hex()[:32]}… != {want_hex[:32]}…")

    rebuilt = build(pinned=vectors)

    def walk(path: str, a: Any, b: Any) -> None:
        if isinstance(a, dict):
            for key in a:
                if key not in b:
                    errs.append(f"{path}.{key}: yangi vektorda yo'q")
                else:
                    walk(f"{path}.{key}", a[key], b[key])
        elif isinstance(a, list):
            if len(a) != len(b):
                errs.append(f"{path}: uzunlik {len(a)} != {len(b)}")
            else:
                for i, (x, y) in enumerate(zip(a, b)):
                    walk(f"{path}[{i}]", x, y)
        elif a != b:
            errs.append(f"{path}: {str(a)[:40]}… != {str(b)[:40]}…")

    walk("kat", vectors, rebuilt)

    # tasodifiy qiymatlar uchun alohida semantik tekshiruv
    pk_kem = vectors["primitives"]["ml_kem_768"]
    sk = mlkem_from_seed(bytes.fromhex(pk_kem["sk_seed"]))
    eq("ML-KEM Decaps", mlkem_decaps(sk, bytes.fromhex(pk_kem["ct"])),
       pk_kem["shared_secret"])

    d = vectors["primitives"]["ml_dsa_65"]
    if not mldsa_verify(bytes.fromhex(d["pk"]), bytes.fromhex(d["sig"]),
                        bytes.fromhex(d["msg"])):
        errs.append("ML-DSA-65: qotirilgan imzo tekshiruvdan o'tmadi")

    e = vectors["primitives"]["ed25519"]
    if not ed25519_verify(bytes.fromhex(e["pk"]), bytes.fromhex(e["sig"]),
                          bytes.fromhex(e["msg"])):
        errs.append("Ed25519: imzo tekshiruvdan o'tmadi")
    return errs


def load() -> dict:
    return json.loads(KAT_PATH.read_text(encoding="utf-8"))


def save(vectors: dict) -> None:
    KAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    KAT_PATH.write_text(
        json.dumps(vectors, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    existing = load() if KAT_PATH.exists() else None
    vectors = build(pinned=existing)
    save(vectors)
    errs = verify(load())
    if errs:
        print("KAT XATOLARI:")
        for e in errs:
            print("  -", e)
        return 1
    n = sum(1 for _ in json.dumps(vectors).split('"')) // 2
    print(f"KAT OK -> {KAT_PATH}")
    print(f"  primitivlar : {len(vectors['primitives'])} guruh")
    print(f"  handshake   : RK0 = {vectors['handshake']['rk0'][:32]}…")
    print(f"  ratchet     : wire = {vectors['ratchet']['message']['wire_len']} bayt")
    print(f"  S-FILE      : {vectors['s_file']['total_chunks']} bo'lak, "
          f"root = {vectors['s_file']['root_hash'][:32]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
