"""
AETHER-Q v5.1 — Transport / AEAD Record Layer (spec §8).

Handshake (0x01..0x08) `SharedSecret` chiqargach, ma'lumot shu qatlam orqali
uzatiladi: ChaCha20-Poly1305, yo'nalishli kalitlar, monotonik nonce, rekeying
(forward secrecy).
"""

import struct
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from .kdf import hkdf_extract, hkdf_expand

TRANSPORT_LABEL = b"AETHER-Q-v5.1-TRANSPORT/L3/v1"

TYPE_APP_DATA = 0x17
TYPE_ALERT = 0x15
TYPE_KEY_UPDATE = 0x18

_MAX_SEQ = (1 << 96) - 1


def _le96(seq: int) -> bytes:
    return seq.to_bytes(12, "little")


class _DirState:
    """Bitta yo'nalish (c2s yoki s2c) uchun kalit + nonce holati."""

    def __init__(self, key: bytes, iv: bytes):
        self.key = key
        self.iv = iv
        self.seq = 0
        self._aead = ChaCha20Poly1305(key)

    def _nonce(self) -> bytes:
        if self.seq > _MAX_SEQ:
            raise OverflowError("seq tugadi — rekey SHART edi (N13)")
        n = int.from_bytes(self.iv, "little") ^ self.seq
        return _le96(n & _MAX_SEQ)

    def rekey(self, n: int):
        """K_{n+1} = HKDF-Expand(K_n, 'rekey' || n). Eski kalit tashlanadi (N14)."""
        new_key = hkdf_expand(self.key, TRANSPORT_LABEL + b"/rekey" +
                              n.to_bytes(8, "big"), 32)
        self.key = new_key
        self._aead = ChaCha20Poly1305(new_key)
        self.seq = 0


class Session:
    """Ikki tomonlama AEAD sessiyasi. role: 'client' yoki 'server'."""

    def __init__(self, prk_handshake: bytes, profile_id: int, role: str, epoch: int = 0):
        self.profile_id = profile_id
        self.epoch = epoch
        self.role = role
        ts = hkdf_expand(prk_handshake, TRANSPORT_LABEL + b"/ts" + bytes([profile_id]), 32)
        k_c2s = hkdf_expand(ts, b"c2s-key", 32)
        iv_c2s = hkdf_expand(ts, b"c2s-iv", 12)
        k_s2c = hkdf_expand(ts, b"s2c-key", 32)
        iv_s2c = hkdf_expand(ts, b"s2c-iv", 12)
        self._c2s = _DirState(k_c2s, iv_c2s)
        self._s2c = _DirState(k_s2c, iv_s2c)
        self._rekey_n = 0

    def _send_dir(self):
        return self._c2s if self.role == "client" else self._s2c

    def _recv_dir(self):
        return self._s2c if self.role == "client" else self._c2s

    @staticmethod
    def from_shared_secret(shared_secret: bytes, profile_id: int, role: str, epoch: int = 0):
        prk = hkdf_extract(TRANSPORT_LABEL, shared_secret)
        return Session(prk, profile_id, role, epoch)

    def _aad(self, rtype: int, length: int) -> bytes:
        return struct.pack(">BII B", rtype, length, self.epoch, self.profile_id)

    def seal(self, plaintext: bytes, rtype: int = TYPE_APP_DATA) -> bytes:
        d = self._send_dir()
        length = len(plaintext) + 16
        aad = self._aad(rtype, length)
        ct = d._aead.encrypt(d._nonce(), plaintext, aad)
        d.seq += 1
        return struct.pack(">BI", rtype, length) + ct

    def open(self, record: bytes) -> Tuple[int, bytes]:
        rtype, length = struct.unpack(">BI", record[:5])
        ct = record[5:5 + length]
        d = self._recv_dir()
        aad = self._aad(rtype, length)
        pt = d._aead.decrypt(d._nonce(), ct, aad)   # tag xato → InvalidTag (fatal, N15)
        d.seq += 1
        return rtype, pt

    def rekey(self):
        """Ikkala yo'nalishni rekey qiladi (forward secrecy)."""
        self._rekey_n += 1
        self._c2s.rekey(self._rekey_n)
        self._s2c.rekey(self._rekey_n)
