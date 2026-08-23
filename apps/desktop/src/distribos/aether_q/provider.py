"""``AetherQ51Provider`` — protokol chegarasi (port).

Desktop va Android bir xil protokol xulqini ta'minlashi uchun butun
kriptografiya SHU interfeys ortida turadi. Biznes qatlami hech qachon
``vendor.*`` ni to'g'ridan-to'g'ri chaqirmaydi — buni
``tests/security/test_crypto_boundary.py`` qulflaydi.

Ikki qatlam (ADR-0001):

* **Sessiya** (``begin_*``/``session_*``) — AETHER-Q 0x01/0x03 handshake,
  o'zgartirilmagan spetsifikatsiya. Juftlash, epoch kalitini tarqatish,
  rotatsiya, revocation, snapshot oqimi.
* **Hodisa muhri** (``seal_event``/``open_event``) — DES-1, mustaqil
  ochiladigan envelope. MQTT pub/sub uchun.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ContentType(enum.IntEnum):
    """DES-1 ``content_type`` (specs/distribos-event-seal/DES-1.md)."""

    EVENT_BATCH = 1
    ACK = 2
    SYNC_DIGEST = 3
    SYNC_REQUEST = 4
    SNAPSHOT_MANIFEST = 5
    SNAPSHOT_CHUNK = 6
    DEVICE_STATUS = 7
    REVOCATION = 8
    PROTOCOL_CONTROL = 9


class RejectReason(enum.IntEnum):
    """Nega ochilmadi. Tarmoqqa CHIQMAYDI — faqat lokal log/diagnostika.

    AETHER-Q N15: batafsil xatoni jo'natuvchiga qaytarish oracle yaratadi.
    """

    MALFORMED = 1
    UNKNOWN_VERSION = 2
    UNSUPPORTED_PROFILE = 3
    UNKNOWN_EPOCH = 4
    UNKNOWN_KEY = 5
    FOREIGN_TENANT = 6
    UNKNOWN_SENDER = 7
    REVOKED_SENDER = 8
    BAD_SIGNATURE = 9
    REPLAY = 10
    AEAD_FAILURE = 11
    SCHEMA_INVALID = 12
    TOO_LARGE = 13
    STALE = 14


class AetherQError(Exception):
    """Protokol xatosi. ``reason`` lokal, tashqariga chiqmaydi."""

    def __init__(self, reason: RejectReason, detail: str = "") -> None:
        super().__init__(f"{reason.name}: {detail}" if detail else reason.name)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class DeviceIdentity:
    """Qurilmaning ochiq identifikatori. Maxfiy kalit BU YERDA EMAS."""

    device_id: bytes           # 16 bayt, tenant ichida opaque
    sign_public_key: bytes     # ML-DSA-65 ochiq kaliti, 1952 bayt
    kem_public_key: bytes      # ML-KEM-768 ochiq kaliti, 1184 bayt
    protocol_version: str      # "5.1.0"


@dataclass(frozen=True, slots=True)
class SealedEnvelope:
    """DES-1 envelope — MQTT'ga chiqadigan yagona shakl."""

    wire: bytes
    content_type: ContentType
    epoch: int
    sender_device_id: bytes


@dataclass(frozen=True, slots=True)
class OpenedEnvelope:
    """Muvaffaqiyatli ochilgan va tekshirilgan envelope."""

    payload: bytes
    content_type: ContentType
    epoch: int
    sender_device_id: bytes
    sequence: int


@dataclass(frozen=True, slots=True)
class ProtocolHealth:
    """Diagnostika oynasi uchun. Maxfiy material CHIQMAYDI."""

    protocol_version: str
    profile_id: int
    epoch: int
    key_id: int
    device_id_masked: str
    peers_known: int
    peers_revoked: int
    replay_window_size: int
    production_ready: bool
    blocking_reasons: tuple[str, ...]


@runtime_checkable
class AetherQ51Provider(Protocol):
    """DistribOS xavfsizlik chegarasi.

    Har bir implementatsiya AETHER-Q v5.1 (`specs/aether-q-v5.1/MAPPING.md`)
    va DES-1 (`specs/distribos-event-seal/DES-1.md`) ga muvofiq bo'lishi SHART.
    """

    # --- qurilma hayot sikli -------------------------------------------

    def initialize_device(self, tenant_id: bytes) -> DeviceIdentity:
        """Yangi qurilma kalit juftlarini yaratadi (ML-DSA-65 + ML-KEM-768)."""
        ...

    def export_public_identity(self) -> DeviceIdentity:
        """Ochiq identifikatorni beradi. Maxfiy kalit HECH QACHON chiqmaydi."""
        ...

    def provision_device(self, invitation: bytes) -> DeviceIdentity:
        """Bir martalik taklif orqali tenantga qo'shiladi (QR onboarding)."""
        ...

    def revoke_device(self, device_id: bytes, reason: str) -> None:
        """Qurilmani bekor qiladi. Undan keyingi hodisalar rad etiladi."""
        ...

    # --- kalit boshqaruvi ----------------------------------------------

    def rotate_keys(self) -> int:
        """Yangi epoch ochadi. Yangi ``epoch`` raqamini qaytaradi."""
        ...

    # --- hodisa muhri (DES-1) ------------------------------------------

    def seal_message(
        self, payload: bytes, content_type: ContentType
    ) -> SealedEnvelope:
        """Payload'ni DES-1 envelope'ga muhrlaydi."""
        ...

    def open_message(self, wire: bytes) -> OpenedEnvelope:
        """DES-1 envelope'ni ochadi va TO'LIQ tekshiradi.

        Rad etilsa ``AetherQError`` ko'tariladi. Chaqiruvchi hech qachon
        qisman tekshirilgan natijani ololmaydi (fail-closed).
        """
        ...

    # --- alohida tekshiruvlar (audit va test uchun) ---------------------

    def verify_sender(self, device_id: bytes) -> bool:
        """Qurilma ma'lum va bekor qilinmaganmi."""
        ...

    def validate_freshness(self, epoch: int, occurred_at_ms: int) -> bool:
        """Vaqt oynasi va epoch mosligini tekshiradi."""
        ...

    def detect_replay(self, epoch: int, device_id: bytes, sequence: int) -> bool:
        """``True`` — bu takror (replay). Sliding-window, AETHER-Q N5."""
        ...

    # --- diagnostika ----------------------------------------------------

    def protocol_health_check(self) -> ProtocolHealth:
        """Sync center / diagnostika oynasi uchun holat."""
        ...
