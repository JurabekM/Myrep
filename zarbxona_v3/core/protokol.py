"""§13.4–13.6 — xabarlar, MQTT mavzulari, wire qatlami (AQW1)."""

from __future__ import annotations

import base64
import hmac
import json
import struct

from .ibtido import sha3, tagged_hash
from .konstanta import L_MINT_AUTH, L_SRV_ID, L_WIRE, MAX_XABAR
from .kupyura import Qator
from .partiya import Partiya


class ProtokolXatosi(Exception):
    pass


# --- MQTT mavzulari (§13.2) --------------------------------------------------


def bank_id(bank_pk: bytes) -> str:
    return sha3(L_SRV_ID + bank_pk).hex()[:16]


def mavzular(bank_pk: bytes, sessiya_id: str) -> tuple[str, str]:
    """(c2b — zarbxona nashr qiladi, b2c — obuna bo'ladi)."""
    b = bank_id(bank_pk)
    return f"aetherq/bank/{b}/c2b/{sessiya_id}", f"aetherq/bank/{b}/b2c/{sessiya_id}"


# --- mint_auth (§13.5) --------------------------------------------------------


def mint_auth_xesh(bank_pk: bytes, chaqiriq: bytes, cert_id: bytes) -> bytes:
    return tagged_hash(L_MINT_AUTH, bank_pk, chaqiriq, cert_id)


def mint_auth_imzo(sk, bank_pk: bytes, chaqiriq: bytes, cert_id: bytes) -> bytes:
    """`sk` — kalit yoki imzolovchi (4.x Pico)."""
    from .imzolovchi import imzolovchi
    return imzolovchi(sk).mint_auth_imzosi(bank_pk, chaqiriq, cert_id)


# --- JSON xabarlar (§13.4) ------------------------------------------------------


def kodla(d: dict) -> bytes:
    b = json.dumps(d, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(b) > MAX_XABAR:
        raise ProtokolXatosi(f"xabar 1 MiB dan katta ({len(b)} bayt)")
    return b


def och(b: bytes) -> dict:
    if len(b) > MAX_XABAR:
        raise ProtokolXatosi("xabar 1 MiB dan katta")
    try:
        d = json.loads(b.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise ProtokolXatosi(f"JSON emas: {e}") from e
    if not isinstance(d, dict) or d.get("v") != 1:
        raise ProtokolXatosi("xabar formati noto'g'ri (v != 1)")
    return d


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s, validate=True)


def qator_kodla(q: Qator) -> list:
    """8 maydonli ro'yxat, baytlar standart base64 (padding bilan)."""
    return [_b64(q.note_id), q.nominal, q.egasi, q.seq, _b64(q.batch_id),
            _b64(q.cheklov_xeshi), _b64(q.muhr), _b64(q.isbot)]


def qator_och(r: list, leaf_index: int) -> Qator:
    if not isinstance(r, list) or len(r) != 8:
        raise ProtokolXatosi("qator 8 maydonli ro'yxat bo'lishi kerak")
    try:
        return Qator(leaf_index, _unb64(r[0]), int(r[1]), str(r[2]), int(r[3]), _unb64(r[4]),
                     _unb64(r[5]), _unb64(r[6]), _unb64(r[7]))
    except (ValueError, TypeError) as e:
        raise ProtokolXatosi(f"qator buzilgan: {e}") from e


def batch_begin_param(p: Partiya) -> dict:
    return {"batch_id": p.partiya_id.hex(), "root": p.ildiz.hex(), "note_count": p.soni,
            "first_seq": p.birinchi_seq, "total": p.jami, "reserve_lock": p.zaxira_qulfi,
            "minted_ms": p.zarb_ms, "signature": p.imzo.hex(), "constraints": p.cheklov}


# --- wire AQW1 (§13.6) --------------------------------------------------------

SEHR = b"AQW1"
C2B, B2C = b"c2b", b"b2c"
_BOSH = 4 + 8 + 16


def _teg(kalit: bytes, yonalish: bytes, n: int, yozuv: bytes) -> bytes:
    return sha3(L_WIRE + kalit + yonalish + struct.pack(">Q", n) + yozuv)[:16]


class Wire:
    """Soxta, takroriy va eski paketlarni AEAD'ga QADAR tashlaydi."""

    def __init__(self, kalit: bytes, yuborish: bytes = C2B, qabul: bytes = B2C):
        if len(kalit) != 32:
            raise ValueError("wire kaliti 32 bayt")
        self.kalit, self.yuborish, self.qabul = kalit, yuborish, qabul
        self.yuborilgan = 0         # 1 dan boshlanadi (birinchi `ora` da)
        self.oxirgi_qabul = 0
        self.tashlangan = 0

    def ora(self, yozuv: bytes) -> bytes:
        self.yuborilgan += 1
        n = self.yuborilgan
        return SEHR + struct.pack(">Q", n) + _teg(self.kalit, self.yuborish, n, yozuv) + yozuv

    def ech(self, paket: bytes) -> bytes | None:
        """Yaroqsiz bo'lsa jim `None` va `tashlangan += 1`. Sessiya tirik qoladi."""
        if len(paket) < _BOSH or paket[:4] != SEHR:
            self.tashlangan += 1
            return None
        n = struct.unpack(">Q", paket[4:12])[0]
        teg, yozuv = paket[12:28], paket[28:]
        if not hmac.compare_digest(teg, _teg(self.kalit, self.qabul, n, yozuv)):
            self.tashlangan += 1
            return None
        if n <= self.oxirgi_qabul:
            self.tashlangan += 1
            return None
        self.oxirgi_qabul = n
        return yozuv
