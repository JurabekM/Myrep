"""Sinxronizatsiya jadvallari — event log, outbox, inbox, checkpoint.

Bu jadvallar biznes jadvallaridan ALOHIDA turadi. Sabab: biznes sxemasi
o'zgarganda ham sinxronizatsiya protokoli o'zgarmasligi kerak.
"""

from __future__ import annotations

import datetime as dt
import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from distribos.persistence.base import Base

if TYPE_CHECKING:
    pass


def utcnow() -> dt.datetime:
    """Doim tz-aware UTC.

    Naive datetime bilan solishtirish jimgina noto'g'ri natija beradi —
    shuning uchun butun kod bazasida faqat shu funksiya ishlatiladi.
    """
    return dt.datetime.now(dt.UTC)


class DeliveryState(enum.StrEnum):
    """Hodisaning yetkazilish holati (topshiriq §7.5).

    Foydalanuvchiga BU kodlar ko'rsatilmaydi — `presentation/status.py`
    ularni tushunarli matnga aylantiradi.
    """

    LOCAL_COMMITTED = "LOCAL_COMMITTED"
    SEALED = "SEALED"
    QUEUED = "QUEUED"
    MQTT_PUBLISHED = "MQTT_PUBLISHED"
    MQTT_ACKNOWLEDGED = "MQTT_ACKNOWLEDGED"
    PEER_RECEIVED = "PEER_RECEIVED"
    PEER_APPLIED = "PEER_APPLIED"
    PEER_REJECTED = "PEER_REJECTED"
    CONFLICT = "CONFLICT"
    DEAD_LETTER = "DEAD_LETTER"


class DeviceState(enum.StrEnum):
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class EventLog(Base):
    """O'zgarmas (immutable) hodisa jurnali — tizimning haqiqat manbai.

    O'z hodisalarimiz ham, peer'lardan kelganlar ham SHU yerda yotadi.
    Biznes jadvallari bu jurnaldan proyeksiya qilinadi, ya'ni ular
    keshdan iborat va qayta qurilishi mumkin.
    """

    __tablename__ = "event_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    tenant_id: Mapped[bytes] = mapped_column(LargeBinary(16), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)

    actor_id: Mapped[str | None] = mapped_column(String(64))
    device_id: Mapped[bytes] = mapped_column(LargeBinary(16), nullable=False)

    occurred_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    #: HLC tamg'asi (`HybridTimestamp.encode()`), konflikt hal qilish uchun.
    logical_timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Qurilma-lokal monotonik hisoblagich. Anti-entropy shunga tayanadi.
    device_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)

    correlation_id: Mapped[str | None] = mapped_column(String(36))
    causation_id: Mapped[str | None] = mapped_column(String(36))
    idempotency_key: Mapped[str | None] = mapped_column(String(64))

    #: CBOR kodlangan payload. Faqat lokal — MQTT'ga DES-1 ichida chiqadi.
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    #: Hodisa lokal yaratilganmi yoki peer'dan kelganmi.
    is_local: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    #: Proyektor uni biznes jadvallariga qo'lladimi.
    applied_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    recorded_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    #: Proyektor necha marta urinib ko'rdi. Hodisa ota-ona yozuvidan
    #: OLDIN kelishi mumkin (tartib buzilishi) — shunda u kechiktiriladi
    #: va keyingi urinishda qayta ko'riladi, YO'QOTILMAYDI.
    projection_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    __table_args__ = (
        # Anti-entropy yadrosi: "shu qurilmadan N..M oralig'ini ber".
        UniqueConstraint("device_id", "device_sequence", name="uq_event_device_seq"),
        Index("ix_event_aggregate", "aggregate_type", "aggregate_id"),
        Index("ix_event_type_time", "event_type", "occurred_at"),
        # Qo'llanmagan hodisalarni tez topish uchun (proyektor navbati).
        Index("ix_event_unapplied", "applied_at"),
        Index("ix_event_tenant_seq", "tenant_id", "device_id", "device_sequence"),
    )


class OutboxEntry(Base):
    """Yuborilishi kerak bo'lgan hodisalar (transactional outbox).

    Yozuv biznes o'zgarishi bilan BIR tranzaksiyada yaratiladi. Shuning
    uchun "baza yangilandi, lekin hodisa yo'qoldi" holati bo'lishi mumkin
    emas — bu naqshning butun ma'nosi.
    """

    __tablename__ = "sync_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("event_log.event_id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )

    state: Mapped[str] = mapped_column(
        String(24), nullable=False, default=DeliveryState.LOCAL_COMMITTED
    )
    channel: Mapped[str] = mapped_column(String(24), nullable=False, default="events")
    partition: Mapped[str] = mapped_column(String(16), nullable=False, default="0")

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    #: Exponential backoff — shu vaqtgacha urinmaymiz.
    next_attempt_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    event: Mapped[EventLog] = relationship(
        "EventLog", primaryjoin="OutboxEntry.event_id == foreign(EventLog.event_id)"
    )

    __table_args__ = (
        # Yuborish navbati: holat + vaqt bo'yicha.
        Index("ix_outbox_pending", "state", "next_attempt_at"),
    )


class InboxEntry(Base):
    """Qabul qilingan hodisalar — deduplikatsiya reyestri.

    Bir hodisa o'n marta kelsa ham biznes natijasi bir marta qo'llanadi:
    `event_id` unique, ikkinchi INSERT tranzaksiyada rad etiladi.
    """

    __tablename__ = "sync_inbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)

    sender_device_id: Mapped[bytes] = mapped_column(LargeBinary(16), nullable=False)
    sender_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    epoch: Mapped[int] = mapped_column(Integer, nullable=False)

    received_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    applied_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    #: Necha marta takror kelgani — diagnostika uchun foydali.
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_inbox_sender", "sender_device_id", "sender_sequence"),
    )


class PeerDevice(Base):
    """Tanilgan qurilmalar reyestri — kim kim ekanligi va vakolati."""

    __tablename__ = "sync_peer_device"

    device_id: Mapped[bytes] = mapped_column(LargeBinary(16), primary_key=True)
    tenant_id: Mapped[bytes] = mapped_column(LargeBinary(16), nullable=False)

    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default="desktop")
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="agent")

    #: ML-DSA-65 ochiq kaliti (1952 bayt) — har hodisa imzosi shu bilan tekshiriladi.
    sign_public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    #: ML-KEM-768 ochiq kaliti (1184 bayt) — sessiya o'rnatish uchun.
    kem_public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    state: Mapped[str] = mapped_column(String(16), nullable=False, default=DeviceState.INVITED)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(Text)

    #: Bizga ma'lum bo'lgan oxirgi ketma-ketlik — anti-entropy digest'i.
    last_applied_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_seen_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    #: Bu qurilma to'liq ma'lumotga ega (snapshot bera oladi).
    is_full_replica: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    __table_args__ = (Index("ix_peer_state", "state"),)

    @property
    def is_revoked(self) -> bool:
        return self.state == DeviceState.REVOKED


class EpochKeyRecord(Base):
    """Epoch kaliti metama'lumoti.

    `root_secret_wrapped` — OS credential store yoki KEK bilan o'ralgan.
    Ochiq holda HECH QACHON saqlanmaydi.
    """

    __tablename__ = "sync_epoch_key"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    epoch: Mapped[int] = mapped_column(Integer, nullable=False)
    key_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tenant_id: Mapped[bytes] = mapped_column(LargeBinary(16), nullable=False)

    root_secret_wrapped: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    profile_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0x01)

    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    retired_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("epoch", "key_id", name="uq_epoch_key"),
        Index("ix_epoch_current", "is_current"),
    )


class SyncCheckpoint(Base):
    """Peer bilan oxirgi muvaffaqiyatli sinxronizatsiya nuqtasi."""

    __tablename__ = "sync_checkpoint"

    peer_device_id: Mapped[bytes] = mapped_column(LargeBinary(16), primary_key=True)

    last_applied_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_sync_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    last_digest_sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    protocol_version: Mapped[str] = mapped_column(String(10), nullable=False, default="5.1")

    #: Yetishmayotgan oraliqlar, JSON: [[from, to], ...]. Bo'sh — hammasi bor.
    missing_ranges: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class DeadLetter(Base):
    """Qo'llab bo'lmagan xabarlar. Jimgina tashlab yuborilmaydi."""

    __tablename__ = "sync_dead_letter"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_id: Mapped[str | None] = mapped_column(String(36))
    sender_device_id: Mapped[bytes | None] = mapped_column(LargeBinary(16))
    channel: Mapped[str] = mapped_column(String(24), nullable=False)

    #: `RejectReason` nomi. Tarmoqqa CHIQMAYDI — faqat lokal diagnostika.
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    #: Xom baytlar tekshiruv uchun saqlanadi, lekin hajmi cheklangan.
    raw_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    occurred_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_dead_letter_open", "resolved_at", "occurred_at"),)


class ConflictRecord(Base):
    """Aniqlangan konflikt. Avtomatik yashirilmaydi (topshiriq §13)."""

    __tablename__ = "sync_conflict"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(64))

    local_event_id: Mapped[str | None] = mapped_column(String(36))
    remote_event_id: Mapped[str | None] = mapped_column(String(36))

    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    #: AUTO_RESOLVED yoki NEEDS_REVIEW.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEEDS_REVIEW")
    resolution: Mapped[str | None] = mapped_column(Text)

    local_value: Mapped[str | None] = mapped_column(Text)
    remote_value: Mapped[str | None] = mapped_column(Text)

    detected_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("ix_conflict_open", "status", "detected_at"),
        Index("ix_conflict_aggregate", "aggregate_type", "aggregate_id"),
    )


class ReplayWindow(Base):
    """Anti-replay oynasi (AETHER-Q N5/S6).

    Har `(epoch, device)` juftligi uchun ko'rilgan eng yuqori `seq` va
    undan pastdagi bitmask. Bitmask 1024 bit = 128 bayt.
    """

    __tablename__ = "sync_replay_window"

    epoch: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[bytes] = mapped_column(LargeBinary(16), primary_key=True)

    highest_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bitmap: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, default=b"")
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class DeviceSequence(Base):
    """Bu qurilmaning o'z monotonik hisoblagichi.

    Bitta qator. Hisoblagich hodisa bilan BIR tranzaksiyada oshiriladi,
    aks holda ikki hodisa bir xil `seq` olib, DES-1 nonce takrorlanardi —
    bu AEAD uchun halokatli.
    """

    __tablename__ = "sync_device_sequence"

    device_id: Mapped[bytes] = mapped_column(LargeBinary(16), primary_key=True)
    next_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
