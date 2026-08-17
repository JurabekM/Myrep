"""Spec §6: Double Ratchet, xabar shifrlash va post-kvant ratchet.

Bu yerda spec'ning eng og'ir kamchiligi (K-3) modellashtirilgan:

  SPEC:      MK = HKDF-SHA-512(CK, salt="SCUTUM-Q1/MSG",
                               info=session_id || message_no, L=32)
             `CK` o'zgarmaydi -> CK oshkor bo'lsa chain'dagi BARCHA xabarlar
             (o'tgani ham, kelajagi ham) ochiladi.

  HARDENED:  MK      = HMAC-SHA-512(CK, 0x01)[:32]
             CK_next = HMAC-SHA-512(CK, 0x02)[:32]
             bir tomonlama zanjir -> forward secrecy va break-in recovery.

Shuningdek K-4: ratchet ochiq kaliti va PN spec Envelope'ida yo'q — bu yerda
`RatchetHeader` sifatida qo'shilgan (aks holda ratchet ishlamaydi).
"""
from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import Optional

from ..config import ProtocolConfig
from ..crypto import canonical
from ..crypto.primitives import (
    aead_open,
    aead_seal,
    hkdf_sha512,
    hmac_sha512,
    key_commitment,
    mlkem_decaps,
    mlkem_encaps,
    mlkem_generate,
    mlkem_pub,
    uint64be,
    x25519_dh,
    x25519_generate,
    x25519_pub,
)
from .envelope import (
    DIR_INITIATOR,
    DIR_RESPONDER,
    Envelope,
    MsgType,
    RatchetHeader,
    message_nonce,
)
from .errors import DecryptionError, RatchetError, ReplayError

RK_LEN = 64
CK_LEN = 32
MK_LEN = 32
COMMIT_LEN = 32


# ---------------------------------------------------------------------------
# KDF lar
# ---------------------------------------------------------------------------
def kdf_rk(rk: bytes, secret: bytes) -> tuple[bytes, bytes]:
    """KDF_RK(RK, dh_or_pq_secret) -> (RK_next, CK)

    Spec §6 bu funksiyani e'lon qiladi, lekin konkret ta'rifini BERMAYDI.
    Bu yerdagi ta'rif Signal Double Ratchet bilan mos: RK — salt, sir — IKM.
    """
    out = hkdf_sha512(secret, rk, b"SCUTUM-Q1/RK", RK_LEN + CK_LEN)
    return out[:RK_LEN], out[RK_LEN:]


def kdf_ck(
    cfg: ProtocolConfig, ck: bytes, session_id: bytes, message_no: int
) -> tuple[bytes, bytes]:
    """-> (CK_next, MK)"""
    if cfg.advance_chain_key:
        mk = hmac_sha512(ck, b"\x01")[:MK_LEN]
        ck_next = hmac_sha512(ck, b"\x02")[:CK_LEN]
        return ck_next, mk
    # SPEC: yagona konkret formula. CK oldinga siljimaydi.
    mk = hkdf_sha512(
        ck, b"SCUTUM-Q1/MSG", session_id + uint64be(message_no), MK_LEN
    )
    return ck, mk


# ---------------------------------------------------------------------------
# Holat
# ---------------------------------------------------------------------------
@dataclass
class RatchetState:
    session_id: bytes
    is_initiator: bool

    rk: bytes
    dhs_sk: object = None
    dhs_pk: bytes = b""
    dhr_pk: Optional[bytes] = None

    cks: Optional[bytes] = None
    ckr: Optional[bytes] = None

    ns: int = 0          # joriy yuborish chain'idagi tartib
    nr: int = 0          # joriy qabul chain'idagi tartib
    pn: int = 0          # oldingi yuborish chain uzunligi

    send_no: int = 0     # spec §4 `message_no` — yo'nalish bo'yicha monoton
    recv_max: int = -1
    seen_recv: set[int] = field(default_factory=set)

    # (DHr_pk, n) -> (MK, saqlangan_vaqt)   — spec §6.5
    skipped: dict[tuple[bytes, int], tuple[bytes, float]] = field(default_factory=dict)
    skipped_chains: list[bytes] = field(default_factory=list)

    # post-kvant ratchet (spec §6.1)
    pq_sk: object = None            # joriy ML-KEM maxfiy kalitimiz
    pq_sk_prev: object = None       # oldingisi (peer hali eskisiga Encaps qilgan bo'lishi mumkin)
    pq_peer_pk: Optional[bytes] = None
    pq_requested: bool = False      # keyingi ratchet qadamiga PQ qo'shilsinmi
    pq_out_ct: Optional[bytes] = None   # joriy ratchet kalitimizga biriktirilgan ct
    pq_out_pk: Optional[bytes] = None
    pq_msgs_since: int = 0
    pq_last_time: float = field(default_factory=time.time)
    pq_steps: int = 0

    dh_steps: int = 0
    closed: bool = False

    # --- yo'nalish baytlari ---
    @property
    def send_dir(self) -> bytes:
        return DIR_INITIATOR if self.is_initiator else DIR_RESPONDER

    @property
    def recv_dir(self) -> bytes:
        return DIR_RESPONDER if self.is_initiator else DIR_INITIATOR

    def pq_ratchet_due(self, cfg: ProtocolConfig) -> bool:
        """Spec §6.1: kamida har 100 xabar yoki 10 daqiqada (qaysi biri avval)."""
        return (
            self.pq_msgs_since >= cfg.pq_ratchet_every_msgs
            or (time.time() - self.pq_last_time) >= cfg.pq_ratchet_every_secs
        )

    def snapshot(self) -> dict:
        """GUI vizualizatori uchun holat kesimi."""
        return {
            "session_id": self.session_id,
            "role": "initiator" if self.is_initiator else "responder",
            "RK": self.rk,
            "CKs": self.cks,
            "CKr": self.ckr,
            "DHs_pk": self.dhs_pk,
            "DHr_pk": self.dhr_pk,
            "Ns": self.ns,
            "Nr": self.nr,
            "PN": self.pn,
            "message_no": self.send_no,
            "skipped": len(self.skipped),
            "dh_steps": self.dh_steps,
            "pq_steps": self.pq_steps,
            "pq_msgs_since": self.pq_msgs_since,
            "closed": self.closed,
        }


# ---------------------------------------------------------------------------
# Bootstrap (X3DH -> Double Ratchet)
# ---------------------------------------------------------------------------
def init_initiator(
    session_id: bytes, rk0: bytes, peer_spk_x_pk: bytes, peer_spk_mlkem_pk: bytes
) -> RatchetState:
    """Yuboruvchi: darhol birinchi DH ratchet qadamini bajaradi."""
    st = RatchetState(session_id=session_id, is_initiator=True, rk=rk0)
    st.pq_peer_pk = peer_spk_mlkem_pk
    st.dhr_pk = peer_spk_x_pk
    _new_sending_ratchet(st)
    return st


def init_responder(session_id: bytes, rk0: bytes, spk_x_sk, spk_mlkem_sk) -> RatchetState:
    """Qabul qiluvchi: SPK juftini boshlang'ich ratchet kaliti sifatida ishlatadi."""
    st = RatchetState(session_id=session_id, is_initiator=False, rk=rk0)
    st.dhs_sk = spk_x_sk
    st.dhs_pk = x25519_pub(spk_x_sk)
    st.dhr_pk = None
    st.pq_sk = spk_mlkem_sk
    return st


# ---------------------------------------------------------------------------
# DH ratchet (+ unga biriktirilgan post-kvant qadam)
# ---------------------------------------------------------------------------
def _new_sending_ratchet(st: RatchetState) -> None:
    """Yangi yuborish ratchet kalitini yaratadi va `rk -> cks` qadamini bajaradi.

    Agar PQ qadam so'ralgan bo'lsa, ML-KEM Encaps AYNI shu qadamga biriktiriladi.
    Bu spec §6.1 dagi "alohida RATCHET_PQ xabari" g'oyasidan farq qiladi va
    ataylab shunday: mustaqil PQ xabari DH ratchet bilan sinxron bo'la olmaydi
    (yuboruvchi tomonidan o'z-o'zidan bajarilgan ratchet qadami qabul qiluvchida
    hech qachon takrorlanmaydi). Bu — spec §6.1 ning ta'riflanmagan holat
    mashinasi muammosining amaliy isboti.
    """
    st.pn = st.ns
    st.ns = 0
    st.dhs_sk = x25519_generate()
    st.dhs_pk = x25519_pub(st.dhs_sk)

    extra = b""
    st.pq_out_ct = st.pq_out_pk = None
    if st.pq_requested and st.pq_peer_pk is not None:
        ss, ct = mlkem_encaps(st.pq_peer_pk)
        new_sk = mlkem_generate()
        st.pq_sk_prev, st.pq_sk = st.pq_sk, new_sk
        st.pq_out_ct, st.pq_out_pk = ct, mlkem_pub(new_sk)
        extra = ss
        st.pq_requested = False
        st.pq_msgs_since = 0
        st.pq_last_time = time.time()
        st.pq_steps += 1

    st.rk, st.cks = kdf_rk(st.rk, x25519_dh(st.dhs_sk, st.dhr_pk) + extra)
    st.dh_steps += 1


def _trial_dh_ratchet(trial: RatchetState, header: RatchetHeader, pq_key: str) -> None:
    """`trial` — ALLAQACHON nusxa, chaqiruvchi mas'ul (`decrypt()` quyida).

    MUHIM (tashqi audit, 2026-08-17): ML-KEM **implicit rejection**
    tufayli (FIPS 203) noto'g'ri maxfiy kalit bilan `Decaps` chaqirilsa,
    bu ODATDA istisno BERMAYDI — shunchaki boshqa, noto'g'ri umumiy sirni
    qaytaradi. Shuning uchun "avval joriy kalitni sinab ko'r, xato bo'lsa
    oldingisini sina" degan try/except naqshi ISHLAMAYDI — birinchi urinish
    deyarli har doim "muvaffaqiyatli" ko'rinadi, hatto noto'g'ri bo'lsa ham.

    To'g'ri yechim: `pq_key` orqali ANIQ qaysi kalit sinalishi tashqaridan
    beriladi; qaysi variant TO'G'RI ekanini faqat keyinroq AEAD
    autentifikatsiyasi hal qiladi (`decrypt()` ikkala variantni ham nusxada
    quradi va faqat g'olibini asl holatga COMMIT qiladi)."""
    trial.nr = 0
    trial.dhr_pk = header.dh_pk

    extra = b""
    if header.has_pq:
        sk = trial.pq_sk if pq_key == "current" else trial.pq_sk_prev
        if sk is None:
            raise RatchetError(f"PQ kalit ({pq_key}) mavjud emas")
        extra = mlkem_decaps(sk, header.pq_ct)
        trial.pq_steps += 1
        trial.pq_msgs_since = 0
        trial.pq_last_time = time.time()
    if header.pq_pk:
        trial.pq_peer_pk = header.pq_pk

    trial.rk, trial.ckr = kdf_rk(trial.rk, x25519_dh(trial.dhs_sk, trial.dhr_pk) + extra)
    _new_sending_ratchet(trial)


def request_pq_ratchet(st: RatchetState) -> None:
    """Spec §6.1: keyingi ratchet qadamiga post-kvant sirini qo'shishni so'rash."""
    st.pq_requested = True


def _trim_skipped(st: RatchetState, cfg: ProtocolConfig) -> None:
    """Spec §6.5: global limit + TTL (v1.0 da faqat chain limiti bor edi)."""
    if not cfg.bounded_skipped_keys:
        return
    now = time.time()
    expired = [k for k, (_mk, ts) in st.skipped.items()
               if now - ts > cfg.skipped_ttl_secs]
    for k in expired:
        st.skipped.pop(k, None)
    hard_cap = cfg.max_skipped_keys * cfg.max_skipped_chains
    while len(st.skipped) > hard_cap:
        st.skipped.pop(next(iter(st.skipped)))


def _skip_message_keys(st: RatchetState, cfg: ProtocolConfig, until_n: int) -> None:
    """Tartibi buzilgan xabarlar uchun kalitlarni saqlash (faqat HARDENED zanjirida)."""
    if st.ckr is None:
        return
    if until_n - st.nr > cfg.max_skipped_keys:
        raise RatchetError(
            f"MAX_SKIPPED_KEYS oshib ketdi ({until_n - st.nr} > {cfg.max_skipped_keys})"
        )
    while st.nr < until_n:
        st.ckr, mk = kdf_ck(cfg, st.ckr, st.session_id, st.nr)
        st.skipped[(st.dhr_pk, st.nr)] = (mk, time.time())
        st.nr += 1
    _trim_skipped(st, cfg)


# ---------------------------------------------------------------------------
# Shifrlash
# ---------------------------------------------------------------------------
def encrypt(
    st: RatchetState,
    cfg: ProtocolConfig,
    plaintext: bytes,
    *,
    sender_id: bytes,
    recipient_id: bytes,
    msg_type: str = MsgType.MSG,
    now: Optional[int] = None,
) -> tuple[Envelope, bytes]:
    """Bitta xabarni shifrlaydi. -> (Envelope, ishlatilgan MK)"""
    if st.closed:
        raise RatchetError("sessiya yopilgan")
    if st.cks is None:
        raise RatchetError("yuborish chain'i hali o'rnatilmagan")

    message_no = st.send_no
    st.cks, mk = kdf_ck(cfg, st.cks, st.session_id, message_no)

    header = RatchetHeader(
        dh_pk=st.dhs_pk, pn=st.pn, n=st.ns,
        pq_ct=st.pq_out_ct, pq_pk=st.pq_out_pk,
    )
    env = Envelope(
        type=msg_type,
        sender_device_id=sender_id,
        recipient_device_id=recipient_id,
        session_id=st.session_id,
        message_no=message_no,
        timestamp=int(now if now is not None else time.time()),
        header=header,
    )
    nonce = message_nonce(st.session_id, st.send_dir, message_no)
    ct = aead_seal(mk, nonce, plaintext, env.aad(cfg))
    if cfg.key_commitment:
        ct = key_commitment(mk) + ct
    env.body = ct

    st.ns += 1
    st.send_no += 1
    st.pq_msgs_since += 1
    return env, mk


# ---------------------------------------------------------------------------
# Deshifrlash
# ---------------------------------------------------------------------------
def _open_with(
    cfg: ProtocolConfig, st: RatchetState, mk: bytes, env: Envelope
) -> bytes:
    nonce = message_nonce(st.session_id, st.recv_dir, env.message_no)
    body = env.body
    if cfg.key_commitment:
        if len(body) < COMMIT_LEN:
            raise DecryptionError("kalit-majburiyat tegi yo'q")
        commit, body = body[:COMMIT_LEN], body[COMMIT_LEN:]
        import hmac as _hmac

        if not _hmac.compare_digest(commit, key_commitment(mk)):
            raise DecryptionError("kalit-majburiyat tegi mos emas")
    try:
        return aead_open(mk, nonce, body, env.aad(cfg))
    except Exception as exc:  # noqa: BLE001
        # Yagona, ma'lumot bermaydigan xato (spec §10.1)
        raise DecryptionError("xabar ochilmadi") from exc


def _candidate_same_chain(st: RatchetState, cfg: ProtocolConfig, env: Envelope) -> tuple[RatchetState, bytes]:
    """`env.header.dh_pk == st.dhr_pk` — mavjud, allaqachon autentifikatsiya
    qilingan zanjir ichida. Shunga qaramay NUSXADA ishlaymiz: agar `n`
    hujumchi tomonidan sun'iy ravishda katta qilib yuborilgan bo'lsa (dh_pk
    ochiq, imzosiz — buni bilish uchun hujumchiga hech narsa kerak emas),
    `_skip_message_keys` haqiqiy `ckr`ni oldinga surib, `MAX_SKIPPED_KEYS`
    byudjetini behuda sarflashi mumkin edi — bu ham faqat AEAD
    muvaffaqiyatidan keyin COMMIT qilinadi."""
    trial = copy.deepcopy(st)
    if cfg.advance_chain_key:
        _skip_message_keys(trial, cfg, env.header.n)
        trial.ckr, mk = kdf_ck(cfg, trial.ckr, trial.session_id, env.header.n)
        trial.nr += 1
    else:
        _, mk = kdf_ck(cfg, trial.ckr, trial.session_id, env.message_no)
        trial.nr = max(trial.nr, env.header.n + 1)
    return trial, mk


def _candidate_new_chain(
    st: RatchetState, cfg: ProtocolConfig, env: Envelope, pq_key: str,
) -> Optional[tuple[RatchetState, bytes]]:
    """Yangi DH ratchet zanjiri — nusxada quriladi. `pq_key` ("current"
    yoki "prev") ML-KEM implicit rejection tufayli TASHQARIDAN beriladi
    (yuqoridagi `_trial_dh_ratchet` docstring'iga qarang); har ikkala
    variant ham chaqiruvchida ALOHIDA sinaladi."""
    trial = copy.deepcopy(st)
    try:
        if trial.dhr_pk is not None and cfg.advance_chain_key:
            _skip_message_keys(trial, cfg, env.header.pn)
        _trial_dh_ratchet(trial, env.header, pq_key)
    except RatchetError:
        return None
    if trial.ckr is None:
        return None
    if cfg.advance_chain_key:
        _skip_message_keys(trial, cfg, env.header.n)
        trial.ckr, mk = kdf_ck(cfg, trial.ckr, trial.session_id, env.header.n)
        trial.nr += 1
    else:
        _, mk = kdf_ck(cfg, trial.ckr, trial.session_id, env.message_no)
        trial.nr = max(trial.nr, env.header.n + 1)
    return trial, mk


def decrypt(st: RatchetState, cfg: ProtocolConfig, env: Envelope) -> bytes:
    """Spec §6 + tashqi audit tuzatishi (2026-08-17, KRITIK):

    Avvalgi versiya `env.header.dh_pk` autentifikatsiyalanishidan OLDIN
    `st` ni to'g'ridan-to'g'ri mutatsiya qilardi (yangi DH ratchet qadami,
    ML-KEM decaps, skipped-key hisoblash). `header.dh_pk` esa Envelope
    AAD'ida bo'lsa-da, imzosiz — istalgan hujumchi (yoki ishonchsiz server)
    soxta `dh_pk`/`pq_ct` bilan bitta paket yuborib, AEAD muvaffaqiyatsiz
    bo'lgandan KEYIN ham `st`ni QAYTARIB BO'LMAYDIGAN tarzda buzishi mumkin
    edi — keyingi HAQIQIY xabarlar ham ochilmay qolardi (isbotlangan PoC).

    Endi har bir ratchet o'tishi **nusxada** ("trial") hisoblanadi va
    **faqat AEAD haqiqiy autentifikatsiya bergandan keyin** asl `st`ga
    COMMIT qilinadi. Muvaffaqiyatsiz urinish `st`ni HECH QANDAY holatda
    o'zgartirmaydi."""
    if st.closed:
        raise RatchetError("sessiya yopilgan")
    if env.session_id != st.session_id:
        raise RatchetError("session_id mos emas")
    if env.header is None:
        raise RatchetError(
            "ratchet sarlavhasi yo'q — spec Envelope'ida bu maydonlar yo'q (K-4)"
        )
    if env.message_no in st.seen_recv:
        raise ReplayError(f"message_no={env.message_no} allaqachon qabul qilingan")

    # --- saqlangan (o'tkazib yuborilgan) kalit — pop faqat muvaffaqiyatdan keyin
    key = (env.header.dh_pk, env.header.n)
    if key in st.skipped:
        mk, _stored_at = st.skipped[key]
        pt = _open_with(cfg, st, mk, env)   # muvaffaqiyatsiz bo'lsa istisno -> pop qilinmaydi
        del st.skipped[key]
        st.seen_recv.add(env.message_no)
        return pt

    # --- nomzod(lar)ni tuzish ---
    candidates: list[tuple[RatchetState, bytes]] = []
    if st.dhr_pk is not None and env.header.dh_pk == st.dhr_pk:
        candidates.append(_candidate_same_chain(st, cfg, env))
    else:
        if env.header.has_pq:
            for pq_key in ("current", "prev"):
                c = _candidate_new_chain(st, cfg, env, pq_key)
                if c is not None:
                    candidates.append(c)
        else:
            c = _candidate_new_chain(st, cfg, env, "none")
            if c is not None:
                candidates.append(c)

    if not candidates:
        raise RatchetError("ratchet nomzodi qurib bo'lmadi (PQ kalit yo'q yoki chain o'rnatilmagan)")

    last_exc: Optional[Exception] = None
    for trial, mk in candidates:
        try:
            pt = _open_with(cfg, trial, mk, env)
        except Exception as exc:  # noqa: BLE001 — keyingi nomzodni sinaymiz
            last_exc = exc
            continue
        # --- g'olib: faqat shu yerda asl holatga COMMIT qilinadi ---
        st.__dict__.update(trial.__dict__)
        st.seen_recv.add(env.message_no)
        st.recv_max = max(st.recv_max, env.message_no)
        return pt

    raise DecryptionError("xabar ochilmadi") from last_exc


