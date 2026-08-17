"""Majburiy testlar (spec §10) — GUI va CLI uchun umumiy to'plam."""
from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Callable

from .config import ProtocolConfig, hardened_config, spec_config
from .crypto import canonical
from .crypto.canonical import Encoding
from .crypto.primitives import (
    aead_open,
    aead_seal,
    argon2id,
    ed25519_generate,
    ed25519_pub,
    ed25519_sign,
    ed25519_verify,
    hkdf_sha512,
    hybrid_sign,
    hybrid_verify,
    mldsa_generate,
    mldsa_pub,
    mldsa_sign,
    mldsa_verify,
    mlkem_decaps,
    mlkem_encaps,
    mlkem_generate,
    mlkem_pub,
    random_bytes,
    sha3_256,
    x25519_dh,
    x25519_generate,
    x25519_pub,
)
from .protocol.envelope import Envelope, MsgType, message_nonce
from .protocol.errors import ProtocolError
from .protocol.identity import DeviceKeys, build_prekey_bundle, verify_prekey_bundle
from .protocol.merkle import build_tree, verify_proof
from .protocol.sfile import encrypt_file, receive_file
from .sim.world import World


@dataclass
class TestResult:
    group: str
    name: str
    ok: bool
    detail: str = ""
    ms: float = 0.0


TESTS: list[tuple[str, str, Callable[[ProtocolConfig], str]]] = []


def _flip(data: bytes) -> bytes:
    """Oxirgi baytning barcha bitlarini teskarisiga aylantiradi.

    Baytni 0x00 ga "o'rnatish" emas, aynan flip — aks holda bayt allaqachon
    0x00 bo'lsa, ma'lumot umuman o'zgarmaydi va test yolg'on o'tadi.
    """
    return bytes(data[:-1]) + bytes([data[-1] ^ 0xFF])


def test(group: str, name: str):
    def deco(fn):
        TESTS.append((group, name, fn))
        return fn

    return deco


# ===========================================================================
# 1. KAT / primitivlar
# ===========================================================================
@test("KAT", "SHA3-256 test vektori")
def _t_sha3(cfg):
    # NIST: SHA3-256("abc")
    got = sha3_256(b"abc").hex()
    exp = "3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532"
    assert got == exp, f"{got} != {exp}"
    return "NIST vektori mos"


@test("KAT", "HKDF-SHA-512 determinizmi")
def _t_hkdf(cfg):
    a = hkdf_sha512(b"ikm", b"salt", b"info", 64)
    b = hkdf_sha512(b"ikm", b"salt", b"info", 64)
    c = hkdf_sha512(b"ikm", b"salt", b"info2", 64)
    assert a == b and a != c and len(a) == 64
    return "bir xil kirish -> bir xil chiqish, info ajratadi"


@test("KAT", "ChaCha20-Poly1305 seal/open + AAD")
def _t_aead(cfg):
    k, n = random_bytes(32), random_bytes(12)
    ct = aead_seal(k, n, b"maxfiy", b"aad")
    assert aead_open(k, n, ct, b"aad") == b"maxfiy"
    try:
        aead_open(k, n, ct, b"boshqa-aad")
        raise AssertionError("noto'g'ri AAD qabul qilindi")
    except Exception as exc:
        if isinstance(exc, AssertionError):
            raise
    return "AAD o'zgarishi aniqlanadi"


@test("KAT", "X25519 kalit kelishuvi")
def _t_x25519(cfg):
    a, b = x25519_generate(), x25519_generate()
    assert x25519_dh(a, x25519_pub(b)) == x25519_dh(b, x25519_pub(a))
    return "ikki tomon bir xil sirni oladi"


@test("KAT", "Ed25519 imzo")
def _t_ed(cfg):
    sk = ed25519_generate()
    sig = ed25519_sign(sk, b"xabar")
    assert ed25519_verify(ed25519_pub(sk), sig, b"xabar")
    assert not ed25519_verify(ed25519_pub(sk), sig, b"boshqa")
    return "haqiqiy imzo o'tadi, soxtasi o'tmaydi"


@test("KAT", "ML-KEM-768 encaps/decaps (FIPS 203)")
def _t_mlkem(cfg):
    sk = mlkem_generate()
    pk = mlkem_pub(sk)
    assert len(pk) == 1184
    ss, ct = mlkem_encaps(pk)
    assert len(ct) == 1088 and len(ss) == 32
    assert mlkem_decaps(sk, ct) == ss
    return "pk=1184 ct=1088 ss=32, shared secret mos"


@test("KAT", "ML-DSA-65 imzo (FIPS 204)")
def _t_mldsa(cfg):
    sk = mldsa_generate()
    pk = mldsa_pub(sk)
    sig = mldsa_sign(sk, b"xabar")
    assert len(pk) == 1952 and len(sig) == 3309
    assert mldsa_verify(pk, sig, b"xabar")
    assert not mldsa_verify(pk, sig, b"boshqa")
    return "pk=1952 sig=3309, tekshiruv to'g'ri"


@test("KAT", "Gibrid imzo: bittasi buzilsa RAD ETILADI")
def _t_hybrid(cfg):
    ed, ml = ed25519_generate(), mldsa_generate()
    sig = hybrid_sign(ed, ml, b"M")
    assert hybrid_verify(ed25519_pub(ed), mldsa_pub(ml), sig, b"M")
    # Bit-flip ishlatiladi: oxirgi baytni 0x00 ga o'rnatish, agar u allaqachon
    # 0x00 bo'lsa, imzoni umuman o'zgartirmaydi (~1/256 yolg'on o'tish).
    bad = type(sig)(sig.ed25519, _flip(sig.mldsa65))
    assert not hybrid_verify(ed25519_pub(ed), mldsa_pub(ml), bad, b"M")
    bad2 = type(sig)(_flip(sig.ed25519), sig.mldsa65)
    assert not hybrid_verify(ed25519_pub(ed), mldsa_pub(ml), bad2, b"M")
    return "spec §5.3: 'bittasi o'tsa bo'ldi' siyosati yo'q"


@test("KAT", "Argon2id minimal profil")
def _t_argon(cfg):
    t0 = time.perf_counter()
    k = argon2id(b"parol", b"s" * 16, memory_kib=cfg.argon2_memory_kib,
                 time_cost=cfg.argon2_time_cost)
    dt = (time.perf_counter() - t0) * 1000
    assert len(k) == 32
    assert cfg.argon2_memory_kib >= 19 * 1024, "OWASP minimal poldan past"
    return f"m={cfg.argon2_memory_kib // 1024} MiB t={cfg.argon2_time_cost}, {dt:.0f} ms"


@test("KAT", "Rasmiy KAT vektorlari fayli (kat/scutum-q1-kat.json)")
def _t_kat_file(cfg):
    """Spec §10 p.1 — hujjat bilan birga yetkaziladigan test vektorlari."""
    from . import kat

    if not kat.KAT_PATH.exists():
        raise AssertionError("KAT fayli topilmadi — `python -m scutum.kat` ni ishga tushiring")
    vectors = kat.load()
    assert vectors["suite"] == "SCUTUM-Q1", "KAT boshqa suite uchun"
    errs = kat.verify(vectors)
    assert not errs, "; ".join(errs[:3])
    n = (len(vectors["primitives"]) + len(vectors["identity"])
         + len(vectors["handshake"]) + len(vectors["ratchet"])
         + len(vectors["s_file"]))
    return f"KAT v{vectors['kat_version']}, {n} vektor guruhi qayta hisoblandi"


@test("KAT", "Domen ajratgichlari kodda va KAT'da mos")
def _t_domain_seps(cfg):
    from . import kat

    declared = set(kat.load()["domain_separators"])
    root = kat.KAT_PATH.parent.parent / "scutum"
    found: set[str] = set()
    import re

    # kat.py va selftest.py — vosita kodi, protokol ajratgichlari emas
    tooling = {"kat.py", "selftest.py"}
    for path in root.rglob("*.py"):
        if path.name in tooling:
            continue
        for m in re.finditer(r'b"(SCUTUM-Q1/[A-Za-z/-]*)"', path.read_text("utf-8")):
            found.add(m.group(1))
    missing = found - declared
    assert not missing, f"KAT'da e'lon qilinmagan domen ajratgichlari: {sorted(missing)}"
    return f"{len(found)} ajratgich kodda topildi, hammasi e'lon qilingan"


@test("KAT", "Kanonik CBOR determinizmi")
def _t_cbor(cfg):
    obj = {"b": 2, "a": 1, "c": b"\x01\x02"}
    e1 = canonical.encode(obj, Encoding.CBOR_DETERMINISTIC)
    e2 = canonical.encode(dict(reversed(list(obj.items()))), Encoding.CBOR_DETERMINISTIC)
    assert e1 == e2, "kalit tartibi natijani o'zgartirdi"
    assert canonical.is_deterministic(e1)
    return "kalit tartibidan qat'i nazar bir xil baytlar"


# ===========================================================================
# 2. Handshake va sessiya (spec §10 p.2)
# ===========================================================================
@test("Sessiya", "INIT -> ACK -> MSG to'liq oqimi")
def _t_flow(cfg):
    w = World(cfg)
    sid = w.handshake()
    line = w.send(w.alice, "salom")
    assert line.ok, line.detail
    assert line.text == "salom"
    return f"sessiya {sid.hex()[:8]}, xabar yetkazildi"


@test("Sessiya", "Ikki tomonlama almashinuv (20 xabar)")
def _t_bidi(cfg):
    w = World(cfg)
    w.handshake()
    for i in range(20):
        line = w.send(w.alice if i % 2 == 0 else w.bob, f"m{i}")
        assert line.ok, f"{i}: {line.detail}"
    return "20/20 xabar muvaffaqiyatli"


@test("Sessiya", "Noto'g'ri imzoli PreKeyBundle rad etiladi")
def _t_bad_bundle(cfg):
    w = World(cfg)
    b = w.server.fetch_bundle(w.bob.device_id)
    b["sig_ed25519"] = _flip(b["sig_ed25519"])
    try:
        verify_prekey_bundle(b, cfg)
    except Exception:
        return "soxta imzo aniqlandi"
    raise AssertionError("soxta bundle qabul qilindi")


@test("Sessiya", "Noto'g'ri imzoli INIT rad etiladi")
def _t_bad_init(cfg):
    w = World(cfg)
    env = w.alice.start_session(w.server.fetch_bundle(w.bob.device_id))
    body = canonical.decode(env.body, cfg.encoding)
    body["sig"] = _flip(body["sig"])
    env.body = canonical.encode(body, cfg.encoding)
    try:
        w.bob.accept_session(env)
    except Exception:
        return "soxta INIT imzosi aniqlandi"
    raise AssertionError("soxta INIT qabul qilindi")


@test("Sessiya", "Xabar replay to'siladi")
def _t_replay(cfg):
    w = World(cfg)
    w.handshake()
    env = w.alice.send(w.session_id, b"pul o'tkaz")
    w.bob.receive(Envelope.from_wire(env.to_wire(cfg), cfg))
    try:
        w.bob.receive(Envelope.from_wire(env.to_wire(cfg), cfg))
    except Exception:
        return "takroriy xabar rad etildi"
    raise AssertionError("replay o'tib ketdi")


@test("Sessiya", "session_id kolliziyasi rad etiladi (K-6)")
def _t_session_collision(cfg):
    """Tashqi audit (2026-08-16) topilmasi: attacker-tanlangan session_id
    mavjud sessiyani jimgina almashtira olmasligi kerak."""
    from .protocol.handshake import create_init

    w = World(cfg)
    fixed_sid = b"\x22" * 16
    bundle1 = w.server.fetch_bundle(w.bob.device_id)
    st1 = create_init(w.alice.device, bundle1, cfg, session_id=fixed_sid)
    w.bob.accept_session(st1.envelope)
    w.server.publish_bundle(w.bob.device_id, w.bob.bundle())
    original_state = w.bob.sessions[fixed_sid].state

    bundle2 = w.server.fetch_bundle(w.bob.device_id)
    st2 = create_init(w.mallory.device, bundle2, cfg, session_id=fixed_sid)
    try:
        w.bob.accept_session(st2.envelope)
    except Exception:
        assert w.bob.sessions[fixed_sid].state is original_state
        return "kolliziya rad etildi, asl sessiya saqlandi"
    raise AssertionError("session_id kolliziyasi qabul qilindi — sessiya almashtirildi")


@test("Sessiya", "Soxta ratchet sarlavhasi holatni buzmaydi (tashqi audit)")
def _t_forged_header_no_corruption(cfg):
    """2026-08-17 topilma: avval AEAD tekshiruvidan OLDIN `st` mutatsiya
    qilinardi — soxta dh_pk/pq_ct bilan bitta paket sessiyani doimiy
    buzardi, garchi paketning o'zi oxir-oqibat rad etilsa ham."""
    from .crypto import canonical
    from .crypto.primitives import x25519_generate, x25519_pub, random_bytes

    w = World(cfg)
    w.handshake()
    env1 = w.alice.send(w.session_id, b"asl xabar")
    w.bob.receive(Envelope.from_wire(env1.to_wire(cfg), cfg))
    bob_state = w.bob.sessions[w.session_id].state
    dhr_before, rk_before = bob_state.dhr_pk, bob_state.rk

    d = canonical.decode(env1.to_wire(cfg), cfg.encoding)
    d["hdr"]["dh"] = x25519_pub(x25519_generate())
    d["hdr"]["n"] = 0
    d["no"] = 999
    d["body"] = random_bytes(64)
    forged = canonical.encode(d, cfg.encoding)
    try:
        w.bob.receive(Envelope.from_wire(forged, cfg))
        raise AssertionError("soxta paket qabul qilindi")
    except AssertionError:
        raise
    except Exception:
        pass
    assert bob_state.dhr_pk == dhr_before, "dhr_pk muvaffaqiyatsiz urinishdan keyin o'zgardi"
    assert bob_state.rk == rk_before, "rk muvaffaqiyatsiz urinishdan keyin o'zgardi"
    env2 = w.alice.send(w.session_id, b"ikkinchi haqiqiy xabar")
    msg = w.bob.receive(Envelope.from_wire(env2.to_wire(cfg), cfg))
    assert msg.plaintext == b"ikkinchi haqiqiy xabar"
    return "soxta paketdan keyin ham holat toza, keyingi xabar ochildi"


@test("Sessiya", "CLOSE autentifikatsiyalanadi (tashqi audit)")
def _t_close_authenticated(cfg):
    from .protocol.envelope import MsgType

    w = World(cfg)
    w.handshake()
    forged = Envelope(
        type=MsgType.CLOSE, sender_device_id=w.mallory.device_id,
        recipient_device_id=w.bob.device_id, session_id=w.session_id,
        timestamp=0, message_no=999,
    )
    try:
        w.bob.receive(forged)
        raise AssertionError("imzosiz/shifrlanmagan CLOSE qabul qilindi")
    except AssertionError:
        raise
    except Exception:
        pass
    assert not w.bob.sessions[w.session_id].state.closed
    line = w.send(w.alice, "soxta CLOSE'dan keyin ham ishlaydi")
    assert line.ok
    close_env = w.alice.close(w.session_id)
    w.bob.receive(Envelope.from_wire(close_env.to_wire(cfg), cfg))
    assert w.bob.sessions[w.session_id].state.closed
    return "soxta CLOSE rad etildi, haqiqiy (AEAD orqali) CLOSE ishladi"


@test("Sessiya", "revoke_epoch bundle imzosiga kiradi (tashqi audit)")
def _t_revoke_epoch_signed(cfg):
    if not cfg.sign_full_bundle:
        return "SPEC: bundle imzosi xom konkatenatsiya, bu tekshiruv HARDENED uchun"
    w = World(cfg)
    w.bob.device.revoke_epoch = 5
    bundle = w.bob.bundle()
    tampered = dict(bundle)
    tampered["revoke_epoch"] = 0
    try:
        verify_prekey_bundle(tampered, cfg)
        raise AssertionError("revoke_epoch pasaytirilgan bundle imzosi hali ham haqiqiy deb topildi")
    except AssertionError:
        raise
    except Exception:
        pass
    return "revoke_epoch o'zgartirilsa bundle imzosi buziladi"


@test("Sessiya", "Xavfsizlik raqami o'zgarishi kuzatiladi (tashqi audit)")
def _t_trust_observed(cfg):
    """`check_trust`/`trust` avval hech qayerda chaqirilmasdi (dekorativ)."""
    events = []
    w = World(cfg)
    w.alice._on_event = lambda name, text, data: events.append(text)
    w.handshake()
    assert any("TRUST" in e for e in events), "birinchi handshake'da TRUST hodisasi yo'q"
    assert w.bob.device_id in w.alice.trusted, "birinchi ko'rilgan qurilma pinlanmadi"
    return f"{sum(1 for e in events if 'TRUST' in e)} ta TRUST hodisasi kuzatildi"


@test("Sessiya", "Ciphertext o'zgartirilsa rad etiladi")
def _t_tamper(cfg):
    w = World(cfg)
    w.handshake()
    env = w.alice.send(w.session_id, b"aslida")
    d = canonical.decode(env.to_wire(cfg), cfg.encoding)
    body = bytearray(d["body"])
    body[0] ^= 0xFF
    d["body"] = bytes(body)
    try:
        w.bob.receive(Envelope.from_wire(canonical.encode(d, cfg.encoding), cfg))
    except Exception:
        return "AEAD tegi o'zgarishni aniqladi"
    raise AssertionError("o'zgartirilgan xabar qabul qilindi")


@test("Sessiya", "AAD maydonini almashtirish rad etiladi")
def _t_aad(cfg):
    w = World(cfg)
    w.handshake()
    env = w.alice.send(w.session_id, b"asl")
    d = canonical.decode(env.to_wire(cfg), cfg.encoding)
    d["ts"] = d["ts"] + 1000        # timestamp AAD ichida (spec §4)
    try:
        w.bob.receive(Envelope.from_wire(canonical.encode(d, cfg.encoding), cfg))
    except Exception:
        return "timestamp o'zgarishi aniqlandi"
    raise AssertionError("AAD almashtirildi va sezilmadi")


@test("Sessiya", "Tartibi buzilgan yetkazish")
def _t_ooo(cfg):
    w = World(cfg)
    w.handshake()
    envs = [w.alice.send(w.session_id, f"m{i}".encode()) for i in range(5)]
    got = []
    for env in reversed(envs):        # teskari tartibda
        got.append(w.bob.receive(env).plaintext.decode())
    assert sorted(got) == sorted(f"m{i}" for i in range(5)), got
    return "5/5 xabar teskari tartibda ochildi"


@test("Sessiya", "Post-kvant ratchet root-key'ni yangilaydi")
def _t_pq(cfg):
    w = World(cfg)
    w.handshake()
    w.send(w.alice, "oldin")
    before = w.alice.sessions[w.session_id].state.rk
    w.pq_ratchet(w.alice)
    st = w.alice.sessions[w.session_id].state
    assert st.rk != before, "RK o'zgarmadi"
    assert st.pq_steps >= 1, "PQ qadam hisoblanmadi"
    line = w.send(w.alice, "keyin")
    assert line.ok, line.detail
    return f"RK yangilandi, PQ qadam #{st.pq_steps}, aloqa saqlandi"


@test("Sessiya", "OPK majburiyligi (spec §5.2)")
def _t_opk_mandatory(cfg):
    """HARDENED: OPK'siz bundle rad etilishi MUST. SPEC: OPK ta'sirsiz."""
    w = World(cfg)
    bundle = build_prekey_bundle(w.bob.device, cfg, with_opk=False)
    try:
        w.alice.start_session(bundle)
        accepted = True
    except Exception:
        accepted = False
    if cfg.include_opk_dh:
        assert not accepted, "OPK'siz bundle qabul qilindi — §5.2 buzildi"
        return "OPK'siz bundle rad etildi"
    assert accepted, "SPEC rejimida OPK'siz bundle rad etildi"
    return "SPEC: OPK ta'sirsiz, bundle qabul qilindi (K-2 ko'rinishi)"


@test("Sessiya", "Skipped-key limiti va TTL (spec §6.5)")
def _t_skipped_bounds(cfg):
    if not cfg.advance_chain_key:
        return "SPEC: CK statik — skipped mexanizmi ishlatilmaydi"
    w = World(cfg)
    w.handshake()
    st_b = w.bob.sessions[w.session_id].state
    envs = [w.alice.send(w.session_id, f"m{i}".encode()) for i in range(50)]
    w.bob.receive(envs[-1])
    stored = len(st_b.skipped)
    assert stored == 49, f"kutilgan 49 saqlangan kalit, {stored} topildi"
    assert all(isinstance(v, tuple) and len(v) == 2 for v in st_b.skipped.values()), \
        "skipped yozuvlari (MK, vaqt) juftligi bo'lishi kerak"

    if cfg.bounded_skipped_keys:
        expired = replace(cfg, skipped_ttl_secs=0)
        from .protocol.ratchet import _trim_skipped

        _trim_skipped(st_b, expired)
        assert not st_b.skipped, f"TTL o'tgan kalitlar tozalanmadi: {len(st_b.skipped)}"
        return f"{stored} kalit saqlandi, TTL bo'yicha hammasi tozalandi"
    return f"{stored} kalit saqlandi (limit yoqilmagan)"


@test("Sessiya", "Bekor qilingan qurilmaga sessiya ochilmaydi")
def _t_revoke(cfg):
    w = World(cfg)
    w.alice.revoke_device(w.bob.device.dc())
    try:
        w.alice.start_session(w.server.fetch_bundle(w.bob.device_id))
    except Exception:
        return "DEVICE_REVOKE siyosati qo'llandi"
    raise AssertionError("bekor qilingan qurilmaga sessiya ochildi")


# ===========================================================================
# 3. S-FILE (spec §10 p.3)
# ===========================================================================
@test("S-FILE", "Shifrlash -> qabul qilish -> to'liq tiklash")
def _t_file(cfg):
    c = replace(cfg, chunk_size=8192)
    data = random_bytes(8192 * 4 + 555)
    enc = encrypt_file(data, c, name="a.bin", mime="application/octet-stream")
    res = receive_file(enc.manifest, enc.fk, enc.chunks, c)
    assert res.ok, res.error
    assert res.data == data, "tiklangan ma'lumot mos emas"
    return f"{enc.manifest['total_chunks']} bo'lak, bayt-bayt mos"


@test("S-FILE", "Bo'lak o'zgartirilsa aniqlanadi")
def _t_file_tamper(cfg):
    c = replace(cfg, chunk_size=4096)
    enc = encrypt_file(random_bytes(4096 * 3), c, name="a")
    ch = list(enc.chunks)
    bad = bytearray(ch[1].ciphertext)
    bad[5] ^= 0x01
    ch[1] = type(ch[1])(1, bytes(bad), b"")
    res = receive_file(enc.manifest, enc.fk, ch, c)
    assert not res.ok, "o'zgartirilgan bo'lak qabul qilindi"
    return f"rad etildi: {res.error}"


@test("S-FILE", "Truncation aniqlanadi")
def _t_file_trunc(cfg):
    c = replace(cfg, chunk_size=4096)
    enc = encrypt_file(random_bytes(4096 * 4), c, name="a")
    res = receive_file(enc.manifest, enc.fk, enc.chunks[:-1], c)
    assert not res.ok
    return f"rad etildi: {res.error}"


@test("S-FILE", "Takroriy bo'lak aniqlanadi")
def _t_file_dup(cfg):
    c = replace(cfg, chunk_size=4096)
    enc = encrypt_file(random_bytes(4096 * 3), c, name="a")
    ch = list(enc.chunks)
    ch[2] = ch[1]
    res = receive_file(enc.manifest, enc.fk, ch, c)
    assert not res.ok
    return f"rad etildi: {res.error}"


@test("S-FILE", "Merkle isboti tekshiriladi")
def _t_merkle(cfg):
    c = replace(cfg, chunk_size=4096)
    enc = encrypt_file(random_bytes(4096 * 7 + 10), c, name="a")
    total = enc.manifest["total_chunks"]
    for i in range(total):
        ok = verify_proof(enc.chunks[i].leaf, enc.proof(i),
                          enc.manifest["root_hash"], c, total=total)
        assert ok, f"bo'lak {i} isboti o'tmadi"
    bad = verify_proof(sha3_256(b"soxta"), enc.proof(0),
                       enc.manifest["root_hash"], c, total=total)
    assert not bad, "soxta barg isbotdan o'tdi"
    return f"{total}/{total} isbot o'tdi, soxta barg rad etildi"


@test("S-FILE", "Manifest almashtirilsa aniqlanadi")
def _t_manifest(cfg):
    c = replace(cfg, chunk_size=4096)
    enc = encrypt_file(random_bytes(4096 * 3), c, name="a")
    m = dict(enc.manifest)
    m["plaintext_size"] = m["plaintext_size"] - 1     # AAD_i ichida
    res = receive_file(m, enc.fk, enc.chunks, c)
    assert not res.ok
    return f"rad etildi: {res.error}"


# ===========================================================================
# 4. Fuzzing (spec §10 p.4)
# ===========================================================================
@test("Fuzz", "Buzilgan wire: faqat ProtocolError chiqadi (1000 ta)")
def _t_fuzz_wire(cfg):
    """Spec §10 p.4 + §10.1: har qanday kirish uchun yagona xato sinfi."""
    w = World(cfg)
    w.handshake()
    base = w.alice.send(w.session_id, b"asos").to_wire(cfg)
    import random as _r

    rnd = _r.Random(1234)
    leaks: dict[str, int] = {}
    for _ in range(1000):
        b = bytearray(base)
        for _ in range(rnd.randint(1, 6)):
            b[rnd.randrange(len(b))] = rnd.randrange(256)
        try:
            w.bob.receive(Envelope.from_wire(bytes(b), cfg))
        except ProtocolError:
            pass
        except Exception as exc:  # noqa: BLE001
            leaks[type(exc).__name__] = leaks.get(type(exc).__name__, 0) + 1
    assert not leaks, f"xom istisnolar oqib chiqdi: {leaks}"
    return "1000 mutatsiya, barchasi ProtocolError bilan yopildi"


@test("Fuzz", "Tasodifiy baytlar: faqat ProtocolError chiqadi (1000 ta)")
def _t_fuzz_random(cfg):
    import random as _r

    rnd = _r.Random(99)
    leaks: dict[str, int] = {}
    for _ in range(1000):
        raw = bytes(rnd.randrange(256) for _ in range(rnd.randint(1, 400)))
        try:
            Envelope.from_wire(raw, cfg)
        except ProtocolError:
            pass
        except Exception as exc:  # noqa: BLE001
            leaks[type(exc).__name__] = leaks.get(type(exc).__name__, 0) + 1
    assert not leaks, f"xom istisnolar oqib chiqdi: {leaks}"
    return "1000 tasodifiy blob, parser barqaror"


@test("Fuzz", "Buzilgan INIT: faqat ProtocolError chiqadi (400 ta)")
def _t_fuzz_init(cfg):
    import random as _r

    w = World(cfg)
    base = w.alice.start_session(w.server.fetch_bundle(w.bob.device_id)).to_wire(cfg)
    rnd = _r.Random(7)
    leaks: dict[str, int] = {}
    for _ in range(400):
        b = bytearray(base)
        for _ in range(rnd.randint(1, 6)):
            b[rnd.randrange(len(b))] = rnd.randrange(256)
        try:
            w.bob.accept_session(Envelope.from_wire(bytes(b), cfg))
        except ProtocolError:
            pass
        except Exception as exc:  # noqa: BLE001
            leaks[type(exc).__name__] = leaks.get(type(exc).__name__, 0) + 1
    assert not leaks, f"xom istisnolar oqib chiqdi: {leaks}"
    return "400 mutatsiya, handshake parser barqaror"


# ===========================================================================
# 5. Gigiyena (spec §10 p.5)
# ===========================================================================
@test("Gigiyena", "Loglarda maxfiy kalit/plaintext yo'q")
def _t_no_secrets(cfg):
    w = World(cfg)
    w.handshake()
    secret = "JUDA-MAXFIY-MATN-42"
    w.send(w.alice, secret)
    st = w.alice.sessions[w.session_id].state
    blob = " ".join(f"{e.actor} {e.text}" for e in w.trace.events)
    assert secret not in blob, "ochiq matn logga tushdi"
    for name, val in (("RK", st.rk), ("CKs", st.cks)):
        if val and val.hex() in blob:
            raise AssertionError(f"{name} logga tushdi")
    return f"{len(w.trace.events)} log yozuvi tekshirildi — toza"


@test("Gigiyena", "Xato javoblari yagona wire kodiga ega")
def _t_error_uniform(cfg):
    from .protocol.errors import DecryptionError, ProtocolError, ReplayError

    codes = {ProtocolError("a").wire(), DecryptionError("b").wire(),
             ReplayError("c").wire()}
    assert len(codes) == 1, f"turli kodlar: {codes}"
    return "spec §10.1: xato sababi tarmoqqa oshkor bo'lmaydi"


@test("Gigiyena", "Nonce har xabar uchun yagona (1000 xabar)")
def _t_nonce_unique(cfg):
    sid = random_bytes(16)
    seen = set()
    for i in range(1000):
        n = message_nonce(sid, b"\x00", i)
        assert n not in seen, f"nonce takrorlandi, i={i}"
        seen.add(n)
    return "1000/1000 yagona"


@test("Gigiyena", "Envelope o'lchamlari oqilona")
def _t_sizes(cfg):
    w = World(cfg)
    sid = w.handshake()
    init = next(e for _t, _r, wr in w.server.captured
                for e in [Envelope.from_wire(wr, cfg)] if e.type == MsgType.INIT)
    msg = w.alice.send(sid, b"x" * 100)
    return (f"INIT {init.size(cfg):,} B (ML-KEM ct 1088 + ML-DSA sig 3309), "
            f"MSG {msg.size(cfg):,} B")


# ===========================================================================
# 6. ROSTOR-1 — spec `docs/SPEC-ROSTOR-1.1.md`
# ===========================================================================
@test("ROSTOR", "SMT: borlik va yo'qlik isboti (§8.2)")
def _t_rostor_smt(cfg):
    from .rostor.smt import SparseMerkleTree, smt_key, verify_smt_proof

    t = SparseMerkleTree()
    keys = [smt_key(f"k{i}".encode()) for i in range(9)]
    for i, k in enumerate(keys):
        t.set(k, f"v{i}".encode())
    root = t.root()
    for i, k in enumerate(keys):
        p = t.prove(k)
        assert p.value == f"v{i}".encode()
        assert verify_smt_proof(p, root)
    missing = t.prove(smt_key(b"never-registered"))
    assert missing.value is None
    assert verify_smt_proof(missing, root)
    forged = missing.__class__(key=keys[0], value=None, siblings=missing.siblings)
    assert not verify_smt_proof(forged, root), "mavjud kalit uchun soxta yo'qlik isboti o'tdi"
    return f"{len(keys)} inclusion + 1 non-inclusion isbot, soxtalashtirish rad etildi"


@test("ROSTOR", "Merkle consistency proof: tarixni qayta yozish aniqlanadi (§8.3)")
def _t_rostor_consistency(cfg):
    from .config import hardened_config
    from .protocol.merkle import build_tree, consistency_proof, verify_consistency
    from .crypto.primitives import sha3_256

    hcfg = hardened_config()
    leaves = [sha3_256(f"leaf{i}".encode()) for i in range(9)]
    old_root = build_tree(leaves[:4], hcfg).tree_root
    new_root = build_tree(leaves, hcfg).tree_root
    proof = consistency_proof(leaves, 4, hcfg)
    assert verify_consistency(4, 9, proof, old_root, new_root, hcfg)

    rewritten = list(leaves)
    rewritten[0] = sha3_256(b"tarix qayta yozildi")
    bad_root = build_tree(rewritten, hcfg).tree_root
    bad_proof = consistency_proof(rewritten, 4, hcfg)
    assert not verify_consistency(4, 9, bad_proof, old_root, bad_root, hcfg)
    return "o'sish tasdiqlandi, tarix qayta yozish aniqlandi"


@test("ROSTOR", "Shaffoflik jurnali: witness-cosign, freshness, rollback (§8.4-8.6)")
def _t_rostor_transparency(cfg):
    from .crypto.primitives import ed25519_generate, ed25519_pub, mldsa_generate, mldsa_pub, random_bytes
    from .rostor.transparency import TransparencyLog, LogClient, Witness, build_registry_payload, sign_log_entry
    from .rostor.errors import LogError

    op_ed, op_ml = ed25519_generate(), mldsa_generate()
    log = TransparencyLog(random_bytes(16), op_ed, op_ml)
    w1 = Witness(random_bytes(16), ed25519_generate(), mldsa_generate())
    w2 = Witness(random_bytes(16), ed25519_generate(), mldsa_generate())
    client = LogClient(ed25519_pub(op_ed), mldsa_pub(op_ml),
        {w1.witness_id: (ed25519_pub(w1.ed_sk), mldsa_pub(w1.mldsa_sk)),
         w2.witness_id: (ed25519_pub(w2.ed_sk), mldsa_pub(w2.mldsa_sk))})

    sub_ed, sub_ml, sub_id = ed25519_generate(), mldsa_generate(), random_bytes(16)
    log.submit(sign_log_entry(sub_ed, sub_ml, sub_id, "institution",
                              build_registry_payload(b"k0", b"p0")))
    sth = log.publish_sth()
    sth.witness_sigs = [w1.cosign(sth, log.entries)]   # faqat 1 ta -> yetarsiz
    try:
        client.accept_sth(sth)
        raise AssertionError("yetarsiz witness bilan qabul qilindi")
    except LogError:
        pass
    sth.witness_sigs.append(w2.cosign(sth, log.entries))
    client.accept_sth(sth, entries=log.entries)
    checkpoint_1 = client.checkpoint

    log.submit(sign_log_entry(sub_ed, sub_ml, sub_id, "institution",
                              build_registry_payload(b"k1", b"p1")))
    sth2 = log.publish_sth()
    sth2.witness_sigs = [w1.cosign(sth2, log.entries), w2.cosign(sth2, log.entries)]
    client.accept_sth(sth2, entries=log.entries)

    try:
        client.accept_sth(sth)   # eski, kichikroq STH qayta yuborilishi -> rollback
        raise AssertionError("rollback aniqlanmadi")
    except LogError:
        pass
    return f"witness threshold, {checkpoint_1[0]}->{client.checkpoint[0]} o'sish, rollback aniqlandi"


@test("ROSTOR", "SMT reestr faqat jurnaldan derive qilinadi (tashqi audit, KRITIK)")
def _t_rostor_log_smt_binding(cfg):
    """2026-08-17 topilma: avval SMT reestr `apply_registry_update()`
    orqali jurnaldan MUSTAQIL o'zgarardi — witness/client buni sezmasdi.
    Endi `smt_root` faqat `derive_registry(entries)` orqali TASDIQLANADI."""
    from .crypto.primitives import ed25519_generate, ed25519_pub, mldsa_generate, mldsa_pub, random_bytes
    from .rostor.transparency import (
        TransparencyLog, LogClient, Witness, build_registry_payload,
        derive_registry, sign_log_entry,
    )
    from .rostor.smt import smt_key
    from .rostor.errors import LogError

    op_ed, op_ml = ed25519_generate(), mldsa_generate()
    log = TransparencyLog(random_bytes(16), op_ed, op_ml)
    w1 = Witness(random_bytes(16), ed25519_generate(), mldsa_generate())
    client = LogClient(ed25519_pub(op_ed), mldsa_pub(op_ml),
                       {w1.witness_id: (ed25519_pub(w1.ed_sk), mldsa_pub(w1.mldsa_sk))},
                       min_witness_cosigns=1)
    sub_ed, sub_ml, sub_id = ed25519_generate(), mldsa_generate(), random_bytes(16)
    log.submit(sign_log_entry(sub_ed, sub_ml, sub_id, "institution",
                              build_registry_payload(b"real-inst", b"real-value")))

    assert log.registry.root() == derive_registry(log.entries).root(), \
        "log.registry jurnaldan derive qilingan holatga mos emas"
    assert log.lookup(b"real-inst").value == b"real-value"

    # Yovuz operator jurnalga TEGMASDAN, to'g'ridan-to'g'ri SMT'ni o'zgartiradi
    log.registry.set(smt_key(b"soxta-institutsiya"), b"soxta")
    sth = log.publish_sth()   # buzilgan registry bilan STH yasaydi
    try:
        w1.cosign(sth, log.entries)
        raise AssertionError("witness jurnalga mos kelmaydigan smt_root'ni imzoladi")
    except LogError:
        pass
    try:
        client.accept_sth(sth, entries=log.entries)
        raise AssertionError("client jurnalga mos kelmaydigan smt_root'ni qabul qildi")
    except LogError:
        pass
    return "jurnaldan tashqari SMT o'zgarishi witness va client tomonidan aniqlandi"


@test("ROSTOR", "Registrator konsorsiumi: k-of-n va domen ajratish (§4.1)")
def _t_rostor_registrar(cfg):
    import time as _t
    from .crypto.primitives import ed25519_generate, ed25519_pub, mldsa_generate, mldsa_pub, hybrid_sign, random_bytes
    from .rostor.registrar import (GenesisAnchor, RegistrarEntry, RegistrarRoster,
        RegistrarApproval, verify_registrar_approval)

    members = [(random_bytes(16), ed25519_generate(), mldsa_generate()) for _ in range(5)]
    genesis = GenesisAnchor(v=1, roster_epoch=0, published_at=int(_t.time()), registrars=[
        RegistrarEntry(rid, ed25519_pub(ed), mldsa_pub(ml), f"R{i}")
        for i, (rid, ed, ml) in enumerate(members)
    ])
    roster = RegistrarRoster(genesis)
    K = 3
    appr = RegistrarApproval(log_id=random_bytes(16), action="issue_ic",
                             roster_epoch=0, target_hash=random_bytes(32))
    signed = appr.signed_payload()
    for rid, ed, ml in members[:2]:
        appr.approvals.append((rid, hybrid_sign(ed, ml, signed)))
    assert not verify_registrar_approval(appr, roster, K), "2/5 (K=3) bilan o'tdi"
    appr.approvals.append((members[2][0], hybrid_sign(members[2][1], members[2][2], signed)))
    assert verify_registrar_approval(appr, roster, K)

    appr_wrong_action = RegistrarApproval(log_id=appr.log_id, action="revoke",
                                          roster_epoch=0, target_hash=appr.target_hash)
    appr_wrong_action.approvals = appr.approvals
    assert not verify_registrar_approval(appr_wrong_action, roster, K), \
        "imzo boshqa 'action' uchun qayta ishlatildi"
    return "3/5 kvorum o'tdi, 2/5 rad etildi, domen ajratish ishladi"


@test("ROSTOR", "IC->IDC->badge zanjiri va fishing rad etilishi (§9-10, R6)")
def _t_rostor_badge(cfg):
    from .config import hardened_config
    from .protocol.identity import DeviceKeys
    from .rostor.identity import InstitutionKeys, issue_endorsement
    from .rostor.badge import derive_badge, LogSnapshot, Badge
    from .crypto.primitives import hybrid_sign

    hcfg = hardened_config()
    bank = InstitutionKeys.generate("bank", "Bank X")
    idc = DeviceKeys.generate("Bank X backend", hcfg)
    endorsement = issue_endorsement(bank, idc.dc())
    snap = LogSnapshot(institutions={bank.institution_id: bank.certificate()},
                       endorsements={idc.device_id: endorsement})

    msg = b"350000 som"
    sig = hybrid_sign(idc.ik_ed, idc.ik_mldsa, msg)
    res = derive_badge(idc_dc=idc.dc(), sig=sig, signed_payload=msg, snapshot=snap)
    assert res.badge == Badge.VERIFIED

    attacker = DeviceKeys.generate("Firibgar", hcfg)
    fake_sig = hybrid_sign(attacker.ik_ed, attacker.ik_mldsa, msg)
    res2 = derive_badge(idc_dc=idc.dc(), sig=fake_sig, signed_payload=msg, snapshot=snap)
    assert res2.badge == Badge.INVALID_SIGNATURE

    res3 = derive_badge(idc_dc=attacker.dc(), sig=hybrid_sign(attacker.ik_ed, attacker.ik_mldsa, msg),
                        signed_payload=msg, snapshot=snap)
    assert res3.badge == Badge.UNVERIFIED

    bank.revoke()
    snap.institutions[bank.institution_id] = bank.certificate()
    res4 = derive_badge(idc_dc=idc.dc(), sig=sig, signed_payload=msg, snapshot=snap)
    assert res4.badge == Badge.REVOKED
    return "VERIFIED / INVALID_SIGNATURE / UNVERIFIED / REVOKED — barchasi to'g'ri"


@test("ROSTOR", "Soxta IDC (device_id o'g'irlash) rad etiladi (tashqi audit, KRITIK)")
def _t_rostor_badge_dc_substitution(cfg):
    """2026-08-17 topilma: `device_id` ochiq maydon — hujumchi haqiqiy
    institutsiyaning device_id'sini olib, ichiga o'z ochiq kalitlarini
    qo'ygan soxta DC yasab, o'z maxfiy kaliti bilan imzolab VERIFIED
    belgisini olishi mumkin edi (endorsement.dc_hash tekshirilmagani uchun)."""
    from .config import hardened_config
    from .protocol.identity import DeviceKeys
    from .rostor.identity import InstitutionKeys, issue_endorsement
    from .rostor.badge import derive_badge, LogSnapshot, Badge
    from .crypto.primitives import hybrid_sign

    hcfg = hardened_config()
    bank = InstitutionKeys.generate("bank", "Bank Y")
    real_idc = DeviceKeys.generate("Bank Y backend", hcfg)
    endorsement = issue_endorsement(bank, real_idc.dc())
    snap = LogSnapshot(institutions={bank.institution_id: bank.certificate()},
                       endorsements={real_idc.device_id: endorsement})

    attacker = DeviceKeys.generate("Firibgar", hcfg)
    forged_dc = dict(attacker.dc())
    forged_dc["device_id"] = real_idc.device_id   # haqiqiy device_id o'g'irlanadi

    msg = b"forged idc test"
    sig = hybrid_sign(attacker.ik_ed, attacker.ik_mldsa, msg)
    res = derive_badge(idc_dc=forged_dc, sig=sig, signed_payload=msg, snapshot=snap)
    assert res.badge != Badge.VERIFIED, "soxta IDC VERIFIED belgisini oldi"

    real_sig = hybrid_sign(real_idc.ik_ed, real_idc.ik_mldsa, msg)
    res2 = derive_badge(idc_dc=real_idc.dc(), sig=real_sig, signed_payload=msg, snapshot=snap)
    assert res2.badge == Badge.VERIFIED, "haqiqiy IDC buzildi"
    return f"soxta IDC -> {res.badge.value}, haqiqiy IDC -> VERIFIED"


@test("ROSTOR", "TXN_CONFIRM: to'liq bog'lanish (request_hash, R7)")
def _t_rostor_txn_confirm(cfg):
    from .config import hardened_config
    from .protocol.identity import DeviceKeys
    from .rostor.txn_confirm import (create_txn_confirm_request, create_txn_confirm_response,
        verify_txn_confirm_response)

    hcfg = hardened_config()
    bank_idc = DeviceKeys.generate("Bank backend", hcfg)
    user = DeviceKeys.generate("Foydalanuvchi", hcfg)

    small = create_txn_confirm_request(bank_idc, b"\x01" * 16, amount_minor=100000,
                                       currency="UZS", recipient_masked="****0001", purpose="kichik")
    big = create_txn_confirm_request(bank_idc, b"\x01" * 16, amount_minor=35_000_00,
                                     currency="UZS", recipient_masked="****9999", purpose="katta")
    resp_for_small = create_txn_confirm_response(user, small, "APPROVE", account_id=b"\x02" * 16)
    assert verify_txn_confirm_response(resp_for_small, user.dc(), small)
    assert not verify_txn_confirm_response(resp_for_small, user.dc(), big), \
        "kichik so'rovga berilgan javob katta so'rovga yopishtirildi"

    import time as _t
    expired = create_txn_confirm_request(bank_idc, b"\x01" * 16, amount_minor=1,
                                         currency="UZS", recipient_masked="x", purpose="x",
                                         ttl_secs=1, now=int(_t.time()) - 10)
    resp = create_txn_confirm_response(user, expired, "APPROVE", account_id=b"\x02" * 16)
    assert not verify_txn_confirm_response(resp, user.dc(), expired), "muddati o'tgan so'rov qabul qilindi"
    return "request_hash bog'lanishi va muddat tekshiruvi to'g'ri"


@test("ROSTOR", "PaymentIntent: kredensial-maydon rad etiladi (§14, R9)")
def _t_rostor_payment(cfg):
    from .config import hardened_config
    from .protocol.identity import DeviceKeys
    from .rostor.payment import create_payment_intent, verify_payment_intent, reject_unknown_fields
    from .rostor.errors import PolicyViolation

    hcfg = hardened_config()
    merchant = DeviceKeys.generate("Merchant", hcfg)
    intent = create_payment_intent(merchant, memo="Yetkazib berish")
    assert verify_payment_intent(intent, merchant.dc())
    try:
        create_payment_intent(merchant, memo="http://fake-click.uz/pay")
        raise AssertionError("URL saqlovchi memo qabul qilindi")
    except PolicyViolation:
        pass
    try:
        reject_unknown_fields({"v": 1, "card_number": "1234"})
        raise AssertionError("card_number maydoni qabul qilindi")
    except PolicyViolation:
        pass
    return "imzo tekshirildi, URL memo va kredensial maydon rad etildi"


@test("ROSTOR", "AccountAuthState: kvorum va rollback himoyasi (§13, R8)")
def _t_rostor_account(cfg):
    from .config import hardened_config
    from .protocol.identity import DeviceKeys
    from .rostor.account import (AccountAuthState, RecoveryPolicy, create_recovery_request,
        create_quorum_approval, apply_recovery, commit_approver_roster)
    from .rostor.errors import AccountAuthError
    from .crypto.primitives import ed25519_generate, ed25519_pub, mldsa_generate, mldsa_pub

    hcfg = hardened_config()
    new_dev = DeviceKeys.generate("Yangi qurilma", hcfg)
    a1_id, a1_ed, a1_ml = b"\x01" * 16, ed25519_generate(), mldsa_generate()
    a2_id, a2_ed, a2_ml = b"\x02" * 16, ed25519_generate(), mldsa_generate()
    pks = {a1_id: (ed25519_pub(a1_ed), mldsa_pub(a1_ml)), a2_id: (ed25519_pub(a2_ed), mldsa_pub(a2_ml))}
    state = AccountAuthState(account_id=b"\xAA" * 16, policy_epoch=0, authorized_devices=[],
        recovery_policy=RecoveryPolicy("existing_device_cosign", k=2, n=3,
                                       approver_roster_ref=commit_approver_roster(pks)))

    req = create_recovery_request(new_dev.dc(), state.account_id, state.policy_epoch, "existing_device_cosign")

    # Tashqi audit (KRITIK #4): hujumchi O'Z kalitlarini "approver ro'yxati"
    # sifatida taqdim etishga urinadi — siyosatdagi approver_roster_ref
    # bilan mos kelmagani uchun rad etilishi kerak.
    attacker_id, attacker_ed, attacker_ml = b"\xFF" * 16, ed25519_generate(), mldsa_generate()
    attacker_pks = {attacker_id: (ed25519_pub(attacker_ed), mldsa_pub(attacker_ml))}
    attacker_appr = create_quorum_approval(attacker_id, attacker_ed, attacker_ml, req)
    try:
        apply_recovery(state, req, [attacker_appr], attacker_pks)
        raise AssertionError("hujumchining o'z roster'i qabul qilindi")
    except AccountAuthError:
        pass

    a1 = create_quorum_approval(a1_id, a1_ed, a1_ml, req)
    try:
        apply_recovery(state, req, [a1], pks)
        raise AssertionError("1/2 kvorum bilan o'tdi")
    except AccountAuthError:
        pass
    a2 = create_quorum_approval(a2_id, a2_ed, a2_ml, req)
    new_state = apply_recovery(state, req, [a1, a2], pks)
    assert new_state.policy_epoch == 1 and new_state.is_authorized(new_dev.device_id)
    try:
        apply_recovery(new_state, req, [a1, a2], pks)   # eski so'rov, yangi holat
        raise AssertionError("eski so'rov yangilangan holatda qabul qilindi")
    except AccountAuthError:
        pass
    return "kvorum, atomik yangilash, rollback himoyasi to'g'ri"


@test("ROSTOR", "FraudReport: ballash ikki shartni birga talab qiladi (§15, R11)")
def _t_rostor_fraud_report(cfg):
    from .config import hardened_config
    from .protocol.identity import DeviceKeys
    from .rostor.fraud_report import create_fraud_report, verify_fraud_report, score_reports, is_flagged, RateLimiter

    hcfg = hardened_config()
    reports = []
    for i in range(6):
        dev = DeviceKeys.generate(f"Reporter{i}", hcfg)
        r = create_fraud_report(dev, "wallet", b"soxta-hamyon", "T6",
                                interaction_ref=b"\x01" * 16 if i < 5 else None)
        assert verify_fraud_report(r, dev.dc())
        reports.append(r)
    score, distinct = score_reports(reports)
    assert score == 5 * 3 + 1 and distinct == 6
    assert is_flagged(reports)

    single_dev = DeviceKeys.generate("Yolg'iz", hcfg)
    single = [create_fraud_report(single_dev, "wallet", b"x", "T6", interaction_ref=b"\x01" * 16)] * 20
    assert not is_flagged(single), "bitta reporter yolg'iz FLAGGED holatiga olib keldi (MIN_K buzildi)"

    limiter = RateLimiter(limit_per_day=3)
    dik = b"\x99" * 16
    for _ in range(3):
        assert limiter.allow(dik)
    assert not limiter.allow(dik)
    return f"score={score}, distinct={distinct}, MIN_K to'sig'i va rate-limit to'g'ri"


@test("ROSTOR", "ApkManifestAttestation: Android SHA-256 ko'prigi (§16, R12)")
def _t_rostor_apk(cfg):
    from .config import hardened_config
    from .protocol.identity import DeviceKeys
    from .rostor.apk import create_apk_attestation, verify_apk_attestation, android_sha256

    hcfg = hardened_config()
    publisher = DeviceKeys.generate("Publisher", hcfg)
    apk_bytes = b"APK MAZMUNI"
    apk_h = android_sha256(apk_bytes)
    cert_h = android_sha256(b"cert")
    att = create_apk_attestation(publisher, package_name="uz.gov.mygov", version_code=1,
                                 channel="official", apk_sha256=apk_h, android_signing_cert_sha256=cert_h)
    assert verify_apk_attestation(att, publisher.dc(), android_sha256(apk_bytes), cert_h)
    assert not verify_apk_attestation(att, publisher.dc(), android_sha256(b"BOSHQA FAYL"), cert_h)
    assert not verify_apk_attestation(att, publisher.dc(), android_sha256(apk_bytes), android_sha256(b"boshqa cert"))
    import hashlib
    assert apk_h == hashlib.sha256(apk_bytes).digest(), "apk_sha256 Android SHA-256 bilan mos emas"
    return "Android SHA-256 (SHA3 emas) bilan attestatsiya to'g'ri ishladi"


@test("ROSTOR", "CALL_CONTEXT: fail-closed qo'ng'iroq autentifikatsiyasi (§11.3, R2)")
def _t_rostor_call_context(cfg):
    """Tashqi audit topilmasi (KRITIK #6): spec R2 ni "tuzatilgan" deb
    belgilagan, lekin CALL_CONTEXT kodda umuman yo'q edi."""
    from .config import hardened_config
    from .protocol.identity import DeviceKeys
    from .rostor.identity import InstitutionKeys
    from .rostor.call_context import create_call_context, is_call_legitimate

    hcfg = hardened_config()
    bank = InstitutionKeys.generate("bank", "Bank Z")
    idc = DeviceKeys.generate("Bank Z backend", hcfg)
    idc_by_inst = {bank.institution_id: idc.dc()}

    cc = create_call_context(idc, bank.institution_id, "+998712001122", "Test")
    assert is_call_legitimate("+998712001122", [cc], idc_by_inst), \
        "mos, haqiqiy CALL_CONTEXT rad etildi"
    assert not is_call_legitimate("+998901234567", [cc], idc_by_inst), \
        "mos kelmaydigan raqam uchun ham True qaytdi (fail-open bug)"
    assert not is_call_legitimate("+998712001122", [], idc_by_inst), \
        "hech qanday CALL_CONTEXT bo'lmasa ham True qaytdi"
    return "mos raqam -> True, mos kelmagan/mavjud bo'lmagan -> fail-closed False"


@test("ROSTOR", "Rasmiy KAT vektorlari fayli (kat/rostor-1-kat.json)")
def _t_rostor_kat_file(cfg):
    from . import rostor_kat

    if not rostor_kat.KAT_PATH.exists():
        raise AssertionError("KAT fayli topilmadi — `python -m scutum.rostor_kat` ni ishga tushiring")
    vectors = rostor_kat.load()
    errs = rostor_kat.verify(vectors)
    assert not errs, "; ".join(errs[:3])
    return f"KAT v{vectors['kat_version']}, {len(vectors) - 2} vektor guruhi qayta hisoblandi"


@test("ROSTOR", "Domen ajratgichlari kodda va KAT'da mos")
def _t_rostor_domain_seps(cfg):
    import re
    from . import rostor_kat

    declared = set(rostor_kat.load()["domain_separators"])
    root = rostor_kat.KAT_PATH.parent.parent / "scutum" / "rostor"
    found: set[str] = set()
    for path in root.rglob("*.py"):
        for m in re.finditer(r'b"(ROSTOR-1/[A-Za-z/-]*)"', path.read_text("utf-8")):
            found.add(m.group(1))
    missing = found - declared
    assert not missing, f"KAT'da e'lon qilinmagan domen ajratgichlari: {sorted(missing)}"
    return f"{len(found)} ajratgich kodda topildi, hammasi e'lon qilingan"


@test("ROSTOR", "T1-T6: barcha real hujum ssenariylari PROTECTED=SAFE")
def _t_rostor_fraud_scenarios(cfg):
    from .sim.fraud_attacks import ATTACKS, run_attack, Outcome

    lines = []
    broken = []
    for key in ATTACKS:
        r = run_attack(key)
        lines.append(f"{r.threat}={r.protected}")
        if r.unprotected != Outcome.BROKEN:
            broken.append(f"{key}: UNPROTECTED kutilganidek BROKEN emas ({r.unprotected})")
        if r.protected not in (Outcome.SAFE,):
            broken.append(f"{key}: PROTECTED SAFE emas ({r.protected})")
    assert not broken, "; ".join(broken)
    return ", ".join(lines)


# ===========================================================================
# Ishga tushirish
# ===========================================================================
def run_all(cfg: ProtocolConfig, on_result=None) -> list[TestResult]:
    out: list[TestResult] = []
    for group, name, fn in TESTS:
        t0 = time.perf_counter()
        try:
            detail = fn(cfg) or ""
            r = TestResult(group, name, True, detail)
        except Exception as exc:  # noqa: BLE001
            r = TestResult(group, name, False, f"{type(exc).__name__}: {exc}")
        r.ms = (time.perf_counter() - t0) * 1000
        out.append(r)
        if on_result:
            on_result(r)
    return out


def main() -> int:
    for label, cfg in (("SPEC", spec_config()), ("HARDENED", hardened_config())):
        print(f"\n{'='*66}\n{label} rejimi\n{'='*66}")
        res = run_all(cfg)
        for r in res:
            mark = "PASS" if r.ok else "FAIL"
            print(f"[{mark}] {r.group:<9} {r.name:<48} {r.ms:6.0f}ms  {r.detail}")
        bad = [r for r in res if not r.ok]
        print(f"\n{len(res) - len(bad)}/{len(res)} o'tdi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
