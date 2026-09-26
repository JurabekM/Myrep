"""QVL/1 record layer: ChaCha20-Poly1305 records with RFC 4303 replay window.

Record body : ``sid(8) || seq(u64 BE) || AEAD ciphertext``
AAD         : ``ver || type || sid || seq``
Nonce       : ``dir(4) || seq(8)`` with dir = b"UP\\0\\0" (node->gw) or b"DN\\0\\0".
"""
from __future__ import annotations

import struct

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from .wire import VERSION, FrameType, ProtocolError, make_frame, parse_frame

DIR_UP = b"UP\x00\x00"
DIR_DN = b"DN\x00\x00"
REKEY_AFTER = 2**20
RECORD_TYPES = (FrameType.DATA, FrameType.ALERT, FrameType.CLOSE)
# ver(1) + type(1) + sid(8) + seq(8) + Poly1305 tag(16); excludes u32 stream length.
RECORD_OVERHEAD = 1 + 1 + 8 + 8 + 16


class ReplayWindow:
    """64-entry sliding anti-replay bitmap (RFC 4303 section 3.4.3).

    ``check`` is side-effect free; ``update`` is called only after the AEAD
    tag verified, so forged packets cannot advance the window.
    """

    SIZE = 64

    def __init__(self) -> None:
        self.top = 0
        self.bitmap = 0  # bit i set => (top - i) seen

    def check(self, seq: int) -> bool:
        if seq == 0:
            return False
        if seq > self.top:
            return True
        diff = self.top - seq
        if diff >= self.SIZE:
            return False
        return not (self.bitmap >> diff) & 1

    def update(self, seq: int) -> None:
        if not self.check(seq):
            raise ProtocolError("replay")
        if seq > self.top:
            shift = seq - self.top
            self.bitmap = ((self.bitmap << shift) | 1) & ((1 << self.SIZE) - 1) if shift < self.SIZE else 1
            self.top = seq
        else:
            self.bitmap |= 1 << (self.top - seq)


class Session:
    """One direction pair of traffic keys bound to a session id."""

    def __init__(self, role: str, k_up: bytes, k_down: bytes, session_id: bytes, peer_id: bytes = b"") -> None:
        if role not in ("node", "gateway"):
            raise ValueError("role must be node or gateway")
        self.role = role
        self.session_id = session_id
        self.peer_id = peer_id
        if role == "node":
            self._tx, self._tx_dir = ChaCha20Poly1305(k_up), DIR_UP
            self._rx, self._rx_dir = ChaCha20Poly1305(k_down), DIR_DN
        else:
            self._tx, self._tx_dir = ChaCha20Poly1305(k_down), DIR_DN
            self._rx, self._rx_dir = ChaCha20Poly1305(k_up), DIR_UP
        self.send_seq = 0
        self.window = ReplayWindow()
        self.closed = False
        self.ticket = None  # resumption ticket minted by the handshake, if any

    @property
    def needs_rekey(self) -> bool:
        return self.send_seq >= REKEY_AFTER

    def seal(self, ftype: FrameType, plaintext: bytes) -> bytes:
        if ftype not in RECORD_TYPES:
            raise ProtocolError("not a record type")
        if self.needs_rekey:
            raise ProtocolError("rekey required")
        self.send_seq += 1
        hdr = self.session_id + struct.pack(">Q", self.send_seq)
        aad = bytes([VERSION, int(ftype)]) + hdr
        nonce = self._tx_dir + struct.pack(">Q", self.send_seq)
        return make_frame(ftype, hdr + self._tx.encrypt(nonce, plaintext, aad))

    def open(self, frame: bytes) -> tuple[FrameType, bytes]:
        ftype, body = parse_frame(frame)
        if ftype not in RECORD_TYPES:
            raise ProtocolError("not a record type")
        if len(body) < 8 + 8 + 16:
            raise ProtocolError("short record")
        sid, (seq,) = body[:8], struct.unpack(">Q", body[8:16])
        if sid != self.session_id:
            raise ProtocolError("wrong session")
        if not self.window.check(seq):
            raise ProtocolError("replay")
        aad = bytes([VERSION, int(ftype)]) + body[:16]
        nonce = self._rx_dir + struct.pack(">Q", seq)
        try:
            pt = self._rx.decrypt(nonce, body[16:], aad)
        except InvalidTag as e:
            raise ProtocolError("bad record MAC") from e
        self.window.update(seq)
        return ftype, pt
