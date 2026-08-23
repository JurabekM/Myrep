"""Hodisa jurnali va transactional outbox.

Topshiriq §7.1 ning yuragi: biznes o'zgarishi, hodisa yozuvi va outbox
yozuvi **bitta** lokal tranzaksiyada commit bo'ladi. Internet bo'lmasa
ham 1-8 bosqichlar bajariladi; yuborish keyin, fon worker'da.

Nega bu naqsh: agar biznes jadvalini yozib, keyin alohida MQTT'ga
yuborsak, ikkita jimgina buziladigan holat paydo bo'ladi —
«yozildi, lekin yuborilmadi» (ma'lumot peer'larga yetmaydi) va
«yuborildi, lekin yozilmadi» (peer'da bor, bizda yo'q). Outbox ikkalasini
ham yo'q qiladi.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

import cbor2
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from distribos.domain.ids import HybridClock, uuid7_str
from distribos.persistence.models import (
    DeliveryState,
    DeviceSequence,
    EventLog,
    InboxEntry,
    OutboxEntry,
    utcnow,
)


class SequenceExhausted(RuntimeError):
    """Qurilma hisoblagichi tugadi — DES-1 nonce takrorlanishi xavfi."""


#: DES-1 nonce 96-bit; hisoblagich shundan oshmasligi SHART.
MAX_DEVICE_SEQUENCE = (1 << 96) - 1


@dataclass(slots=True)
class NewEvent:
    """Yozilishi kerak bo'lgan hodisa (hali `device_sequence` berilmagan)."""

    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, Any]
    actor_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    idempotency_key: str | None = None
    schema_version: int = 1
    channel: str = "events"
    occurred_at: dt.datetime = field(default_factory=utcnow)


class EventStore:
    """Hodisa jurnaliga yozish va outbox'ga qo'yish.

    Bu sinf **sessiyani o'zi ochmaydi va commit qilmaydi** — chaqiruvchi
    `Database.unit_of_work()` ichida ishlatadi. Shundagina biznes
    o'zgarishi bilan bir tranzaksiyada bo'ladi.
    """

    def __init__(self, device_id: bytes, tenant_id: bytes, clock: HybridClock) -> None:
        if len(device_id) != 16:
            raise ValueError("device_id 16 bayt bo'lishi kerak")
        self._device_id = device_id
        self._tenant_id = tenant_id
        self._clock = clock

    # --- yozish ---------------------------------------------------------

    def _next_sequence(self, session: Session) -> int:
        """Monotonik hisoblagichni atomar oshiradi.

        `UPDATE ... RETURNING` bitta operatsiyada bajariladi — ikki oqim
        bir vaqtda chaqirsa ham bir xil raqam bermaydi. Bu kritik: takror
        `seq` DES-1 nonce'ni takrorlaydi, bu esa AEAD uchun halokatli.
        """
        row = session.execute(
            select(DeviceSequence).where(DeviceSequence.device_id == self._device_id)
        ).scalar_one_or_none()

        if row is None:
            session.add(DeviceSequence(device_id=self._device_id, next_sequence=2))
            session.flush()
            return 1

        result = session.execute(
            update(DeviceSequence)
            .where(DeviceSequence.device_id == self._device_id)
            .values(next_sequence=DeviceSequence.next_sequence + 1)
            .returning(DeviceSequence.next_sequence)
        ).scalar_one()

        allocated = result - 1
        if allocated >= MAX_DEVICE_SEQUENCE:
            raise SequenceExhausted(
                "Qurilma hisoblagichi tugadi — kalit rotatsiyasi (yangi epoch) SHART"
            )
        return allocated

    def append(self, session: Session, event: NewEvent) -> EventLog:
        """Hodisani jurnalga yozadi va outbox'ga qo'yadi.

        Idempotentlik: bir xil `idempotency_key` bilan qayta chaqirilsa,
        yangi hodisa yaratilmaydi va mavjudi qaytariladi.
        """
        if event.idempotency_key:
            existing = session.execute(
                select(EventLog).where(EventLog.idempotency_key == event.idempotency_key)
            ).scalar_one_or_none()
            if existing is not None:
                return existing

        sequence = self._next_sequence(session)
        stamp = self._clock.now()

        record = EventLog(
            event_id=uuid7_str(),
            event_type=event.event_type,
            schema_version=event.schema_version,
            tenant_id=self._tenant_id,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            actor_id=event.actor_id,
            device_id=self._device_id,
            occurred_at=event.occurred_at,
            logical_timestamp=stamp.encode(),
            device_sequence=sequence,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            idempotency_key=event.idempotency_key,
            payload=cbor2.dumps(event.payload),
            is_local=True,
            # Lokal hodisa ham proyektor orqali qo'llanadi (applied_at=None).
            # Yagona kod yo'li: desktop va telefon BIR XIL hodisalardan
            # BIR XIL holatni hisoblaydi — bu determinizmning asosi.
            applied_at=None,
        )
        session.add(record)
        session.flush()

        session.add(
            OutboxEntry(
                event_id=record.event_id,
                state=DeliveryState.LOCAL_COMMITTED,
                channel=event.channel,
                partition=str(sequence % 8),
            )
        )
        return record

    def append_remote(
        self,
        session: Session,
        *,
        event_id: str,
        event_type: str,
        schema_version: int,
        aggregate_type: str,
        aggregate_id: str,
        actor_id: str | None,
        sender_device_id: bytes,
        sender_sequence: int,
        occurred_at: dt.datetime,
        logical_timestamp: str,
        payload: bytes,
        epoch: int,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> EventLog | None:
        """Peer'dan kelgan hodisani yozadi.

        `None` qaytsa — bu **takror** (dublikat) va biznes natijasi
        ikkinchi marta qo'llanmasligi kerak. Bir hodisa o'n marta kelsa
        ham natija bir marta.
        """
        from distribos.domain.ids import HybridTimestamp

        inbox = session.execute(
            select(InboxEntry).where(InboxEntry.event_id == event_id)
        ).scalar_one_or_none()

        if inbox is not None:
            inbox.duplicate_count = (inbox.duplicate_count or 0) + 1
            return None

        session.add(
            InboxEntry(
                event_id=event_id,
                sender_device_id=sender_device_id,
                sender_sequence=sender_sequence,
                epoch=epoch,
            )
        )

        # Kelgan tamg'ani hisobga olamiz — mahalliy soat oldinga suriladi
        # (HLC qoidasi), lekin haddan tashqari kelajak qabul qilinmaydi.
        try:
            self._clock.observe(HybridTimestamp.decode(logical_timestamp))
        except (ValueError, AttributeError):
            pass  # buzuq tamg'a hodisani rad etmaydi — u imzo bilan tasdiqlangan

        record = EventLog(
            event_id=event_id,
            event_type=event_type,
            schema_version=schema_version,
            tenant_id=self._tenant_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            actor_id=actor_id,
            device_id=sender_device_id,
            occurred_at=occurred_at,
            logical_timestamp=logical_timestamp,
            device_sequence=sender_sequence,
            correlation_id=correlation_id,
            causation_id=causation_id,
            idempotency_key=idempotency_key,
            payload=payload,
            is_local=False,
            applied_at=None,   # proyektor keyin qo'llaydi
        )
        session.add(record)
        session.flush()
        return record

    # --- o'qish ---------------------------------------------------------

    def pending_outbox(
        self, session: Session, *, limit: int = 100, now: dt.datetime | None = None
    ) -> list[tuple[OutboxEntry, EventLog]]:
        """Yuborilishi kerak bo'lgan hodisalar (backoff hisobga olinadi)."""
        moment = now or utcnow()
        stmt = (
            select(OutboxEntry, EventLog)
            .join(EventLog, EventLog.event_id == OutboxEntry.event_id)
            .where(
                OutboxEntry.state.in_(
                    (
                        DeliveryState.LOCAL_COMMITTED,
                        DeliveryState.SEALED,
                        DeliveryState.QUEUED,
                    )
                ),
                (OutboxEntry.next_attempt_at.is_(None))
                | (OutboxEntry.next_attempt_at <= moment),
            )
            .order_by(OutboxEntry.id)
            .limit(limit)
        )
        return list(session.execute(stmt).all())  # type: ignore[arg-type]

    def unapplied_remote_events(
        self, session: Session, *, limit: int = 500
    ) -> list[EventLog]:
        """Proyektor qo'llashi kerak bo'lgan hodisalar, tartib bilan."""
        stmt = (
            select(EventLog)
            .where(EventLog.applied_at.is_(None))
            .order_by(EventLog.device_id, EventLog.device_sequence)
            .limit(limit)
        )
        return list(session.execute(stmt).scalars())

    def highest_sequence_by_device(self, session: Session) -> dict[bytes, int]:
        """Anti-entropy digest: har qurilma bo'yicha eng yuqori `seq`."""
        from sqlalchemy import func

        rows = session.execute(
            select(EventLog.device_id, func.max(EventLog.device_sequence)).group_by(
                EventLog.device_id
            )
        ).all()
        return {device_id: int(highest) for device_id, highest in rows}

    def events_in_range(
        self, session: Session, device_id: bytes, start: int, end: int, *, limit: int = 500
    ) -> list[EventLog]:
        """Anti-entropy: yetishmayotgan oraliqni beradi (ikkala chegara ham kiradi)."""
        stmt = (
            select(EventLog)
            .where(
                EventLog.device_id == device_id,
                EventLog.device_sequence >= start,
                EventLog.device_sequence <= end,
            )
            .order_by(EventLog.device_sequence)
            .limit(limit)
        )
        return list(session.execute(stmt).scalars())

    @staticmethod
    def decode_payload(record: EventLog) -> dict[str, Any]:
        data = cbor2.loads(record.payload)
        if not isinstance(data, dict):
            raise ValueError(f"payload dict emas: {type(data).__name__}")
        return data
