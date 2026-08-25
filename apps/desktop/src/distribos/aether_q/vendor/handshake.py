"""
AETHER-Q v5.1 — Handshake State Machine + Negotiation (Bosqich 6).

§8 transport `Session` (AEAD record layer) `SharedSecret`/PRK talab qiladi. Bu modul
uni ISHONCHLI kelishuv orqali o'rnatadi:

  - VERSIYA va PROFIL kelishuvi (client offered ∩ server supported, preferens tartibi)
  - DOWNGRADE himoyasi — Finished MAC to'liq transcript ustidan (TLS 1.3 uslubi):
    MITM ClientHello'dagi kuchli profillarni olib tashlasa, client va server
    transcript'lari farq qiladi → Finished mos kelmaydi → uzilish (S5).
  - Forward secrecy — server har handshake'da EPHEMERAL ML-KEM kalit juftini yaratadi.
  - Aniq STATE MACHINE (holatlar, o'tishlar) va ALERT kodlari.

Xabar oqimi (2-RTT):
    Client                                  Server
    ── ClientHello ──────────────────────▶  (versiya/profil kelishuv, ephemeral ek)
    ◀────────────────────── ServerHello ──
    ── ClientKeyExchange + ClientFinished ▶ (decaps, CF tekshir)
    ◀────────────────────── ServerFinished ─
    [CONNECTED — master → transport.Session]
"""

import os
import struct
from enum import IntEnum
from typing import List, Optional, Tuple

from .hybrid import kem_for, SUPPORTED as KEM_PROFILES
from .sig import MLDSA65
from .kdf import sha3_256, hkdf_extract, hkdf_expand, kmac256, ct_eq
from .transport import Session
from . import dos

AQ_VERSION = 0x0501                         # v5.1
SUPPORTED_VERSIONS_DEFAULT = [0x0501]
# Profil preferens tartibi (kuchli → zaif). Server shu tartibda tanlaydi.
# FAQAT haqiqatan KEM implementatsiyasiga ega profillar (hybrid.SUPPORTED):
#   0x01 = X25519+ML-KEM-768 (hybrid, afzal), 0x03 = ML-KEM-768 standalone.
# 0x02 (PARANOID) HQC-192 yo'qligi sababli kiritilmagan; 0x06/0x07/0x08 —
# alohida modullardagi maxsus profillar (handshake KEM'i emas).
PROFILE_PREFERENCE = [0x01, 0x03]


class MsgType(IntEnum):
    CLIENT_HELLO = 0x01
    SERVER_HELLO = 0x02
    CLIENT_KEX = 0x03
    FINISHED = 0x04
    HELLO_RETRY = 0x06          # DoS: stateless PoW cookie so'rovi
    CLIENT_HELLO_RETRY = 0x07   # klient: cookie+PoW bilan qayta CH
    NEW_SESSION_TICKET = 0x08   # server: keyingi ulanish uchun resumption ticket
    CLIENT_AUTH = 0x09          # klient: ML-DSA sertifikat + imzo (mutual auth)
    EARLY_DATA = 0x0A           # klient: 0-RTT ma'lumot (CH bilan birga)
    ALERT = 0x15


class Alert(IntEnum):
    CLOSE_NOTIFY = 0x00
    NO_COMMON_VERSION = 0x28
    NO_COMMON_PROFILE = 0x29
    BAD_FINISHED = 0x2A                      # downgrade YOKI tamper aniqlandi
    DECAPS_FAILED = 0x2B
    UNEXPECTED_MESSAGE = 0x2C
    PROFILE_NOT_OFFERED = 0x2D
    DOS_REJECT = 0x2E                        # cookie/PoW yaroqsiz
    BAD_SIGNATURE = 0x2F                     # server ML-DSA imzosi yaroqsiz (auth)
    BAD_TICKET = 0x30                        # resumption ticket yaroqsiz/muddati o'tgan
    CLIENT_AUTH_REQUIRED = 0x31              # server klient auth talab qildi, klientda identity yo'q
    BAD_CLIENT_AUTH = 0x32                   # klient imzosi yaroqsiz yoki ruxsat etilmagan


class TicketAuthority:
    """
    Session ticket chiqaruvchi (server tomoni) — **stateless**, TLS 1.3 uslubida.

    Ticket = nonce ‖ AEAD(ticket_key, nonce, RMS ‖ profile ‖ issued_at; AAD).
    Server hech qanday sessiya holatini saqlamaydi — barcha ma'lumot ticket ichida
    shifrlangan. `ticket_key` faqat serverda; uni bilmagan hech kim ticket yasay olmaydi.

    Resumption'da ML-DSA imzo O'TKAZIB YUBORILADI: server autentifikatsiyasi RMS
    (resumption master secret) bilimidan kelib chiqadi — faqat haqiqiy server ticket'ni
    ochib RMS ni oladi, shu bois Finished MAC'i faqat unda to'g'ri chiqadi.

    ⚠ KONTEKST BOG'LANISHI (AQ-05): bitta `ticket_key` bir nechta ilova
      kontekstiga (tenant, virtual host, ALPN) xizmat qilsa, kontekstlararo
      ticket ko'chirilishi mumkin edi. Endi AAD ga ilova bergan `context`
      biriktiriladi — boshqa kontekstda ochilganda AEAD teg mos kelmaydi va
      ticket rad etiladi (to'liq handshake'ga qaytiladi). `context=b""` —
      eski xatti-harakat (bitta kontekst).
    """

    __slots__ = ("_key", "ttl")
    _AAD = b"AQTKT"

    def __init__(self, key: bytes = None, ttl_seconds: int = 3600):
        self._key = key or os.urandom(32)
        self.ttl = ttl_seconds

    def _aad(self, context: bytes) -> bytes:
        # Kontekst uzunligini ham qamraymiz: (b"x", b"") va (b"", b"x") kabi
        # ajratuvchi cheklarni chalkashmasligi uchun.
        return self._AAD + len(context).to_bytes(2, "big") + context

    def issue(self, rms: bytes, profile: int, now: int = None,
              context: bytes = b"") -> bytes:
        import time as _t
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        now = int(now if now is not None else _t.time())
        nonce = os.urandom(12)
        pt = rms + bytes([profile]) + now.to_bytes(8, "big")
        ct = ChaCha20Poly1305(self._key).encrypt(nonce, pt, self._aad(context))
        return nonce + ct

    def open(self, ticket: bytes, now: int = None, context: bytes = b""):
        """Qaytaradi: (rms, profile) yoki None (yaroqsiz/muddati o'tgan/boshqa
        kontekst)."""
        import time as _t
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        if len(ticket) < 13:
            return None
        now = int(now if now is not None else _t.time())
        try:
            pt = ChaCha20Poly1305(self._key).decrypt(
                ticket[:12], ticket[12:], self._aad(context))
        except Exception:
            return None                                  # soxta / boshqa server / boshqa kontekst
        if len(pt) != 32 + 1 + 8:
            return None
        rms, profile = pt[:32], pt[32]
        issued = int.from_bytes(pt[33:41], "big")
        if now < issued or now - issued > self.ttl:      # muddat oynasi
            return None
        return rms, profile


class HState(IntEnum):
    START = 0
    WAIT_SERVER_HELLO = 1
    WAIT_CLIENT_KEX = 2
    WAIT_SERVER_FINISHED = 3
    CONNECTED = 4
    CLOSED = 5


class AetherAlert(Exception):
    def __init__(self, code: Alert):
        super().__init__(f"AETHER alert: {code.name} (0x{int(code):02x})")
        self.code = code


# ------------------------------------------------------------------ wire

def _msg(mtype: MsgType, body: bytes) -> bytes:
    assert len(body) < (1 << 24)
    return struct.pack(">BH", int(mtype), AQ_VERSION) + len(body).to_bytes(3, "big") + body


class MalformedMessage(ValueError):
    """
    Buzilgan/qisqa xabar. `ValueError` merosxo'ri — mavjud `except ValueError`
    yo'llari o'zgarmaydi, lekin xato endi ANIQ nomlanadi.

    NEGA KERAK: fuzzing (3.5 mln holat) ko'rsatdiki, parserlar uzunlik
    maydonlariga ISHONIB indekslardi — hujumchi yuborgan qisqa yoki yolg'on
    uzunlikli xabar `IndexError`/`struct.error` chiqarardi. Bu xavfsiz edi
    (jarayon yiqilmasdi, ma'lumot oqmasdi), lekin xato yo'li nozik emas:
    protokol darajasidagi rad etish tasodifiy Python istisnosidan farq qilishi
    kerak, aks holda yuqori qatlam ularni ajrata olmaydi.
    """


def _need(buf: bytes, n: int, what: str):
    """`buf` da kamida `n` bayt borligini talab qiladi."""
    if len(buf) < n:
        raise MalformedMessage(f"{what}: {n} bayt kerak, {len(buf)} bor")


def _parse_header(data: bytes) -> Tuple[MsgType, int, bytes]:
    _need(data, 6, "xabar sarlavhasi")
    try:
        mtype = MsgType(data[0])
    except ValueError:
        raise MalformedMessage(f"noma'lum xabar turi: 0x{data[0]:02x}")
    ver = struct.unpack(">H", data[1:3])[0]
    length = int.from_bytes(data[3:6], "big")
    body = data[6:6 + length]
    if len(body) != length:
        raise MalformedMessage(f"tana qisqa: {length} e'lon qilingan, {len(body)} bor")
    return mtype, ver, body


def _frame_len(data: bytes) -> int:
    """Header'dan to'liq frame uzunligini (6 + tana) qaytaradi."""
    _need(data, 6, "xabar sarlavhasi")
    return 6 + int.from_bytes(data[3:6], "big")


def _reject_trailing(data: bytes, what: str):
    """`data` AYNAN bitta frame bo'lishini talab qiladi (F-02 / S3.1).

    `_parse_header` faqat tana QISQA emasligini tekshiradi — frame'dan keyin
    ortiqcha bayt bo'lsa uni JIMGINA e'tiborsiz qoldiradi. O'sha ortiqcha
    baytlar keyin transcript'ga qo'shilib, MITM tomonidan transcript'ni
    zaharlashga (transcript-injection) yo'l ochardi. Bu yerda ular RAD etiladi.
    """
    n = _frame_len(data)
    if len(data) != n:
        raise MalformedMessage(
            f"{what}: bitta frame kutilgan, lekin {len(data) - n} ortiqcha bayt "
            "bor (trailing-bytes / transcript-injection urinishi?)")


FLAG_WANT_TICKET = 0x01      # klient NewSessionTicket kutadi
FLAG_EARLY_DATA  = 0x02      # klient CH dan keyin 0-RTT xabar yuboradi


def enc_client_hello(versions: List[int], profiles: List[int], client_random: bytes,
                     ticket: bytes = b"", want_ticket: bool = False,
                     early: bool = False) -> bytes:
    b = bytes([len(versions)]) + b"".join(struct.pack(">H", v) for v in versions)
    b += bytes([len(profiles)]) + bytes(profiles)
    b += client_random
    # flags: klient ticket kutayotganini bildiradi — server faqat shunda NST yuboradi
    # (aks holda klient uni transport record deb o'qib xato qilardi).
    b += bytes((FLAG_WANT_TICKET if want_ticket else 0)
               | (FLAG_EARLY_DATA if early else 0) for _ in [0])
    b += struct.pack(">H", len(ticket)) + ticket      # session resumption (bo'sh = to'liq HS)
    return _msg(MsgType.CLIENT_HELLO, b)


def dec_client_hello(body: bytes):
    """Qaytaradi: (versions, profiles, client_random, ticket, want_ticket, early)."""
    _need(body, 1, "ClientHello")
    nv = body[0]; off = 1
    _need(body, off + 2 * nv, "versiyalar ro'yxati")
    versions = [struct.unpack(">H", body[off + 2 * i:off + 2 * i + 2])[0] for i in range(nv)]
    off += 2 * nv
    _need(body, off + 1, "profillar soni")
    npf = body[off]; off += 1
    _need(body, off + npf, "profillar ro'yxati")
    profiles = list(body[off:off + npf]); off += npf
    _need(body, off + 32, "client_random")
    client_random = body[off:off + 32]; off += 32
    ticket, want_ticket, early = b"", False, False
    if off < len(body):                               # flags + ticket (resumption)
        want_ticket = bool(body[off] & FLAG_WANT_TICKET)
        early = bool(body[off] & FLAG_EARLY_DATA); off += 1
        if off + 2 <= len(body):
            tlen = struct.unpack(">H", body[off:off + 2])[0]
            _need(body, off + 2 + tlen, "ticket")
            ticket = body[off + 2:off + 2 + tlen]
    return versions, profiles, client_random, ticket, want_ticket, early


SH_FLAG_CLIENT_AUTH = 0x01   # server klient autentifikatsiyasini TALAB qiladi


def _sh_core(version: int, profile: int, server_random: bytes, ek: bytes,
             flags: int = 0) -> bytes:
    """
    SH ning IMZOLANADIGAN yadrosi (imzo maydonisiz) — ikki tomon bir xil hisoblaydi.
    `flags` shu yadro ichida → MITM klient-auth talabini o'chira olmaydi (imzo buziladi).
    """
    return (struct.pack(">HB", version, profile) + server_random
            + struct.pack(">H", len(ek)) + ek + bytes([flags]))


def enc_server_hello(version: int, profile: int, server_random: bytes, ek: bytes,
                     sig: bytes = b"", flags: int = 0) -> bytes:
    b = _sh_core(version, profile, server_random, ek, flags) + struct.pack(">H", len(sig)) + sig
    return _msg(MsgType.SERVER_HELLO, b)


def dec_server_hello(body: bytes):
    """Qaytaradi: (version, profile, server_random, ek, sig, flags)."""
    _need(body, 37, "ServerHello sarlavhasi")
    version, profile = struct.unpack(">HB", body[:3])
    server_random = body[3:35]
    ek_len = struct.unpack(">H", body[35:37])[0]
    off = 37 + ek_len
    _need(body, off + 1, "ek va flags")
    ek = body[37:off]
    flags = body[off]; off += 1
    _need(body, off + 2, "imzo uzunligi")
    sig_len = struct.unpack(">H", body[off:off + 2])[0]
    _need(body, off + 2 + sig_len, "imzo")
    sig = body[off + 2:off + 2 + sig_len]
    return version, profile, server_random, ek, sig, flags


def enc_client_auth(pk: bytes, sig: bytes) -> bytes:
    return _msg(MsgType.CLIENT_AUTH,
                struct.pack(">H", len(pk)) + pk + struct.pack(">H", len(sig)) + sig)


def dec_client_auth(body: bytes):
    pk_len = struct.unpack(">H", body[:2])[0]
    pk = body[2:2 + pk_len]
    off = 2 + pk_len
    sig_len = struct.unpack(">H", body[off:off + 2])[0]
    return pk, body[off + 2:off + 2 + sig_len]


def enc_client_kex(ct: bytes) -> bytes:
    return _msg(MsgType.CLIENT_KEX, struct.pack(">H", len(ct)) + ct)


def dec_client_kex(body: bytes) -> bytes:
    ct_len = struct.unpack(">H", body[:2])[0]
    return body[2:2 + ct_len]


def enc_finished(mac: bytes) -> bytes:
    return _msg(MsgType.FINISHED, mac)


def enc_hello_retry(cookie: bytes, difficulty: int) -> bytes:
    return _msg(MsgType.HELLO_RETRY, bytes([difficulty, len(cookie)]) + cookie)


def dec_hello_retry(body: bytes):
    difficulty = body[0]
    clen = body[1]
    cookie = body[2:2 + clen]
    return cookie, difficulty


def enc_client_hello_retry(cookie: bytes, pow_nonce: int, ch_bytes: bytes) -> bytes:
    b = bytes([len(cookie)]) + cookie + pow_nonce.to_bytes(8, "big")
    b += len(ch_bytes).to_bytes(3, "big") + ch_bytes
    return _msg(MsgType.CLIENT_HELLO_RETRY, b)


def dec_client_hello_retry(body: bytes):
    clen = body[0]; off = 1
    cookie = body[off:off + clen]; off += clen
    nonce = int.from_bytes(body[off:off + 8], "big"); off += 8
    ch_len = int.from_bytes(body[off:off + 3], "big"); off += 3
    ch_bytes = body[off:off + ch_len]
    return cookie, nonce, ch_bytes


def enc_alert(code: Alert) -> bytes:
    return _msg(MsgType.ALERT, bytes([0x02, int(code)]))    # level=fatal


# ------------------------------------------------------------- key schedule

def enc_early_data(blob: bytes) -> bytes:
    return _msg(MsgType.EARLY_DATA, blob)


def enc_new_session_ticket(ticket: bytes, ttl: int) -> bytes:
    return _msg(MsgType.NEW_SESSION_TICKET, struct.pack(">IH", ttl, len(ticket)) + ticket)


def dec_new_session_ticket(body: bytes):
    ttl, tlen = struct.unpack(">IH", body[:6])
    return body[6:6 + tlen], ttl


def server_id_hash(server_pub: bytes) -> bytes:
    """Server identity'ning kalit jadvalidagi ixcham ko'rinishi."""
    return sha3_256(b"AETHER-Q-v5.1-SRV-ID" + server_pub) if server_pub else b""


def _derive_hs(ss: bytes, rms: bytes = b"", server_id: bytes = b"") -> bytes:
    """
    Handshake secret. Resumption'da RMS **salt** sifatida kiritiladi → faqat RMS ni
    biladigan tomon (haqiqiy server + o'sha klient) bir xil HS ga keladi. Bu imzosiz
    autentifikatsiyani ta'minlaydi (TLS 1.3 PSK+DHE bilan bir xil g'oya).

    ⚠ `server_id` RMS ni QAYSI server identity'siga bog'laydi.

    NEGA KERAK — F-01 (AI audit P1 sessiyasida topilgan va ekspluatatsiya
    qilingan): ticket ichida faqat `RMS ‖ profile ‖ issued_at` bor edi, ya'ni
    server identity YO'Q. Bir xil ticket kalitiga ega ikkinchi server (klasterda
    odatiy konfiguratsiya) klient ticket'ini ochib RMS ni oladi va IMZOSIZ javob
    beradi; klient buni «ticket qabul qilindi» deb talqin qilib, pinned server
    bilan gaplashyapman deb o'ylaydi. Finished buni to'xtatmaydi — ikkinchi
    server RMS ni haqiqatan biladi va to'g'ri MAC hisoblaydi.

    Endi klient PINNED identity'ni, server esa O'Z identity'sini kiritadi:
    ular farq qilsa HS farq qiladi va Finished tekshiruvi yiqiladi.
    """
    return hkdf_extract(rms, ss + server_id)                  # handshake secret


def _derive_rms(hs: bytes, transcript: bytes) -> bytes:
    """Resumption master secret — keyingi ulanish uchun (ticket ichida saqlanadi)."""
    return hkdf_expand(hs, b"AETHER-Q-v5.1 resumption" + sha3_256(transcript), 32)


def _fin_keys(hs: bytes) -> Tuple[bytes, bytes]:
    return (hkdf_expand(hs, b"AETHER-Q-v5.1 c finished", 32),
            hkdf_expand(hs, b"AETHER-Q-v5.1 s finished", 32))


def _mac(key: bytes, transcript: bytes, tag: bytes) -> bytes:
    return kmac256(key, transcript, 32, custom=b"AETHER-Q-v5.1-" + tag)


def _master(hs: bytes, transcript: bytes) -> bytes:
    return hkdf_expand(hs, b"AETHER-Q-v5.1 master" + sha3_256(transcript), 32)


# ------------------------------------------------------------------ Client

# ── Klient PoW siyosati (AQ-L05) ──
# HelloRetry AUTENTIFIKATSIYADAN OLDIN keladi va `difficulty` baytini hujumchi
# boshqarishi mumkin. Cheklovsiz klient `2^30` iteratsiyagacha ishlab, CPU'sini
# begonaga berardi (masofaviy klient-tomon DoS). Endi qat'iy shift bor:
MAX_POW_DIFFICULTY = 20      # ~10^6 urinish (~1 s) — amaliy yuqori chegara
MAX_POW_RETRIES = 1          # bitta retry yetarli; ikkinchisi hujum belgisi


class ClientHandshake:
    def __init__(self, offered_versions=None, offered_profiles=None, server_pub=None,
                 resume=None, want_ticket=False, identity=None, early_data=None,
                 max_pow_difficulty: int = MAX_POW_DIFFICULTY,
                 max_pow_retries: int = MAX_POW_RETRIES):
        self.versions = offered_versions or list(SUPPORTED_VERSIONS_DEFAULT)
        self.profiles = offered_profiles or list(PROFILE_PREFERENCE)
        # AQ-L05: klient o'z ish byudjetini O'ZI belgilaydi, server emas.
        self.max_pow_difficulty = int(max_pow_difficulty)
        self.max_pow_retries = int(max_pow_retries)
        self._pow_retries = 0
        self.server_pub = server_pub             # pinned ML-DSA pk → None: auth tekshirilmaydi
        # resume = (ticket, rms) — oldingi sessiyadan; berilsa ML-DSA imzo O'TKAZILADI
        self._resume = resume
        self._want_ticket = want_ticket
        self._identity = identity      # (sign_pk, sign_priv) — mutual auth uchun
        self._early_data = early_data if resume else None   # 0-RTT faqat resumption'da
        self.early_sent = False
        self.resumed = False                     # haqiqatan resumption bo'ldimi
        self.new_ticket = None                   # serverdan kelgan yangi (ticket, rms)
        self.state = HState.START
        self._transcript = b""
        self._ch = b""
        self._hs = None
        self._c_fin_key = None
        self._s_fin_key = None
        self.version = None
        self.profile = None
        self.session: Optional[Session] = None

    def start(self) -> bytes:
        """ClientHello ni qaytaradi (birinchi flight)."""
        if self.state != HState.START:
            raise AetherAlert(Alert.UNEXPECTED_MESSAGE)
        ticket = self._resume[0] if self._resume else b""
        has_early = self._early_data is not None
        ch = enc_client_hello(self.versions, self.profiles, os.urandom(32), ticket,
                              want_ticket=self._want_ticket, early=has_early)
        self._ch = ch                              # DoS retry'da qayta yuborish uchun
        self._transcript += ch
        self.state = HState.WAIT_SERVER_HELLO
        if has_early:
            # 0-RTT: early data CH bilan BIRGA ketadi (server javobini kutmasdan).
            # ⚠ Replay xavfi — faqat IDEMPOTENT amallar uchun (early.py N17).
            from .early import seal_early
            self.early_sent = True
            return ch + enc_early_data(seal_early(self._resume[1], ch, self._early_data))
        return ch

    def recv(self, data: bytes) -> Optional[bytes]:
        mtype, _, body = _parse_header(data)
        if mtype == MsgType.ALERT:
            self.state = HState.CLOSED
            raise AetherAlert(Alert(body[1]))

        if self.state == HState.WAIT_SERVER_HELLO:
            # DoS: HelloRetryRequest → PoW yechib, SHU CH ni qayta yuboramiz.
            # (Transcript o'zgarmaydi — CH allaqachon transcript'da; DoS qatlami
            #  autentifikatsiyalangan transcript'dan tashqarida.)
            if mtype == MsgType.HELLO_RETRY:
                # ⚠ AQ-L05: bu xabar SERVER AUTENTIFIKATSIYASIDAN OLDIN keladi,
                # ya'ni `difficulty` ni aktiv MITM boshqarishi mumkin. Klient
                # o'z byudjetidan oshiq ishga HECH QACHON kirmaydi va bitta
                # retry bilan cheklanadi — aks holda masofaviy CPU-DoS.
                self._pow_retries += 1
                if self._pow_retries > self.max_pow_retries:
                    raise AetherAlert(Alert.DOS_REJECT)
                cookie, difficulty = dec_hello_retry(body)
                if difficulty > self.max_pow_difficulty:
                    raise AetherAlert(Alert.DOS_REJECT)
                nonce = dos.solve_pow(cookie, difficulty)
                return enc_client_hello_retry(cookie, nonce, self._ch)
            if mtype != MsgType.SERVER_HELLO:
                raise AetherAlert(Alert.UNEXPECTED_MESSAGE)
            version, profile, srv_rand, ek, sig, sh_flags = dec_server_hello(body)
            # Local downgrade sanity: tanlangan versiya/profil OFFERED bo'lishi shart
            if version not in self.versions:
                raise AetherAlert(Alert.NO_COMMON_VERSION)
            if profile not in self.profiles:
                raise AetherAlert(Alert.PROFILE_NOT_OFFERED)
            # RESUMPTION: biz ticket yuborgan va server IMZOSIZ javob bergan bo'lsa,
            # u ticket'ni qabul qilgan. Autentifikatsiya RMS bilimidan kelib chiqadi
            # (faqat haqiqiy server ticket'ni ochib RMS ni oladi) → imzo shart emas.
            resuming = bool(self._resume) and not sig
            if not resuming and self.server_pub is not None:
                # To'liq handshake: server autentifikatsiyasi ENCAPS'DAN OLDIN.
                # Imzo transcript(CH) ‖ SH-core ustidan → ek autentifikatsiyalanadi.
                core = _sh_core(version, profile, srv_rand, ek, sh_flags)
                if not MLDSA65.verify(self.server_pub, sig, sha3_256(self._transcript + core)):
                    raise AetherAlert(Alert.BAD_SIGNATURE)
            self.resumed = resuming
            self.version, self.profile = version, profile
            _reject_trailing(data, "ServerHello")        # F-02: transcript-injection'ni to'sish
            self._transcript += data
            # Encaps → ss (kelishilgan profil KEM'i bilan; resumption'da ham EPHEMERAL
            # KEM ishlatiladi → forward secrecy saqlanadi, TLS 1.3 PSK+DHE kabi)
            ct, ss = kem_for(profile).encaps(ek)
            # Resumption'da RMS ni PINNED server identity'siga bog'laymiz (F-01).
            # To'liq handshake'da bog'lash shart emas — imzo allaqachon `ek` ni
            # autentifikatsiya qilgan; u yerda `b""` qoldirish orqaga moslikni
            # ham saqlaydi (pin qilmagan klient bilan ishlaydi).
            sid = server_id_hash(self.server_pub) if resuming else b""
            self._hs = _derive_hs(ss, self._resume[1] if resuming else b"", sid)
            self._c_fin_key, self._s_fin_key = _fin_keys(self._hs)
            # ClientKeyExchange
            ckx = enc_client_kex(ct)
            self._transcript += ckx
            # MUTUAL AUTH: server talab qilsa, klient ML-DSA imzosini yuboradi.
            # Imzo transcript(CH‖SH‖CKX) ustidan → sessiyaga bog'langan, replay yo'q.
            auth = b""
            if sh_flags & SH_FLAG_CLIENT_AUTH:
                if self._identity is None:
                    raise AetherAlert(Alert.CLIENT_AUTH_REQUIRED)
                cpk, cpriv = self._identity
                auth = enc_client_auth(cpk, MLDSA65.sign(cpriv, sha3_256(self._transcript)))
                self._transcript += auth
            # ClientFinished = MAC(c_fin_key, transcript so far)
            cf = _mac(self._c_fin_key, sha3_256(self._transcript), b"CF")
            fin = enc_finished(cf)
            self._transcript += fin
            self.state = HState.WAIT_SERVER_FINISHED
            return ckx + auth + fin

        if self.state == HState.WAIT_SERVER_FINISHED:
            if mtype != MsgType.FINISHED:
                raise AetherAlert(Alert.UNEXPECTED_MESSAGE)
            expected = _mac(self._s_fin_key, sha3_256(self._transcript), b"SF")
            if not ct_eq(expected, body):
                # Downgrade YOKI server-tamper: transcript mos emas
                raise AetherAlert(Alert.BAD_FINISHED)
            _reject_trailing(data, "ServerFinished")     # F-02: transcript-injection'ni to'sish
            self._transcript += data
            master = _master(self._hs, self._transcript)
            self._rms = _derive_rms(self._hs, self._transcript)   # keyingi resumption uchun
            self.session = Session.from_shared_secret(master, self.profile, "client")
            self.state = HState.CONNECTED
            return None

        if self.state == HState.CONNECTED and mtype == MsgType.NEW_SESSION_TICKET:
            # Server keyingi ulanish uchun ticket berdi — RMS bilan birga saqlaymiz.
            ticket, ttl = dec_new_session_ticket(body)
            self.new_ticket = (ticket, self._rms)
            return None

        raise AetherAlert(Alert.UNEXPECTED_MESSAGE)


# ------------------------------------------------------------------ Server

class ServerHandshake:
    def __init__(self, supported_versions=None, supported_profiles=None,
                 puzzle_authority=None, sig_priv=None, ticket_authority=None,
                 require_client_auth=False, allowed_clients=None, early_guard=None,
                 ticket_context=b""):
        self.tickets = ticket_authority          # None → resumption o'chirilgan
        # AQ-05: ticket shu ilova kontekstiga (tenant/vhost/ALPN) qulflanadi.
        self.ticket_context = bytes(ticket_context)
        self._want_ticket = False                # klient NST kutayaptimi
        self.require_client_auth = require_client_auth
        self.allowed_clients = allowed_clients   # None → har qanday to'g'ri imzo qabul
        self.client_pk = None                    # autentifikatsiyalangan klient
        self.early_guard = early_guard           # None → 0-RTT qabul qilinmaydi
        self.early_data = None                   # qabul qilingan 0-RTT ma'lumot
        self.early_rejected = False              # replay yoki yaroqsiz
        self._rms_in = b""                       # qabul qilingan ticket'dagi RMS
        self.resumed = False
        self.versions = supported_versions or list(SUPPORTED_VERSIONS_DEFAULT)
        self.profiles = supported_profiles or list(PROFILE_PREFERENCE)
        self.puzzle = puzzle_authority           # DoS: None → PoW talab qilinmaydi
        self.sig_priv = sig_priv                 # None → server auth yo'q (backward compat)
        self._own_pub_cache = None               # server_id_hash uchun (F-01)
        self.state = HState.START
        self._transcript = b""
        self._dk = None
        self._hs = None
        self._c_fin_key = None
        self._s_fin_key = None
        self.version = None
        self.profile = None
        self.session: Optional[Session] = None

    def _negotiate(self, client_versions, client_profiles):
        common_v = [v for v in client_versions if v in self.versions]
        if not common_v:
            raise AetherAlert(Alert.NO_COMMON_VERSION)
        version = max(common_v)
        # Server preferens tartibida birinchi umumiy profil.
        # MUHIM: faqat HAQIQATAN KEM implementatsiyasiga ega profil tanlanadi —
        # aks holda server o'zi bajara olmaydigan profilga majburlanishi mumkin.
        profile = None
        for p in self.profiles:                    # server preferens tartibi
            if p in client_profiles and p in KEM_PROFILES:
                profile = p
                break
        if profile is None:
            raise AetherAlert(Alert.NO_COMMON_PROFILE)
        return version, profile

    def _process_client_hello(self, ch_data: bytes, early_blob: bytes = b"") -> bytes:
        """CH ni qayta ishlaydi: negotiation + ephemeral KEM + ServerHello."""
        mtype, _, body = _parse_header(ch_data)
        if mtype != MsgType.CLIENT_HELLO:
            raise AetherAlert(Alert.UNEXPECTED_MESSAGE)
        versions, profiles, _cr, ticket, want_ticket, self._early_flag = dec_client_hello(body)
        self._want_ticket = want_ticket
        self.version, self.profile = self._negotiate(versions, profiles)
        # RESUMPTION: yaroqli ticket bo'lsa, RMS ni olamiz va ML-DSA IMZONI
        # O'TKAZIB YUBORAMIZ (handshake vaqtining ~40% i shu imzoga ketardi).
        if ticket and self.tickets is not None:
            opened = self.tickets.open(ticket, context=self.ticket_context)
            if opened is not None and opened[1] == self.profile:
                self._rms_in, self.resumed = opened[0], True
        # 0-RTT: resumption muvaffaqiyatli bo'lsa va klient early yuborgan bo'lsa
        if early_blob and self.require_client_auth:
            # S3.3c: mutual-auth serverda 0-RTT ma'lumot klient AUTH'idan OLDIN
            # keladi — uni autentifikatsiyalangan klientga bog'lab bo'lmaydi.
            # Shu bois QABUL QILINMAYDI (ilova uni auth qilingan klient vakolati
            # deb ishlatib yubormasin). TLS 1.3 ham 0-RTT + klient-sertifikatni
            # birga tavsiya etmaydi.
            self.early_rejected = True
        elif early_blob and self.resumed and self.early_guard is not None:
            from .early import open_early
            if not self.early_guard.check_and_insert(ch_data):
                self.early_rejected = True          # REPLAY aniqlandi → rad
            else:
                data = open_early(self._rms_in, ch_data, early_blob)
                if data is None:
                    self.early_rejected = True
                else:
                    self.early_data = data
        elif early_blob:
            self.early_rejected = True              # resumption yo'q → 0-RTT mumkin emas
        self._transcript += ch_data                 # server RECEIVED CH (MITM tegsa farq qiladi)
        # Profil-aware ephemeral KEM (0x01 hybrid / 0x03 minimal) — forward secrecy
        # (resumption'da ham ephemeral: PSK+DHE rejimi, o'tgan sessiyalar himoyalangan)
        ek, self._dk = kem_for(self.profile).keygen()
        sh_flags = SH_FLAG_CLIENT_AUTH if self.require_client_auth else 0
        core = _sh_core(self.version, self.profile, os.urandom(32), ek, sh_flags)
        # To'liq handshake'da server autentifikatsiyasi: transcript(CH) ‖ SH-core ustidan
        # ML-DSA imzo → ephemeral ek autentifikatsiyalanadi, aktiv MITM uni almashtira olmaydi.
        sig = (MLDSA65.sign(self.sig_priv, sha3_256(self._transcript + core))
               if (self.sig_priv and not self.resumed) else b"")
        sh = _msg(MsgType.SERVER_HELLO, core + struct.pack(">H", len(sig)) + sig)
        self._transcript += sh
        self.state = HState.WAIT_CLIENT_KEX
        return sh

    def _own_pub(self) -> bytes:
        """Serverning o'z ML-DSA public key'i (F-01 identity bog'lanishi uchun)."""
        if self._own_pub_cache is None:
            try:
                self._own_pub_cache = (
                    self.sig_priv.public_key().public_bytes_raw()
                    if self.sig_priv is not None else b"")
            except Exception:
                self._own_pub_cache = b""      # imzo kaliti yo'q → bog'lash ham yo'q
        return self._own_pub_cache

    def recv(self, data: bytes) -> Optional[bytes]:
        mtype, _, body = _parse_header(data)
        if mtype == MsgType.ALERT:
            self.state = HState.CLOSED
            raise AetherAlert(Alert(body[1]))

        if self.state == HState.START:
            # DoS: PoW talab qilinsa, birinchi ClientHello'ga HOLAT AJRATMASDAN
            # HelloRetryRequest (stateless cookie) qaytaramiz. Qimmat ish (ephemeral
            # KEM, negotiation) faqat cookie+PoW tasdiqlangach bajariladi.
            if self.puzzle is not None:
                if mtype == MsgType.CLIENT_HELLO:
                    cookie = self.puzzle.issue(data)           # stateless
                    return enc_hello_retry(cookie, self.puzzle.difficulty)
                if mtype == MsgType.CLIENT_HELLO_RETRY:
                    cookie, nonce, ch = dec_client_hello_retry(body)
                    status, _ = self.puzzle.gate(ch, cookie, nonce)
                    if status != "ok":
                        raise AetherAlert(Alert.DOS_REJECT)
                    return self._process_client_hello(ch)      # endi qimmat yo'l
                raise AetherAlert(Alert.UNEXPECTED_MESSAGE)
            if mtype != MsgType.CLIENT_HELLO:
                raise AetherAlert(Alert.UNEXPECTED_MESSAGE)
            # CH dan keyin FAQAT bitta 0-RTT (EARLY_DATA) xabar kelishi mumkin.
            # S3.1: CH'dan keyingi boshqa har qanday bayt (yoki EARLY_DATA'dan
            # keyingi qoldiq) JIMGINA yutilmasdan RAD etiladi.
            ch_len = _frame_len(data)
            ch_only, rest = data[:ch_len], data[ch_len:]
            early = b""
            if rest:
                _reject_trailing(rest, "ClientHello'dan keyingi ma'lumot")
                emt, _, ebody = _parse_header(rest)
                if emt != MsgType.EARLY_DATA:
                    raise AetherAlert(Alert.UNEXPECTED_MESSAGE)
                early = ebody
            return self._process_client_hello(ch_only, early)

        if self.state == HState.WAIT_CLIENT_KEX:
            # Client flight: ClientKeyExchange || ClientFinished (bir data'da)
            if mtype != MsgType.CLIENT_KEX:
                raise AetherAlert(Alert.UNEXPECTED_MESSAGE)
            ckx_len = 6 + int.from_bytes(data[3:6], "big")
            ckx_data, rest = data[:ckx_len], data[ckx_len:]
            ct = dec_client_kex(body)
            ss = kem_for(self.profile).decaps(self._dk, ct)
            # Resumption'da RMS salt sifatida — faqat ticket'ni ochgan server bilan
            # o'sha RMS ni saqlagan klient bir xil HS ga keladi (imzosiz auth).
            # Server O'Z identity'sini kiritadi. Boshqa identity'li server
            # (hatto ticket kalitiga ega bo'lsa ham) klient kutgan HS ga
            # kela olmaydi → Finished yiqiladi (F-01 himoyasi).
            sid = server_id_hash(self._own_pub()) if self.resumed else b""
            self._hs = _derive_hs(ss, self._rms_in if self.resumed else b"", sid)
            self._c_fin_key, self._s_fin_key = _fin_keys(self._hs)
            self._transcript += ckx_data
            # MUTUAL AUTH: talab qilingan bo'lsa, ClientAuth CF dan OLDIN keladi
            if self.require_client_auth:
                if not rest or _parse_header(rest)[0] != MsgType.CLIENT_AUTH:
                    raise AetherAlert(Alert.CLIENT_AUTH_REQUIRED)
                auth_len = 6 + int.from_bytes(rest[3:6], "big")
                auth_data, rest = rest[:auth_len], rest[auth_len:]
                cpk, csig = dec_client_auth(_parse_header(auth_data)[2])
                # Imzo transcript(CH‖SH‖CKX) ustidan → sessiyaga bog'langan (replay yo'q)
                if not MLDSA65.verify(cpk, csig, sha3_256(self._transcript)):
                    raise AetherAlert(Alert.BAD_CLIENT_AUTH)
                if self.allowed_clients is not None and cpk not in self.allowed_clients:
                    raise AetherAlert(Alert.BAD_CLIENT_AUTH)
                self.client_pk = cpk
                self._transcript += auth_data
            fin_data = rest
            # S3.1: ClientFinished — flight'ning OXIRGI xabari; undan keyin
            # hech narsa bo'lmasligi kerak. Ortiqcha bayt transcript'ga
            # qo'shilishidan OLDIN rad etiladi.
            _reject_trailing(fin_data, "ClientFinished")
            # ClientFinished tekshirish (transcript CKX/Auth gacha)
            fmtype, _, cf_body = _parse_header(fin_data)
            if fmtype != MsgType.FINISHED:
                raise AetherAlert(Alert.UNEXPECTED_MESSAGE)
            expected_cf = _mac(self._c_fin_key, sha3_256(self._transcript), b"CF")
            if not ct_eq(expected_cf, cf_body):
                # DOWNGRADE aniqlandi: server-transcript ≠ client-transcript
                raise AetherAlert(Alert.BAD_FINISHED)
            self._transcript += fin_data
            # ServerFinished
            sf = _mac(self._s_fin_key, sha3_256(self._transcript), b"SF")
            sfin = enc_finished(sf)
            self._transcript += sfin
            master = _master(self._hs, self._transcript)
            self.session = Session.from_shared_secret(master, self.profile, "server")
            self.state = HState.CONNECTED
            # Keyingi ulanish uchun yangi ticket (stateless — server holat saqlamaydi)
            if self.tickets is not None and self._want_ticket:
                rms = _derive_rms(self._hs, self._transcript)
                nst = enc_new_session_ticket(
                    self.tickets.issue(rms, self.profile,
                                       context=self.ticket_context),
                    self.tickets.ttl)
                return sfin + nst
            return sfin

        raise AetherAlert(Alert.UNEXPECTED_MESSAGE)
