"""Spec §5: S-MSG sessiya ochish (INIT / ACK).

Bu modul spec'ning eng muhim ikki kamchiligi jamlangan joy:

  K-1  dh3 = X25519(EK_A, IK_B) yo'q  -> SPK bitta nuqtali nosozlik
  K-2  dh4 = X25519(EK_A, OPK_B) yo'q -> OPK dekorativ, INIT replay ochiq
  Y-1  KEM ciphertext transkriptga bog'lanmagan
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from ..config import SUITE, ProtocolConfig
from ..crypto import canonical
from ..crypto.primitives import (
    HybridSignature,
    hkdf_sha512,
    hybrid_sign,
    hybrid_verify,
    mlkem_decaps,
    mlkem_encaps,
    random_bytes,
    sha3_256,
    x25519_dh,
    x25519_generate,
    x25519_pub,
)
from .envelope import Envelope, MsgType
from .errors import PolicyError, ProtocolError, ReplayError, VerificationError
from .identity import DeviceKeys, dc_bytes, verify_prekey_bundle

ROOT_KEY_LEN = 64  # spec §5.2: L = 64


# ---------------------------------------------------------------------------
# Transkript va root key
# ---------------------------------------------------------------------------
def init_salt(dc_a: dict, dc_b: dict, cfg: ProtocolConfig) -> bytes:
    """salt = SHA3-256("SCUTUM-Q1/INIT" || sender_DC || recipient_DC)  — spec §5.2"""
    return sha3_256(b"SCUTUM-Q1/INIT", dc_bytes(dc_a, cfg), dc_bytes(dc_b, cfg))


def init_transcript(
    *,
    ek_pk: bytes,
    spk_x_pk: bytes,
    mlkem_pk: bytes,
    mlkem_ct: bytes,
    opk_pk: Optional[bytes],
    dc_a: dict,
    dc_b: dict,
    cfg: ProtocolConfig,
) -> bytes:
    """To'liq handshake transkripti (Y-1 tuzatishi).

    Spec'da bu YO'Q: salt faqat ikki DC dan iborat, ephemeral ochiq kalit ham,
    ML-KEM ciphertext ham KDF ga kirmaydi.
    """
    return sha3_256(
        b"SCUTUM-Q1/transcript",
        canonical.encode(
            {
                "suite": SUITE,
                "ek": ek_pk,
                "spk_x": spk_x_pk,
                "kem_pk": mlkem_pk,
                "kem_ct": mlkem_ct,
                "opk": opk_pk,
                "dc_a": dc_a,
                "dc_b": dc_b,
            },
            cfg.encoding,
        ),
    )


def derive_root_key(
    *,
    cfg: ProtocolConfig,
    dh1: bytes,
    dh2: bytes,
    dh3: Optional[bytes],
    dh4: Optional[bytes],
    kem_ss: bytes,
    salt: bytes,
    transcript: Optional[bytes],
) -> bytes:
    """RK0 = HKDF-SHA-512(ikm, salt, info="root-key", L=64)  — spec §5.2

    SPEC:      ikm = dh1 || dh2 || pq.shared_secret
    HARDENED:  ikm = dh1 || dh2 || dh3 || [dh4] || pq.shared_secret
               va info ga to'liq transkript xeshi qo'shiladi.
    """
    parts = [dh1, dh2]
    if cfg.include_dh3_identity:
        if dh3 is None:
            raise ProtocolError("dh3 talab qilinadi, lekin berilmadi")
        parts.append(dh3)
    if cfg.include_opk_dh and dh4 is not None:
        parts.append(dh4)
    parts.append(kem_ss)
    ikm = b"".join(parts)

    info = b"root-key"
    if cfg.bind_kem_transcript:
        if transcript is None:
            raise ProtocolError("transkript talab qilinadi, lekin berilmadi")
        info = b"root-key" + transcript

    return hkdf_sha512(ikm, salt, info, ROOT_KEY_LEN)


# ---------------------------------------------------------------------------
# INIT
# ---------------------------------------------------------------------------
@dataclass
class InitState:
    """Yuboruvchi tomonda INIT dan keyingi holat."""

    session_id: bytes
    rk0: bytes
    ek_sk: object
    ek_pk: bytes
    peer_dc: dict
    peer_spk_x_pk: bytes
    peer_spk_mlkem_pk: bytes
    kem_ct: bytes
    opk_id: Optional[bytes]
    transcript: bytes
    envelope: Envelope


def _init_body_core(
    dc_a: dict, ek_pk: bytes, kem_ct: bytes, opk_id: Optional[bytes]
) -> dict:
    return {"dc": dc_a, "ek": ek_pk, "kem_ct": kem_ct, "opk_id": opk_id}


def create_init(
    sender: DeviceKeys,
    bundle: dict,
    cfg: ProtocolConfig,
    *,
    now: Optional[int] = None,
    session_id: Optional[bytes] = None,
    ek_sk: Optional[object] = None,
) -> InitState:
    """Spec §5.2 INIT xabarini yaratadi."""
    now = int(now if now is not None else time.time())
    verify_prekey_bundle(bundle, cfg, now=now)

    dc_b = bundle["dc"]
    dc_a = sender.dc()
    session_id = session_id or random_bytes(16)

    ek_sk = ek_sk or x25519_generate()
    ek_pk = x25519_pub(ek_sk)

    # --- spec §5.2 ---
    dh1 = x25519_dh(ek_sk, bundle["spk_x_pk"])
    dh2 = x25519_dh(sender.ik_x, bundle["spk_x_pk"])
    # --- K-1 tuzatishi: qabul qiluvchining identity kaliti ---
    dh3 = x25519_dh(ek_sk, dc_b["x25519_pk"])
    # --- K-2 tuzatishi: OPK haqiqatan qatnashadi va MAJBURIY (spec §5.2) ---
    opk_pk = bundle.get("opk_pk")
    if cfg.include_opk_dh and opk_pk is None:
        raise PolicyError(
            "bundle'da OPK yo'q — spec §5.2 bo'yicha OPK majburiy; "
            "server zaxirani tugatgan yoki OPK'ni olib tashlagan bo'lishi mumkin"
        )
    dh4 = x25519_dh(ek_sk, opk_pk) if opk_pk else None

    kem_ss, kem_ct = mlkem_encaps(bundle["spk_mlkem_pk"])

    transcript = init_transcript(
        ek_pk=ek_pk,
        spk_x_pk=bundle["spk_x_pk"],
        mlkem_pk=bundle["spk_mlkem_pk"],
        mlkem_ct=kem_ct,
        opk_pk=opk_pk,
        dc_a=dc_a,
        dc_b=dc_b,
        cfg=cfg,
    )
    rk0 = derive_root_key(
        cfg=cfg,
        dh1=dh1,
        dh2=dh2,
        dh3=dh3,
        dh4=dh4,
        kem_ss=kem_ss,
        salt=init_salt(dc_a, dc_b, cfg),
        transcript=transcript,
    )

    env = Envelope(
        type=MsgType.INIT,
        sender_device_id=sender.device_id,
        recipient_device_id=dc_b["device_id"],
        session_id=session_id,
        message_no=0,
        timestamp=now,
    )
    core = _init_body_core(dc_a, ek_pk, kem_ct, bundle.get("opk_id"))
    signed = env.aad(cfg) + canonical.encode(core, cfg.encoding)
    if cfg.bind_kem_transcript:
        signed += transcript
    sig = hybrid_sign(sender.ik_ed, sender.ik_mldsa, signed)

    body = dict(core)
    body["sig"] = sig.to_bytes()
    env.body = canonical.encode(body, cfg.encoding)

    return InitState(
        session_id=session_id,
        rk0=rk0,
        ek_sk=ek_sk,
        ek_pk=ek_pk,
        peer_dc=dc_b,
        peer_spk_x_pk=bundle["spk_x_pk"],
        peer_spk_mlkem_pk=bundle["spk_mlkem_pk"],
        kem_ct=kem_ct,
        opk_id=bundle.get("opk_id"),
        transcript=transcript,
        envelope=env,
    )


@dataclass
class InitAcceptance:
    """Qabul qiluvchi tomonda INIT ni qayta ishlash natijasi."""

    session_id: bytes
    rk0: bytes
    peer_dc: dict
    peer_ek_pk: bytes
    opk_id: Optional[bytes]
    opk_consumed: bool
    transcript: bytes


class InitReplayCache:
    """K-2 tuzatishi: INIT takrorlanishini to'suvchi kesh.

    Spec'da bunday mexanizm umuman yo'q. Kalit — ML-KEM ciphertext xeshi,
    chunki u har bir halol INIT uchun yangi (Encaps tasodifiy).
    """

    def __init__(self) -> None:
        self._seen: dict[bytes, int] = {}

    def check_and_add(self, key: bytes, ts: int, window: int, now: int) -> None:
        if abs(now - ts) > window:
            raise ReplayError(
                f"INIT timestamp oynadan tashqarida ({abs(now - ts)}s > {window}s)"
            )
        if key in self._seen:
            raise ReplayError("INIT allaqachon ko'rilgan — replay")
        self._seen[key] = ts

    def prune(self, now: int, window: int) -> None:
        self._seen = {k: t for k, t in self._seen.items() if abs(now - t) <= window}

    def __len__(self) -> int:
        return len(self._seen)


def accept_init(
    recipient: DeviceKeys,
    env: Envelope,
    cfg: ProtocolConfig,
    *,
    now: Optional[int] = None,
    replay_cache: Optional[InitReplayCache] = None,
) -> InitAcceptance:
    """Spec §5.2 qabul qiluvchi tomoni."""
    now = int(now if now is not None else time.time())
    if env.type != MsgType.INIT:
        raise ProtocolError(f"INIT kutilgan edi, {env.type} keldi")

    try:
        body = canonical.decode(env.body, cfg.encoding)
        if not isinstance(body, dict):
            raise ProtocolError("INIT body xarita emas")
        dc_a = body["dc"]
        ek_pk = body["ek"]
        kem_ct = body["kem_ct"]
        opk_id = body.get("opk_id")
        if not isinstance(dc_a, dict):
            raise ProtocolError("INIT ichida DC yo'q")
        for f in ("device_id", "x25519_pk", "ed25519_pk", "mldsa65_pk"):
            if not isinstance(dc_a.get(f), (bytes, bytearray)):
                raise ProtocolError(f"DC.{f} maydoni noto'g'ri")
        if not isinstance(dc_a.get("expires_at"), int):
            raise ProtocolError("DC.expires_at noto'g'ri")
        if len(ek_pk) != 32 or len(kem_ct) != 1088:
            raise ProtocolError("INIT kalit materiali o'lchami noto'g'ri")
    except ProtocolError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ProtocolError(f"INIT tuzilishi noto'g'ri: {type(exc).__name__}") from exc
    dc_b = recipient.dc()

    if dc_a["device_id"] != env.sender_device_id:
        raise VerificationError("DC device_id envelope bilan mos emas")
    if now > dc_a["expires_at"]:
        raise VerificationError("yuboruvchi DC muddati o'tgan")

    # --- ML-KEM decapsulation ---
    kem_ss = mlkem_decaps(recipient.spk_mlkem, kem_ct)

    transcript = init_transcript(
        ek_pk=ek_pk,
        spk_x_pk=recipient.spk_x_pk,
        mlkem_pk=recipient.spk_mlkem_pk,
        mlkem_ct=kem_ct,
        opk_pk=recipient.opks[opk_id].pk if opk_id in recipient.opks else None,
        dc_a=dc_a,
        dc_b=dc_b,
        cfg=cfg,
    )

    # --- gibrid imzo tekshiruvi (spec §5.2 / §5.3) ---
    core = _init_body_core(dc_a, ek_pk, kem_ct, opk_id)
    signed = env.aad(cfg) + canonical.encode(core, cfg.encoding)
    if cfg.bind_kem_transcript:
        signed += transcript
    sig = HybridSignature.from_bytes(body["sig"])
    if not hybrid_verify(dc_a["ed25519_pk"], dc_a["mldsa65_pk"], sig, signed):
        raise VerificationError("INIT gibrid imzosi haqiqiy emas")

    # --- replay himoyasi (K-2) ---
    if cfg.init_replay_cache:
        if replay_cache is None:
            raise ProtocolError("init_replay_cache yoqilgan, lekin kesh berilmagan")
        replay_cache.check_and_add(
            sha3_256(b"SCUTUM-Q1/init-id", kem_ct),
            env.timestamp,
            cfg.replay_window_secs,
            now,
        )

    # --- DH lar ---
    dh1 = x25519_dh(recipient.spk_x, ek_pk)
    dh2 = x25519_dh(recipient.spk_x, dc_a["x25519_pk"])
    dh3 = x25519_dh(recipient.ik_x, ek_pk)

    dh4 = None
    opk_consumed = False
    if cfg.include_opk_dh and opk_id is None:
        raise PolicyError("INIT'da OPK ko'rsatilmagan — spec §5.2 bo'yicha majburiy")
    if opk_id is not None:
        opk = recipient.take_opk(opk_id)   # spec §5.2: atomik o'chirish MUST
        if opk is not None:
            dh4 = x25519_dh(opk.sk, ek_pk)
            opk_consumed = True
        elif cfg.include_opk_dh:
            # OPK haqiqatan kerak bo'lsa, uning yo'qligi = replay yoki xato
            raise ReplayError("ko'rsatilgan OPK mavjud emas (allaqachon ishlatilgan)")

    rk0 = derive_root_key(
        cfg=cfg,
        dh1=dh1,
        dh2=dh2,
        dh3=dh3,
        dh4=dh4,
        kem_ss=kem_ss,
        salt=init_salt(dc_a, dc_b, cfg),
        transcript=transcript,
    )

    return InitAcceptance(
        session_id=env.session_id,
        rk0=rk0,
        peer_dc=dc_a,
        peer_ek_pk=ek_pk,
        opk_id=opk_id,
        opk_consumed=opk_consumed,
        transcript=transcript,
    )
