"""
AETHER-Q v5.1 — Rust (aq-core) uchun KAT vektorlari, Python referensidan (aether_q_v3/aether_q_v51).

Ishga tushirish (Windows, PYTHONIOENCODING=utf-8):
    python kat/gen_wire_kat.py <chiqish.json>

Har bir vektor deterministik kirishdan (yoki Python tomonidan yaratilgan natijadan) olinadi.
Rust tomoni bu natijalarga bayt-bayt mos kelishi shart.
"""

import json
import os
import sys

REF = r"C:/Users/comp_2.1/Downloads/aether_q_v3"
sys.path.insert(0, REF)

from cryptography.hazmat.primitives.asymmetric import mldsa, mlkem, x25519  # noqa: E402
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305  # noqa: E402

from aether_q_v51 import handshake as hs  # noqa: E402
from aether_q_v51.hybrid import DEFAULT_LABEL, MINIMAL_LABEL, _combine  # noqa: E402
from aether_q_v51.kdf import hkdf_expand, hkdf_extract, kmac256, sha3_256  # noqa: E402
from aether_q_v51.kem import MLKEM768  # noqa: E402
from aether_q_v51.transport import TRANSPORT_LABEL, Session  # noqa: E402


def h(b: bytes) -> str:
    return b.hex()


def main(out_path: str) -> None:
    v = {"protocol": "AETHER-Q 5.1.0", "generator": "kat/gen_wire_kat.py", "vectors": {}}
    V = v["vectors"]

    # 1) HKDF-SHA3-256 (RFC 5869, SHA3 bilan)
    ikm = bytes(range(32))
    prk = hkdf_extract(b"salt-aq", ikm)
    V["hkdf"] = {
        "salt": h(b"salt-aq"), "ikm": h(ikm), "prk": h(prk),
        "info": h(b"info-aq"), "okm_64": h(hkdf_expand(prk, b"info-aq", 64)),
        "empty_salt_prk": h(hkdf_extract(b"", ikm)),
    }

    # 2) KMAC256 (SP 800-185)
    key = b"k" * 32
    V["kmac256"] = {
        "key": h(key), "data": h(b"data-aq"),
        "custom": h(b"AETHER-Q-v5.1-CF"), "out_32": h(kmac256(key, b"data-aq", 32, custom=b"AETHER-Q-v5.1-CF")),
        "out_16_nocustom": h(kmac256(key, b"data-aq", 16)),
    }

    # 3) KEM combiner (0x01 hybrid, 0x03 minimal)
    ss_m, ct_m = bytes(range(32)), bytes(1088)
    ss_x, ct_x, pk_x = bytes(range(64, 96)), bytes(range(0, 32)), bytes(range(32, 64))
    V["combiner"] = {
        "profile_01": {
            "label": h(DEFAULT_LABEL), "ss_m": h(ss_m), "ct_m": h(ct_m),
            "ss_x": h(ss_x), "ct_x": h(ct_x), "pk_x": h(pk_x),
            "ss": h(_combine(0x01, DEFAULT_LABEL, ss_m, ct_m, ss_x, ct_x, pk_x)),
        },
        "profile_03": {
            "label": h(MINIMAL_LABEL), "ss_m": h(ss_m), "ct_m": h(ct_m),
            "ss": h(_combine(0x03, MINIMAL_LABEL, ss_m, ct_m)),
        },
    }

    # 3b) Implicit rejection kaliti (F1 / S4): nol X25519 nuqta holati
    from aether_q_v51.hybrid import _reject_key  # noqa: E402
    dk_seed_rej = bytes(range(64))
    V["reject_0x01"] = {
        "dk_m": h(dk_seed_rej), "ss_m": h(ss_m), "ct_m": h(ct_m), "ct_x": h(ct_x),
        "key": h(_reject_key({"dk_m": dk_seed_rej}, ss_m, ct_m, ct_x)),
    }

    # 4) ML-KEM-768 (FIPS 203): seed -> ek; Python encaps -> ct, ss; Rust decaps tekshiradi
    seed_kem = bytes(range(64))
    priv_kem = mlkem.MLKEM768PrivateKey.from_seed_bytes(seed_kem)
    ek = priv_kem.public_key().public_bytes_raw()
    ct, ss = MLKEM768.encaps(ek)
    V["mlkem768"] = {"seed": h(seed_kem), "ek": h(ek), "ct": h(ct), "ss": h(ss)}

    # 5) ML-DSA-65 (FIPS 204): seed -> pk; Python imzo; Rust verify qiladi
    seed_dsa = bytes(range(32))
    priv_dsa = mldsa.MLDSA65PrivateKey.from_seed_bytes(seed_dsa)
    pk_dsa = priv_dsa.public_key().public_bytes_raw()
    msg_dsa = b"AETHER-Q transcript digest (KAT)"
    sig_dsa = priv_dsa.sign(msg_dsa)
    V["mldsa65"] = {"seed": h(seed_dsa), "pk": h(pk_dsa), "msg": h(msg_dsa), "sig": h(sig_dsa)}

    # 6) X25519 (RFC 7748)
    sk_a = bytes(range(1, 33))
    sk_b = bytes(range(33, 65))
    pk_a = x25519.X25519PrivateKey.from_private_bytes(sk_a).public_key().public_bytes_raw()
    pk_b = x25519.X25519PrivateKey.from_private_bytes(sk_b).public_key().public_bytes_raw()
    shared = x25519.X25519PrivateKey.from_private_bytes(sk_a).exchange(
        x25519.X25519PublicKey.from_public_bytes(pk_b))
    V["x25519"] = {"sk_a": h(sk_a), "pk_a": h(pk_a), "sk_b": h(sk_b), "pk_b": h(pk_b), "shared": h(shared)}

    # 7) Handshake kalit jadvali: HS, fin kalitlari, CF/SF MAC, master, RMS
    ss_hs = bytes(range(0xA0, 0xC0))
    transcript = bytes((i * 7) & 0xFF for i in range(300))
    th = sha3_256(transcript)
    hs_full = hs._derive_hs(ss_hs)
    c_fin, s_fin = hs._fin_keys(hs_full)
    V["handshake_full"] = {
        "ss": h(ss_hs), "transcript": h(transcript), "hs": h(hs_full),
        "c_fin": h(c_fin), "s_fin": h(s_fin),
        "cf": h(hs._mac(c_fin, th, b"CF")), "sf": h(hs._mac(s_fin, th, b"SF")),
        "master": h(hs._master(hs_full, transcript)), "rms": h(hs._derive_rms(hs_full, transcript)),
    }
    rms_in = bytes(range(0x30, 0x50))
    srv_pub = bytes(range(64))
    sid = hs.server_id_hash(srv_pub)
    hs_res = hs._derive_hs(ss_hs, rms_in, sid)
    V["handshake_resumed"] = {
        "rms": h(rms_in), "server_pub": h(srv_pub), "server_id": h(sid),
        "ss": h(ss_hs), "hs": h(hs_res),
    }

    # 8) Transport: kalit jadvali, record (seal), rekey
    master = bytes(range(0x10, 0x30))
    cli = Session.from_shared_secret(master, 0x01, "client")
    srv = Session.from_shared_secret(master, 0x01, "server")
    recs = []
    for pt in [b"hello", b"", b"x" * 100]:
        rec = cli.seal(pt)
        recs.append({"pt": h(pt), "rec": h(rec)})
        assert srv.open(rec) == (0x17, pt)
    cli.rekey()
    srv.rekey()
    rec_rk = cli.seal(b"after rekey")
    assert srv.open(rec_rk) == (0x17, b"after rekey")
    fresh_c = Session.from_shared_secret(master, 0x01, "client")
    V["transport"] = {
        "master": h(master), "profile": 1,
        "c2s_key": h(fresh_c._c2s.key), "c2s_iv": h(fresh_c._c2s.iv),
        "s2c_key": h(fresh_c._s2c.key), "s2c_iv": h(fresh_c._s2c.iv),
        "records_client_send": recs,
        "after_rekey_rec": h(rec_rk), "after_rekey_pt": h(b"after rekey"),
        "rekey_label": h(TRANSPORT_LABEL + b"/rekey"),
    }

    # 9) Frame kodlashi (wire formatlar)
    srand = bytes(range(0x50, 0x70))
    ek_fake = bytes(range(256)) * 5                      # 1280 bayt (uzunlik sinovi)
    V["frames"] = {
        "ch": h(hs.enc_client_hello([0x0501], [0x01, 0x03], bytes(range(32)), b"", want_ticket=False, early=False)),
        "sh_no_sig": h(hs.enc_server_hello(0x0501, 0x01, srand, ek_fake, b"", 0x01)),
        "ckx": h(hs.enc_client_kex(bytes(range(200)))),
        "fin": h(hs.enc_finished(bytes(range(32)))),
        "client_auth": h(hs.enc_client_auth(bytes(range(16)), bytes(range(40)))),
        "alert_bad_finished": h(hs.enc_alert(hs.Alert.BAD_FINISHED)),
        "sh_core_flags1": h(hs._sh_core(0x0501, 0x01, srand, ek_fake, 0x01)),
    }

    # 10) Session resumption ticket (nonce ‖ AEAD(K, RMS‖profile‖issued; AAD=AQTKT‖len(ctx)‖ctx))
    from aether_q_v51.handshake import TicketAuthority  # noqa: E402
    tkey = bytes(range(0x40, 0x60))
    tnonce = bytes(range(12))
    trms = bytes(range(0x60, 0x80))
    tctx = b"tenant-A"
    tissued = 1_700_000_000
    taad = b"AQTKT" + len(tctx).to_bytes(2, "big") + tctx
    tpt = trms + bytes([0x01]) + tissued.to_bytes(8, "big")
    ticket = tnonce + ChaCha20Poly1305(tkey).encrypt(tnonce, tpt, taad)
    assert TicketAuthority(key=tkey).open(ticket, now=tissued + 10, context=tctx) == (trms, 0x01)
    V["ticket"] = {"key": h(tkey), "nonce": h(tnonce), "rms": h(trms), "profile": 1,
                   "context": h(tctx), "issued": tissued, "now": tissued + 10, "ticket": h(ticket)}

    # 11) PoW cookie + nonce (stateless puzzle, D=8)
    from aether_q_v51.dos import PuzzleAuthority, solve_pow, verify_pow  # noqa: E402
    psecret = bytes(range(0x80, 0xA0))
    pch = bytes((i * 3 + 1) & 0xFF for i in range(47))
    pnow = 1_700_000_000
    pauth = PuzzleAuthority(difficulty=8, secret=psecret)
    cookie = pauth.issue(pch, now=pnow)
    pnonce = solve_pow(cookie, 8)
    assert verify_pow(cookie, pnonce, 8)
    V["puzzle"] = {"secret": h(psecret), "difficulty": 8, "ch": h(pch), "now": pnow,
                   "cookie": h(cookie), "pow_nonce": pnonce}

    # 12) 0-RTT early data kaliti va blob (fixed nonce; Python open_early tekshiradi)
    from aether_q_v51.early import derive_early_key, open_early  # noqa: E402
    erms = bytes(range(0x30, 0x50))
    ech = bytes((i * 5 + 2) & 0xFF for i in range(47))
    edata = b"GET /health"
    enonce = bytes(range(12))
    ekey = derive_early_key(erms, ech)
    eblob = enonce + ChaCha20Poly1305(ekey).encrypt(enonce, edata, sha3_256(ech))
    assert open_early(erms, ech, eblob) == edata
    V["early"] = {"rms": h(erms), "ch": h(ech), "data": h(edata), "blob": h(eblob), "key": h(ekey)}

    # 13) Yangi frame'lar: HELLO_RETRY, CH_RETRY, NST, EARLY_DATA
    V["frames2"] = {
        "hello_retry": h(hs.enc_hello_retry(cookie, 8)),
        "ch_retry": h(hs.enc_client_hello_retry(cookie, pnonce, pch)),
        "nst": h(hs.enc_new_session_ticket(ticket, 3600)),
        "early_data": h(hs.enc_early_data(eblob)),
    }

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(v, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("wrote", out_path, "vectors:", ", ".join(V.keys()))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "aq51_wire_kat.json"))
