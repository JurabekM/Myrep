"""Spec §4: umumiy paket qobig'i va AAD qurilishi."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from ..config import PROTOCOL_VERSION, SUITE, ProtocolConfig
from ..crypto import canonical
from ..crypto.primitives import sha3_256, uint64be
from .errors import ProtocolError


class MsgType:
    INIT = "INIT"
    ACK = "ACK"
    MSG = "MSG"
    RATCHET_PQ = "RATCHET_PQ"
    CLOSE = "CLOSE"
    DEVICE_REVOKE = "DEVICE_REVOKE"
    FILE_MANIFEST = "FILE_MANIFEST"  # spec'da alohida turi yo'q; S-FILE uchun

    ALL = (INIT, ACK, MSG, RATCHET_PQ, CLOSE, DEVICE_REVOKE, FILE_MANIFEST)


#: yo'nalish baytlari — spec'da `direction` kodlanishi umuman ta'riflanmagan
DIR_INITIATOR = b"\x00"
DIR_RESPONDER = b"\x01"


@dataclass
class RatchetHeader:
    """Ratchet sarlavhasi.

    DIQQAT (K-4): bu maydonlar spec §4 Envelope sxemasida YO'Q. Ularsiz Double
    Ratchet'ni amalga oshirib bo'lmaydi, shuning uchun simulyator ularni
    qo'shadi va `header_in_aad` bayrog'i ular AEAD bilan himoyalanishini
    boshqaradi.
    """

    dh_pk: bytes           # yuboruvchining joriy ratchet ochiq kaliti
    pn: int                # oldingi chain uzunligi
    n: int                 # shu chain ichidagi tartib raqami
    pq_ct: Optional[bytes] = None   # shu ratchet kaliti bilan birga kelgan ML-KEM ct
    pq_pk: Optional[bytes] = None   # yuboruvchining yangi ML-KEM ochiq kaliti

    @property
    def has_pq(self) -> bool:
        return self.pq_ct is not None

    def to_dict(self) -> dict:
        return {
            "dh": self.dh_pk,
            "pn": self.pn,
            "n": self.n,
            "pq_ct": self.pq_ct,
            "pq_pk": self.pq_pk,
        }

    @staticmethod
    def from_dict(d: dict) -> "RatchetHeader":
        return RatchetHeader(
            d["dh"], int(d["pn"]), int(d["n"]), d.get("pq_ct"), d.get("pq_pk")
        )


@dataclass
class Envelope:
    """Spec §4 Envelope."""

    type: str
    sender_device_id: bytes
    recipient_device_id: Optional[bytes] = None
    session_id: Optional[bytes] = None
    message_no: Optional[int] = None
    timestamp: int = field(default_factory=lambda: int(time.time()))
    body: bytes = b""
    v: int = PROTOCOL_VERSION
    suite: str = SUITE
    header: Optional[RatchetHeader] = None   # K-4 qo'shimchasi

    # ---------------- AAD ----------------
    def aad_fields(self, cfg: ProtocolConfig) -> dict:
        """AAD ga kiradigan maydonlar (spec §4).

        "v, suite, type, yuboruvchi/qabul qiluvchi identifikatorlari,
         session_id, message_no va timestamp MUST AEAD associated_data
         tarkibiga kiritiladi."
        """
        d = {
            "v": self.v,
            "suite": self.suite,
            "type": self.type,
            "snd": self.sender_device_id,
            "rcv": self.recipient_device_id,
            "sid": self.session_id,
            "no": self.message_no,
            "ts": self.timestamp,
        }
        if cfg.header_in_aad and self.header is not None:
            d["hdr"] = self.header.to_dict()
        return d

    def aad(self, cfg: ProtocolConfig) -> bytes:
        return canonical.encode(self.aad_fields(cfg), cfg.encoding)

    # ---------------- wire format ----------------
    def to_wire(self, cfg: ProtocolConfig) -> bytes:
        d = self.aad_fields(cfg)
        d["body"] = self.body
        if not cfg.header_in_aad and self.header is not None:
            # sarlavha uzatiladi, lekin AAD bilan himoyalanmagan (SPEC holati)
            d["hdr"] = self.header.to_dict()
        return canonical.encode(d, cfg.encoding)

    @staticmethod
    def from_wire(raw: bytes, cfg: ProtocolConfig) -> "Envelope":
        """Paketni qat'iy tekshirib ochadi.

        Spec §10.1 taqiqi ("xato sababi orqali holatni oshkor qiluvchi turli
        javoblar") va §10 p.4 (fuzzing) talabi: parser HECH QACHON xom
        kutubxona istisnosini (CBORDecodeError, KeyError, struct.error, …)
        tashqariga chiqarmasligi kerak — hammasi `ProtocolError` ga aylanadi.
        """
        try:
            if cfg.strict_encoding and not canonical.is_deterministic(raw, cfg.encoding):
                raise ProtocolError("paket kanonik kodlanmagan — rad etildi")
            d = canonical.decode(raw, cfg.encoding)
        except ProtocolError:
            raise
        except Exception as exc:  # noqa: BLE001 — barcha parser xatolari
            raise ProtocolError(f"paketni dekodlab bo'lmadi: {type(exc).__name__}") from exc

        if not isinstance(d, dict):
            raise ProtocolError("paket xaritasi (map) emas")

        try:
            env = Envelope(
                type=_str(d, "type"),
                sender_device_id=_bytes(d, "snd", 16),
                recipient_device_id=_bytes(d, "rcv", 16, optional=True),
                session_id=_bytes(d, "sid", 16, optional=True),
                message_no=_uint(d, "no", optional=True),
                timestamp=_uint(d, "ts"),
                body=_bytes(d, "body", optional=True) or b"",
                v=_uint(d, "v"),
                suite=_str(d, "suite"),
                header=_header(d.get("hdr")),
            )
        except ProtocolError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProtocolError(f"paket tuzilishi noto'g'ri: {type(exc).__name__}") from exc

        if env.v != PROTOCOL_VERSION:
            raise ProtocolError(f"qo'llab-quvvatlanmaydigan versiya: {env.v}")
        if env.suite != SUITE:
            raise ProtocolError(f"qo'llab-quvvatlanmaydigan suite: {env.suite}")
        if env.type not in MsgType.ALL:
            raise ProtocolError(f"noma'lum xabar turi: {env.type}")
        return env

    def size(self, cfg: ProtocolConfig) -> int:
        return len(self.to_wire(cfg))


# ---------------------------------------------------------------------------
# Qat'iy maydon tekshiruvchilari
# ---------------------------------------------------------------------------
MAX_BODY = 16 * 1024 * 1024
_MLKEM_CT = 1088
_MLKEM_PK = 1184


def _bytes(d: dict, key: str, length: int | None = None, *, optional: bool = False):
    v = d.get(key)
    if v is None:
        if optional:
            return None
        raise ProtocolError(f"`{key}` maydoni yo'q")
    if not isinstance(v, (bytes, bytearray)):
        raise ProtocolError(f"`{key}` bytes bo'lishi kerak")
    v = bytes(v)
    if length is not None and len(v) != length:
        raise ProtocolError(f"`{key}` uzunligi {len(v)}, kutilgan {length}")
    if len(v) > MAX_BODY:
        raise ProtocolError(f"`{key}` juda katta")
    return v


def _uint(d: dict, key: str, *, optional: bool = False):
    v = d.get(key)
    if v is None:
        if optional:
            return None
        raise ProtocolError(f"`{key}` maydoni yo'q")
    if isinstance(v, bool) or not isinstance(v, int) or v < 0 or v > 2**64 - 1:
        raise ProtocolError(f"`{key}` uint64 bo'lishi kerak")
    return v


def _str(d: dict, key: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or len(v) > 64:
        raise ProtocolError(f"`{key}` qisqa satr bo'lishi kerak")
    return v


def _header(h) -> Optional[RatchetHeader]:
    if h is None:
        return None
    if not isinstance(h, dict):
        raise ProtocolError("`hdr` xarita bo'lishi kerak")
    hdr = RatchetHeader(
        dh_pk=_bytes(h, "dh", 32),
        pn=_uint(h, "pn"),
        n=_uint(h, "n"),
        pq_ct=_bytes(h, "pq_ct", _MLKEM_CT, optional=True),
        pq_pk=_bytes(h, "pq_pk", _MLKEM_PK, optional=True),
    )
    if hdr.pn > 2**32 or hdr.n > 2**32:
        raise ProtocolError("`hdr` hisoblagichlari haddan tashqari katta")
    return hdr


# ---------------------------------------------------------------------------
# Nonce (spec §6)
# ---------------------------------------------------------------------------
def message_nonce(session_id: bytes, direction: bytes, message_no: int) -> bytes:
    """nonce = first_12_bytes(SHA3-256(session_id || direction || message_no))

    Kalitga bog'liq emas — xavfsizligi butunlay MK ning har xabar uchun
    yagonaligiga tayanadi.
    """
    return sha3_256(session_id, direction, uint64be(message_no))[:12]


def file_chunk_nonce(file_id: bytes, index: int) -> bytes:
    """nonce_i = first_12_bytes(SHA3-256(file_id || uint64be(i)))  — spec §7.1"""
    return sha3_256(file_id, uint64be(index))[:12]
