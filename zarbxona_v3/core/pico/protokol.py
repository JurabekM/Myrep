"""Pico USB protokoli (AQP1): ramka, maydonlar, buyruq va xato kodlari.

Ramka (ikki yo'nalishda ham bir xil):

    0  2  sehr      'A' 'Q'
    2  1  versiya   1
    3  1  kod       buyruq 0x01..0x3F · javob = buyruq | 0x80 · 0x7F = KUTMOQDA
    4  2  seq       u16 LE (xost tanlaydi, qurilma qaytaradi)
    6  2  n         u16 LE, foydali yuk uzunligi (≤ MAX_YUK)
    8  n  yuk
  8+n 4  crc32     IEEE (zlib.crc32), [0, 8+n) baytlar ustidan, LE

Yuk — maydonlar ketma-ketligi, har biri `u16 LE uzunlik || baytlar`. Sonlar maydon
ichida qat'iy kenglikda LE: u8 → 1, u32 → 4, u64 → 8, u128 → 16 bayt.
Javob yuki: birinchi bayt — holat (0 = OK), keyin maydonlar. Xatoda: holat = xato
kodi, keyin bitta maydon — inson uchun matn (utf-8) va ba'zan qo'shimcha maydonlar.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from ..imzolovchi import ImzolovchiXatosi

SEHR = b"AQ"
VERSIYA = 1
SARLAVHA_UZ = 8
CRC_UZ = 4
MAX_YUK = 8192

# --- buyruqlar ---------------------------------------------------------------------
SALOM = 0x01
KALIT_YARAT = 0x02
KALIT_IMPORT = 0x03
PIN_OCH = 0x04
QULFLA = 0x05
RUXSAT = 0x06
HOLAT = 0x07
KALIT_OCHIR = 0x08
IMZO_PARTIYA = 0x10
IMZO_BOSH = 0x11
IMZO_MINT_AUTH = 0x12

KUTMOQDA = 0x7F          # oraliq xabar: «tugmani bosing» (javob emas)
JAVOB_BIT = 0x80
XATO_RAMKA = 0xFF        # buzilgan ramkaga javob (seq = 0)

BUYRUQ_NOMI = {SALOM: "SALOM", KALIT_YARAT: "KALIT_YARAT", KALIT_IMPORT: "KALIT_IMPORT",
               PIN_OCH: "PIN_OCH", QULFLA: "QULFLA", RUXSAT: "RUXSAT", HOLAT: "HOLAT",
               KALIT_OCHIR: "KALIT_OCHIR", IMZO_PARTIYA: "IMZO_PARTIYA",
               IMZO_BOSH: "IMZO_BOSH", IMZO_MINT_AUTH: "IMZO_MINT_AUTH"}

# --- xato kodlari -------------------------------------------------------------------
OK = 0
X_NOMALUM = 1        # noma'lum buyruq
X_FORMAT = 2         # maydonlar soni/uzunligi noto'g'ri, CRC xato
X_KALIT_YOQ = 3
X_QULFLANGAN = 4     # avval PIN_OCH kerak
X_PIN = 5            # PIN noto'g'ri; qo'shimcha maydon: qolgan urinish (u8)
X_TUGMA_YOQ = 6      # tugma vaqtida bosilmadi
X_RUXSAT_YOQ = 7     # faol ruxsat yo'q yoki muddati tugagan
X_BYUDJET = 8        # partiya summasi ruxsat qoldig'idan katta
X_TARTIB = 9         # jurnal boshi tartibi orqaga ketdi
X_KALIT_BOR = 10     # kalit allaqachon bor
X_OCHIRILDI = 11     # PIN ko'p marta xato — kalit o'chirildi
X_ICHKI = 12
X_RAD = 13           # operator tugmani uzoq bosib rad etdi
X_ALOQA = 100        # faqat xostda: port yo'q, uzildi, javob kelmadi, buzilgan javob

XATO_MATNI = {
    X_NOMALUM: "noma'lum buyruq", X_FORMAT: "ramka yoki maydon formati xato",
    X_KALIT_YOQ: "Pico'da kalit yo'q", X_QULFLANGAN: "Pico qulflangan — PIN kerak",
    X_PIN: "PIN noto'g'ri", X_TUGMA_YOQ: "Pico tugmasi vaqtida bosilmadi",
    X_RUXSAT_YOQ: "Pico'da faol ruxsat yo'q (muddati tugagan bo'lishi mumkin)",
    X_BYUDJET: "partiya summasi Pico ruxsatidan oshadi",
    X_TARTIB: "jurnal boshi tartibi orqaga ketdi", X_KALIT_BOR: "Pico'da kalit allaqachon bor",
    X_OCHIRILDI: "PIN ko'p marta xato kiritildi — kalit O'CHIRILDI",
    X_ICHKI: "Pico ichki xatosi", X_RAD: "operator Pico tugmasi bilan RAD ETDI",
    X_ALOQA: "Pico bilan aloqa yo'q",
}

# --- qurilma qoidalari (ichki dastur bilan bir xil) ---------------------------------
PIN_MIN, PIN_MAX = 6, 64
MAX_URINISH = 5                 # ketma-ket xato PIN — keyin kalit o'chiriladi
TUGMA_KUTISH_S = 30             # tugma kutish vaqti
UZUN_BOSISH_S = 2.0             # shuncha yoki uzunroq bosish = RAD
MAX_RUXSAT_S = 24 * 3600
MAX_QULF_UZ = 256               # zaxira qulfi baytlarda
MAX_BUYURTMA_ID_UZ = 64
MAX_CHAQIRIQ_UZ = 128
ENTROPIYA_UZ = 32
SERIYA_UZ = 8

# SALOM holat bitlari
H_KALIT_BOR = 0x01
H_OCHIQ = 0x02
H_IMPORT = 0x04
H_RUXSAT = 0x08


class PicoXatosi(ImzolovchiXatosi):
    def __init__(self, kod: int, xabar: str = "", qoshimcha: list[bytes] | None = None):
        self.qoshimcha = qoshimcha or []
        super().__init__(xabar or XATO_MATNI.get(kod, f"xato {kod}"), kod)


class RamkaXatosi(ValueError):
    pass


@dataclass
class Ramka:
    kod: int
    seq: int
    yuk: bytes = b""

    def bayt(self) -> bytes:
        if len(self.yuk) > MAX_YUK:
            raise RamkaXatosi("yuk juda katta")
        s = SEHR + struct.pack("<BBHH", VERSIYA, self.kod, self.seq & 0xFFFF, len(self.yuk))
        b = s + self.yuk
        return b + struct.pack("<I", zlib.crc32(b) & 0xFFFFFFFF)


class Oquvchi:
    """Oqimdan ramkalarni ajratadi: axlatni o'tkazib yuboradi, keyingi 'AQ' dan sinxronlanadi.
    `qosh(baytlar)` → tayyor ramkalar ro'yxati; buzilganlari `buzilgan` hisobiga."""

    def __init__(self):
        self.bufer = bytearray()
        self.buzilgan = 0

    def qosh(self, d: bytes) -> list[Ramka]:
        self.bufer += d
        chiqdi: list[Ramka] = []
        while True:
            i = self.bufer.find(SEHR)
            if i < 0:
                del self.bufer[:max(0, len(self.bufer) - 1)]   # oxirgi 'A' qolishi mumkin
                return chiqdi
            if i:
                del self.bufer[:i]
            if len(self.bufer) < SARLAVHA_UZ:
                return chiqdi
            ver, kod, seq, n = struct.unpack_from("<BBHH", self.bufer, 2)
            if ver != VERSIYA or n > MAX_YUK:
                self.buzilgan += 1
                del self.bufer[:2]
                continue
            jami = SARLAVHA_UZ + n + CRC_UZ
            if len(self.bufer) < jami:
                return chiqdi
            b = bytes(self.bufer[:SARLAVHA_UZ + n])
            (crc,) = struct.unpack_from("<I", self.bufer, SARLAVHA_UZ + n)
            if zlib.crc32(b) & 0xFFFFFFFF != crc:
                self.buzilgan += 1
                del self.bufer[:2]
                continue
            del self.bufer[:jami]
            chiqdi.append(Ramka(kod, seq, b[SARLAVHA_UZ:]))


# --- maydonlar -------------------------------------------------------------------------


def maydonlar(*qismlar: bytes) -> bytes:
    b = bytearray()
    for q in qismlar:
        if len(q) > 0xFFFF:
            raise RamkaXatosi("maydon juda uzun")
        b += struct.pack("<H", len(q)) + q
    return bytes(b)


def ajrat(yuk: bytes) -> list[bytes]:
    """Maydonlarga ajratadi; ortiqcha yoki yetishmayotgan bayt — `RamkaXatosi`."""
    natija, i = [], 0
    while i < len(yuk):
        if i + 2 > len(yuk):
            raise RamkaXatosi("maydon uzunligi kesilgan")
        (n,) = struct.unpack_from("<H", yuk, i)
        i += 2
        if i + n > len(yuk):
            raise RamkaXatosi("maydon kesilgan")
        natija.append(bytes(yuk[i:i + n]))
        i += n
    return natija


def u8(n: int) -> bytes:
    return n.to_bytes(1, "little")


def u32(n: int) -> bytes:
    return n.to_bytes(4, "little")


def u64(n: int) -> bytes:
    return n.to_bytes(8, "little")


def u128(n: int) -> bytes:
    return n.to_bytes(16, "little")


def son(b: bytes, kenglik: int) -> int:
    if len(b) != kenglik:
        raise RamkaXatosi(f"son {kenglik} bayt bo'lishi kerak")
    return int.from_bytes(b, "little")


def javob_yuki(holat: int, *qismlar: bytes) -> bytes:
    return bytes([holat]) + maydonlar(*qismlar)


def xato_yuki(kod: int, matn: str | None = None, *qoshimcha: bytes) -> bytes:
    return javob_yuki(kod, (matn or XATO_MATNI.get(kod, "")).encode("utf-8"), *qoshimcha)
