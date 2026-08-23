"""MQTT 5 transporti.

Bu qatlam **faqat baytlarni tashiydi**. U hech qachon ochiq biznes
ma'lumotini ko'rmaydi: `publish()` ga faqat DES-1 envelope beriladi va
buni tip tekshiruvi majburlaydi (`SealedEnvelope`).

Broker ACK (PUBACK) **biznes natijasi qo'llandi degani emas** — bu
ikkalasi alohida holat (`DeliveryState.MQTT_ACKNOWLEDGED` va
`PEER_APPLIED`). ADR-0003 ga qarang.
"""

from __future__ import annotations

import logging
import random
import ssl
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from distribos.aether_q.provider import SealedEnvelope
from distribos.infrastructure.config import MqttSettings
from distribos.mqtt.topics import CHANNEL_QOS, RETAIN_ALLOWED, Channel, TopicSpace

logger = logging.getLogger(__name__)


class MqttTransportError(RuntimeError):
    """Transport darajasidagi xato."""


@dataclass(slots=True)
class ConnectionStatus:
    """Diagnostika oynasi uchun jonli holat."""

    connected: bool = False
    broker_host: str = ""
    broker_port: int = 0
    #: Broker CONNACK'da qaytargan HAQIQIY qiymat — biz so'ragan emas.
    negotiated_session_expiry: int | None = None
    negotiated_maximum_packet_size: int | None = None
    session_present: bool = False
    last_error: str | None = None
    reconnect_attempts: int = 0
    messages_published: int = 0
    messages_received: int = 0


@dataclass(slots=True)
class InboundMessage:
    topic: str
    payload: bytes
    channel: Channel | None
    correlation_data: bytes | None = None
    response_topic: str | None = None


#: Reconnect backoff: 1s dan 5 daqiqagacha, jitter bilan.
_BACKOFF_MIN = 1.0
_BACKOFF_MAX = 300.0


def backoff_delay(attempt: int, *, rng: random.Random | None = None) -> float:
    """Exponential backoff + full jitter.

    Jitter shart: jitter'siz butun mesh brokerni bir vaqtda "uradi"
    (thundering herd) va broker bizni ban qilishi mumkin.
    """
    generator = rng or random
    ceiling = min(_BACKOFF_MAX, _BACKOFF_MIN * (2 ** min(attempt, 10)))
    return generator.uniform(_BACKOFF_MIN, ceiling)


class MqttTransport:
    """MQTT 5 klienti — paho ustidagi yupqa, xavfsiz qobiq."""

    def __init__(
        self,
        settings: MqttSettings,
        topics: TopicSpace,
        device_id: bytes,
        *,
        on_message: Callable[[InboundMessage], None] | None = None,
    ) -> None:
        self._settings = settings
        self._topics = topics
        self._device_id = device_id
        self._on_message = on_message
        self.status = ConnectionStatus(
            broker_host=settings.host, broker_port=settings.port
        )
        self._lock = threading.Lock()
        self._client = self._build_client()

    def _build_client(self) -> mqtt.Client:
        client = mqtt.Client(
            CallbackAPIVersion.VERSION2,
            client_id=f"distribos-{self._device_id.hex()[:16]}",
            protocol=mqtt.MQTTv5,
            clean_session=None,   # MQTT 5 da clean_start CONNECT'da beriladi
        )

        if self._settings.tls_required:
            context = ssl.create_default_context(cafile=str(self._settings.ca_cert_path)
                                                 if self._settings.ca_cert_path else None)
            # Sertifikat tekshiruvi HECH QACHON o'chirilmaydi.
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            if self._settings.client_cert_path and self._settings.client_key_path:
                context.load_cert_chain(
                    str(self._settings.client_cert_path),
                    str(self._settings.client_key_path),
                )
            client.tls_set_context(context)

        if self._settings.username:
            client.username_pw_set(self._settings.username, self._settings.password)

        client.on_connect = self._handle_connect
        client.on_disconnect = self._handle_disconnect
        client.on_message = self._handle_message
        client.on_publish = self._handle_publish

        # paho o'zi qayta ulanadi, lekin jitter bilan chegaralaymiz.
        client.reconnect_delay_set(min_delay=1, max_delay=int(_BACKOFF_MAX))
        return client

    # --- ulanish ---------------------------------------------------------

    def connect(self, *, timeout: float = 10.0) -> None:
        properties = Properties(PacketTypes.CONNECT)
        properties.SessionExpiryInterval = self._settings.session_expiry_seconds

        try:
            self._client.connect(
                self._settings.host,
                self._settings.port,
                keepalive=self._settings.keepalive_seconds,
                clean_start=self._settings.clean_start,
                properties=properties,
            )
        except OSError as exc:
            self.status.last_error = str(exc)
            raise MqttTransportError(f"Brokerga ulanib bo'lmadi: {exc}") from exc

        self._client.loop_start()

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
        self.status.connected = False

    # --- callback'lar ----------------------------------------------------

    def _handle_connect(self, _client, _userdata, flags, reason_code, properties=None):
        if reason_code.is_failure:
            self.status.connected = False
            self.status.last_error = str(reason_code)
            logger.warning("MQTT ulanish rad etildi: %s", reason_code)
            return

        self.status.connected = True
        self.status.last_error = None
        self.status.session_present = bool(getattr(flags, "session_present", False))

        # Broker cheklovlarini TAXMIN QILMAYMIZ — CONNACK'dan o'qiymiz.
        if properties is not None:
            expiry = getattr(properties, "SessionExpiryInterval", None)
            self.status.negotiated_session_expiry = (
                expiry if expiry is not None else self._settings.session_expiry_seconds
            )
            self.status.negotiated_maximum_packet_size = getattr(
                properties, "MaximumPacketSize", None
            )

        for topic, qos in self._topics.all_subscriptions(self._device_id):
            self._client.subscribe(topic, qos=qos)
        logger.info("MQTT ulandi, session_present=%s", self.status.session_present)

    def _handle_disconnect(self, _client, _userdata, _flags, reason_code, _properties=None):
        self.status.connected = False
        self.status.reconnect_attempts += 1
        if reason_code and getattr(reason_code, "is_failure", False):
            self.status.last_error = str(reason_code)
        logger.info("MQTT uzildi: %s", reason_code)

    def _handle_publish(self, _client, _userdata, _mid, _reason_code=None, _properties=None):
        with self._lock:
            self.status.messages_published += 1

    def _handle_message(self, _client, _userdata, message: mqtt.MQTTMessage) -> None:
        from distribos.mqtt.topics import parse_channel

        with self._lock:
            self.status.messages_received += 1

        # Hajm chegarasi transport darajasida — kripto qatlamiga katta
        # paket umuman yetib bormaydi (DoS himoyasi).
        if len(message.payload) > self._settings.max_payload_bytes:
            logger.warning(
                "Juda katta xabar tashlandi: %d bayt, topik %s",
                len(message.payload), message.topic,
            )
            return

        properties = getattr(message, "properties", None)
        inbound = InboundMessage(
            topic=message.topic,
            payload=bytes(message.payload),
            channel=parse_channel(message.topic),
            correlation_data=getattr(properties, "CorrelationData", None),
            response_topic=getattr(properties, "ResponseTopic", None),
        )
        if self._on_message is not None:
            try:
                self._on_message(inbound)
            except Exception:
                # Bitta buzuq xabar butun tinglovchini o'ldirmasligi kerak.
                logger.exception("Kelgan xabarni qayta ishlashda xato")

    # --- yuborish --------------------------------------------------------

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
    ) -> int:
        """DES-1 envelope'ni publish qiladi.

        Faqat `SealedEnvelope` qabul qilinadi — ochiq `bytes` emas. Bu
        "ochiq matn brokerga chiqib ketdi" xatosini tip darajasida
        imkonsiz qiladi.
        """
        if len(envelope.wire) > self._settings.max_payload_bytes:
            raise MqttTransportError(
                f"Envelope {len(envelope.wire)} bayt — chegara "
                f"{self._settings.max_payload_bytes}"
            )

        topic = (
            self._topics.device_topic(channel, target_device_id)
            if target_device_id is not None
            else self._topics.publish_topic(channel, partition)
        )

        properties = Properties(PacketTypes.PUBLISH)
        if correlation_data is not None:
            properties.CorrelationData = correlation_data
        if response_topic is not None:
            properties.ResponseTopic = response_topic
        if message_expiry_seconds is not None:
            properties.MessageExpiryInterval = message_expiry_seconds

        # Retained faqat presence uchun (ADR-0003): broker ma'lumotlar
        # ombori emas.
        retain = channel in RETAIN_ALLOWED

        info = self._client.publish(
            topic,
            payload=envelope.wire,
            qos=_qos_for(channel),
            retain=retain,
            properties=properties,
        )
        return int(info.mid)

    def publish_raw(self, wire: bytes, channel: Channel) -> int:
        """Muhrlanmagan baytlarni yuboradi — FAQAT qurilmani ulash uchun.

        Yangi qurilmada epoch kaliti hali yo'q, ya'ni DES-1 envelope
        ochilmaydi. BOOT-1 esa taklif siri bilan alohida shifrlangan
        (`specs/distribos-event-seal/BOOT-1.md`), ya'ni bu yerda ham
        ochiq matn tarmoqqa chiqmaydi.

        Boshqa kanallarda ishlatish TAQIQLANADI va bu qulflangan.
        """
        if channel is not Channel.PROTOCOL_CONTROL:
            raise MqttTransportError(
                f"publish_raw faqat protocol-control uchun, {channel.value} emas"
            )
        if len(wire) > self._settings.max_payload_bytes:
            raise MqttTransportError(f"{len(wire)} bayt — chegara oshdi")

        info = self._client.publish(
            self._topics.publish_topic(channel, "boot"),
            payload=wire,
            qos=CHANNEL_QOS[channel],
            retain=False,
        )
        return int(info.mid)

    def is_connected(self) -> bool:
        return self.status.connected


def _qos_for(channel: Channel) -> int:
    return CHANNEL_QOS[channel]


@dataclass(slots=True)
class LoopbackTransport:
    """Test uchun brokersiz transport.

    CI `broker.hivemq.com` ga ULANMAYDI (ADR-0002). Sinxronizatsiya
    mantiqi shu soxta transport ustida to'liq sinaladi; haqiqiy broker
    bilan integratsiya alohida, konteynerli testda.
    """

    peers: dict[bytes, Callable[[InboundMessage], None]] = field(default_factory=dict)
    delivered: list[tuple[str, bytes]] = field(default_factory=list)
    #: Xabarni yetkazmaslik (tarmoq uzilishi simulyatsiyasi).
    offline: bool = False
    #: Har xabarni necha marta yetkazish (dublikat simulyatsiyasi).
    duplicate_factor: int = 1
    #: Yetkazishni teskari tartibda qilish (out-of-order simulyatsiyasi).
    reorder: bool = False
    _pending: list[tuple[str, bytes]] = field(default_factory=list)

    def register(self, device_id: bytes, handler: Callable[[InboundMessage], None]) -> None:
        self.peers[device_id] = handler

    def publish_raw(self, topic: str, payload: bytes, sender: bytes) -> None:
        from distribos.mqtt.topics import parse_channel

        if self.offline:
            self._pending.append((topic, payload))
            return
        self._deliver(topic, payload, sender, parse_channel(topic))

    def _deliver(self, topic: str, payload: bytes, sender: bytes, channel) -> None:
        self.delivered.append((topic, payload))
        for device_id, handler in self.peers.items():
            if device_id == sender:
                continue
            for _ in range(self.duplicate_factor):
                handler(InboundMessage(topic=topic, payload=payload, channel=channel))

    def go_online(self, sender: bytes) -> None:
        """Tarmoq qaytdi — navbatdagi xabarlar yetkaziladi."""
        from distribos.mqtt.topics import parse_channel

        self.offline = False
        pending = list(reversed(self._pending)) if self.reorder else list(self._pending)
        self._pending.clear()
        for topic, payload in pending:
            self._deliver(topic, payload, sender, parse_channel(topic))
