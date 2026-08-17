"""Protokol rejimi va har bir kamchilik uchun alohida kalit.

Simulyatorning yadro g'oyasi: bitta kod bazasi ikki xil protokolni gavdalantiradi.

  * `SPEC`     — hujjatda yozilganidek, AYNAN. Kamchiliklari bilan birga.
  * `HARDENED` — auditda topilgan kamchiliklar tuzatilgan variant.
  * `CUSTOM`   — har bir bayroqni qo'lda yoqib/o'chirib tekshirish.

Har bayroq izohida tegishli audit topilmasi kodi bor (K-1..K-4, Y-1..Y-8).
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from enum import Enum

from .crypto.canonical import Encoding

SUITE = "SCUTUM-Q1"
PROTOCOL_VERSION = 1


class Mode(str, Enum):
    SPEC = "SPEC"
    HARDENED = "HARDENED"
    CUSTOM = "CUSTOM"


@dataclass
class Flag:
    key: str
    finding: str
    title: str
    detail: str


#: GUI uchun bayroqlar katalogi (tartib = audit jiddiyligi bo'yicha)
FLAG_CATALOG: list[Flag] = [
    Flag(
        "include_dh3_identity",
        "K-1",
        "INIT'ga qabul qiluvchi identity DH (dh3) qo'shish",
        "Spec'da dh1/dh2/pq — uchalasi ham faqat SPK'ga bog'langan. dh3 = "
        "X25519(EK_A, IK_B) bo'lmasa, SPK sirining oshkor bo'lishi butun "
        "sessiyani va qabul qiluvchining shaxsini beradi.",
    ),
    Flag(
        "include_opk_dh",
        "K-2",
        "OPK'ni haqiqatan KDF'ga kiritish (dh4)",
        "Spec OPK'ni e'lon qiladi, uzatadi va o'chiradi — lekin ikm'ga "
        "qo'shmaydi. Natijada OPK mexanizmi dekorativ va INIT replay ochiq.",
    ),
    Flag(
        "init_replay_cache",
        "K-2",
        "INIT replay keshi (ct-hash + timestamp oynasi)",
        "Spec'da replay oynasi ham, INIT keshi ham ta'riflanmagan. Kesh "
        "bo'lmasa eski INIT qayta yuborilib, ayni RK0 bilan yangi sessiya "
        "ochiladi.",
    ),
    Flag(
        "advance_chain_key",
        "K-3",
        "Chain key'ni bir tomonlama oldinga siljitish",
        "Spec'dagi yagona konkret formula MK'ni statik CK'dan message_no "
        "orqali chiqaradi -> CK oshkor bo'lsa chain'dagi BARCHA o'tgan va "
        "kelajakdagi xabarlar ochiladi. Forward secrecy yo'qoladi.",
    ),
    Flag(
        "header_in_aad",
        "K-4",
        "Ratchet sarlavhasini (dh, pn, n) AAD'ga kiritish",
        "Spec'ning Envelope sxemasida ratchet ochiq kaliti ham, PN ham yo'q — "
        "Double Ratchet'ni umuman amalga oshirib bo'lmaydi. Simulyator bu "
        "maydonlarni qo'shadi; bayroq ularning AAD bilan himoyalanishini "
        "boshqaradi.",
    ),
    Flag(
        "bind_kem_transcript",
        "Y-1",
        "ML-KEM ct/pk va ephemeral pk'ni KDF transkriptiga bog'lash",
        "Spec'da salt faqat DC'lardan iborat; KEM ciphertext va ephemeral "
        "ochiq kalit KDF'ga kirmaydi (ML-KEM binding muammosi, MAL-BIND-K-CT).",
    ),
    Flag(
        "key_commitment",
        "Y-2",
        "AEAD uchun kalit-majburiyat tegi",
        "ChaCha20-Poly1305 key-committing emas. Parol bilan shifrlangan "
        "backup'da bu partitioning-oracle hujumiga yo'l ochadi.",
    ),
    Flag(
        "merkle_domain_sep",
        "Y-3",
        "Merkle: barg/tugun domen ajratish + toq tugunni ko'chirish",
        "Spec leaf va internal uchun bir xil SHA3-256 ishlatadi va daraxt "
        "tuzilishini ta'riflamaydi -> tugun-turi chalkashligi va duplikat-"
        "tugun (CVE-2012-2459 uslubi) hujumlari.",
    ),
    Flag(
        "separate_meta_key",
        "Y-4",
        "Fayl metama'lumoti uchun alohida kalit/nonce",
        "name_enc / mime_enc uchun kalit, nonce va AAD spec'da umuman "
        "ta'riflanmagan -> amaliyotda FK va takroriy nonce ishlatiladi.",
    ),
    Flag(
        "strict_encoding",
        "Y-5",
        "Yagona majburiy kanonik kodlash (CBOR determinstic)",
        "Spec CBOR va JSON'ni muqobil qiladi, ayni paytda AAD'ning "
        "byte-for-byte mosligini talab qiladi — bu ziddiyat.",
    ),
    Flag(
        "sign_full_bundle",
        "Y-6",
        "Butun PreKeyBundle'ni (SPK_expiry bilan) imzolash",
        "Spec sig(DC || SPK) — SPK_expiry imzo tashqarisida qoladi, ya'ni "
        "server muddati o'tgan SPK'ni cheksiz uzaytira oladi.",
    ),
    Flag(
        "fingerprint_keys_only",
        "Y-7",
        "device_fingerprint faqat identity kalitlardan",
        "Spec fingerprint'ni butun DC'dan oladi — DC har yangilanganda "
        "foydalanuvchining xavfsizlik raqami o'zgaradi va tasdiq bekor bo'ladi.",
    ),
    Flag(
        "revoke_epoch",
        "Y-8",
        "DEVICE_REVOKE uchun monoton epoch",
        "Spec'da bekor qilish tartibi yo'q -> server revoke xabarini ushlab "
        "qolsa (rollback) klient hech qachon bilmaydi.",
    ),
    Flag(
        "bounded_skipped_keys",
        "O-3",
        "Skipped-key uchun global limit va TTL",
        "MAX_SKIPPED_KEYS=1000 har chain uchun; chainlar soni cheklanmagan -> "
        "xotira tugatish (DoS).",
    ),
]

_HARDENED_ONLY = {f.key for f in FLAG_CATALOG}


@dataclass
class ProtocolConfig:
    """Protokol xatti-harakatini boshqaruvchi to'liq konfiguratsiya."""

    mode: Mode = Mode.SPEC

    # --- audit bayroqlari (SPEC = hammasi False) ---
    include_dh3_identity: bool = False
    include_opk_dh: bool = False
    init_replay_cache: bool = False
    advance_chain_key: bool = False
    header_in_aad: bool = False
    bind_kem_transcript: bool = False
    key_commitment: bool = False
    merkle_domain_sep: bool = False
    separate_meta_key: bool = False
    strict_encoding: bool = False
    sign_full_bundle: bool = False
    fingerprint_keys_only: bool = False
    revoke_epoch: bool = False
    bounded_skipped_keys: bool = False

    # --- spec parametrlari ---
    encoding: Encoding = Encoding.CBOR_DETERMINISTIC
    chunk_size: int = 4 * 1024 * 1024          # spec §7.1
    max_skipped_keys: int = 1000               # spec §6
    max_skipped_chains: int = 8                # spec §6.5 (HARDENED)
    skipped_ttl_secs: int = 7 * 86400          # spec §6.5 SKIPPED_TTL
    pq_ratchet_every_msgs: int = 100           # spec §6.1
    pq_ratchet_every_secs: int = 600           # spec §6.1
    spk_lifetime_days: int = 30                # spec §8
    dik_lifetime_days: int = 365               # spec §8
    replay_window_secs: int = 120              # spec'da yo'q (HARDENED)
    argon2_memory_kib: int = 65536
    argon2_time_cost: int = 3

    def flag(self, key: str) -> bool:
        return bool(getattr(self, key))

    def enabled_flags(self) -> list[str]:
        return [f.key for f in FLAG_CATALOG if self.flag(f.key)]

    def describe(self) -> str:
        n = len(self.enabled_flags())
        total = len(FLAG_CATALOG)
        return f"{self.mode.value} — {n}/{total} tuzatish yoqilgan"


def spec_config() -> ProtocolConfig:
    """Hujjatdagi protokol, aynan. Hech bir tuzatish yoqilmagan."""
    return ProtocolConfig(mode=Mode.SPEC)


def hardened_config() -> ProtocolConfig:
    """Audit topilmalari tuzatilgan protokol."""
    cfg = ProtocolConfig(mode=Mode.HARDENED)
    for key in _HARDENED_ONLY:
        setattr(cfg, key, True)
    return cfg


def custom_from(base: ProtocolConfig, **overrides) -> ProtocolConfig:
    return replace(base, mode=Mode.CUSTOM, **overrides)


def config_diff(a: ProtocolConfig, b: ProtocolConfig) -> list[str]:
    out = []
    for f in fields(ProtocolConfig):
        if f.name == "mode":
            continue
        va, vb = getattr(a, f.name), getattr(b, f.name)
        if va != vb:
            out.append(f"{f.name}: {va} -> {vb}")
    return out
