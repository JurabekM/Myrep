"""`iot` testlari uchun: kichik MQTT 3.1.1 broker, Modbus TCP simulyatori, plaginni o'rnatish.

Broker faqat testga yetarli qismni biladi (CONNECT, SUBSCRIBE, UNSUBSCRIBE, PUBLISH
QoS 0/1, PING, retain) — bu `paho` klientini haqiqiy TCP orqali sinash uchun.
"""

import asyncio
import json
import shutil
from contextlib import suppress
from pathlib import Path
from typing import Any

from pymodbus.datastore import ModbusDeviceContext, ModbusSequentialDataBlock, ModbusServerContext
from pymodbus.server import ModbusTcpServer

from conftest import free_port
from srv1_core.plugins.registry import BUILTIN_DIR

HOLDING, INPUT, COILS = 3, 4, 1


def topic_matches(pattern: str, topic: str) -> bool:
    wanted, actual = pattern.split("/"), topic.split("/")
    for index, part in enumerate(wanted):
        if part == "#":
            return True
        if index >= len(actual) or part not in ("+", actual[index]):
            return False
    return len(wanted) == len(actual)


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte, value = value % 128, value // 128
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def _publish_packet(topic: str, payload: bytes, retain: bool = False) -> bytes:
    name = topic.encode("utf-8")
    body = len(name).to_bytes(2, "big") + name + payload
    return bytes([0x30 | (1 if retain else 0)]) + _varint(len(body)) + body


class MiniBroker:
    def __init__(self) -> None:
        self.port = free_port()
        self.received: list[tuple[str, bytes]] = []
        self.connects = 0
        self.credentials: list[tuple[str, str]] = []
        self._server: asyncio.Server | None = None
        self._clients: dict[asyncio.StreamWriter, set[str]] = {}
        self._retained: dict[str, bytes] = {}

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._serve, "127.0.0.1", self.port)

    async def stop(self) -> None:
        server, self._server = self._server, None
        if server is not None:
            server.close()
        for writer in list(self._clients):
            writer.close()
        self._clients.clear()
        if server is not None:
            await server.wait_closed()

    def subscriptions(self) -> set[str]:
        return {topic for topics in self._clients.values() for topic in topics}

    def inject(self, topic: str, payload: bytes) -> None:
        """Boshqa klient nashr qilgandek: mos obunachilarga yetkazadi."""
        self._fan_out(topic, payload)

    def _fan_out(self, topic: str, payload: bytes) -> None:
        packet = _publish_packet(topic, payload)
        for writer, topics in self._clients.items():
            if any(topic_matches(pattern, topic) for pattern in topics):
                with suppress(OSError, RuntimeError):
                    writer.write(packet)

    async def _read_packet(self, reader: asyncio.StreamReader) -> tuple[int, bytes]:
        header = (await reader.readexactly(1))[0]
        length, shift = 0, 0
        while True:
            byte = (await reader.readexactly(1))[0]
            length |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                break
        return header, await reader.readexactly(length)

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                header, body = await self._read_packet(reader)
                if not self._handle(header, body, writer):
                    break
                await writer.drain()
        except (asyncio.IncompleteReadError, OSError):
            pass
        finally:
            self._clients.pop(writer, None)
            writer.close()

    def _handle(self, header: int, body: bytes, writer: asyncio.StreamWriter) -> bool:
        kind = header >> 4
        if kind == 1:  # CONNECT
            self.connects += 1
            self._clients[writer] = set()
            self._remember_credentials(body)
            writer.write(b"\x20\x02\x00\x00")
        elif kind == 3:  # PUBLISH
            self._on_publish(header, body, writer)
        elif kind == 8:  # SUBSCRIBE
            self._on_subscribe(body, writer)
        elif kind == 10:  # UNSUBSCRIBE
            position = 2
            while position < len(body):
                size = int.from_bytes(body[position : position + 2], "big")
                self._clients[writer].discard(body[position + 2 : position + 2 + size].decode())
                position += 2 + size
            writer.write(b"\xb0\x02" + body[:2])
        elif kind == 12:  # PINGREQ
            writer.write(b"\xd0\x00")
        elif kind == 14:  # DISCONNECT
            return False
        return True

    def _remember_credentials(self, body: bytes) -> None:
        flags = body[7]
        position = 10
        fields: list[str] = []
        for _ in range(1 + bool(flags & 0x80) + bool(flags & 0x40)):
            size = int.from_bytes(body[position : position + 2], "big")
            fields.append(body[position + 2 : position + 2 + size].decode("utf-8", "replace"))
            position += 2 + size
        if flags & 0x80:
            self.credentials.append((fields[1], fields[2] if flags & 0x40 else ""))

    def _on_publish(self, header: int, body: bytes, writer: asyncio.StreamWriter) -> None:
        qos, retain = (header >> 1) & 0x03, bool(header & 0x01)
        size = int.from_bytes(body[:2], "big")
        topic = body[2 : 2 + size].decode("utf-8")
        position = 2 + size
        if qos:
            writer.write(b"\x40\x02" + body[position : position + 2])
            position += 2
        payload = body[position:]
        self.received.append((topic, payload))
        if retain:
            self._retained[topic] = payload
        self._fan_out(topic, payload)

    def _on_subscribe(self, body: bytes, writer: asyncio.StreamWriter) -> None:
        position, granted = 2, bytearray()
        added: list[str] = []
        while position < len(body):
            size = int.from_bytes(body[position : position + 2], "big")
            added.append(body[position + 2 : position + 2 + size].decode("utf-8"))
            position += 3 + size
            granted.append(0)
        self._clients[writer].update(added)
        writer.write(b"\x90" + _varint(2 + len(granted)) + body[:2] + bytes(granted))
        for topic, payload in self._retained.items():
            if any(topic_matches(pattern, topic) for pattern in added):
                writer.write(_publish_packet(topic, payload, retain=True))


class ModbusSimulator:
    """Modbus TCP qurilmasi: 0..63 manzilli registrlar va coil'lar."""

    def __init__(self, holding: list[int]) -> None:
        self.port = free_port()
        registers = ModbusSequentialDataBlock(1, [*holding, *[0] * (64 - len(holding))])
        bits = ModbusSequentialDataBlock(1, [False] * 64)
        context = ModbusServerContext(
            devices=ModbusDeviceContext(hr=registers, ir=registers, co=bits, di=bits), single=True
        )
        self._server = ModbusTcpServer(context, address=("127.0.0.1", self.port))
        self._task: asyncio.Task[Any] | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._server.serve_forever())
        for _ in range(100):
            try:
                _reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
            except OSError:
                await asyncio.sleep(0.05)
                continue
            writer.close()
            return
        raise RuntimeError("Modbus simulyatori ishga tushmadi")

    async def stop(self) -> None:
        await self._server.shutdown()
        if self._task is not None:
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def holding(self, address: int, count: int = 1) -> list[int]:
        values = await self._server.async_getValues(1, HOLDING, address, count)
        return [int(value) for value in values]

    async def set_holding(self, address: int, values: list[int]) -> None:
        await self._server.async_setValues(1, HOLDING, address, values)

    async def set_input(self, address: int, values: list[int]) -> None:
        await self._server.async_setValues(1, INPUT, address, values)

    async def coil(self, address: int) -> bool:
        return bool((await self._server.async_getValues(1, COILS, address, 1))[0])


def install_iot(plugin_root: Path, plugin_data_dir: Path, **settings: object) -> None:
    """Plaginni `plugin_root` ga nusxalaydi va `iot.json` yozadi (`settings` — yuqori daraja)."""
    target = plugin_root / "iot"
    shutil.copytree(BUILTIN_DIR / "iot", target, ignore=shutil.ignore_patterns("__pycache__"))
    manifest = target / "plugin.toml"
    text = manifest.read_text(encoding="utf-8").replace("ports = [1883]", 'ports = ["1024-65535"]')
    manifest.write_text(text, encoding="utf-8")
    plugin_data_dir.mkdir(parents=True, exist_ok=True)
    (plugin_data_dir / "iot.json").write_text(json.dumps(settings), encoding="utf-8")
