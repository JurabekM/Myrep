"""MQTT transport for free public brokers (broker.hivemq.com, EMQX, Mosquitto).

Why it works without a database
-------------------------------
Replication here is *last-write-wins per row*, so the shared state is exactly
"the newest message for every row". That maps one-to-one onto MQTT **retained
messages**: each row is published to its own topic with ``retain=true``, and a
broker hands every retained message to a client the moment it subscribes.
A device that has never connected therefore receives the full snapshot, and
afterwards live changes arrive as they are published.

    <prefix>/<workspace>/<Entity>/<uid>      retain=1, QoS 1

Deletions publish a retained tombstone (``op="delete"``) so devices that connect
later also learn about them.

Trade-offs, stated plainly
--------------------------
* A public broker is **readable and writable by anyone** who knows the topic.
  Use a long random workspace key and switch the passphrase on (payloads are
  then AES-256-GCM sealed — see :mod:`app.sync.crypto`).
* Retained messages on a free broker carry no durability promise; the desktop
  remains the system of record and can re-publish everything at any time with
  "Hamma ma'lumotni yuklash".
"""

from __future__ import annotations

import json
import logging
import ssl
import threading
import time
import uuid

from app.sync.crypto import DecryptionError, decrypt, derive_key, encrypt
from app.sync.transports.base import Change, TransportError

try:  # pragma: no cover - optional dependency
    import paho.mqtt.client as mqtt

    _HAS_PAHO = True
except ImportError:  # pragma: no cover
    mqtt = None  # type: ignore[assignment]
    _HAS_PAHO = False

logger = logging.getLogger(__name__)

DEFAULT_HOST = "broker.hivemq.com"
DEFAULT_PORT = 8883
DEFAULT_PREFIX = "buildcontrol"

CONNECT_TIMEOUT = 15.0
#: Stop draining once the broker has been quiet for this long.
QUIET_PERIOD = 1.5
#: Never spend longer than this collecting the retained snapshot.
DRAIN_TIMEOUT = 20.0

#: Well-known brokers offered in the settings page.
PUBLIC_BROKERS: list[tuple[str, int, str]] = [
    ("broker.hivemq.com", 8883, "HiveMQ (ommaviy, TLS)"),
    ("broker.emqx.io", 8883, "EMQX (ommaviy, TLS)"),
    ("test.mosquitto.org", 8886, "Mosquitto (ommaviy, TLS)"),
]


class MqttTransport:
    """Retained-per-row change log carried over MQTT."""

    key = "mqtt"

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        tenant: str = "buildcontrol",
        prefix: str = DEFAULT_PREFIX,
        use_tls: bool = True,
        username: str = "",
        password: str = "",
        passphrase: str = "",
    ) -> None:
        if not _HAS_PAHO:  # pragma: no cover - dependency guard
            raise TransportError("`paho-mqtt` kutubxonasi o'rnatilmagan")
        self.host = (host or DEFAULT_HOST).strip()
        self.port = int(port or DEFAULT_PORT)
        self.tenant = (tenant or "buildcontrol").strip()
        self.prefix = (prefix or DEFAULT_PREFIX).strip().strip("/")
        self.use_tls = use_tls
        self.username = username
        self.password = password
        self._key = derive_key(passphrase, self.tenant) if passphrase else None

        self._client: mqtt.Client | None = None
        self._lock = threading.Lock()
        self._inbox: list[Change] = []
        self._last_message = 0.0
        self._connected = threading.Event()
        self._error: str = ""
        self._subscribed = threading.Event()

    # -- topics ------------------------------------------------------------- #
    @property
    def _root(self) -> str:
        return f"{self.prefix}/{self.tenant}"

    def _topic(self, entity: str, uid: str) -> str:
        return f"{self._root}/{entity}/{uid}"

    def describe(self) -> str:
        scheme = "mqtts" if self.use_tls else "mqtt"
        sealed = " · shifrlangan" if self._key else ""
        return f"{scheme}://{self.host}:{self.port}/{self._root}{sealed}"

    # -- connection --------------------------------------------------------- #
    def _connect(self) -> mqtt.Client:
        if self._client is not None:
            return self._client
        client_id = f"bc-{uuid.uuid4().hex[:12]}"
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
            clean_session=True,
        )
        if self.username:
            client.username_pw_set(self.username, self.password or None)
        if self.use_tls:
            client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)

        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_subscribe = lambda *_args, **_kwargs: self._subscribed.set()

        try:
            client.connect(self.host, self.port, keepalive=30)
        except Exception as exc:
            raise TransportError(f"Brokerga ulanib bo'lmadi: {exc}") from exc
        client.loop_start()

        if not self._connected.wait(CONNECT_TIMEOUT):
            client.loop_stop()
            raise TransportError(self._error or "Broker javob bermadi (timeout)")
        if self._error:
            client.loop_stop()
            raise TransportError(self._error)

        self._client = client
        self._subscribed.wait(5.0)
        # Give the broker a moment to flush the retained snapshot.
        self._wait_quiet()
        return client

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties=None) -> None:
        code = getattr(reason_code, "value", reason_code)
        if code != 0:
            self._error = f"Broker ulanishni rad etdi (code {code})"
            self._connected.set()
            return
        client.subscribe(f"{self._root}/#", qos=1)
        self._connected.set()

    def _on_message(self, _client, _userdata, message) -> None:
        self._last_message = time.monotonic()
        if not message.payload:
            return  # retained message cleared by another client
        try:
            body = decrypt(message.payload, self._key)
        except DecryptionError as exc:
            self._error = str(exc)
            return
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        if not isinstance(body, dict) or body.get("tenant") not in (None, self.tenant):
            return
        with self._lock:
            self._inbox.append(Change.from_wire(body, ""))

    def _wait_quiet(self) -> None:
        """Block until the broker stops sending for :data:`QUIET_PERIOD`."""
        deadline = time.monotonic() + DRAIN_TIMEOUT
        self._last_message = time.monotonic()
        while time.monotonic() < deadline:
            if time.monotonic() - self._last_message > QUIET_PERIOD:
                return
            time.sleep(0.1)

    def close(self) -> None:
        """Disconnect; safe to call more than once."""
        client, self._client = self._client, None
        if client is not None:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:  # pragma: no cover - best effort
                logger.debug("mqtt disconnect failed", exc_info=True)

    def __enter__(self) -> MqttTransport:
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    # -- transport API ------------------------------------------------------- #
    def check(self) -> str:
        try:
            self._connect()
            with self._lock:
                count = len(self._inbox)
            return f"OK · {self.host}:{self.port} · {count} ta yozuv topildi"
        finally:
            self.close()

    def push(self, changes: list[Change]) -> int:
        if not changes:
            return 0
        client = self._connect()
        for change in changes:
            body = change.to_wire(self.tenant)
            payload = (
                encrypt(body, self._key)
                if self._key
                else json.dumps(body, ensure_ascii=False).encode("utf-8")
            )
            info = client.publish(
                self._topic(change.entity, change.uid), payload, qos=1, retain=True
            )
            info.wait_for_publish(timeout=10)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                raise TransportError(f"Xabar yuborilmadi (rc={info.rc})")
        return len(changes)

    def pull(self, after: str, limit: int = 500) -> list[Change]:
        """Return everything received so far; the cursor is unused for MQTT.

        Ordering does not matter: the engine resolves by ``sync_ts``
        (last-write-wins), so a retained snapshot converges the same way a
        replayed log does.
        """
        self._connect()
        del after
        with self._lock:
            batch, self._inbox = self._inbox[:limit], self._inbox[limit:]
        if self._error:
            message, self._error = self._error, ""
            raise TransportError(message)
        return batch
