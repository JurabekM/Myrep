"""MQTT transport: operatsiyalarni shifrlab nashr qiladi, boshqa qurilmalardan olib qo'llaydi.

Broker manzili sozlamada (production: broker.hivemq.com, TLS 8883). Testda lokal Mosquitto.
"""

import logging
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import paho.mqtt.client as mqtt

from .crypto import DecryptionError, open_envelope, seal, topic_for

log = logging.getLogger(__name__)


class MqttSync:
    def __init__(
        self,
        key: bytes,
        *,
        device_id: str,
        apply_op: Callable[[dict[str, Any]], bool],
        host: str = "broker.hivemq.com",
        port: int = 8883,
        tls: bool = True,
    ) -> None:
        """apply_op(op) -> True agar operatsiya yangi bo'lib qo'llangan bo'lsa (dedupe mahalliy bazada)."""
        self._key = key
        self._topic = topic_for(key)
        self._device_id = device_id
        self._apply = apply_op
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

    def start(self, timeout: float = 10.0) -> None:
        self._client.connect(self._host, self._port, keepalive=30)
        self._client.loop_start()
        if not self._subscribed.wait(timeout):
            raise TimeoutError("MQTT obuna tasdiqlanmadi")

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def publish(
        self,
        op_type: str,
        store_id: str,
        payload: dict[str, Any],
        *,
        op_id: str | None = None,
    ) -> dict[str, Any]:
        """Operatsiyani shifrlab yuboradi. op_id berilsa (masalan, savdo id'si), qayta yuborish dublikat emas.

        Qaytaradi: yuborilgan ochiq operatsiya. Ulanmagan bo'lsa, xato ko'tariladi.
        """
        if not self._connected:
            raise ConnectionError("MQTT broker bilan ulanmagan")
        op = {
            "op_id": op_id or str(uuid.uuid4()),
            "type": op_type,
            "device": self._device_id,
            "ts": datetime.now(UTC).isoformat(),
            "store_id": store_id,
            "payload": payload,
        }
        info = self._client.publish(self._topic, seal(self._key, op, self._topic), qos=1)
        info.wait_for_publish(timeout=10)
        return op

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
        self._apply(op)
