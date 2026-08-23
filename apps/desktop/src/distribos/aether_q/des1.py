"""DES-1 kodek — ``specs/distribos-event-seal/DES-1.md`` ning implementatsiyasi.

Bu modul FAQAT baytlarni yig'adi va ochadi. Kalit qayerdan keladi, qurilma
bekor qilinganmi, replay bo'ldimi — bularni ``real.py`` hal qiladi. Shunday
ajratish kodekni sof funksiya qiladi va KAT bilan qulflash imkonini beradi.

Barcha butun sonlar big-endian (AETHER-Q §1.2), ``seq`` dan tashqari — u
LE96 (AETHER-Q §8.2 nonce konvensiyasi bilan bir xil).
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from typing import Final

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from .vendor import kdf, sig

DES1_VERSION: Final = 0x0001
DES1_LABEL: Final = b"DistribOS-DES-1/AETHER-Q-v5.1/v1"
SIG_CONTEXT: Final = b"DES1/sig/v1"

HEADER_SIZE: Final = 66
SIGNATURE_SIZE: Final = 3309          # ML-DSA-65
AEAD_TAG_SIZE: Final = 16
TENANT_TAG_SIZE: Final = 16
DEVICE_ID_SIZE: Final = 16
SEQ_SIZE: Final = 12
RAND_SIZE: Final = 6

_MAX_SEQ: Final = (1 << 96) - 1

#: Envelope'ning eng kichik hajmi (bo'sh plaintext + tag + imzo).
MIN_ENVELOPE_SIZE: Final = HEADER_SIZE + AEAD_TAG_SIZE + SIGNATURE_SIZE

# version(u16), profile_id(u8), content_type(u8), epoch(u32), key_id(u64)
_HEADER_STRUCT: Final = struct.Struct(">HBBIQ")


class Des1FormatError(ValueError):
    """Envelope shakli buzilgan. Sabab tarmoqqa CHIQMAYDI."""


@dataclass(frozen=True, slots=True)
class EpochKeys:
    """Bitta ``(epoch, key_id)`` uchun ajratilgan kalitlar.

    ``epoch_root_secret`` dan HKDF orqali chiqariladi (DES-1 kalit ajratish
    bo'limi). Bu obyekt maxfiy — ``repr`` da hech qachon ochilmaydi.
    """

    epoch: int
    key_id: int
    aead_key: bytes      # 32 bayt
    aead_iv: bytes       # 12 bayt
    tenant_tag: bytes    # 16 bayt — shu tenant uchun kutilgan qiymat

    def __repr__(self) -> str:  # maxfiy material sizib chiqmasin
        return f"EpochKeys(epoch={self.epoch}, key_id={self.key_id}, <secrets hidden>)"


def derive_epoch_keys(
    epoch_root_secret: bytes,
    tenant_id: bytes,
    epoch: int,
    key_id: int,
    profile_id: int,
) -> EpochKeys:
    """DES-1 kalit ajratish — AETHER-Q §4 combiner qoidalariga muvofiq.

    ``profile_id`` va to'liq transcript har KDF'ga bind qilinadi (N1, S5) —
    ya'ni 0x01 dan 0x03 ga downgrade kalitni o'zgartiradi va xabar ochilmaydi.
    """
    if len(epoch_root_secret) != 32:
        raise ValueError("epoch_root_secret 32 bayt bo'lishi kerak")

    transcript = kdf.sha3_256(
        bytes([profile_id]) + DES1_LABEL + tenant_id
        + struct.pack(">IQ", epoch, key_id)
    )
    prk = kdf.hkdf_extract(transcript, epoch_root_secret)
    aead_key = kdf.hkdf_expand(prk, DES1_LABEL + b"/aead-key", 32)
    aead_iv = kdf.hkdf_expand(prk, DES1_LABEL + b"/aead-iv", 12)
    k_tag = kdf.hkdf_expand(prk, DES1_LABEL + b"/tenant-tag", 32)
    tenant_tag = kdf.kmac256(k_tag, tenant_id, 32, custom=b"DES1/tenant")[:TENANT_TAG_SIZE]
    return EpochKeys(epoch, key_id, aead_key, aead_iv, tenant_tag)


@dataclass(frozen=True, slots=True)
class Des1Header:
    """Ochiq (shifrlanmagan) header. AAD sifatida to'liq autentifikatsiyalanadi."""

    version: int
    profile_id: int
    content_type: int
    epoch: int
    key_id: int
    tenant_tag: bytes
    sender_device_id: bytes
    sequence: int
    rand: bytes

    def pack(self) -> bytes:
        if not 0 <= self.sequence <= _MAX_SEQ:
            raise Des1FormatError("sequence 96-bit oynadan chiqdi")
        if len(self.tenant_tag) != TENANT_TAG_SIZE:
            raise Des1FormatError("tenant_tag 16 bayt bo'lishi kerak")
        if len(self.sender_device_id) != DEVICE_ID_SIZE:
            raise Des1FormatError("sender_device_id 16 bayt bo'lishi kerak")
        if len(self.rand) != RAND_SIZE:
            raise Des1FormatError("rand 6 bayt bo'lishi kerak")
        return (
            _HEADER_STRUCT.pack(
                self.version, self.profile_id, self.content_type,
                self.epoch, self.key_id,
            )
            + self.tenant_tag
            + self.sender_device_id
            + self.sequence.to_bytes(SEQ_SIZE, "little")
            + self.rand
        )

    @classmethod
    def unpack(cls, raw: bytes) -> "Des1Header":
        if len(raw) < HEADER_SIZE:
            raise Des1FormatError("header qisqa")
        version, profile_id, content_type, epoch, key_id = _HEADER_STRUCT.unpack(raw[:16])
        return cls(
            version=version,
            profile_id=profile_id,
            content_type=content_type,
            epoch=epoch,
            key_id=key_id,
            tenant_tag=raw[16:32],
            sender_device_id=raw[32:48],
            sequence=int.from_bytes(raw[48:60], "little"),
            rand=raw[60:66],
        )


def _nonce(seq: int, iv: bytes) -> bytes:
    """nonce = seq XOR IV_ep (AETHER-Q §8.2 bilan bir xil shakl)."""
    n = int.from_bytes(iv, "little") ^ (seq & _MAX_SEQ)
    return (n & _MAX_SEQ).to_bytes(12, "little")


def _signed_bytes(packed_header: bytes, ciphertext: bytes) -> bytes:
    return SIG_CONTEXT + packed_header + hashlib.sha3_256(ciphertext).digest()


def seal(
    plaintext: bytes,
    header: Des1Header,
    keys: EpochKeys,
    signing_private_key: object,
) -> bytes:
    """DES-1 envelope quradi: header + ciphertext + signature."""
    if header.epoch != keys.epoch or header.key_id != keys.key_id:
        raise Des1FormatError("header epoch/key_id kalitlarga mos emas")

    packed = header.pack()
    aead = ChaCha20Poly1305(keys.aead_key)
    ciphertext = aead.encrypt(_nonce(header.sequence, keys.aead_iv), plaintext, packed)
    signature = sig.MLDSA65.sign(signing_private_key, _signed_bytes(packed, ciphertext))
    if len(signature) != SIGNATURE_SIZE:
        raise Des1FormatError("kutilmagan imzo uzunligi")
    return packed + ciphertext + signature


def split(wire: bytes) -> tuple[Des1Header, bytes, bytes, bytes]:
    """Envelope'ni (header, packed_header, ciphertext, signature) ga ajratadi.

    Kriptografik tekshiruv QILMAYDI — faqat shakl. Chaqiruvchi imzo va AEAD
    ni o'zi tekshirishi SHART.
    """
    if len(wire) < MIN_ENVELOPE_SIZE:
        raise Des1FormatError("envelope juda qisqa")
    packed = wire[:HEADER_SIZE]
    ciphertext = wire[HEADER_SIZE:-SIGNATURE_SIZE]
    signature = wire[-SIGNATURE_SIZE:]
    if len(ciphertext) < AEAD_TAG_SIZE:
        raise Des1FormatError("ciphertext tag'siz")
    return Des1Header.unpack(packed), packed, ciphertext, signature


def verify_signature(
    packed_header: bytes,
    ciphertext: bytes,
    signature: bytes,
    sender_public_key: bytes,
) -> bool:
    """ML-DSA-65 imzosini tekshiradi. Exception ko'tarmaydi — bool qaytaradi."""
    try:
        return bool(
            sig.MLDSA65.verify(
                sender_public_key, signature, _signed_bytes(packed_header, ciphertext)
            )
        )
    except Exception:
        return False


def open_aead(header: Des1Header, ciphertext: bytes, keys: EpochKeys) -> bytes:
    """AEAD ochadi. Tag xato bo'lsa Des1FormatError (N15: fatal, batafsilsiz)."""
    aead = ChaCha20Poly1305(keys.aead_key)
    try:
        return aead.decrypt(
            _nonce(header.sequence, keys.aead_iv), ciphertext, header.pack()
        )
    except Exception as exc:  # InvalidTag va boshqalar — bir xil javob
        raise Des1FormatError("AEAD ochilmadi") from exc


def tenant_tag_matches(header: Des1Header, keys: EpochKeys) -> bool:
    """Constant-time tenant tekshiruvi (AETHER-Q ct_eq ustidan)."""
    return kdf.ct_eq(header.tenant_tag, keys.tenant_tag)
