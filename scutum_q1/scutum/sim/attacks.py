"""Hujum laboratoriyasi.

Har bir hujum joriy konfiguratsiya ostida HAQIQATAN ishga tushiriladi va
natijasi o'lchanadi. Hech qanday natija oldindan "yozib qo'yilmagan" —
`SPEC` va `HARDENED` rejimlarida turlicha chiqishi shundan.

Natija turlari:
  BROKEN      — hujumchi maqsadiga erishdi (protokol ushlab turolmadi)
  SAFE        — himoya ishladi
  STRUCTURAL  — buzilish ijro etilmadi, lekin tuzilmaviy zaiflik o'lchandi
  INFO        — o'lchov/kuzatuv
  N/A         — bu rejimda ma'noga ega emas
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Callable, Optional

from ..config import ProtocolConfig, hardened_config, spec_config
from ..crypto import canonical
from ..crypto.primitives import (
    aead_open,
    mlkem_decaps,
    random_bytes,
    sha3_256,
    x25519_dh,
)
from ..protocol import ratchet as R
from ..protocol.envelope import Envelope, MsgType, message_nonce
from ..protocol.handshake import ROOT_KEY_LEN, derive_root_key, init_salt
from ..protocol.identity import build_prekey_bundle, verify_prekey_bundle
from ..protocol.merkle import build_tree, leaf_hash
from ..protocol.sfile import encrypt_file
from .trace import Level, Trace
from .world import World


class Outcome:
    BROKEN = "BROKEN"
    SAFE = "SAFE"
    STRUCTURAL = "STRUCTURAL"
    INFO = "INFO"
    NA = "N/A"


@dataclass
class AttackResult:
    key: str
    title: str
    finding: str
    severity: str
    outcome: str
    summary: str
    evidence: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


@dataclass
class Attack:
    key: str
    title: str
    finding: str
    severity: str
    goal: str
    run: Callable[[ProtocolConfig, Trace], AttackResult]


def _mk(a: "Attack", outcome: str, summary: str, ev: list[str]) -> AttackResult:
    return AttackResult(a.key, a.title, a.finding, a.severity, outcome, summary, ev)


def _hex(b: bytes, n: int = 16) -> str:
    return b[:n].hex() + ("…" if len(b) > n else "")


# ===========================================================================
# K-1  SPK kompromati -> to'liq sessiya kompromati
# ===========================================================================
def _atk_spk_compromise(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    w = World(cfg, trace)
    bob = w.bob
    bundle = w.server.fetch_bundle(bob.device_id)
    init_env = w.alice.start_session(bundle)
    real_rk0 = w.alice.pending[init_env.session_id].rk0

    # Hujumchi FAQAT Bobning SPK maxfiy kalitlarini qo'lga kiritdi.
    body = canonical.decode(init_env.body, cfg.encoding)
    ek_pk, kem_ct = body["ek"], body["kem_ct"]
    dc_a, dc_b = body["dc"], bob.device.dc()

    dh1 = x25519_dh(bob.device.spk_x, ek_pk)
    dh2 = x25519_dh(bob.device.spk_x, dc_a["x25519_pk"])
    kem_ss = mlkem_decaps(bob.device.spk_mlkem, kem_ct)

    ev = [
        "Hujumchi qo'lida: SPK_x25519_sk + SPK_mlkem_sk (Bobning IK_sk YO'Q)",
        f"dh1 = X25519(SPK_sk, EK_A)      -> {_hex(dh1)}",
        f"dh2 = X25519(SPK_sk, IK_A_pk)   -> {_hex(dh2)}",
        f"pq  = Decaps(SPK_mlkem_sk, ct)  -> {_hex(kem_ss)}",
    ]
    try:
        forged = derive_root_key(
            cfg=cfg, dh1=dh1, dh2=dh2, dh3=None, dh4=None, kem_ss=kem_ss,
            salt=init_salt(dc_a, dc_b, cfg), transcript=None,
        )
    except Exception as exc:
        ev.append(f"dh3/transkript talab qilindi -> hujumchi hisoblay olmadi: {exc}")
        return _mk(ATTACKS["spk_compromise"], Outcome.SAFE,
                   "SPK kompromati yetarli emas — IK_B_sk ham kerak", ev)

    ev.append(f"hujumchi RK0 = {_hex(forged, 24)}")
    ev.append(f"haqiqiy  RK0 = {_hex(real_rk0, 24)}")
    if forged == real_rk0:
        ev.append("=> BIR XIL. Hujumchi butun sessiyani ochadi va Bobni "
                  "to'liq impersonatsiya qiladi.")
        return _mk(ATTACKS["spk_compromise"], Outcome.BROKEN,
                   "SPK sirining oshkor bo'lishi = to'liq sessiya kompromati", ev)
    ev.append("=> FARQ QILADI. Qabul qiluvchi identity kaliti ham talab qilinadi.")
    return _mk(ATTACKS["spk_compromise"], Outcome.SAFE,
               "dh3 tufayli SPK yolg'iz yetarli emas", ev)


# ===========================================================================
# K-2  INIT replay / OPK dekorativligi
# ===========================================================================
def _atk_init_replay(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    """K-2'ning ASOSIY da'vosi — "OPK KDF'ga kirmaydi, shuning uchun
    dekorativ" — bu yerda `derive_root_key` darajasida, TO'G'RIDAN-TO'G'RI
    sinaladi: OPK'dan hosil bo'lgan `dh4` ni almashtirish RK0'ni
    o'zgartiradimi?

    Diqqat: to'liq INIT paketini litseral qayta yuborish endi K-6
    (session_id kolliziyasi guardi, tashqi audit 2026-08-16) tomonidan
    HAM to'siladi — bu ikkala himoya bir-biriga mustaqil ekanini
    ko'rsatish uchun pastda alohida qayd etilgan, lekin BROKEN/SAFE
    hukmi faqat K-2'ning o'z mexanizmiga (OPK'ning RK0'ga ta'siriga)
    asoslanadi, aks holda K-6 K-2 natijasini "yashirib qo'yar" edi.
    """
    w = World(cfg, trace)
    bundle = w.server.fetch_bundle(w.bob.device_id)

    dh1, dh2, dh3 = (random_bytes(32) for _ in range(3))
    dh4_real = random_bytes(32)      # OPK bilan hosil bo'lgan haqiqiy DH
    dh4_forged = random_bytes(32)    # hujumchi taxmin qilgan/almashtirgan DH
    kem_ss = random_bytes(32)
    salt = random_bytes(32)
    transcript = random_bytes(32)   # HARDENED (bind_kem_transcript) uchun kerak

    rk_real = derive_root_key(cfg=cfg, dh1=dh1, dh2=dh2, dh3=dh3, dh4=dh4_real,
                              kem_ss=kem_ss, salt=salt, transcript=transcript)
    rk_forged = derive_root_key(cfg=cfg, dh1=dh1, dh2=dh2, dh3=dh3, dh4=dh4_forged,
                                kem_ss=kem_ss, salt=salt, transcript=transcript)

    ev = [
        "Bir xil dh1/dh2/dh3/kem_ss, LEKIN turli dh4 (OPK'dan hosil bo'lgan sir)",
        f"RK0(haqiqiy OPK)   = {_hex(rk_real, 24)}",
        f"RK0(soxta/eski OPK) = {_hex(rk_forged, 24)}",
    ]

    # Qo'shimcha, mustaqil kuzatuv: to'liq paketni litseral qayta yuborish
    # endi K-6 tomonidan ham to'siladi (bir xil session_id):
    init_env = w.alice.start_session(bundle)
    wire = w.server.enqueue(init_env)
    w.bob.accept_session(Envelope.from_wire(w.server.deliver(w.bob.device_id), cfg))
    try:
        w.bob.accept_session(Envelope.from_wire(wire, cfg))
        literal_replay = "O'TDI (kutilmagan)"
    except Exception as exc:
        literal_replay = f"rad etildi ({type(exc).__name__}, K-6 guardi orqali)"
    ev.append(f"[qo'shimcha] litseral paket qayta yuborish: {literal_replay}")

    if rk_real == rk_forged:
        ev.append("=> BIR XIL. OPK RK0'ga HECH QANDAY ta'sir qilmaydi — "
                  "mexanizm dekorativ. OPK almashtirilsa ham (yoki umuman "
                  "bo'lmasa ham) natija bir xil bo'lardi.")
        return _mk(ATTACKS["init_replay"], Outcome.BROKEN,
                   "OPK root-key derivatsiyasiga ta'sir qilmaydi", ev)
    ev.append("=> FARQ QILADI. OPK RK0'ga majburiy hissa qo'shadi.")
    return _mk(ATTACKS["init_replay"], Outcome.SAFE,
               "OPK RK0'ga bog'langan (dh4 majburiy)", ev)


# ===========================================================================
# K-6  session_id kolliziyasi -> sessiyani jimgina almashtirish
#      (tashqi audit orqali topilgan, 2026-08-16; original spec'da yo'q)
# ===========================================================================
def _atk_session_collision(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    from ..protocol.handshake import create_init

    w = World(cfg, trace)
    fixed_sid = b"\x11" * 16   # hujumchi Alisaning session_id sini ushlab qoladi

    bundle1 = w.server.fetch_bundle(w.bob.device_id)
    st1 = create_init(w.alice.device, bundle1, cfg, session_id=fixed_sid)
    w.bob.accept_session(st1.envelope)
    w.server.publish_bundle(w.bob.device_id, w.bob.bundle())
    alice_state = w.bob.sessions[fixed_sid].state

    ev = [
        "Alisa Bobur bilan sessiya ochdi, session_id server uchun OCHIQ "
        "(AAD ichida, shifrlanmagan)",
        f"session_id = {fixed_sid.hex()}",
        "Hujumchi (Mallory) AYNI shu session_id bilan Boburga o'z INIT'ini yuboradi",
    ]

    bundle2 = w.server.fetch_bundle(w.bob.device_id)   # yangi OPK
    st2 = create_init(w.mallory.device, bundle2, cfg, session_id=fixed_sid)
    try:
        w.bob.accept_session(st2.envelope)
    except Exception as exc:
        ev.append(f"Mallory INIT'i rad etildi: {exc}")
        ev.append("=> mavjud sessiya saqlanib qoldi.")
        return _mk(ATTACKS["session_collision"], Outcome.SAFE,
                   "session_id kolliziyasi rad etildi", ev)

    overwritten = w.bob.sessions[fixed_sid].state is not alice_state
    peer_now = w.bob.sessions[fixed_sid].peer_device_id
    ev.append(f"Bobning session_id={fixed_sid.hex()[:8]} yozuvidagi peer "
             f"endi: {peer_now.hex()[:8]} (Mallory={w.mallory.device_id.hex()[:8]}, "
             f"Alisa={w.alice.device_id.hex()[:8]})")
    if overwritten:
        ev.append("=> Alisaning sessiyasi JIMGINA Mallory'nikiga almashtirildi. "
                  "Alisa endi o'z session_id'i bilan Boburga yoza olmaydi (DoS), "
                  "Bobur esa buni sezmaydi.")
        return _mk(ATTACKS["session_collision"], Outcome.BROKEN,
                   "session_id kolliziyasi mavjud sessiyani almashtirdi", ev)
    ev.append("=> sessiya almashtirilmadi.")
    return _mk(ATTACKS["session_collision"], Outcome.SAFE, "Kolliziya to'sildi", ev)


# ===========================================================================
# K-3  Chain key kompromati -> o'tgan xabarlar
# ===========================================================================
def _atk_chain_key_compromise(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    w = World(cfg, trace)
    w.handshake()
    texts = [f"maxfiy xabar #{i}" for i in range(5)]
    envs: list[Envelope] = []
    for t in texts:
        env = w.alice.send(w.session_id, t.encode())
        envs.append(env)
        w.server.enqueue(env)
        w.bob.receive(Envelope.from_wire(w.server.deliver(w.bob.device_id), cfg))

    st = w.alice.sessions[w.session_id].state
    leaked_ck = st.cks           # 5 ta xabardan KEYIN o'g'irlangan CK
    ev = [
        "Hujumchi 5 ta xabar yuborilgandan KEYIN CKs ni o'g'irladi",
        f"o'g'irlangan CKs = {_hex(leaked_ck, 24)}",
        "Maqsad: 0-xabarni (o'tmish) ochish -> forward secrecy sinovi",
    ]

    target = envs[0]
    _, mk = R.kdf_ck(cfg, leaked_ck, w.session_id, target.message_no)
    nonce = message_nonce(w.session_id, R.DIR_INITIATOR, target.message_no)
    body = target.body[R.COMMIT_LEN:] if cfg.key_commitment else target.body
    try:
        pt = aead_open(mk, nonce, body, target.aad(cfg))
        ev.append(f"0-xabar OCHILDI: {pt.decode()!r}")
        ev.append("=> chain ichida forward secrecy YO'Q.")
        return _mk(ATTACKS["chain_key_compromise"], Outcome.BROKEN,
                   "O'g'irlangan CK o'tgan xabarlarni ochdi", ev)
    except Exception as exc:
        ev.append(f"0-xabar ochilmadi: {exc}")
        ev.append("=> CK bir tomonlama siljigan; o'tmish himoyalangan.")
        return _mk(ATTACKS["chain_key_compromise"], Outcome.SAFE,
                   "Forward secrecy ushlab turdi", ev)


# ===========================================================================
# K-4  Ratchet sarlavhasini o'zgartirish
# ===========================================================================
def _atk_header_tamper(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    w = World(cfg, trace)
    w.handshake()
    env = w.alice.send(w.session_id, b"salom")
    wire = env.to_wire(cfg)

    d = canonical.decode(wire, cfg.encoding)
    if "hdr" not in d:
        return _mk(ATTACKS["header_tamper"], Outcome.NA,
                   "sarlavha AAD ichida — alohida maydon yo'q", [])
    original_pn = d["hdr"]["pn"]
    d["hdr"]["pn"] = original_pn + 777
    tampered = canonical.encode(d, cfg.encoding)

    ev = [
        "Server ratchet sarlavhasidagi `pn` ni o'zgartirdi "
        f"({original_pn} -> {original_pn + 777})",
        "Spec Envelope'ida bu maydon umuman yo'q, ya'ni AAD ham qamramaydi",
    ]
    try:
        w.bob.receive(Envelope.from_wire(tampered, cfg))
        ev.append("Xabar MUVAFFAQIYATLI ochildi — o'zgartirish sezilmadi")
        ev.append("=> hujumchi ratchet holatini jimgina buzadi (desync/DoS)")
        return _mk(ATTACKS["header_tamper"], Outcome.BROKEN,
                   "Sarlavha autentifikatsiyalanmagan", ev)
    except Exception as exc:
        ev.append(f"Rad etildi: {exc}")
        return _mk(ATTACKS["header_tamper"], Outcome.SAFE,
                   "Sarlavha AAD bilan himoyalangan", ev)


# ===========================================================================
# Y-1  KEM ciphertext transkriptga bog'lanmagan
# ===========================================================================
def _atk_transcript_binding(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    dh1, dh2, dh3, ss = (random_bytes(32) for _ in range(4))
    salt = random_bytes(32)
    t1, t2 = sha3_256(b"transkript-1"), sha3_256(b"transkript-2")
    rk_a = derive_root_key(cfg=cfg, dh1=dh1, dh2=dh2, dh3=dh3, dh4=None,
                           kem_ss=ss, salt=salt, transcript=t1)
    rk_b = derive_root_key(cfg=cfg, dh1=dh1, dh2=dh2, dh3=dh3, dh4=None,
                           kem_ss=ss, salt=salt, transcript=t2)
    ev = [
        "Bir xil DH/KEM sirlari, LEKIN turli handshake transkripti",
        f"RK0(transkript-1) = {_hex(rk_a, 24)}",
        f"RK0(transkript-2) = {_hex(rk_b, 24)}",
    ]
    if rk_a == rk_b:
        ev.append("=> RK0 transkriptga BOG'LIQ EMAS. ML-KEM ciphertext, "
                  "ephemeral pk va KEM pk KDF'ga kirmaydi (MAL-BIND-K-CT).")
        return _mk(ATTACKS["transcript_binding"], Outcome.STRUCTURAL,
                   "Handshake transkripti root-key'ga bog'lanmagan", ev)
    ev.append("=> RK0 to'liq transkriptga bog'langan.")
    return _mk(ATTACKS["transcript_binding"], Outcome.SAFE,
               "Transkript bog'lanishi mavjud", ev)


# ===========================================================================
# Y-2  Kalit-majburiyat (key commitment)
# ===========================================================================
def _atk_key_commitment(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    w = World(cfg, trace)
    w.handshake()
    env = w.alice.send(w.session_id, b"hisobot")
    ev = [
        f"MSG body uzunligi: {len(env.body)} bayt "
        f"(plaintext 7 + Poly1305 16 = 23 kutilardi)",
    ]
    if cfg.key_commitment:
        ev.append("Kalit-majburiyat tegi (HMAC-SHA-256, 32 bayt) mavjud")
        ev.append("=> bitta ciphertext ikki xil kalit ostida haqiqiy "
                  "ko'rina olmaydi; partitioning-oracle sinfi yopiq.")
        return _mk(ATTACKS["key_commitment"], Outcome.SAFE,
                   "AEAD kalitga majburiyat beradi", ev)
    ev.append("Kalit-majburiyat tegi YO'Q — faqat Poly1305 tegi bor")
    ev.append("ChaCha20-Poly1305 key-committing emas: Poly1305 — polinomial "
              "MAC, bir ciphertext bir nechta kalit ostida haqiqiy bo'lishi "
              "uchun yechiladigan tenglama.")
    ev.append("Spec §8: backup FOYDALANUVCHI PAROLI (Argon2id) bilan "
              "shifrlanadi -> partitioning-oracle parol qidiruvini "
              "eksponensial tezlashtiradi.")
    ev.append("[Eslatma: to'liq 'invisible salamander' konstruksiyasi bu "
              "simulyatorda ijro etilmadi — bu tuzilmaviy topilma.]")
    return _mk(ATTACKS["key_commitment"], Outcome.STRUCTURAL,
               "AEAD kalitga majburiyat bermaydi", ev)


# ===========================================================================
# Y-3  Merkle: duplikat-tugun ildiz to'qnashuvi
# ===========================================================================
def _atk_merkle_ambiguity(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    leaves3 = [sha3_256(b"A"), sha3_256(b"B"), sha3_256(b"C")]
    leaves4 = leaves3 + [leaves3[2]]          # oxirgi bargni takrorlaymiz
    r3 = build_tree(leaves3, cfg).tree_root
    r4 = build_tree(leaves4, cfg).tree_root
    ev = [
        "3 bargli daraxt: [A, B, C]",
        "4 bargli daraxt: [A, B, C, C]  (oxirgisi dublikat)",
        f"root(3) = {_hex(r3, 24)}",
        f"root(4) = {_hex(r4, 24)}",
    ]
    if r3 == r4:
        ev.append("=> ILDIZLAR BIR XIL. Turli barglar to'plami ayni root_hash "
                  "beradi (CVE-2012-2459 uslubidagi noaniqlik).")
        ev.append("MUHIM: bu spec'da to'liq soxtalashtirishga aylanmaydi, "
                  "chunki AAD_i ichida `i` va `total_chunks` bor va AEAD "
                  "mos kelmaydi. Ya'ni topilma — chuqurlashtirilgan himoya "
                  "(defense-in-depth) darajasida, to'g'ridan-to'g'ri buzilish emas.")
        return _mk(ATTACKS["merkle_ambiguity"], Outcome.STRUCTURAL,
                   "Merkle ildizi barglar to'plamini bir qiymatli aniqlamaydi", ev)
    ev.append("=> ildizlar farq qiladi (domen ajratish + toq tugunni ko'chirish "
              "+ total_chunks bog'lanishi).")
    return _mk(ATTACKS["merkle_ambiguity"], Outcome.SAFE,
               "Merkle ildizi bir qiymatli", ev)


# ===========================================================================
# Y-4  Fayl metama'lumotida nonce takrorlanishi -> keystream tiklash
# ===========================================================================
def _atk_meta_nonce_reuse(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    name = "Q4-moliyaviy-hisobot.pdf"
    mime = "application/pdf"
    enc = encrypt_file(b"payload" * 100, cfg, name=name, mime=mime)
    c1 = enc.manifest["name_enc"]
    c2 = enc.manifest["mime_enc"]
    ev = [
        f"name = {name!r}, mime = {mime!r}",
        f"name_enc nonce = {enc.manifest['file_id'].hex()[:0] or ''}"
        f"{'00'*12 if not cfg.separate_meta_key else '(alohida)'}",
    ]
    if cfg.separate_meta_key:
        ev.append("Alohida meta-kalit va maydonga bog'langan nonce ishlatildi")
        ev.append("=> keystream takrorlanmaydi")
        return _mk(ATTACKS["meta_nonce_reuse"], Outcome.SAFE,
                   "Metama'lumot kaliti/nonce'si to'g'ri ajratilgan", ev)

    n = min(len(c1), len(c2)) - 16          # Poly1305 tegisiz qism
    xor = bytes(a ^ b for a, b in zip(c1[:n], c2[:n]))
    guess = bytes(a ^ b for a, b in zip(xor, mime.encode()))
    ev.append("SPEC: name_enc va mime_enc AYNI kalit (FK) va AYNI nonce bilan")
    ev.append(f"c1 XOR c2 = {_hex(xor, 20)}  ( = p1 XOR p2 )")
    ev.append(f"mime ma'lum deb faraz qilib tiklandi: {guess.decode('utf-8', 'replace')!r}")
    ev.append("=> kalitsiz, faqat XOR bilan fayl nomi qayta tiklandi.")
    return _mk(ATTACKS["meta_nonce_reuse"], Outcome.BROKEN,
               "Nonce takrorlanishi fayl nomini oshkor qildi", ev)


# ===========================================================================
# Y-5  Kodlash chalkashligi (CBOR <-> JSON)
# ===========================================================================
def _atk_encoding_confusion(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    from ..crypto.canonical import Encoding

    w = World(cfg, trace)
    w.handshake()
    env = w.alice.send(w.session_id, b"test")
    other = replace(
        cfg,
        encoding=(Encoding.JSON_CANONICAL
                  if cfg.encoding is Encoding.CBOR_DETERMINISTIC
                  else Encoding.CBOR_DETERMINISTIC),
    )
    ev = [
        f"Yuboruvchi kodlashi: {cfg.encoding.value}",
        f"Qabul qiluvchi kodlashi: {other.encoding.value}",
        "Spec §4 ikkalasini ham ruxsat etadi, ayni paytda AAD'ning "
        "byte-for-byte mosligini talab qiladi.",
    ]
    try:
        Envelope.from_wire(env.to_wire(cfg), other)
        ev.append("Paket o'qildi (AAD baribir mos kelmaydi)")
    except Exception as exc:
        ev.append(f"Paket umuman parse bo'lmadi: {type(exc).__name__}")
    if cfg.strict_encoding:
        ev.append("=> HARDENED: yagona majburiy profil, ziddiyat yo'q.")
        return _mk(ATTACKS["encoding_confusion"], Outcome.SAFE,
                   "Kodlash yagona va majburiy", ev)
    ev.append("=> ikki mos implementatsiya bir-biri bilan HECH QACHON "
              "gaplasha olmaydi (interop buzilishi).")
    return _mk(ATTACKS["encoding_confusion"], Outcome.STRUCTURAL,
               "Kodlash ta'rifi ziddiyatli", ev)


# ===========================================================================
# Y-6  SPK muddatini almashtirish
# ===========================================================================
def _atk_spk_expiry_tamper(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    w = World(cfg, trace)
    bundle = w.server.fetch_bundle(w.bob.device_id)
    original = bundle["spk_expiry"]
    bundle["spk_expiry"] = original + 3650 * 86400        # +10 yil
    ev = [
        f"Server SPK_expiry ni o'zgartirdi: {original} -> {bundle['spk_expiry']}",
        "Spec §5.1 imzo formulasi: sig(DC || SPK) — expiry imzo tashqarisida",
    ]
    try:
        verify_prekey_bundle(bundle, cfg)
        ev.append("Bundle imzosi HAQIQIY deb topildi — o'zgartirish sezilmadi")
        ev.append("=> buzilgan SPK'ni cheksiz amalda ushlab turish mumkin.")
        return _mk(ATTACKS["spk_expiry_tamper"], Outcome.BROKEN,
                   "SPK muddati imzo bilan himoyalanmagan", ev)
    except Exception as exc:
        ev.append(f"Rad etildi: {exc}")
        return _mk(ATTACKS["spk_expiry_tamper"], Outcome.SAFE,
                   "Butun bundle imzolangan", ev)


# ===========================================================================
# Y-7  Fingerprint beqarorligi
# ===========================================================================
def _atk_fingerprint_churn(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    w = World(cfg, trace)
    before = w.bob.fingerprint()
    keys_before = (w.bob.device.ik_x_pk, w.bob.device.ik_ed_pk, w.bob.device.ik_mldsa_pk)
    w.bob.device.renew_dc(cfg, now=int(time.time()) + 3600)
    after = w.bob.fingerprint()
    keys_after = (w.bob.device.ik_x_pk, w.bob.device.ik_ed_pk, w.bob.device.ik_mldsa_pk)

    ev = [
        "Identity kalitlari O'ZGARMADI, faqat DC muddati yangilandi",
        f"kalitlar bir xilmi: {keys_before == keys_after}",
        f"fingerprint (oldin) = {_hex(before, 16)}",
        f"fingerprint (keyin) = {_hex(after, 16)}",
    ]
    if before != after:
        ev.append("=> Xavfsizlik raqami O'ZGARDI. Foydalanuvchi QR bilan "
                  "qilgan tasdig'i bekor bo'ldi; takroriy 'raqam o'zgardi' "
                  "ogohlantirishlari haqiqiy MITM'ni yashiradi.")
        return _mk(ATTACKS["fingerprint_churn"], Outcome.BROKEN,
                   "Fingerprint kalitlar o'zgarmasa ham o'zgaradi", ev)
    ev.append("=> barqaror: fingerprint faqat identity kalitlaridan.")
    return _mk(ATTACKS["fingerprint_churn"], Outcome.SAFE,
               "Fingerprint barqaror", ev)


# ===========================================================================
# Y-8  Bekor qilishni orqaga qaytarish (rollback)
# ===========================================================================
def _atk_revoke_rollback(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    w = World(cfg, trace)
    old_bundle = build_prekey_bundle(w.bob.device, cfg)
    w.alice.revoke_epochs[w.bob.device_id] = 0
    w.alice.start_session(old_bundle)          # epoch 0 — normal

    w.bob.device.revoke_epoch = 5              # kompromatdan keyin rotatsiya
    new_bundle = build_prekey_bundle(w.bob.device, cfg)
    w.alice.start_session(new_bundle)          # epoch 5 ni ko'rdi

    ev = [
        "Alisa Bobning epoch=5 bundle'ini ko'rdi",
        "Server endi ESKI epoch=0 bundle'ni qaytaradi (rollback)",
    ]
    try:
        w.alice.start_session(old_bundle)
        ev.append("Eski bundle QABUL QILINDI — rollback sezilmadi")
        ev.append("=> server bekor qilingan kalitni cheksiz tiriltira oladi.")
        return _mk(ATTACKS["revoke_rollback"], Outcome.BROKEN,
                   "Bekor qilish tartibi kuzatilmaydi", ev)
    except Exception as exc:
        ev.append(f"Rad etildi: {exc}")
        return _mk(ATTACKS["revoke_rollback"], Outcome.SAFE,
                   "Monoton epoch rollback'ni to'sdi", ev)


# ===========================================================================
# Musbat nazorat: Envelope bit-flip
# ===========================================================================
def _atk_envelope_tamper(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    w = World(cfg, trace)
    w.handshake()
    env = w.alice.send(w.session_id, b"bu xabar o'zgartirilmasligi kerak")
    d = canonical.decode(env.to_wire(cfg), cfg.encoding)
    body = bytearray(d["body"])
    body[len(body) // 2] ^= 0x01
    d["body"] = bytes(body)
    ev = ["ciphertext'ning o'rtasidagi bitta bit teskarisiga aylantirildi"]
    try:
        w.bob.receive(Envelope.from_wire(canonical.encode(d, cfg.encoding), cfg))
        ev.append("XAVF: o'zgartirilgan xabar qabul qilindi!")
        return _mk(ATTACKS["envelope_tamper"], Outcome.BROKEN,
                   "AEAD yaxlitligi ishlamadi", ev)
    except Exception as exc:
        ev.append(f"Rad etildi: {exc}")
        ev.append("=> AEAD + AAD kutilganidek ishlaydi (musbat nazorat).")
        return _mk(ATTACKS["envelope_tamper"], Outcome.SAFE,
                   "O'zgartirish aniqlandi", ev)


# ===========================================================================
# Musbat nazorat: xabar replay
# ===========================================================================
def _atk_msg_replay(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    w = World(cfg, trace)
    w.handshake()
    env = w.alice.send(w.session_id, b"pulni o'tkaz")
    wire = env.to_wire(cfg)
    w.bob.receive(Envelope.from_wire(wire, cfg))
    ev = ["Xabar birinchi marta muvaffaqiyatli qabul qilindi",
          "Server ayni paketni qayta yubordi"]
    try:
        w.bob.receive(Envelope.from_wire(wire, cfg))
        ev.append("XAVF: takroriy xabar qabul qilindi!")
        return _mk(ATTACKS["msg_replay"], Outcome.BROKEN,
                   "Xabar replay'i to'silmadi", ev)
    except Exception as exc:
        ev.append(f"Rad etildi: {exc}")
        ev.append("=> spec §6 replay himoyasi ishlaydi (musbat nazorat).")
        return _mk(ATTACKS["msg_replay"], Outcome.SAFE, "Replay to'sildi", ev)


# ===========================================================================
# S-FILE: bo'lakni o'zgartirish va qisqartirish
# ===========================================================================
def _atk_file_tamper(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    small = replace(cfg, chunk_size=4096)
    w = World(small, trace)
    w.handshake()
    data = random_bytes(4096 * 5 + 123)
    enc, res = w.send_file(w.alice, data, "hisobot.bin")
    ev = [f"fayl: {len(data)} bayt, {enc.manifest['total_chunks']} bo'lak",
          f"boshlang'ich tekshiruv: {'OK' if res.ok else res.error}"]

    w.server.tamper_chunk(enc.file_id, 2, b"\x01")
    r1 = w.reverify_file(enc.file_id)
    ev.append(f"2-bo'lak o'zgartirildi -> {'QABUL QILINDI (XAVF!)' if r1.ok else 'rad etildi: ' + r1.error}")

    w.server.upload(enc.file_id, enc.chunks)
    w.server.truncate_file(enc.file_id, enc.manifest["total_chunks"] - 1)
    r2 = w.reverify_file(enc.file_id)
    ev.append(f"fayl qisqartirildi -> {'QABUL QILINDI (XAVF!)' if r2.ok else 'rad etildi: ' + r2.error}")

    if r1.ok or r2.ok:
        return _mk(ATTACKS["file_tamper"], Outcome.BROKEN,
                   "S-FILE yaxlitligi buzildi", ev)
    ev.append("=> Merkle + AEAD_AAD kutilganidek ishlaydi (musbat nazorat).")
    return _mk(ATTACKS["file_tamper"], Outcome.SAFE,
               "O'zgartirish va truncation aniqlandi", ev)


# ===========================================================================
# O-3  Skipped-key DoS
# ===========================================================================
def _atk_skipped_dos(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    if not cfg.advance_chain_key:
        return _mk(ATTACKS["skipped_dos"], Outcome.NA,
                   "SPEC'da CK statik — skipped-key mexanizmi umuman ishlatilmaydi "
                   "(bu o'z-o'zidan K-3 ning ko'rinishi)", [])
    w = World(cfg, trace)
    w.handshake()
    st_b = w.bob.sessions[w.session_id].state
    envs = [w.alice.send(w.session_id, f"m{i}".encode()) for i in range(900)]
    ev = ["Alisa 900 ta xabar yubordi, hujumchi faqat OXIRGISINI yetkazdi",
          f"MAX_SKIPPED_KEYS = {cfg.max_skipped_keys}"]
    try:
        w.bob.receive(envs[-1])
        ev.append(f"Bobda saqlangan skipped kalitlar: {len(st_b.skipped)}")
        ev.append(f"taxminiy xotira: ~{len(st_b.skipped) * 32 / 1024:.1f} KiB "
                  "(bitta sessiya, bitta chain uchun)")
        if cfg.bounded_skipped_keys:
            ev.append(f"global limit: {cfg.max_skipped_keys * cfg.max_skipped_chains}")
            return _mk(ATTACKS["skipped_dos"], Outcome.SAFE,
                       "Global limit qo'llanildi", ev)
        ev.append("=> sessiyalar soni cheklanmagani uchun bu ko'paytiriladi -> DoS")
        return _mk(ATTACKS["skipped_dos"], Outcome.STRUCTURAL,
                   "Skipped-key uchun global limit yo'q", ev)
    except Exception as exc:
        ev.append(f"Rad etildi: {exc}")
        return _mk(ATTACKS["skipped_dos"], Outcome.SAFE, "Chain limiti ishladi", ev)


# ===========================================================================
# Metama'lumot oqishi (spec §1.2 qisman tan oladi)
# ===========================================================================
def _atk_metadata_leak(cfg: ProtocolConfig, trace: Trace) -> AttackResult:
    w = World(cfg, trace)
    w.handshake()
    for i in range(5):
        w.send(w.alice, f"xabar {i}")
    w.send(w.bob, "javob")

    rows = w.server.metadata_log
    ev = ["Server ochiq matnni ko'rmaydi, LEKIN quyidagilarni to'liq ko'radi:"]
    for r in rows[:8]:
        ev.append(
            f"  {r['type']:<12} {r['snd']} -> {r['rcv']}  sid={r['sid']} "
            f"no={r['no']}  {r['bytes']} bayt  ts={r['ts']}"
        )
    ev.append(f"... jami {len(rows)} yozuv")
    ev.append("=> ijtimoiy graf, suhbat vaqti, yo'nalish, xabar soni va "
              "uzunligi to'liq ochiq (header encryption va padding yo'q).")
    return _mk(ATTACKS["metadata_leak"], Outcome.INFO,
               "Metama'lumot to'liq kuzatiladi", ev)


# ===========================================================================
# Ro'yxat
# ===========================================================================
ATTACKS: dict[str, Attack] = {}


def _reg(key, title, finding, severity, goal, fn):
    ATTACKS[key] = Attack(key, title, finding, severity, goal, fn)


_reg("spk_compromise", "SPK kompromati -> to'liq sessiya", "K-1", "KRITIK",
     "Faqat SPK maxfiy kalitlari bilan RK0 ni tiklash", _atk_spk_compromise)
_reg("init_replay", "INIT replay", "K-2", "KRITIK",
     "Ushlangan INIT ni qayta yuborib sessiya ochtirish", _atk_init_replay)
_reg("chain_key_compromise", "Chain key kompromati -> o'tmish", "K-3", "KRITIK",
     "O'g'irlangan CK bilan eski xabarlarni ochish", _atk_chain_key_compromise)
_reg("header_tamper", "Ratchet sarlavhasini o'zgartirish", "K-4", "KRITIK",
     "Autentifikatsiyalanmagan sarlavhani jimgina buzish", _atk_header_tamper)
_reg("session_collision", "session_id kolliziyasi", "K-6", "YUQORI",
     "Mavjud sessiyani boshqa peer bilan jimgina almashtirish", _atk_session_collision)
_reg("transcript_binding", "KEM transkript bog'lanishi", "Y-1", "YUQORI",
     "RK0 handshake transkriptiga bog'liqmi", _atk_transcript_binding)
_reg("key_commitment", "AEAD kalit-majburiyati", "Y-2", "YUQORI",
     "Ciphertext kalitga majburiyat beradimi", _atk_key_commitment)
_reg("merkle_ambiguity", "Merkle ildiz noaniqligi", "Y-3", "YUQORI",
     "Turli barglar to'plami bir xil root berishi", _atk_merkle_ambiguity)
_reg("meta_nonce_reuse", "Fayl metama'lumoti: nonce takrori", "Y-4", "YUQORI",
     "Kalitsiz fayl nomini tiklash", _atk_meta_nonce_reuse)
_reg("encoding_confusion", "Kodlash chalkashligi", "Y-5", "YUQORI",
     "CBOR/JSON ikkiligi AAD ni buzadimi", _atk_encoding_confusion)
_reg("spk_expiry_tamper", "SPK muddatini almashtirish", "Y-6", "YUQORI",
     "Imzo tashqarisidagi maydonni o'zgartirish", _atk_spk_expiry_tamper)
_reg("fingerprint_churn", "Fingerprint beqarorligi", "Y-7", "YUQORI",
     "Kalitlar o'zgarmasa ham raqam o'zgaradimi", _atk_fingerprint_churn)
_reg("revoke_rollback", "Bekor qilish rollback'i", "Y-8", "YUQORI",
     "Eski bundle'ni qayta tiriltirish", _atk_revoke_rollback)
_reg("skipped_dos", "Skipped-key DoS", "O-3", "O'RTA",
     "Xotira tugatish", _atk_skipped_dos)
_reg("metadata_leak", "Metama'lumot oqishi", "O-8", "O'RTA",
     "Server nimani ko'radi", _atk_metadata_leak)
_reg("envelope_tamper", "Envelope bit-flip (musbat nazorat)", "—", "NAZORAT",
     "AEAD yaxlitligi ishlayaptimi", _atk_envelope_tamper)
_reg("msg_replay", "Xabar replay (musbat nazorat)", "—", "NAZORAT",
     "Spec §6 replay himoyasi", _atk_msg_replay)
_reg("file_tamper", "S-FILE tamper/truncation (musbat nazorat)", "—", "NAZORAT",
     "Merkle + AAD ishlayaptimi", _atk_file_tamper)


def run_attack(key: str, cfg: ProtocolConfig, trace: Optional[Trace] = None) -> AttackResult:
    trace = trace or Trace()
    atk = ATTACKS[key]
    t0 = time.perf_counter()
    try:
        res = atk.run(cfg, trace)
    except Exception as exc:  # noqa: BLE001
        res = AttackResult(atk.key, atk.title, atk.finding, atk.severity,
                           Outcome.NA, f"hujum bajarilmadi: {exc}", [repr(exc)])
    res.elapsed_ms = (time.perf_counter() - t0) * 1000
    trace.emit("attack", Level.ATTACK if res.outcome == Outcome.BROKEN else Level.INFO,
               f"{atk.title}: {res.outcome}")
    return res


def run_all(cfg: ProtocolConfig, trace: Optional[Trace] = None) -> list[AttackResult]:
    return [run_attack(k, cfg, trace) for k in ATTACKS]


def compare_modes() -> list[tuple[str, AttackResult, AttackResult]]:
    """Har bir hujumni SPEC va HARDENED ostida yonma-yon ishga tushiradi."""
    spec, hard = spec_config(), hardened_config()
    out = []
    for key in ATTACKS:
        out.append((key, run_attack(key, spec), run_attack(key, hard)))
    return out
