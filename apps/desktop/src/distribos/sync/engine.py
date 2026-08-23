"""Sinxronizatsiya dvigateli — outbox, inbox, ACK va anti-entropy.

Bu qatlam hodisa jurnalini, AETHER-Q muhrini, MQTT transportini va
proyektorni bog'laydi.

Ikkita ajratish qat'iy saqlanadi:

* **transport ACK ≠ biznes ACK.** Broker PUBACK bergani hodisa peer'da
  qo'llandi degani emas. Ular alohida holatlar
  (`MQTT_ACKNOWLEDGED` va `PEER_APPLIED`).
* **broker tarixiga tayanmaymiz.** Yo'qolgan hodisa broker'dan emas,
  peer bilan digest almashuvi orqali tiklanadi.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import cbor2
from sqlalchemy import select
from sqlalchemy.orm import Session

from distribos.aether_q import des1
from distribos.aether_q.provider import (
    AetherQError,
    ContentType,
    OpenedEnvelope,
    RejectReason,
    SealedEnvelope,
)
from distribos.application.projector import Projector
from distribos.mqtt.topics import Channel
from distribos.persistence.models import (
    DeadLetter,
    DeliveryState,
    EventLog,
    OutboxEntry,
    PeerDevice,
    SyncCheckpoint,
    utcnow,
)
from distribos.sync.event_store import EventStore

logger = logging.getLogger(__name__)

#: Bitta DES-1 envelope ichidagi maksimal hodisa soni.
#: ML-DSA-65 imzosi 3309 bayt — batch bo'lmasa ustama juda katta.
MAX_BATCH_EVENTS = 50

#: Necha marta urinilgandan keyin dead-letter'ga tushadi.
MAX_DELIVERY_ATTEMPTS = 8


class Transport(Protocol):
    """Publish chegarasi — haqiqiy MQTT yoki test loopback."""

    def publish(
        self,
        envelope: SealedEnvelope,
        channel: Channel,
        *,
        partition: str = "0",
        target_device_id: bytes | None = None,
        correlation_data: bytes | None = None,
        response_topic: str | None = None,
        message_expiry_seconds: int | None = None,
    ) -> int: ...

    def publish_raw(self, wire: bytes, channel: Channel) -> int:
        """Muhrlanmagan baytlarni yuboradi.

        FAQAT BOOT-1 uchun: qurilmani ulashda peer'da hali epoch kaliti
        yo'q. Boshqa hech qanday holatda ishlatilmaydi — buni
        `tests/security/test_no_plaintext_publish.py` qulflaydi.
        """
        ...

    def is_connected(self) -> bool: ...


class Provider(Protocol):
    def seal_message(self, payload: bytes, content_type: ContentType) -> SealedEnvelope: ...
    def open_message(self, wire: bytes) -> OpenedEnvelope: ...


@dataclass(slots=True)
class SyncStats:
    published_batches: int = 0
    published_events: int = 0
    received_events: int = 0
    duplicates: int = 0
    applied: int = 0
    conflicts: int = 0
    rejected: int = 0
    dead_lettered: int = 0
    acks_sent: int = 0
    acks_received: int = 0
    rejections: dict[str, int] = field(default_factory=dict)

    def note_rejection(self, reason: str) -> None:
        self.rejections[reason] = self.rejections.get(reason, 0) + 1


def _backoff_seconds(attempts: int) -> int:
    """Qayta urinish oralig'i: 2^n soniya, 1 soatgacha."""
    return min(3600, 2 ** min(attempts, 12))


class SyncEngine:
    """Outbox'ni yuboradi, kelgan xabarlarni qo'llaydi, ACK almashadi."""

    def __init__(
        self,
        *,
        device_id: bytes,
        store: EventStore,
        provider: Provider,
        transport: Transport,
        session_factory: Any,
        projector: Projector | None = None,
    ) -> None:
        self._device_id = device_id
        self._store = store
        self._provider = provider
        self._transport = transport
        self._session_factory = session_factory
        self._projector = projector or Projector()
        self.stats = SyncStats()

    # --- chiqish yo'nalishi -----------------------------------------------

    def publish_pending(self, *, limit: int = MAX_BATCH_EVENTS) -> int:
        """Outbox'dagi hodisalarni batch qilib yuboradi.

        Yuborilmasa (offline) — outbox tegilmaydi va keyingi urinishda
        qayta ko'riladi. Bu funksiya hech qachon hodisani yo'qotmaydi.
        """
        if not self._transport.is_connected():
            return 0

        with self._session_factory() as session:
            pending = self._store.pending_outbox(session, limit=limit)
            if not pending:
                return 0

            batch = [self._event_to_dict(event) for _, event in pending]
            envelope_payload = cbor2.dumps({"events": batch})

            try:
                envelope = self._provider.seal_message(
                    envelope_payload, ContentType.EVENT_BATCH
                )
            except AetherQError as exc:
                self._mark_failure(session, [entry for entry, _ in pending], str(exc))
                session.commit()
                logger.error("Muhrlash muvaffaqiyatsiz: %s", exc)
                return 0

            for entry, _ in pending:
                entry.state = DeliveryState.SEALED

            try:
                self._transport.publish(envelope, Channel.EVENTS)
            except Exception as exc:
                self._mark_failure(session, [entry for entry, _ in pending], str(exc))
                session.commit()
                logger.warning("Publish muvaffaqiyatsiz: %s", exc)
                return 0

            moment = utcnow()
            for entry, _ in pending:
                entry.state = DeliveryState.MQTT_PUBLISHED
                entry.attempts = (entry.attempts or 0) + 1
                entry.last_attempt_at = moment
                entry.last_error = None

            session.commit()

        self.stats.published_batches += 1
        self.stats.published_events += len(pending)
        return len(pending)

    def _mark_failure(
        self, session: Session, entries: list[OutboxEntry], error: str
    ) -> None:
        moment = utcnow()
        for entry in entries:
            entry.attempts = (entry.attempts or 0) + 1
            entry.last_attempt_at = moment
            entry.last_error = error[:500]
            entry.next_attempt_at = moment + dt.timedelta(
                seconds=_backoff_seconds(entry.attempts)
            )
            if entry.attempts >= MAX_DELIVERY_ATTEMPTS:
                # Jimgina tashlab yuborilmaydi — dead-letter'da ko'rinadi.
                entry.state = DeliveryState.DEAD_LETTER
                session.add(DeadLetter(
                    event_id=entry.event_id,
                    sender_device_id=self._device_id,
                    channel=entry.channel,
                    reason="MAX_ATTEMPTS",
                    detail=error[:500],
                ))
                self.stats.dead_lettered += 1

    @staticmethod
    def _event_to_dict(event: EventLog) -> dict[str, Any]:
        """Hodisani sim ustidagi shaklga aylantiradi.

        Vaqt **Unix millisekund** (butun son) sifatida uzatiladi, ISO matn
        emas. Sabab: ISO matnda vaqt mintaqasi, aniqlik va formatlash
        farqlari bor — Python `2026-08-23T10:00:00+00:00`, Kotlin esa
        `2026-08-23T10:00Z` yozishi mumkin va ikkalasi bir xil daqiqani
        boshqacha ifodalaydi. Butun son bunday farqlarga o'rin qoldirmaydi.

        `None` qiymatlar CBOR'ga umuman KIRITILMAYDI: Kotlin tomonida
        `null` va "maydon yo'q" bir xil ma'noga ega bo'lishi kerak.
        """
        wire: dict[str, Any] = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "schema_version": event.schema_version,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "occurred_at_ms": int(event.occurred_at.timestamp() * 1000),
            "logical_timestamp": event.logical_timestamp,
            "device_sequence": event.device_sequence,
            "payload": event.payload,
        }
        for key, value in (
            ("actor_id", event.actor_id),
            ("correlation_id", event.correlation_id),
            ("causation_id", event.causation_id),
            ("idempotency_key", event.idempotency_key),
        ):
            if value is not None:
                wire[key] = value
        return wire

    # --- kirish yo'nalishi ------------------------------------------------

    def handle_inbound(self, wire: bytes, channel: Channel | None = None) -> None:
        """Kelgan xabarni ochadi va qo'llaydi.

        Har qanday rad etish sababi lokal yoziladi, lekin **tarmoqqa
        qaytarilmaydi** (AETHER-Q N15 — oracle himoyasi).
        """
        # BOOT-1 (qurilmani ulash) DES-1 EMAS: yangi qurilmada epoch
        # kaliti hali yo'q, shuning uchun uni DES-1 bilan ocholmaymiz.
        # U faqat `protocol-control` kanalida keladi.
        if channel is Channel.PROTOCOL_CONTROL:
            self._handle_bootstrap(wire)
            return

        # O'Z AKS-SADOMIZ — muhrni OCHMASDAN tashlanadi.
        #
        # Broker xabarni barcha obunachilarga, shu jumladan
        # yuboruvchining o'ziga ham qaytaradi. Uni ochishga urinish
        # replay oynasiga tushadi va SOXTA hujum yozuvi yaratadi:
        # jonli sinovda 3 daqiqada 83 ta shunday yozuv to'plandi.
        # Haqiqiy hujum ular orasida ko'rinmay qolardi.
        if des1.peek_sender_device_id(wire) == self._device_id:
            return

        try:
            opened = self._provider.open_message(wire)
        except AetherQError as exc:
            self._dead_letter(reason=exc.reason, channel=channel, size=len(wire))
            self.stats.rejected += 1
            self.stats.note_rejection(exc.reason.name)
            return

        # Ikkinchi to'siq — endi AUTENTIFIKATSIYALANGAN qiymat bo'yicha.
        # Yuqoridagi tekshiruv tez, lekin ishonchsiz headerga tayanadi;
        # bu esa qat'iy. Ikkalasi ham kerak.
        if opened.sender_device_id == self._device_id:
            return

        if opened.content_type is ContentType.EVENT_BATCH:
            self._handle_event_batch(opened)
        elif opened.content_type is ContentType.ACK:
            self._handle_ack(opened)
        elif opened.content_type is ContentType.SYNC_DIGEST:
            self._handle_digest(opened)
        elif opened.content_type is ContentType.SYNC_REQUEST:
            self._handle_sync_request(opened)
        else:
            logger.debug("Qo'llanmaydigan content_type: %s", opened.content_type)

    def _handle_event_batch(self, opened: OpenedEnvelope) -> None:
        try:
            body = cbor2.loads(opened.payload)
            events = body["events"]
        except Exception:
            self._dead_letter(reason=RejectReason.SCHEMA_INVALID,
                              channel=Channel.EVENTS, size=len(opened.payload))
            self.stats.rejected += 1
            return

        applied_ids: list[str] = []
        with self._session_factory() as session:
            for item in events:
                self.stats.received_events += 1
                record = self._store.append_remote(
                    session,
                    event_id=item["event_id"],
                    event_type=item["event_type"],
                    schema_version=int(item.get("schema_version", 1)),
                    aggregate_type=item["aggregate_type"],
                    aggregate_id=item["aggregate_id"],
                    actor_id=item.get("actor_id"),
                    sender_device_id=opened.sender_device_id,
                    sender_sequence=int(item["device_sequence"]),
                    occurred_at=_from_millis(item["occurred_at_ms"]),
                    logical_timestamp=item["logical_timestamp"],
                    payload=item["payload"],
                    epoch=opened.epoch,
                    correlation_id=item.get("correlation_id"),
                    causation_id=item.get("causation_id"),
                    idempotency_key=item.get("idempotency_key"),
                )
                if record is None:
                    # Takror — biznes natijasi IKKINCHI marta qo'llanmaydi.
                    self.stats.duplicates += 1
                    applied_ids.append(item["event_id"])
                    continue
                applied_ids.append(item["event_id"])

            # Butun batch yozilgandan KEYIN qo'llaymiz. Sabab: batch ichida
            # ORDER_CREATED va ORDER_STATE_CHANGED birga kelishi mumkin,
            # yoki mahsulot buyurtmadan keyin turishi mumkin. `drain`
            # bog'liqlik tartibini o'zi hal qiladi.
            result = self._projector.drain(session)
            self.stats.applied += result.applied
            self.stats.conflicts += result.conflicts
            self.stats.rejected += result.rejected

            self._advance_checkpoint(session, opened.sender_device_id, events)
            session.commit()

        if applied_ids:
            self._send_ack(opened.sender_device_id, applied_ids)

    def _advance_checkpoint(
        self, session: Session, peer_device_id: bytes, events: list[dict]
    ) -> None:
        """Peer bo'yicha checkpoint'ni oldinga suradi.

        DIQQAT: checkpoint faqat **uzluksiz** ketma-ketlik uchun suriladi.
        Agar 5 va 7 kelib, 6 kelmagan bo'lsa, checkpoint 5 da qoladi —
        aks holda 6 abadiy yo'qolardi.
        """
        if not events:
            return
        checkpoint = session.get(SyncCheckpoint, peer_device_id)
        if checkpoint is None:
            # DIQQAT: ustun default'i faqat INSERT paytida qo'llanadi, ya'ni
            # flush'gacha maydon `None` bo'ladi. Shuning uchun qiymatni
            # ATAYLAB beramiz — aks holda `None + 1` bilan yiqilamiz.
            checkpoint = SyncCheckpoint(
                peer_device_id=peer_device_id, last_applied_sequence=0
            )
            session.add(checkpoint)

        seen = sorted(int(item["device_sequence"]) for item in events)
        current = checkpoint.last_applied_sequence or 0
        for sequence in seen:
            if sequence == current + 1:
                current += 1
            elif sequence <= current:
                continue
            else:
                break  # bo'shliq bor — to'xtaymiz
        checkpoint.last_applied_sequence = current
        checkpoint.last_sync_at = utcnow()

        peer = session.get(PeerDevice, peer_device_id)
        if peer is not None:
            peer.last_applied_sequence = current
            peer.last_seen_at = utcnow()

    # --- ACK --------------------------------------------------------------

    def _send_ack(self, target_device_id: bytes, event_ids: list[str]) -> None:
        """Ilova darajasidagi ACK — «men buni QO'LLADIM»."""
        if not self._transport.is_connected():
            return
        try:
            envelope = self._provider.seal_message(
                cbor2.dumps({"applied": event_ids}), ContentType.ACK
            )
            self._transport.publish(
                envelope, Channel.ACKS, target_device_id=target_device_id
            )
            self.stats.acks_sent += 1
        except (AetherQError, Exception) as exc:
            logger.debug("ACK yuborilmadi: %s", exc)

    def _handle_ack(self, opened: OpenedEnvelope) -> None:
        try:
            applied = cbor2.loads(opened.payload)["applied"]
        except Exception:
            return

        self.stats.acks_received += 1
        with self._session_factory() as session:
            rows = session.execute(
                select(OutboxEntry).where(OutboxEntry.event_id.in_(applied))
            ).scalars().all()
            for entry in rows:
                entry.state = DeliveryState.PEER_APPLIED
            session.commit()

    # --- anti-entropy ------------------------------------------------------

    def build_digest(self) -> dict[str, int]:
        """Bizdagi har qurilma bo'yicha eng yuqori `seq`."""
        with self._session_factory() as session:
            return {
                device_id.hex(): highest
                for device_id, highest in self._store.highest_sequence_by_device(
                    session
                ).items()
            }

    def send_digest(self) -> None:
        """O'z digest'ini e'lon qiladi — peer yetishmaganini aniqlaydi."""
        if not self._transport.is_connected():
            return
        envelope = self._provider.seal_message(
            cbor2.dumps({"digest": self.build_digest()}), ContentType.SYNC_DIGEST
        )
        self._transport.publish(envelope, Channel.SYNC_REQUESTS)

    def _handle_digest(self, opened: OpenedEnvelope) -> None:
        """Peer digest'ini ko'rib IKKI tomonlama ish qiladi.

        1. **Tortish (pull):** bizda yo'q, peer'da bor hodisalarni so'raymiz.
        2. **Itarish (push):** peer'da yo'q, bizda bor hodisalarni yuboramiz.

        Ikkalasi ham kerak. Faqat tortish bo'lsa, hodisani YO'QOTGAN
        tomon o'zi digest yuborishi shart bo'lardi — lekin u nimani
        yo'qotganini bilmaydi (yo'qolgan xabar haqida xabari yo'q).
        Itarish shu bo'shliqni yopadi.
        """
        try:
            remote = cbor2.loads(opened.payload)["digest"]
        except Exception:
            return

        if not self._transport.is_connected():
            return

        local = self.build_digest()

        # 1. Tortish.
        wanted: dict[str, list[int]] = {}
        for device_hex, remote_highest in remote.items():
            local_highest = local.get(device_hex, 0)
            if remote_highest > local_highest:
                wanted[device_hex] = [local_highest + 1, remote_highest]

        if wanted:
            envelope = self._provider.seal_message(
                cbor2.dumps({"ranges": wanted}), ContentType.SYNC_REQUEST
            )
            self._transport.publish(
                envelope, Channel.SYNC_REQUESTS,
                target_device_id=opened.sender_device_id,
            )

        # 2. Itarish.
        missing_for_peer: dict[str, list[int]] = {}
        for device_hex, local_highest in local.items():
            remote_highest = remote.get(device_hex, 0)
            if local_highest > remote_highest:
                missing_for_peer[device_hex] = [remote_highest + 1, local_highest]

        if missing_for_peer:
            self._push_ranges(missing_for_peer, opened.sender_device_id)

    def _push_ranges(
        self, ranges: dict[str, list[int]], target_device_id: bytes
    ) -> None:
        """Ko'rsatilgan oraliqdagi hodisalarni peer'ga qayta yuboradi."""
        batch: list[dict[str, Any]] = []
        with self._session_factory() as session:
            for device_hex, (start, end) in ranges.items():
                events = self._store.events_in_range(
                    session, bytes.fromhex(device_hex), int(start), int(end),
                    limit=MAX_BATCH_EVENTS,
                )
                batch.extend(self._event_to_dict(event) for event in events)

        if not batch:
            return

        # Qayta muhrlanadi (yangi nonce — replay oynasidan o'tadi), lekin
        # `event_id` o'zgarmaydi, ya'ni qabul qiluvchi dedup qiladi.
        envelope = self._provider.seal_message(
            cbor2.dumps({"events": batch}), ContentType.EVENT_BATCH
        )
        self._transport.publish(
            envelope, Channel.SYNC_RESPONSES, target_device_id=target_device_id
        )

    def _handle_sync_request(self, opened: OpenedEnvelope) -> None:
        """Yetishmayotgan oraliqni topib, qayta yuboradi."""
        try:
            ranges = cbor2.loads(opened.payload)["ranges"]
        except Exception:
            return

        if not self._transport.is_connected():
            return
        self._push_ranges(
            {k: list(v) for k, v in ranges.items()}, opened.sender_device_id
        )

    # --- qurilmani ulash (BOOT-1) -----------------------------------------

    def attach_provisioning(self, service: object) -> None:
        """Ulash xizmatini ulaydi (desktop tomonida)."""
        self._provisioning = service

    def _handle_bootstrap(self, wire: bytes) -> None:
        """JOIN_REQUEST ni qayta ishlaydi va javob yuboradi.

        Ulash xizmati ulanmagan bo'lsa (masalan telefonda) xabar
        e'tiborsiz qoldiriladi — bu xato emas.
        """
        service = getattr(self, "_provisioning", None)
        if service is None:
            return

        from distribos.aether_q import boot1
        from distribos.aether_q.onboarding import OnboardingError

        try:
            if boot1.peek_kind(wire) is not boot1.Boot1Kind.JOIN_REQUEST:
                return
        except boot1.Boot1Error:
            return

        try:
            with self._session_factory() as session:
                outcome = service.handle_join_request(session, wire)
                session.commit()
        except (OnboardingError, boot1.Boot1Error) as exc:
            # Sabab tarmoqqa qaytarilmaydi — faqat lokal jurnal.
            logger.warning("Qurilmani ulash rad etildi: %s", exc)
            self.stats.note_rejection("JOIN_REJECTED")
            return

        if not self._transport.is_connected():
            logger.warning("Ulash javobi yuborilmadi: ulanish yo'q")
            return

        # Javob DES-1 emas, xom BOOT-1 — telefonda hali epoch kaliti yo'q.
        self._transport.publish_raw(
            outcome.response_wire, Channel.PROTOCOL_CONTROL,
        )
        logger.info("Qurilma ulandi (tasdiq kutmoqda): %s", outcome.display_name)

    # --- diagnostika ------------------------------------------------------

    def _dead_letter(
        self, *, reason: RejectReason, channel: Channel | None, size: int
    ) -> None:
        with self._session_factory() as session:
            session.add(DeadLetter(
                channel=channel.value if channel else "unknown",
                reason=reason.name,
                raw_size_bytes=size,
            ))
            session.commit()
        self.stats.dead_lettered += 1

    def queue_depth(self) -> tuple[int, int]:
        """`(outbox, dead_letter)` — diagnostika oynasi uchun."""
        from sqlalchemy import func

        with self._session_factory() as session:
            outbox = session.execute(
                select(func.count()).select_from(OutboxEntry).where(
                    OutboxEntry.state.notin_(
                        (DeliveryState.PEER_APPLIED, DeliveryState.DEAD_LETTER)
                    )
                )
            ).scalar_one()
            dead = session.execute(
                select(func.count()).select_from(DeadLetter).where(
                    DeadLetter.resolved_at.is_(None)
                )
            ).scalar_one()
        return int(outbox), int(dead)


def _from_millis(value: int) -> dt.datetime:
    """Unix millisekunddan tz-aware UTC datetime.

    tzinfo DOIM qo'yiladi: naive datetime bazadagi timestamptz bilan
    solishtirilganda jimgina noto'g'ri natija beradi.
    """
    return dt.datetime.fromtimestamp(int(value) / 1000, tz=dt.UTC)
