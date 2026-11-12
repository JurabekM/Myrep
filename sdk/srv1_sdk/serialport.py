"""Serial portlar: ro'yxat, bandlikni tekshirish, satrlarni o'qish (alohida oqimda), yozish.

`iot` va `electronics` plaginlari uchun umumiy. Ruxsatni (`ctx.check_serial`)
chaqiruvchi tekshiradi — bu modul faqat port bilan ishlaydi.
"""
# pyserial tip ma'lumotisiz keladi; shu fayl uning yagona iste'molchisi.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

import asyncio
import threading
from collections import deque
from collections.abc import Callable
from contextlib import suppress
from typing import Any

import serial
from serial.tools import list_ports

# `loop://` — pyserial'ning xotiradagi halqa porti: yozilgan narsa o'qishga qaytadi.
# Qurilmasiz sinash uchun; temir ham, tarmoq ham ishtirok etmaydi, shuning uchun har doim ruxsat.
LOOPBACK_URL = "loop://"
LINES_KEPT = 300
MAX_LINE_BYTES = 4096
READ_TIMEOUT_S = 0.2

LineSink = Callable[[str, str], None]


def available_ports() -> list[dict[str, Any]]:
    """Tizimdagi serial portlar (bloklovchi: `asyncio.to_thread` bilan chaqiring).

    `vid`/`pid` — USB identifikatori (USB bo'lmagan portda `None`).
    """
    return [
        {
            "port": str(port.device),
            "description": str(port.description or ""),
            "vid": port.vid if isinstance(port.vid, int) else None,
            "pid": port.pid if isinstance(port.pid, int) else None,
            "manufacturer": str(port.manufacturer or ""),
        }
        for port in sorted(list_ports.comports(), key=lambda p: str(p.device))
    ]


def probe_port(name: str) -> str | None:
    """Portni ochib-yopib ko'radi (bloklovchi). Ochilmasa — sabab matni, aks holda `None`.

    Windows'da COM port bitta egaga tegishli: boshqa dastur ochgan bo'lsa, shu yerda
    «ruxsat yo'q» xatosi chiqadi. Ochish DTR'ni o'zgartirib, platani qayta yuklashi mumkin.
    """
    try:
        port = serial.serial_for_url(name, timeout=READ_TIMEOUT_S)
    except (OSError, ValueError) as exc:
        return str(exc) or type(exc).__name__
    with suppress(OSError):
        port.close()
    return None


class SerialPort:
    """Bitta ochiq port. O'qish alohida oqimda; satrlar event loop'ga `on_line` orqali keladi."""

    def __init__(self, name: str, baudrate: int, on_line: LineSink) -> None:
        self.name = name
        self.baudrate = baudrate
        self.lines: deque[str] = deque(maxlen=LINES_KEPT)
        self.error: str | None = None
        self._on_line = on_line
        self._loop = asyncio.get_running_loop()
        self._stop = threading.Event()
        self._port: Any = None
        self._thread: threading.Thread | None = None

    @property
    def is_open(self) -> bool:
        return self._port is not None and self._thread is not None and self._thread.is_alive()

    def open(self) -> None:
        """Portni ochadi (bloklovchi). Xato bo'lsa `serial.SerialException` (OSError)."""
        self._port = serial.serial_for_url(
            self.name, baudrate=self.baudrate, timeout=READ_TIMEOUT_S
        )
        self._thread = threading.Thread(
            target=self._read_loop, name=f"serial-{self.name}", daemon=True
        )
        self._thread.start()

    def _read_loop(self) -> None:
        buffer = bytearray()
        try:
            while not self._stop.is_set():
                chunk: bytes = self._port.read(256)
                if not chunk:
                    continue
                buffer += chunk
                while b"\n" in buffer:
                    raw, _, rest = bytes(buffer).partition(b"\n")
                    buffer = bytearray(rest)
                    self._deliver(raw)
                if len(buffer) > MAX_LINE_BYTES:  # satr ajratgichsiz oqim
                    self._deliver(bytes(buffer))
                    buffer.clear()
        except (OSError, ValueError, TypeError) as exc:
            if not self._stop.is_set():
                self.error = str(exc) or type(exc).__name__
                self._deliver(f"[srv1] port uzildi: {self.error}".encode())

    def _deliver(self, raw: bytes) -> None:
        line = raw.decode("utf-8", "replace").strip("\r\n\x00 ")
        if line and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._accept, line)

    def _accept(self, line: str) -> None:
        self.lines.append(line)
        self._on_line(self.name, line)

    def write(self, data: bytes) -> int:
        """Yozadi (bloklovchi). Port yopiq bo'lsa `OSError`."""
        if self._port is None:
            raise OSError("port ochilmagan")
        written = int(self._port.write(data) or 0)
        self._port.flush()
        return written

    def close(self) -> None:
        """Oqimni to'xtatadi va portni yopadi (bloklovchi)."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(2)
        port, self._port = self._port, None
        if port is not None:
            with suppress(OSError):
                port.close()
