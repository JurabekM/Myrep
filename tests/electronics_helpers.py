"""`electronics` testlari uchun: plaginni o'rnatish, soxta proshivka dasturi, soxta portlar.

Soxta dastur (`fake_flasher.py`) haqiqiy esptool/avrdude o'rnida ishga tushadi: argv'ni
chop etadi va `mode.txt` dagi buyruqqa qarab muvaffaqiyatli tugaydi, xato beradi yoki
osilib qoladi. Platalarga hech narsa yozilmaydi.
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from srv1_core.plugins.registry import BUILTIN_DIR
from srv1_sdk import serialport

FAKE_FLASHER = """
import json, os, sys, time
from pathlib import Path

here = Path(__file__).parent
mode = (here / "mode.txt").read_text(encoding="utf-8").strip()
(here / "pid.txt").write_text(str(os.getpid()), encoding="utf-8")
print("ARGV " + json.dumps(sys.argv[1:]), flush=True)
print("CWD " + json.dumps(os.getcwd()), flush=True)
if "read-flash" in sys.argv:
    Path(sys.argv[-1]).write_bytes(b"eski proshivka")
sys.stdout.write("\\x1b[32mWriting\\x1b[0m 10 %\\rWriting 55 %\\rWriting 100 %\\n")
sys.stdout.flush()
if mode == "hang":
    time.sleep(120)
if mode == "fail":
    print("A fatal error occurred: Failed to connect", flush=True)
    sys.exit(2)
print("Hash of data verified.", flush=True)
"""

# COM7 — CH340 ko'prigi (plata noma'lum), COM8 — Arduino Uno, COM9 — manifestda yo'q port.
FAKE_PORTS: list[dict[str, Any]] = [
    {"port": "COM7", "description": "USB-SERIAL CH340", "vid": 0x1A86, "pid": 0x7523}
    | {"manufacturer": "wch.cn"},
    {"port": "COM8", "description": "Arduino Uno", "vid": 0x2341, "pid": 0x0043}
    | {"manufacturer": "Arduino"},
    {"port": "COM9", "description": "Aloqa porti", "vid": None, "pid": None, "manufacturer": ""},
]


class FakeFlasher:
    def __init__(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.script = directory / "fake_flasher.py"
        self.script.write_text(FAKE_FLASHER, encoding="utf-8")
        self._mode = directory / "mode.txt"
        self._pid = directory / "pid.txt"
        self.mode("ok")

    @property
    def prefix(self) -> list[str]:
        return [getattr(sys, "_base_executable", sys.executable), str(self.script)]

    def mode(self, value: str) -> None:
        self._mode.write_text(value, encoding="utf-8")

    def pid(self) -> int | None:
        return int(self._pid.read_text(encoding="utf-8")) if self._pid.is_file() else None


def install_electronics(
    plugin_root: Path, plugin_data_dir: Path, *, serial: tuple[str, ...] = (), **config: object
) -> Path:
    """Plaginni nusxalaydi, portlarga ruxsat beradi; `firmware` papkasini qaytaradi."""
    target = plugin_root / "electronics"
    shutil.copytree(
        BUILTIN_DIR / "electronics", target, ignore=shutil.ignore_patterns("__pycache__")
    )
    manifest = target / "plugin.toml"
    text = manifest.read_text(encoding="utf-8")
    assert "serial = []" in text
    manifest.write_text(text.replace("serial = []", f"serial = {json.dumps(serial)}"), "utf-8")
    firmware = plugin_data_dir / "firmware"
    firmware.mkdir(parents=True, exist_ok=True)
    (plugin_data_dir / "electronics.json").write_text(
        json.dumps({"config": config}), encoding="utf-8"
    )
    return firmware


def fake_serial(monkeypatch: pytest.MonkeyPatch, *, busy: frozenset[str] = frozenset()) -> None:
    """Tizimda COM7–COM9 bordek ko'rsatadi; ularni ochish — xotiradagi halqa port (`loop://`).

    `busy` dagi portlar boshqa dastur ochgandek «ruxsat yo'q» xatosini beradi.
    """
    real = serialport.serial.serial_for_url

    def open_port(name: str, **kwargs: Any) -> Any:  # noqa: ANN401 — pyserial obyekti
        if name in busy:
            raise serialport.serial.SerialException(
                f"could not open port '{name}': PermissionError(13, 'Access is denied.')"
            )
        return real("loop://", **kwargs)

    monkeypatch.setattr(serialport, "available_ports", lambda: [dict(p) for p in FAKE_PORTS])
    monkeypatch.setattr(serialport.serial, "serial_for_url", open_port)
