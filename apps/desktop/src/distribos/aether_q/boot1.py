"""BOOT-1 kodek — qurilmani ulash (`specs/distribos-event-seal/BOOT-1.md`).

DES-1 envelope'ni ochish uchun epoch kaliti kerak, yangi telefonda esa u
yo'q. BOOT-1 shu bir marotabalik teshikni yopadi: ishonch manbai — QR
orqali uzatilgan **bir martalik taklif siri**.

Bu modul faqat baytlarni yig'adi va ochadi; taklif haqiqiyligini va bir
marta ishlatilishini `onboarding.InvitationRegistry` hal qiladi.
"""

from __future__ import annotations

import enum
import os
import struct
from dataclasses import dataclass
from typing import Any, Final

import cbor2
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from .vendor import kdf

BOOT1_VERSION: Final = 0x0001
BOOT1_LABEL: Final = b"DistribOS-BOOT-1/AETHER-Q-v5.1/v1"

HEADER_SIZE: Final = 23
INVITATION_ID_SIZE: Final = 8
NONCE_SIZE: Final = 12
AEAD_TAG_SIZE: Final = 16

MIN_ENVELOPE_SIZE: Final = HEADER_SIZE + AEAD_TAG_SIZE

_HEADER_STRUCT: Final = struct.Struct(">HB")   # version, kind


class Boot1Error(ValueError):
    """Bootstrap xabari yaroqsiz. Sabab tarmoqqa CHIQMAYDI."""


class Boot1Kind(enum.IntEnum):
    JOIN_REQUEST = 1
    JOIN_RESPONSE = 2


@dataclass(frozen=True, slots=True)
class Boot1Keys:
    """Taklif siridan ajratilgan yo'nalishli kalitlar."""

    request_key: bytes
    request_iv: bytes
    response_key: bytes
    response_iv: bytes
    proof_prk: bytes

    def __repr__(self) -> str:
        return "Boot1Keys(<secrets hidden>)"

    def for_kind(self, kind: Boot1Kind) -> tuple[bytes, bytes]:
        if kind is Boot1Kind.JOIN_REQUEST:
            return self.request_key, self.request_iv
        return self.response_key, self.response_iv


def derive_keys(invitation_secret: bytes) -> Boot1Keys:
    """Taklif siridan yo'nalishli kalitlar.

    Yo'nalish bo'yicha alohida kalit (AETHER-Q N3): ushlab olingan
    so'rovni javob sifatida qayta o'ynatib bo'lmaydi.
    """
    if len(invitation_secret) != 32:
        raise Boot1Error("taklif siri 32 bayt bo'lishi kerak")

    prk = kdf.hkdf_extract(BOOT1_LABEL, invitation_secret)
    return Boot1Keys(
        request_key=kdf.hkdf_expand(prk, BOOT1_LABEL + b"/join-request", 32),
        request_iv=kdf.hkdf_expand(prk, BOOT1_LABEL + b"/iv-request", 12),
        response_key=kdf.hkdf_expand(prk, BOOT1_LABEL + b"/join-response", 32),
        response_iv=kdf.hkdf_expand(prk, BOOT1_LABEL + b"/iv-response", 12),
        proof_prk=prk,
    )


def join_proof(keys: Boot1Keys, device_id: bytes, sign_public_key: bytes) -> bytes:
    """Telefon taklif sirini bilishini QURILMA IDENTITETIGA bog'lab isbotlaydi.

    Tegni ushlab olgan boshqa qurilma uni o'z kaliti bilan ishlatolmaydi.
    """
    return kdf.kmac256(
        keys.proof_prk, device_id + sign_public_key, 32, custom=b"BOOT1/join"
    )


def verify_join_proof(
    keys: Boot1Keys, device_id: bytes, sign_public_key: bytes, proof: bytes
) -> bool:
    return kdf.ct_eq(join_proof(keys, device_id, sign_public_key), proof)


def _pack_header(kind: Boot1Kind, invitation_id: bytes, nonce: bytes) -> bytes:
    if len(invitation_id) != INVITATION_ID_SIZE:
        raise Boot1Error("invitation_id 8 bayt bo'lishi kerak")
    if len(nonce) != NONCE_SIZE:
        raise Boot1Error("nonce 12 bayt bo'lishi kerak")
    return _HEADER_STRUCT.pack(BOOT1_VERSION, int(kind)) + invitation_id + nonce


def seal(
    payload: dict[str, Any],
    kind: Boot1Kind,
    invitation_id: bytes,
    keys: Boot1Keys,
) -> bytes:
    """BOOT-1 envelope quradi."""
    key, iv = keys.for_kind(kind)
    salt = os.urandom(NONCE_SIZE)
    nonce = bytes(a ^ b for a, b in zip(iv, salt, strict=True))

    header = _pack_header(kind, invitation_id, nonce)
    ciphertext = ChaCha20Poly1305(key).encrypt(nonce, cbor2.dumps(payload), header)
    return header + ciphertext


def peek_invitation_id(wire: bytes) -> bytes:
    """Kalitni tanlash uchun taklif ID sini o'qiydi (ochmasdan)."""
    if len(wire) < MIN_ENVELOPE_SIZE:
        raise Boot1Error("envelope juda qisqa")
    version, _kind = _HEADER_STRUCT.unpack(wire[:3])
    if version != BOOT1_VERSION:
        raise Boot1Error(f"noma'lum BOOT-1 versiyasi: {version}")
    return wire[3:3 + INVITATION_ID_SIZE]


def peek_kind(wire: bytes) -> Boot1Kind:
    if len(wire) < MIN_ENVELOPE_SIZE:
        raise Boot1Error("envelope juda qisqa")
    _version, kind = _HEADER_STRUCT.unpack(wire[:3])
    try:
        return Boot1Kind(kind)
    except ValueError as exc:
        raise Boot1Error(f"noma'lum BOOT-1 turi: {kind}") from exc


def open_envelope(
    wire: bytes, keys: Boot1Keys, *, expect: Boot1Kind | None = None
) -> dict[str, Any]:
    """Envelope'ni ochadi va tekshiradi. Xato bo'lsa `Boot1Error`."""
    if len(wire) < MIN_ENVELOPE_SIZE:
        raise Boot1Error("envelope juda qisqa")

    version, raw_kind = _HEADER_STRUCT.unpack(wire[:3])
    if version != BOOT1_VERSION:
        raise Boot1Error(f"noma'lum BOOT-1 versiyasi: {version}")
    try:
        kind = Boot1Kind(raw_kind)
    except ValueError as exc:
        raise Boot1Error(f"noma'lum BOOT-1 turi: {raw_kind}") from exc
    if expect is not None and kind is not expect:
        raise Boot1Error(f"kutilgan {expect.name}, kelgan {kind.name}")

    header = wire[:HEADER_SIZE]
    nonce = wire[11:11 + NONCE_SIZE]
    ciphertext = wire[HEADER_SIZE:]

    key, _iv = keys.for_kind(kind)
    try:
        plaintext = ChaCha20Poly1305(key).decrypt(nonce, ciphertext, header)
    except Exception as exc:
        # Batafsil sabab CHIQMAYDI (oracle himoyasi).
        raise Boot1Error("BOOT-1 envelope ochilmadi") from exc

    payload = cbor2.loads(plaintext)
    if not isinstance(payload, dict):
        raise Boot1Error("payload obyekt emas")
    return payload


# --- yuqori darajadagi yordamchilar ---------------------------------------


def build_join_request(
    *,
    invitation_id: bytes,
    invitation_secret: bytes,
    device_id: bytes,
    sign_public_key: bytes,
    kem_public_key: bytes,
    platform: str,
    display_name: str,
) -> bytes:
    keys = derive_keys(invitation_secret)
    return seal(
        {
            "device_id": device_id,
            "sign_public_key": sign_public_key,
            "kem_public_key": kem_public_key,
            "platform": platform,
            "display_name": display_name,
            "proof": join_proof(keys, device_id, sign_public_key),
        },
        Boot1Kind.JOIN_REQUEST, invitation_id, keys,
    )


def build_join_response(
    *,
    invitation_id: bytes,
    invitation_secret: bytes,
    tenant_id: bytes,
    epoch: int,
    key_id: int,
    epoch_root_secret: bytes,
    profile_id: int,
    role: str,
    host_device_id: bytes,
    host_sign_public_key: bytes,
) -> bytes:
    keys = derive_keys(invitation_secret)
    return seal(
        {
            "tenant_id": tenant_id,
            "epoch": epoch,
            "key_id": key_id,
            "epoch_root_secret": epoch_root_secret,
            "profile_id": profile_id,
            "role": role,
            "host_device_id": host_device_id,
            "host_sign_public_key": host_sign_public_key,
        },
        Boot1Kind.JOIN_RESPONSE, invitation_id, keys,
    )


@dataclass(frozen=True, slots=True)
class JoinRequest:
    device_id: bytes
    sign_public_key: bytes
    kem_public_key: bytes
    platform: str
    display_name: str
    proof: bytes


def parse_join_request(wire: bytes, invitation_secret: bytes) -> JoinRequest:
    """JOIN_REQUEST ni ochadi va isbotni tekshiradi."""
    keys = derive_keys(invitation_secret)
    payload = open_envelope(wire, keys, expect=Boot1Kind.JOIN_REQUEST)

    try:
        request = JoinRequest(
            device_id=bytes(payload["device_id"]),
            sign_public_key=bytes(payload["sign_public_key"]),
            kem_public_key=bytes(payload["kem_public_key"]),
            platform=str(payload["platform"]),
            display_name=str(payload["display_name"]),
            proof=bytes(payload["proof"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise Boot1Error("JOIN_REQUEST maydonlari to'liq emas") from exc

    if len(request.device_id) != 16:
        raise Boot1Error("device_id 16 bayt bo'lishi kerak")
    if len(request.sign_public_key) != 1952:
        raise Boot1Error("ML-DSA-65 ochiq kaliti 1952 bayt bo'lishi kerak")
    if not verify_join_proof(keys, request.device_id, request.sign_public_key, request.proof):
        raise Boot1Error("join isboti noto'g'ri")
    return request


@dataclass(frozen=True, slots=True)
class JoinResponse:
    tenant_id: bytes
    epoch: int
    key_id: int
    epoch_root_secret: bytes
    profile_id: int
    role: str
    host_device_id: bytes
    host_sign_public_key: bytes

    def __repr__(self) -> str:
        return f"JoinResponse(epoch={self.epoch}, role={self.role!r}, <secrets hidden>)"


def parse_join_response(wire: bytes, invitation_secret: bytes) -> JoinResponse:
    keys = derive_keys(invitation_secret)
    payload = open_envelope(wire, keys, expect=Boot1Kind.JOIN_RESPONSE)

    try:
        response = JoinResponse(
            tenant_id=bytes(payload["tenant_id"]),
            epoch=int(payload["epoch"]),
            key_id=int(payload["key_id"]),
            epoch_root_secret=bytes(payload["epoch_root_secret"]),
            profile_id=int(payload["profile_id"]),
            role=str(payload["role"]),
            host_device_id=bytes(payload["host_device_id"]),
            host_sign_public_key=bytes(payload["host_sign_public_key"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise Boot1Error("JOIN_RESPONSE maydonlari to'liq emas") from exc

    if len(response.epoch_root_secret) != 32:
        raise Boot1Error("epoch root secret 32 bayt bo'lishi kerak")
    if response.profile_id not in (0x01, 0x03):
        raise Boot1Error(f"qo'llab-quvvatlanmaydigan profil: {response.profile_id}")
    return response
