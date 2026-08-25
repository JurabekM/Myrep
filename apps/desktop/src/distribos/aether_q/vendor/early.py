"""
AETHER-Q v5.1 — 0-RTT (early data): birinchi xabarni handshake bilan BIRGA yuborish.

Session resumption (§8.3) klientga RMS beradi. 0-RTT undan **early data kaliti**
chiqarib, ClientHello bilan birga shifrlangan ma'lumot yuborishga imkon beradi —
server javobini kutmasdan. Bu 1 RTT tejaydi (sezilarli latency yutug'i).

    K_early = HKDF-Expand(HKDF-Extract(RMS, ""), "AETHER-Q-v5.1 early" ‖ H(CH), 32)
    early   = ChaCha20-Poly1305(K_early, nonce, data, aad = H(CH))

⚠⚠ REPLAY OGOHLANTIRISHI (eng muhim cheklov) ⚠⚠
0-RTT ma'lumot **ephemeral kalit almashinuvidan OLDIN** shifrlanadi, ya'ni u faqat
RMS ga tayanadi. Hujumchi butun ClientHello+early paketini **yozib olib, qayta
yuborishi** mumkin — server uni ikkinchi marta qabul qilib, amalni TAKRORLASHI mumkin.

Shu bois:
  • **N17:** 0-RTT ma'lumot faqat **IDEMPOTENT** amallar uchun ishlatilishi SHART
    (GET, o'qish, holat so'rovi). To'lov, buyurtma, o'zgartirish — **TAQIQLANADI**.
  • **N18:** 0-RTT da **forward secrecy YO'Q** (RMS'ga tayanadi). Handshake
    tugagach, keyingi ma'lumot to'liq FS-himoyalangan kanalga o'tadi.
  • Server `EarlyDataGuard` bilan takroriy (CH-hash, vaqt oynasi) ni rad etadi —
    bu replay'ni **kamaytiradi**, lekin taqsimlangan serverlarda to'liq yo'q qilmaydi.

Bu TLS 1.3 0-RTT bilan aynan bir xil kelishuv (RFC 8446 §8, "Replay Attacks").
"""

import os
import time
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from .kdf import sha3_256, hkdf_extract, hkdf_expand

EARLY_LABEL = b"AETHER-Q-v5.1 early"
NONCE_LEN = 12


def derive_early_key(rms: bytes, ch_bytes: bytes) -> bytes:
    """Early data kaliti — RMS va ClientHello'ga bog'langan."""
    prk = hkdf_extract(rms, EARLY_LABEL)
    return hkdf_expand(prk, EARLY_LABEL + sha3_256(ch_bytes), 32)


def seal_early(rms: bytes, ch_bytes: bytes, data: bytes) -> bytes:
    """Klient: early data'ni shifrlaydi (ClientHello bilan birga yuboriladi)."""
    key = derive_early_key(rms, ch_bytes)
    nonce = os.urandom(NONCE_LEN)
    return nonce + ChaCha20Poly1305(key).encrypt(nonce, data, sha3_256(ch_bytes))


def open_early(rms: bytes, ch_bytes: bytes, blob: bytes) -> Optional[bytes]:
    """Server: early data'ni ochadi. Yaroqsiz → None (handshake davom etadi)."""
    if len(blob) < NONCE_LEN + 16:
        return None
    key = derive_early_key(rms, ch_bytes)
    try:
        return ChaCha20Poly1305(key).decrypt(blob[:NONCE_LEN], blob[NONCE_LEN:],
                                             sha3_256(ch_bytes))
    except Exception:
        return None


class EarlyDataGuard:
    """
    Anti-replay qorovuli (server tomoni): har ClientHello-hash bir marta qabul.

    Vaqt oynasi (`window`) davomida ko'rilgan hash'larni saqlaydi. Oyna tashqarisidagi
    takror — ticket TTL bilan cheklanadi. ⚠ Bu bitta jarayon uchun; taqsimlangan
    klasterda umumiy do'kon (Redis va h.k.) kerak.
    """

    __slots__ = ("_seen", "window", "_max")

    def __init__(self, window_seconds: int = 60, max_entries: int = 100_000):
        self._seen = {}                    # ch_hash → ko'rilgan vaqt
        self.window = window_seconds
        self._max = max_entries

    def check_and_insert(self, ch_bytes: bytes, now: float = None) -> bool:
        """Yangi bo'lsa True (qabul), takror bo'lsa False (RAD — replay)."""
        now = now if now is not None else time.time()
        h = sha3_256(ch_bytes)
        # eskirganlarni tozalash (oddiy amortizatsiya)
        if len(self._seen) > self._max:
            cutoff = now - self.window
            self._seen = {k: t for k, t in self._seen.items() if t > cutoff}
        prev = self._seen.get(h)
        if prev is not None and now - prev <= self.window:
            return False                   # REPLAY aniqlandi
        self._seen[h] = now
        return True

    def __len__(self):
        return len(self._seen)
