"""MQTT topik dizayni.

Qat'iy qoida (topshiriq §8): topik nomida **hech qanday** ochiq ma'lumot
bo'lmaydi. Korxona nomi, telefon, mijoz, mahsulot, filial — hech biri.
Tenant va qurilma identifikatorlari domain-ajratilgan hash orqali opaque
qilinadi (`domain/ids.opaque_tenant_topic_id`).

Topikni bilish hech narsa bermaydi: xabar DES-1 bilan muhrlangan, ochish
uchun epoch kaliti kerak, soxta xabar kiritish uchun esa ML-DSA-65 maxfiy
kaliti kerak.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass

from distribos.domain.ids import device_topic_id, opaque_tenant_topic_id

#: Namespace ildizi. Versiya topikda — protokol yangilanishi eski
#: klientlarni jimgina buzmasligi uchun.
ROOT = "aetherq/v5.1/distribos"

#: Topik segmentida ruxsat etilgan belgilar. `+`/`#` va bo'sh segment yo'q.
_SEGMENT_RE = re.compile(r"^[a-z0-9_-]{1,64}$")


class Channel(enum.StrEnum):
    EVENTS = "events"
    ACKS = "acks"
    SYNC_REQUESTS = "sync-requests"
    SYNC_RESPONSES = "sync-responses"
    SNAPSHOT_MANIFESTS = "snapshot-manifests"
    SNAPSHOT_CHUNKS = "snapshot-chunks"
    DEVICE_STATUS = "device-status"
    REVOCATIONS = "revocations"
    PROTOCOL_CONTROL = "protocol-control"


#: Retained faqat presence uchun (ADR-0003). Boshqa hamma joyda taqiq.
RETAIN_ALLOWED: frozenset[Channel] = frozenset({Channel.DEVICE_STATUS})

#: QoS tanlovi. QoS 2 avtomatik "to'g'ri javob" deb olinmaydi: u broker
#: uchun qimmat va mobil batareyani ko'proq sarflaydi. Biz QoS 1 +
#: **ilova darajasidagi idempotentlik** ni tanlaymiz (topshiriq §7.4).
CHANNEL_QOS: dict[Channel, int] = {
    Channel.EVENTS: 1,
    Channel.ACKS: 1,
    Channel.SYNC_REQUESTS: 1,
    Channel.SYNC_RESPONSES: 1,
    Channel.SNAPSHOT_MANIFESTS: 1,
    Channel.SNAPSHOT_CHUNKS: 1,
    Channel.DEVICE_STATUS: 0,      # presence — yo'qolsa keyingisi keladi
    Channel.REVOCATIONS: 1,
    Channel.PROTOCOL_CONTROL: 1,
}


class TopicError(ValueError):
    """Topik qoidalari buzildi."""


@dataclass(frozen=True, slots=True)
class TopicSpace:
    """Bitta tenant + environment uchun topik fazosi."""

    tenant_topic_id: str
    environment: str

    @classmethod
    def create(cls, tenant_id: bytes, environment: str) -> TopicSpace:
        space = cls(opaque_tenant_topic_id(tenant_id), environment.lower())
        space.validate()
        return space

    def validate(self) -> None:
        for segment in (self.tenant_topic_id, self.environment):
            if not _SEGMENT_RE.match(segment):
                raise TopicError(f"topik segmenti yaroqsiz: {segment!r}")

    def _base(self, channel: Channel) -> str:
        return f"{ROOT}/{self.tenant_topic_id}/{self.environment}/{channel.value}"

    def publish_topic(self, channel: Channel, partition: str = "0") -> str:
        """Publish uchun to'liq topik."""
        if not _SEGMENT_RE.match(partition):
            raise TopicError(f"partition yaroqsiz: {partition!r}")
        return f"{self._base(channel)}/{partition}"

    def device_topic(self, channel: Channel, device_id: bytes) -> str:
        """Aniq qurilmaga yo'naltirilgan topik (sync javoblari, snapshot)."""
        return f"{self._base(channel)}/{device_topic_id(device_id)}"

    def subscribe_pattern(self, channel: Channel) -> str:
        """Kanalning barcha partitsiyalariga obuna.

        `#` emas, `+` ishlatiladi — bitta daraja. `#` butun daraxtni ochadi
        va kerak bo'lmagan trafikni tortadi (§8: wildcard cheklansin).
        """
        return f"{self._base(channel)}/+"

    def all_subscriptions(self, device_id: bytes) -> list[tuple[str, int]]:
        """Bu qurilma obuna bo'lishi kerak bo'lgan topiklar va QoS.

        Faqat kerakli kanallar. `snapshot-chunks` va `sync-responses`
        FAQAT o'zimizga yo'naltirilgan topikda tinglanadi — boshqa
        qurilmalarga ketayotgan katta snapshot oqimini tortmaymiz.
        """
        broadcast = (
            Channel.EVENTS,
            Channel.ACKS,
            Channel.SYNC_REQUESTS,
            Channel.DEVICE_STATUS,
            Channel.REVOCATIONS,
            Channel.PROTOCOL_CONTROL,
        )
        directed = (
            Channel.SYNC_RESPONSES,
            Channel.SNAPSHOT_MANIFESTS,
            Channel.SNAPSHOT_CHUNKS,
        )
        subscriptions = [
            (self.subscribe_pattern(channel), CHANNEL_QOS[channel])
            for channel in broadcast
        ]
        subscriptions += [
            (self.device_topic(channel, device_id), CHANNEL_QOS[channel])
            for channel in directed
        ]
        return subscriptions


def parse_channel(topic: str) -> Channel | None:
    """Topikdan kanalni ajratadi. Noma'lum bo'lsa `None`."""
    parts = topic.split("/")
    if len(parts) < 6 or not topic.startswith(ROOT):
        return None
    try:
        return Channel(parts[5])
    except ValueError:
        return None


def assert_no_plaintext_identifiers(topic: str, forbidden: list[str]) -> None:
    """Topikda maxfiy matn yo'qligini tekshiradi (test va CI uchun).

    `forbidden` — korxona nomi, telefon, mijoz nomi kabi qiymatlar.
    """
    lowered = topic.lower()
    for value in forbidden:
        candidate = value.strip().lower()
        if len(candidate) >= 3 and candidate in lowered:
            raise TopicError(
                f"Topikda ochiq ma'lumot topildi: {value!r} -> {topic!r}"
            )
