"""Modbus: registrlarni davriy o'qish va yozish. Sinxron klient alohida oqimda ishlaydi."""

import asyncio
import time
from collections.abc import Callable
from typing import Any

from pymodbus.client import ModbusSerialClient, ModbusTcpClient
from pymodbus.client.mixin import ModbusClientMixin
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse

from .models import DataType, ModbusDevice, Register

Client = ModbusTcpClient | ModbusSerialClient
ValueSink = Callable[[str, dict[str, float]], None]

_DATATYPE = ModbusClientMixin.DATATYPE
_TYPES: dict[DataType, Any] = {
    "uint16": _DATATYPE.UINT16,
    "int16": _DATATYPE.INT16,
    "uint32": _DATATYPE.UINT32,
    "int32": _DATATYPE.INT32,
    "float32": _DATATYPE.FLOAT32,
}
_WORDS: dict[DataType, int] = {"uint16": 1, "int16": 1, "uint32": 2, "int32": 2, "float32": 2}


class ModbusError(Exception):
    """Qurilma javob bermadi yoki xato qaytardi."""


def _client(device: ModbusDevice) -> Client:
    if device.transport == "tcp":
        return ModbusTcpClient(device.host, port=device.port, timeout=device.timeout_s, retries=0)
    return ModbusSerialClient(
        device.serial_port, baudrate=device.baudrate, timeout=device.timeout_s, retries=0
    )


def _check(response: Any, what: str) -> Any:  # noqa: ANN401 — pymodbus javobi
    if isinstance(response, ExceptionResponse) or response.isError():
        raise ModbusError(f"{what}: {response}")
    return response


def read_register(client: Client, unit: int, register: Register) -> float:
    """Bitta qiymatni o'qiydi va `scale` ga ko'paytiradi (bloklovchi)."""
    address = register.address
    if register.kind == "coil":
        bits = _check(client.read_coils(address, count=1, device_id=unit), register.key).bits
        return 1.0 if bits[0] else 0.0
    if register.kind == "discrete":
        reply = client.read_discrete_inputs(address, count=1, device_id=unit)
        return 1.0 if _check(reply, register.key).bits[0] else 0.0
    count = _WORDS[register.type]
    if register.kind == "holding":
        reply = client.read_holding_registers(address, count=count, device_id=unit)
    else:
        reply = client.read_input_registers(address, count=count, device_id=unit)
    words: list[int] = _check(reply, register.key).registers
    raw = client.convert_from_registers(words, _TYPES[register.type])
    if isinstance(raw, int | float):
        return float(raw) * register.scale
    raise ModbusError(f"{register.key}: kutilmagan qiymat turi")


def write_value(client: Client, unit: int, register: Register, value: float) -> None:
    """Qiymatni yozadi (bloklovchi). `scale` teskari qo'llanadi."""
    if register.kind in ("input", "discrete"):
        raise ModbusError(f"{register.key}: {register.kind} faqat o'qiladi")
    if register.kind == "coil":
        _check(client.write_coil(register.address, bool(value), device_id=unit), register.key)
        return
    raw = value / register.scale if register.scale else value
    typed: int | float = raw if register.type == "float32" else round(raw)
    words = client.convert_to_registers(typed, _TYPES[register.type])
    _check(client.write_registers(register.address, words, device_id=unit), register.key)


class ModbusPoller:
    """Bitta qurilmani `interval_s` da so'rab turadi; xato bo'lsa keyingi safar qayta ulanadi."""

    def __init__(self, device: ModbusDevice, on_values: ValueSink) -> None:
        self.device = device
        self.ok = False
        self.error: str | None = None
        self.last_poll: float | None = None
        self.polls = 0
        self._on_values = on_values
        self._client: Client | None = None
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        async with self._lock:
            await asyncio.to_thread(self._close)

    def _close(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            client.close()

    def _connected(self) -> Client:
        if self._client is None:
            self._client = _client(self.device)
        if not self._client.connected and not self._client.connect():
            self._close()
            raise ModbusError("qurilmaga ulanib bo'lmadi")
        return self._client

    def _poll_once(self) -> dict[str, float]:
        client = self._connected()
        try:
            return {
                register.key: read_register(client, self.device.unit, register)
                for register in self.device.registers
            }
        except (ModbusException, ModbusError, OSError):
            self._close()  # keyingi so'rovda toza ulanish
            raise

    def _write_once(self, register: Register, value: float) -> None:
        client = self._connected()
        try:
            write_value(client, self.device.unit, register, value)
        except (ModbusException, ModbusError, OSError):
            self._close()
            raise

    async def _run(self) -> None:
        while True:
            await self.poll()
            await asyncio.sleep(self.device.interval_s)

    async def poll(self) -> None:
        async with self._lock:
            try:
                values = await asyncio.to_thread(self._poll_once)
            except (ModbusException, ModbusError, OSError) as exc:
                self.ok, self.error = False, str(exc) or type(exc).__name__
                return
        self.ok, self.error = True, None
        self.last_poll = time.time()
        self.polls += 1
        self._on_values(self.device.name, values)

    async def write(self, key: str, value: float) -> None:
        register = next((r for r in self.device.registers if r.key == key), None)
        if register is None:
            raise ModbusError(f"bunday registr yo'q: {key}")
        async with self._lock:
            try:
                await asyncio.to_thread(self._write_once, register, value)
            except (ModbusException, OSError) as exc:
                raise ModbusError(str(exc) or type(exc).__name__) from exc

    def describe(self) -> dict[str, Any]:
        device = self.device
        address = (
            f"{device.host}:{device.port}" if device.transport == "tcp" else device.serial_port
        )
        return {
            "name": device.name,
            "transport": device.transport,
            "address": address,
            "unit": device.unit,
            "interval_s": device.interval_s,
            "registers": len(device.registers),
            "ok": self.ok,
            "error": self.error,
            "last_poll": self.last_poll,
            "polls": self.polls,
        }
