"""Ko'p qurilmali sinov stendi.

Haqiqiy brokerga ULANMAYDI (ADR-0002): CI `broker.hivemq.com` ga bog'liq
bo'lmasligi kerak. Buning o'rniga `LoopbackBus` MQTT ning **yomon**
xulqini ataylab taqlid qiladi — dublikat, tartib buzilishi, uzilish,
kechikish. Sinxronizatsiya mantiqi shu sharoitda to'g'ri ishlashi kerak.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from distribos.aether_q.provider import ContentType, SealedEnvelope
from distribos.aether_q.real import (
    DeviceKeyMaterial,
    RealAetherQProvider,
    generate_device_keys,
)
from distribos.application.command_service import CommandService
from distribos.application.projector import Projector
from distribos.domain.ids import HybridClock, new_device_id
from distribos.mqtt.topics import Channel, TopicSpace
from distribos.persistence.base import Database
from distribos.persistence.models import (
    DeviceState,
    EpochKeyRecord,
    PeerDevice,
)
from distribos.persistence.triggers import install_triggers
from distribos.sync.engine import SyncEngine
from distribos.sync.event_store import EventStore


@dataclass
class LoopbackBus:
    """Brokersiz avtobus — MQTT ning nosoz xulqini taqlid qiladi."""

    #: `device_id` -> handler
    subscribers: dict[bytes, object] = field(default_factory=dict)
    online: set[bytes] = field(default_factory=set)
    #: Offline qurilmalar uchun navbat.
    queued: list[tuple[bytes, bytes | None, Channel, bytes]] = field(default_factory=list)

    duplicate_factor: int = 1
    reorder: bool = False
    #: Yetkazilgan xabarlar tarixi (audit va tekshiruv uchun).
    log: list[tuple[bytes, Channel, int]] = field(default_factory=list)
    #: Simga chiqqan XOM baytlar — «ochiq matn sizib chiqdimi» testi uchun.
    wire_log: list[bytes] = field(default_factory=list)

    def register(self, device_id: bytes, handler: object) -> None:
        self.subscribers[device_id] = handler
        self.online.add(device_id)

    def set_online(self, device_id: bytes, value: bool) -> None:
        if value:
            self.online.add(device_id)
            self._flush(device_id)
        else:
            self.online.discard(device_id)

    #: Yetkazishga tayyor, lekin hali topshirilmagan xabarlar.
    #: Haqiqiy MQTT ASINXRON: publish qaytgach xabar hali yo'lda bo'ladi.
    #: Sinxron yetkazish qabul qiluvchidagi xatoni jo'natuvchining
    #: «publish muvaffaqiyatsiz» xatosiga aylantirib, xatolarni yashirardi.
    inflight: list[tuple[bytes, Channel, bytes]] = field(default_factory=list)

    def publish(
        self, sender: bytes, envelope: SealedEnvelope, channel: Channel,
        target: bytes | None = None,
    ) -> None:
        self.log.append((sender, channel, len(envelope.wire)))
        self.wire_log.append(envelope.wire)
        recipients = [target] if target is not None else [
            device for device in self.subscribers if device != sender
        ]
        for recipient in recipients:
            if recipient is None or recipient == sender:
                continue
            if recipient in self.online and sender in self.online:
                self.inflight.append((recipient, channel, envelope.wire))
            else:
                self.queued.append((recipient, sender, channel, envelope.wire))

    def publish_raw(self, sender: bytes, wire: bytes, channel: Channel) -> None:
        """Muhrlanmagan BOOT-1 baytlari."""
        self.log.append((sender, channel, len(wire)))
        self.wire_log.append(wire)
        for recipient in self.subscribers:
            if recipient == sender:
                continue
            if recipient in self.online and sender in self.online:
                self.inflight.append((recipient, channel, wire))
            else:
                self.queued.append((recipient, sender, channel, wire))

    def pump(self, rounds: int = 10) -> int:
        """Yo'ldagi xabarlarni yetkazadi. Yetkazilgan xabarlar sonini qaytaradi."""
        delivered = 0
        for _ in range(rounds):
            if not self.inflight:
                break
            batch = list(self.inflight)
            self.inflight.clear()
            if self.reorder:
                batch.reverse()
            for recipient, channel, wire in batch:
                delivered += self._deliver(recipient, channel, wire)
        return delivered

    def _deliver(self, recipient: bytes, channel: Channel, wire: bytes) -> int:
        handler = self.subscribers.get(recipient)
        if handler is None:
            return 0
        count = 0
        for _ in range(self.duplicate_factor):
            handler(wire, channel)  # type: ignore[operator]
            count += 1
        return count

    def _flush(self, device_id: bytes) -> None:
        """Qurilma qaytdi — navbatdagi xabarlar yo'lga chiqadi."""
        pending = [item for item in self.queued if item[0] == device_id]
        self.queued = [item for item in self.queued if item[0] != device_id]
        if self.reorder:
            pending.reverse()
        for recipient, sender, channel, wire in pending:
            if sender is None or sender in self.online:
                self.inflight.append((recipient, channel, wire))
            else:
                self.queued.append((recipient, sender, channel, wire))


class BusTransport:
    """`Transport` protokolining stend uchun implementatsiyasi."""

    def __init__(self, bus: LoopbackBus, device_id: bytes) -> None:
        self._bus = bus
        self._device_id = device_id
        self.connected = True

    def publish(
        self, envelope: SealedEnvelope, channel: Channel, *, partition: str = "0",
        target_device_id: bytes | None = None, correlation_data: bytes | None = None,
        response_topic: str | None = None, message_expiry_seconds: int | None = None,
    ) -> int:
        if not self.connected:
            raise ConnectionError("offline")
        self._bus.publish(self._device_id, envelope, channel, target_device_id)
        return 0

    def publish_raw(self, wire: bytes, channel: Channel) -> int:
        """FAQAT BOOT-1 uchun — qurilmani ulashda epoch kaliti hali yo'q."""
        if channel is not Channel.PROTOCOL_CONTROL:
            raise ValueError("publish_raw faqat protocol-control uchun")
        if not self.connected:
            raise ConnectionError("offline")
        self._bus.publish_raw(self._device_id, wire, channel)
        return 0

    def is_connected(self) -> bool:
        return self.connected and self._device_id in self._bus.online


@dataclass
class Node:
    """Bitta qurilma: baza, kalitlar, provayder, dvigatel."""

    name: str
    device_id: bytes
    tenant_id: bytes
    database: Database
    keys: DeviceKeyMaterial
    provider: RealAetherQProvider
    store: EventStore
    engine: SyncEngine
    transport: BusTransport
    topics: TopicSpace
    command: CommandService

    def receive(self, wire: bytes, channel: Channel) -> None:
        self.engine.handle_inbound(wire, channel)

    def set_online(self, value: bool) -> None:
        self.transport.connected = value
        self.engine_bus.set_online(self.device_id, value)  # type: ignore[attr-defined]

    def sync(self, rounds: int = 4) -> None:
        """Outbox'ni bo'shatadi va xabarlarni yetkazadi.

        Bir necha aylanish: javob (ACK), sync-request va uning javobi ham
        o'z navbatida yuborilishi kerak.
        """
        bus: LoopbackBus = self.engine_bus  # type: ignore[attr-defined]
        for _ in range(rounds):
            published = self.engine.publish_pending()
            delivered = bus.pump()
            if published == 0 and delivered == 0:
                break

    def project_pending(self) -> None:
        """Kechiktirilgan hodisalarni qayta ko'radi."""
        with self.database.unit_of_work() as session:
            self.command.replay_pending(session)


def build_node(
    name: str, tenant_id: bytes, bus: LoopbackBus, *, epoch_root: bytes | None = None,
    epoch: int = 1, key_id: int = 1, profile_id: int = 0x01,
) -> Node:
    """Yangi qurilma yaratadi va avtobusga ulaydi."""
    from distribos.infrastructure.secret_store import default_secret_store
    from distribos.aether_q.real import _key_context

    database = Database.in_memory()
    database.create_all()
    install_triggers(database.engine)

    device_id = new_device_id()
    keys = generate_device_keys(device_id)

    # Epoch kaliti — haqiqiy oqimda AETHER-Q sessiyasi orqali tarqatiladi
    # (ADR-0001, 1-qatlam). Stendda uni to'g'ridan-to'g'ri joylaymiz.
    root = epoch_root if epoch_root is not None else os.urandom(32)
    store_secret = default_secret_store(allow_insecure=True)
    with database.unit_of_work() as session:
        session.add(EpochKeyRecord(
            epoch=epoch, key_id=key_id, tenant_id=tenant_id,
            root_secret_wrapped=store_secret.wrap(root, _key_context(epoch, key_id)),
            profile_id=profile_id, is_current=True,
        ))

    provider = RealAetherQProvider(
        tenant_id=tenant_id, keys=keys, session_factory=database.session,
        profile_id=profile_id,
    )
    event_store = EventStore(device_id, tenant_id, HybridClock(device_id.hex()[:8]))
    transport = BusTransport(bus, device_id)
    command = CommandService(event_store, Projector(), actor_role="owner")
    engine = SyncEngine(
        device_id=device_id, store=event_store, provider=provider,
        transport=transport, session_factory=database.session,
        projector=Projector(),
    )

    node = Node(
        name=name, device_id=device_id, tenant_id=tenant_id, database=database,
        keys=keys, provider=provider, store=event_store, engine=engine,
        transport=transport, topics=TopicSpace.create(tenant_id, "test"),
        command=command,
    )
    node.engine_bus = bus  # type: ignore[attr-defined]
    bus.register(device_id, node.receive)
    return node


def introduce(*nodes: Node) -> None:
    """Qurilmalarni bir-biriga tanitadi (provisioning natijasi).

    Haqiqiy oqimda bu QR onboarding + AETHER-Q sessiyasi orqali bo'ladi.
    """
    for node in nodes:
        with node.database.unit_of_work() as session:
            for peer in nodes:
                if session.get(PeerDevice, peer.device_id) is not None:
                    continue
                session.add(PeerDevice(
                    device_id=peer.device_id,
                    tenant_id=peer.tenant_id,
                    display_name=peer.name,
                    platform="desktop" if "desktop" in peer.name else "android",
                    role="owner" if "desktop" in peer.name else "agent",
                    sign_public_key=peer.keys.sign_public_key,
                    kem_public_key=peer.keys.kem_public_key,
                    state=DeviceState.ACTIVE,
                    is_full_replica="desktop" in peer.name,
                ))


def shared_tenant_setup(
    *names: str, bus: LoopbackBus | None = None
) -> tuple[LoopbackBus, bytes, list[Node]]:
    """Bitta tenant, umumiy epoch kaliti bilan bir nechta qurilma."""
    from distribos.domain.ids import new_tenant_id

    channel = bus or LoopbackBus()
    tenant_id = new_tenant_id()
    root = os.urandom(32)
    nodes = [build_node(name, tenant_id, channel, epoch_root=root) for name in names]
    introduce(*nodes)
    return channel, tenant_id, nodes


__all__ = [
    "BusTransport",
    "Channel",
    "ContentType",
    "LoopbackBus",
    "Node",
    "build_node",
    "introduce",
    "shared_tenant_setup",
]
