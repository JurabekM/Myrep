"""§13.2 — kanal: MQTT (ishonchsiz broker) va testlar uchun xotira kanali."""

from __future__ import annotations

import queue
import secrets
import threading
from typing import Protocol

from .protokol import mavzular


class KanalXatosi(Exception):
    pass


class Kanal(Protocol):
    def yubor(self, paket: bytes) -> None: ...
    def qabul(self, muddat: float) -> bytes | None: ...   # muddat o'tsa None
    def yop(self) -> None: ...


class XotiraKanali:
    """Ikki uchli navbat. `juft()` — (mijoz, bank)."""

    def __init__(self, kirish: queue.Queue, chiqish: queue.Queue):
        self._kir, self._chiq = kirish, chiqish
        self.yopiq = False
        self.yuborilganlar: list[bytes] = []

    @classmethod
    def juft(cls) -> tuple[XotiraKanali, XotiraKanali]:
        a, b = queue.Queue(), queue.Queue()
        return cls(a, b), cls(b, a)

    def yubor(self, paket: bytes) -> None:
        if self.yopiq:
            raise KanalXatosi("kanal yopiq")
        self.yuborilganlar.append(paket)
        self._chiq.put(paket)

    def qabul(self, muddat: float) -> bytes | None:
        try:
            return self._kir.get(timeout=max(0.0, muddat))
        except queue.Empty:
            return None

    def aralash(self, paket: bytes) -> None:
        """Test: «broker» (yoki bosqinchi) shu uchga begona paket tashlaydi."""
        self._kir.put(paket)

    def yop(self) -> None:
        self.yopiq = True


class MqttKanal:
    """paho-mqtt ≥ 2. `taraf="mijoz"` — c2b ga nashr, b2c ga obuna.
    `taraf="bank"` — teskari (faqat broker_smoke uchun oyna)."""

    def __init__(self, broker: str, port: int, bank_pk: bytes, sessiya_id: str | None = None,
                 taraf: str = "mijoz", tayyor_muddat: float = 20.0):
        import paho.mqtt.client as mqtt

        self.sessiya_id = sessiya_id or secrets.token_bytes(8).hex()
        c2b, b2c = mavzular(bank_pk, self.sessiya_id)
        self.nashr, self.obuna = (c2b, b2c) if taraf == "mijoz" else (b2c, c2b)
        self._navbat: queue.Queue[bytes] = queue.Queue()
        self._tayyor = threading.Event()
        self._xato: str | None = None
        self._oxirgi = None
        prefiks = "zarbxona-" if taraf == "mijoz" else "zarbxona-oyna-"
        self.c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                             client_id=prefiks + self.sessiya_id, clean_session=True)
        self.c.on_connect = self._on_connect
        self.c.on_subscribe = self._on_subscribe
        self.c.on_message = self._on_message
        try:
            self.c.connect(broker, port, keepalive=60)
        except OSError as e:
            raise KanalXatosi(f"brokerga ulanib bo'lmadi ({broker}:{port}): {e}") from e
        self.c.loop_start()
        # ⚠ obuna TASDIQLANMAGUNCHA hech narsa yubormaymiz (§13.2)
        if not self._tayyor.wait(tayyor_muddat):
            self.yop()
            raise KanalXatosi(self._xato or f"broker {tayyor_muddat:.0f} s ichida javob bermadi")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code.is_failure:
            self._xato = f"broker rad etdi: {reason_code}"
            self._tayyor.set()
            return
        client.subscribe(self.obuna, qos=1)

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties=None):
        if any(rc.is_failure for rc in reason_codes):
            self._xato = "obuna rad etildi"
        self._tayyor.set()

    def _on_message(self, client, userdata, msg):
        self._navbat.put(bytes(msg.payload))

    def yubor(self, paket: bytes) -> None:
        if self._xato:
            raise KanalXatosi(self._xato)
        info = self.c.publish(self.nashr, paket, qos=1)
        self._oxirgi = info
        if info.rc != 0:
            raise KanalXatosi(f"nashr qilinmadi (rc={info.rc})")

    def qabul(self, muddat: float) -> bytes | None:
        try:
            return self._navbat.get(timeout=max(0.0, muddat))
        except queue.Empty:
            return None

    def yop(self) -> None:
        # avval disconnect, keyin loop_stop — «bye» brokerga yetib borsin
        try:
            if self._oxirgi is not None:
                try:
                    self._oxirgi.wait_for_publish(timeout=3)
                except (RuntimeError, ValueError):
                    pass
            self.c.disconnect()
        finally:
            self.c.loop_stop()
