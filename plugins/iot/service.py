"""IoT xizmati: MQTT, serial va Modbus manbalaridan telemetriyani yig'adi va saqlaydi."""

import asyncio
import time
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

from srv1_sdk.context import PluginContext
from srv1_sdk.serialport import LOOPBACK_URL, SerialPort, available_ports

from .modbus import ModbusError, ModbusPoller
from .models import STORE_FILE, TOPIC_MAX, ModbusDevice, Store, load_store, save_store
from .mqtt import Broker, MqttClient
from .telemetry import Sample, TelemetryStore, parse_values

FLUSH_INTERVAL_S = 1.0
PURGE_INTERVAL_S = 3600.0
MESSAGES_KEPT = 300
PAYLOAD_PREVIEW = 500
TELEMETRY_FILE = "telemetry.db"


class IotError(Exception):
    """Amal bajarilmadi; `status` — klientga qaytadigan HTTP kodi."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def check_topic(topic: str, *, wildcards: bool) -> str:
    cleaned = topic.strip()
    if not cleaned or len(cleaned) > TOPIC_MAX or "\x00" in cleaned:
        raise IotError(400, "mavzu bo'sh yoki juda uzun")
    if not wildcards and any(char in cleaned for char in "#+"):
        raise IotError(400, "nashr mavzusida # va + bo'lmaydi")
    return cleaned


class IotService:
    def __init__(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self._store_file = ctx.data_path(STORE_FILE)
        self.store = Store()
        self._db_thread = ThreadPoolExecutor(max_workers=1, thread_name_prefix="iot-db")
        self._telemetry: TelemetryStore | None = None
        self._buffer: list[Sample] = []
        self._tasks: list[asyncio.Task[None]] = []
        self.samples_written = 0
        self.broker: Broker | None = None
        self.broker_error: str | None = None
        self.mqtt: MqttClient | None = None
        self.messages: deque[dict[str, Any]] = deque(maxlen=MESSAGES_KEPT)
        self.message_count = 0
        self.serial: dict[str, SerialPort] = {}
        self.pollers: dict[str, ModbusPoller] = {}

    # --- hayot sikli ------------------------------------------------------
    def prepare(self) -> None:
        self.store = load_store(self._store_file)

    async def _db[T](self, func: Callable[..., T], *args: Any) -> T:  # noqa: ANN401
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._db_thread, partial(func, *args))

    @property
    def telemetry(self) -> TelemetryStore:
        if self._telemetry is None:
            raise IotError(503, "telemetriya ombori hali tayyor emas")
        return self._telemetry

    async def start(self) -> None:
        self._telemetry = await self._db(TelemetryStore, self.ctx.data_path(TELEMETRY_FILE))
        await self.purge()
        self._tasks = [
            asyncio.create_task(self._every(FLUSH_INTERVAL_S, self.flush)),
            asyncio.create_task(self._every(PURGE_INTERVAL_S, self.purge)),
        ]
        await self._start_mqtt()
        for device in self.store.modbus:
            self._start_poller(device)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        for poller in self.pollers.values():
            await poller.stop()
        for port in self.serial.values():
            await asyncio.to_thread(port.close)
        if self.mqtt is not None:
            await asyncio.to_thread(self.mqtt.stop)
        if self.broker is not None:
            await self.broker.stop()
        await self.flush()
        if self._telemetry is not None:
            await self._db(self._telemetry.close)
            self._telemetry = None
        self._db_thread.shutdown(wait=False)

    async def _every(self, interval_s: float, action: Callable[[], Any]) -> None:
        while True:
            await asyncio.sleep(interval_s)
            try:
                await action()
            except Exception as exc:
                self.ctx.log("error", "iot_periodic_failed", error=f"{type(exc).__name__}: {exc}")

    # --- telemetriya --------------------------------------------------------
    def record(self, source: str, values: dict[str, float], ts: float | None = None) -> None:
        """Qiymatlarni navbatga qo'yadi (diskka `flush` yozadi) va hodisa chiqaradi."""
        if not values:
            return
        stamp = time.time() if ts is None else ts
        self._buffer += [Sample(stamp, source, key, value) for key, value in values.items()]
        self.ctx.publish("telemetry", {"source": source, "ts": stamp, **values})

    async def flush(self) -> None:
        if not self._buffer or self._telemetry is None:
            return
        batch, self._buffer = self._buffer, []
        self.samples_written += await self._db(self._telemetry.write, batch)

    async def purge(self) -> dict[str, Any]:
        cutoff = time.time() - self.store.retention_days * 86400
        removed = await self._db(self.telemetry.purge, cutoff)
        return {"removed": removed, "retention_days": self.store.retention_days}

    async def latest(self, source: str) -> list[dict[str, Any]]:
        await self.flush()
        return [sample.as_dict() for sample in await self._db(self.telemetry.latest, source)]

    async def series(
        self, source: str, key: str, minutes: float, limit: int
    ) -> list[dict[str, Any]]:
        await self.flush()
        since = time.time() - minutes * 60
        samples = await self._db(self.telemetry.series, source, key, since, limit)
        return [{"ts": sample.ts, "value": sample.value} for sample in samples]

    # --- MQTT ---------------------------------------------------------------
    async def _start_mqtt(self) -> None:
        cfg = self.store.mqtt
        if not cfg.enabled:
            return
        if cfg.manage_broker:
            self.broker = Broker(self.ctx, cfg)
            if not self.broker.available:
                self.broker_error = f"mosquitto.exe topilmadi: {self.broker.exe}"
                self.ctx.log("warning", "mosquitto_missing", path=str(self.broker.exe))
            else:
                try:
                    await self.broker.start()
                except (OSError, RuntimeError) as exc:
                    self.broker_error = str(exc)
                    self.ctx.log("error", "mosquitto_start_failed", error=str(exc))
        self.mqtt = MqttClient(cfg, self._on_mqtt_message, self._on_mqtt_state)
        self.mqtt.start()

    def mqtt_state(self) -> str:
        if not self.store.mqtt.enabled or self.mqtt is None:
            return "disabled"
        return "connected" if self.mqtt.connected else "disconnected"

    def _on_mqtt_state(self) -> None:
        self.ctx.publish("mqtt_state", {"state": self.mqtt_state()})

    def _on_mqtt_message(self, topic: str, payload: bytes) -> None:
        text = payload.decode("utf-8", "replace")
        self.message_count += 1
        self.messages.append({"ts": time.time(), "topic": topic, "payload": text[:PAYLOAD_PREVIEW]})
        self.record(f"mqtt:{topic}", parse_values(text))
        self.ctx.publish("mqtt", {"topic": topic, "payload": text[:PAYLOAD_PREVIEW]})

    def _client(self) -> MqttClient:
        if self.mqtt is None:
            raise IotError(409, "MQTT o'chirilgan (mqtt.enabled = false)")
        return self.mqtt

    def publish(self, topic: str, payload: str, qos: int, retain: bool) -> dict[str, Any]:
        client = self._client()
        cleaned = check_topic(topic, wildcards=False)
        if not client.publish(cleaned, payload.encode("utf-8"), qos=qos, retain=retain):
            raise IotError(503, "brokerga ulanmagan")
        return {"published": cleaned, "bytes": len(payload.encode("utf-8"))}

    async def subscribe(self, topic: str) -> list[dict[str, str]]:
        client = self._client()
        client.subscribe(check_topic(topic, wildcards=True))
        await self._save_subscriptions(client)
        return self.subscriptions()

    async def unsubscribe(self, topic: str) -> list[dict[str, str]]:
        client = self._client()
        if not client.unsubscribe(topic.strip()):
            raise IotError(404, f"bunday obuna yo'q: {topic}")
        await self._save_subscriptions(client)
        return self.subscriptions()

    async def _save_subscriptions(self, client: MqttClient) -> None:
        self.store.mqtt.subscriptions = list(client.subscriptions)
        await asyncio.to_thread(save_store, self._store_file, self.store)

    def subscriptions(self) -> list[dict[str, str]]:
        topics = self.mqtt.subscriptions if self.mqtt is not None else []
        return [{"topic": topic} for topic in topics]

    def message_lines(self, tail: int) -> list[str]:
        recent = list(self.messages)[-tail:]
        return [
            f"{time.strftime('%H:%M:%S', time.localtime(m['ts']))} {m['topic']}  {m['payload']}"
            for m in recent
        ]

    # --- serial -------------------------------------------------------------
    def _port(self, name: str) -> SerialPort:
        port = self.serial.get(self._port_name(name, check=False))
        if port is None:
            raise IotError(404, f"port ochilmagan: {name}")
        return port

    def _port_name(self, name: str, *, check: bool) -> str:
        cleaned = name.strip()
        if cleaned == LOOPBACK_URL:
            return cleaned
        if "://" in cleaned or "/" in cleaned or "\\" in cleaned:
            raise IotError(400, "faqat COM portlar (yoki sinov uchun loop://) ochiladi")
        return self.ctx.check_serial(cleaned) if check else cleaned.upper()

    async def open_serial(self, name: str, baudrate: int) -> dict[str, Any]:
        port_name = self._port_name(name, check=True)
        if port_name in self.serial and self.serial[port_name].is_open:
            raise IotError(409, f"port allaqachon ochiq: {port_name}")
        port = SerialPort(port_name, baudrate, self._on_serial_line)
        try:
            await asyncio.to_thread(port.open)
        except (OSError, ValueError) as exc:
            raise IotError(502, f"{port_name} ochilmadi: {exc}") from exc
        self.serial[port_name] = port
        self.ctx.log("info", "serial_opened", port=port_name, baudrate=baudrate)
        return {"port": port_name, "baudrate": baudrate, "open": True}

    async def close_serial(self, name: str) -> dict[str, Any]:
        port = self._port(name)
        await asyncio.to_thread(port.close)
        del self.serial[port.name]
        return {"port": port.name, "open": False}

    async def write_serial(self, name: str, text: str, newline: bool) -> dict[str, Any]:
        port = self._port(name)
        data = (text + ("\n" if newline else "")).encode("utf-8")
        try:
            written = await asyncio.to_thread(port.write, data)
        except (OSError, ValueError) as exc:
            raise IotError(502, f"{port.name} ga yozilmadi: {exc}") from exc
        return {"port": port.name, "bytes": written}

    def _on_serial_line(self, name: str, line: str) -> None:
        self.record(f"serial:{name}", parse_values(line))
        self.ctx.publish("serial", {"port": name, "line": line[:PAYLOAD_PREVIEW]})

    async def serial_ports(self) -> list[dict[str, Any]]:
        """Tizimdagi portlar va ochiq portlar (ruxsat belgisi bilan)."""
        allowed = set(self.ctx.manifest.permissions.serial)
        rows: dict[str, dict[str, Any]] = {
            item["port"].upper(): {**item, "port": item["port"].upper()}
            for item in await asyncio.to_thread(available_ports)
        }
        for name in self.serial:
            rows.setdefault(name, {"port": name, "description": ""})
        for name, row in rows.items():
            port = self.serial.get(name)
            row["allowed"] = name in allowed or name == LOOPBACK_URL
            row["open"] = port is not None and port.is_open
            row["baudrate"] = port.baudrate if port is not None else None
            row["error"] = port.error if port is not None else None
        return [rows[name] for name in sorted(rows)]

    def serial_lines(self, name: str, tail: int) -> list[str]:
        return list(self._port(name).lines)[-tail:]

    # --- Modbus -------------------------------------------------------------
    def _start_poller(self, device: ModbusDevice) -> None:
        poller = ModbusPoller(device, self._on_modbus_values)
        self.pollers[device.name] = poller
        if device.transport == "rtu":
            try:
                self.ctx.check_serial(device.serial_port)
            except PermissionError as exc:
                poller.error = str(exc)
                return
        poller.start()

    def _on_modbus_values(self, name: str, values: dict[str, float]) -> None:
        self.record(f"modbus:{name}", values)

    def _poller(self, name: str) -> ModbusPoller:
        poller = self.pollers.get(name)
        if poller is None:
            raise IotError(404, f"bunday qurilma yo'q: {name}")
        return poller

    async def add_modbus(self, device: ModbusDevice) -> dict[str, Any]:
        if device.name in self.pollers:
            raise IotError(409, f"bunday qurilma bor: {device.name}")
        if device.transport == "rtu":
            self.ctx.check_serial(device.serial_port)
        self.store.modbus.append(device)
        await asyncio.to_thread(save_store, self._store_file, self.store)
        self._start_poller(device)
        return self.pollers[device.name].describe()

    async def remove_modbus(self, name: str) -> dict[str, Any]:
        poller = self._poller(name)
        await poller.stop()
        del self.pollers[name]
        self.store.modbus = [device for device in self.store.modbus if device.name != name]
        await asyncio.to_thread(save_store, self._store_file, self.store)
        return {"removed": name}

    async def poll_modbus(self, name: str) -> dict[str, Any]:
        poller = self._poller(name)
        await poller.poll()
        return poller.describe()

    async def write_modbus(self, name: str, key: str, value: float) -> dict[str, Any]:
        """Qurilmaga yozadi — xavfli amal, auditga yoziladi."""
        poller = self._poller(name)
        target = f"{name}/{key}"
        try:
            await poller.write(key, value)
        except ModbusError as exc:
            await self.ctx.audit("modbus.write", target, ok=False, detail={"error": str(exc)})
            raise IotError(502, str(exc)) from exc
        await self.ctx.audit("modbus.write", target, detail={"value": value})
        await poller.poll()
        return {"device": name, "key": key, "value": value}

    # --- holat --------------------------------------------------------------
    async def status(self) -> dict[str, Any]:
        broker = self.broker
        managed = self.store.mqtt.enabled and self.store.mqtt.manage_broker
        if not managed:
            broker_state = "external" if self.store.mqtt.enabled else "disabled"
        elif broker is not None and broker.running:
            broker_state = "running"
        else:
            broker_state = "missing" if broker is not None and not broker.available else "stopped"
        return {
            "mqtt_state": self.mqtt_state(),
            "mqtt_error": self.mqtt.last_error if self.mqtt is not None else None,
            "mqtt_messages": self.message_count,
            "broker": broker_state,
            "broker_error": self.broker_error,
            "broker_pid": broker.pid if broker is not None else None,
            "samples": self.samples_written + len(self._buffer),
            "serial_open": sum(port.is_open for port in self.serial.values()),
            "modbus_devices": len(self.pollers),
            "modbus_ok": sum(poller.ok for poller in self.pollers.values()),
            "retention_days": self.store.retention_days,
        }
