"""
AETHER-Q v5.1 — DoS himoyasi: stateless PoW cookie (Kuchaytirish).

Muammo (spec §9.4): ba'zi profillar (ayniqsa 0x06 ZK-verify, 0x07 threshold,
handshake KEM keygen) verifikatorda QIMMAT, lekin hujumchi uchun ARZON yaratiladi.
Hujumchi ClientHello selini yuborib serverni tiz cho'ktiradi (asimmetrik DoS).

Yechim: **stateless client-puzzle** (TLS HelloRetryRequest cookie + hashcash PoW):
  1. Klient ClientHello yuboradi.
  2. Server (yuk ostida) HAR QANDAY holat AJRATMASDAN javob beradi:
     HelloRetryRequest{cookie, difficulty}. cookie = MAC(server_secret, H(CH) ‖ ts)
     — server hech narsa saqlamaydi (SYN-cookie uslubi).
  3. Klient PoW yechadi: nonce topadiki, H(cookie ‖ nonce) da ≥D nol bit bo'lsin.
     (ARZON-forge ⇒ endi klient uchun QIMMAT — asimmetriya teskari aylandi.)
  4. Server cookie MAC (arzon) + PoW (bitta hash — arzon) ni tekshiradi; faqat SHUNDAN
     KEYIN qimmat yo'lni (ephemeral KEM, ZK verify) bajaradi.

cookie stateless: server per-klient holat saqlamaydi ⇒ xotira-DoS yo'q.
cookie ClientHello'ga bog'langan ⇒ boshqa CH bilan qayta ishlatib bo'lmaydi.
cookie TTL bilan ⇒ replay oynasi cheklangan.
"""

import os
import time
from typing import Optional, Tuple
from .kdf import sha3_256, kmac256, ct_eq

POW_LABEL = b"AETHER-Q-v5.1-POW"
COOKIE_CUSTOM = b"AETHER-Q-v5.1-COOKIE"
_COOKIE_LEN = 8 + 16          # ts(8) ‖ mac(16)


def leading_zero_bits(d: bytes) -> int:
    """Digest boshidagi nol bitlar soni."""
    n = 0
    for byte in d:
        if byte == 0:
            n += 8
            continue
        for k in range(7, -1, -1):
            if (byte >> k) & 1:
                return n + (7 - k)
    return n


class PuzzleAuthority:
    """Server tomoni: stateless cookie chiqaradi va tekshiradi."""

    def __init__(self, difficulty: int = 16, ttl_seconds: int = 30, secret: bytes = None):
        self._secret = secret or os.urandom(32)     # faqat serverda; hech qayerga chiqmaydi
        self.difficulty = difficulty
        self.ttl = ttl_seconds

    def issue(self, client_hello: bytes, now: Optional[int] = None) -> bytes:
        """Stateless cookie: ts ‖ MAC(secret, H(CH) ‖ ts ‖ difficulty)."""
        now = int(now if now is not None else time.time())
        ts = now.to_bytes(8, "big")
        mac = kmac256(self._secret, sha3_256(client_hello) + ts + bytes([self.difficulty]),
                      16, custom=COOKIE_CUSTOM)
        return ts + mac

    def verify_cookie(self, client_hello: bytes, cookie: bytes, now: Optional[int] = None) -> bool:
        """Cookie serverniki, muddati o'tmagan va shu CH'ga bog'langanmi (arzon)."""
        now = int(now if now is not None else time.time())
        if len(cookie) != _COOKIE_LEN:
            return False
        ts, mac = cookie[:8], cookie[8:]
        issued = int.from_bytes(ts, "big")
        if now < issued or now - issued > self.ttl:      # muddat oynasi
            return False
        expected = kmac256(self._secret, sha3_256(client_hello) + ts + bytes([self.difficulty]),
                           16, custom=COOKIE_CUSTOM)
        return ct_eq(expected, mac)

    def gate(self, client_hello: bytes, cookie: bytes = None, pow_nonce: int = None,
             now: Optional[int] = None) -> Tuple[str, Optional[bytes]]:
        """
        Kirishni tekshiradi:
          ('retry', cookie)  — puzzle yechish kerak (server holat ajratmaydi)
          ('reject', reason) — cookie/PoW yaroqsiz
          ('ok', None)       — qimmat yo'lni bajarish mumkin
        """
        if cookie is None:
            return ("retry", self.issue(client_hello, now))
        if not self.verify_cookie(client_hello, cookie, now):
            return ("reject", b"bad_or_expired_cookie")
        if pow_nonce is None or not verify_pow(cookie, pow_nonce, self.difficulty):
            return ("reject", b"bad_pow")
        return ("ok", None)


def solve_pow(cookie: bytes, difficulty: int, max_iters: int = 1 << 30) -> int:
    """Klient ishi: H(POW ‖ cookie ‖ nonce) da ≥difficulty nol bit beruvchi nonce."""
    nonce = 0
    while nonce < max_iters:
        d = sha3_256(POW_LABEL + cookie + nonce.to_bytes(8, "big"))
        if leading_zero_bits(d) >= difficulty:
            return nonce
        nonce += 1
    raise RuntimeError("PoW yechilmadi (max_iters)")


def verify_pow(cookie: bytes, nonce: int, difficulty: int) -> bool:
    """Server ishi: bitta hash (ARZON)."""
    d = sha3_256(POW_LABEL + cookie + nonce.to_bytes(8, "big"))
    return leading_zero_bits(d) >= difficulty
