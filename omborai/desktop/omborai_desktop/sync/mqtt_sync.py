"""MQTT transport: operatsiyalarni shifrlab nashr qiladi, boshqa qurilmalardan oladi.

Broker manzili sozlamada (production: broker.hivemq.com, TLS 8883). Testda lokal Mosquitto.
"""

import logging
import threading
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt

from .crypto import DecryptionError, open_envelope, seal, topic_for
from .ops import SNAPSHOT_REQUEST

log = logging.getLogger(__name__)


class MqttSync:
    def __init__(
        self,
        key: bytes,
        *,
        device_id: str,
        apply_op: Callable[[dict[str, Any]], bool],
        on_request: Callable[[dict[str, Any]], None] | None = None,
        host: str = "broker.hivemq.com",
        port: int = 8883,
        tls: bool = True,
    ) -> None:
        """apply_op(op) -> True agar operatsiya yangi bo'lib qo'llangan bo'lsa.

        on_request(op): snapshot_request kelganda chaqiriladi (yangi qurilmaga ma'lumot uzatish uchun).
        """
        self._key = key
        self._topic = topic_for(key)
        self._device_id = device_id
        self._apply = apply_op
        self._on_request = on_request
        self._subscribed = threading.Event()
        self._connected = False
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"omborai-{device_id}",
            clean_session=False,  # uzilganda broker xabarlarni saqlaydi (broker qo'llab-quvvatlasa)
        )
        if tls:
            self._client.tls_set()
        self._client.on_connect = self._on_connect
        self._client.on_subscribe = self._on_subscribe
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        self._host, self._port = host, port

    @property
    def topic(self) -> str:
        return self._topic

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def on_request(self) -> Callable[[dict[str, Any]], None] | None:
        return self._on_request

    @on_request.setter
    def on_request(self, handler: Callable[[dict[str, Any]], None] | None) -> None:
        self._on_request = handler

    def start(self, timeout: float = 10.0) -> None:
        self._client.connect(self._host, self._port, keepalive=30)
        self._client.loop_start()
        if not self._subscribed.wait(timeout):
            raise TimeoutError("MQTT obuna tasdiqlanmadi")

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def send(self, op: dict[str, Any]) -> None:
        """Tayyor operatsiyani shifrlab nashr qiladi va broker tasdig'ini kutadi. Ulanmagan bo'lsa xato."""
        if not self._connected:
            raise ConnectionError("MQTT broker bilan ulanmagan")
        info = self._client.publish(self._topic, seal(self._key, op, self._topic), qos=1)
        info.wait_for_publish(timeout=10)

    # --- callbacks ---------------------------------------------------------

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:  # type: ignore[no-untyped-def]
        client.subscribe(self._topic, qos=1)

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties) -> None:  # type: ignore[no-untyped-def]
        self._connected = True
        self._subscribed.set()

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:  # type: ignore[no-untyped-def]
        self._connected = False

    def _on_message(self, client, userdata, msg) -> None:  # type: ignore[no-untyped-def]
        try:
            op = open_envelope(self._key, msg.payload, self._topic)
        except DecryptionError:
            log.warning("Shifrlangan xabar ochilmadi (boshqa kalit yoki buzilgan)")
            return
        if op.get("device") == self._device_id:
            return  # o'z xabarimiz: allaqachon mahalliy qo'llangan
        if op.get("type") == SNAPSHOT_REQUEST:
            if self._on_request is not None:
                self._on_request(op)
            return
        self._apply(op)
