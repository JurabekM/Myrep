"""`electronics` plagini: haqiqiy yadro; portlar soxta (`loop://`), proshivka dasturi — soxta
skript yoki haqiqiy esptool/avrdude (mavjud bo'lmagan platagacha). Haqiqiy plataga hech narsa
yozilmaydi."""

import asyncio
import hashlib
import json
import sqlite3
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager, closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import psutil
import pytest

from conftest import Served, serve_app
from electronics_helpers import FakeFlasher, fake_serial, install_electronics
from srv1_core.paths import DataPaths
from srv1_core.plugins.registry import BUILTIN_DIR
from srv1_sdk import serialport

API = "/api/v1/plugins/electronics/api"
AVRDUDE_EXE = BUILTIN_DIR.parent / "tools" / "avrdude" / "avrdude.exe"
BIN = b"\xe9" + bytes(range(200))
HEX = ":100000000C9434000C943E000C943E000C943E0082\n:00000001FF\n"


async def _eventually[T](
    probe: Callable[[], Awaitable[T]], accept: Callable[[T], bool], what: str, timeout_s: float = 20
) -> T:
    value = await probe()
    try:
        async with asyncio.timeout(timeout_s):
            while not accept(value):
                await asyncio.sleep(0.05)
                value = await probe()
    except TimeoutError:
        pytest.fail(f"{what}: kutilgan holat yuz bermadi, oxirgi qiymat: {value!r}")
    return value


@dataclass
class Lab:
    client: httpx.AsyncClient
    served: Served
    firmware: Path
    flasher: FakeFlasher
    paths: DataPaths

    async def get(self, path: str, **params: str | float) -> Any:  # noqa: ANN401
        response = await self.client.get(f"{API}{path}", params=params)
        assert response.status_code == 200, response.text
        return response.json()

    async def post(self, operation: str, /, **body: object) -> httpx.Response:
        return await self.client.post(f"{API}{operation}", json=body)

    async def flash(self, **body: object) -> httpx.Response:
        return await self.post("/flash", **body)

    async def finished(self, timeout_s: float = 20) -> dict[str, Any]:
        return await _eventually(
            lambda: self.get("/flash"), lambda job: job["state"] != "running", "yozish", timeout_s
        )

    async def commands(self) -> list[list[str]]:
        """Soxta dastur chop etgan argv'lar (ishga tushish tartibida)."""
        log: list[str] = await self.get("/flash/log")
        return [json.loads(line.split("ARGV ", 1)[1]) for line in log if "ARGV " in line]

    def audit(self) -> list[tuple[str, str, int]]:
        with closing(sqlite3.connect(self.paths.db_file)) as conn:
            return conn.execute(
                "SELECT action, target, ok FROM audit_log"
                " WHERE actor = 'plugin:electronics' ORDER BY id"
            ).fetchall()

    def spawned(self) -> int:
        return sum(action == "process.spawn" for action, _target, _ok in self.audit())


@asynccontextmanager
async def _lab(
    paths: DataPaths,
    plugin_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    real_tools: bool = False,
    busy: frozenset[str] = frozenset(),
    **config: object,
) -> AsyncGenerator[Lab]:
    flasher = FakeFlasher(paths.root / "fake-tool")
    tools: dict[str, object] = (
        {} if real_tools else {"esptool": flasher.prefix, "avrdude": flasher.prefix}
    )
    firmware = install_electronics(
        plugin_root,
        paths.root / "plugins" / "electronics" / "data",
        serial=("COM7", "COM8"),
        **tools,
        **config,
    )
    (firmware / "app.bin").write_bytes(BIN)
    (firmware / "sketch.hex").write_text(HEX, encoding="ascii", newline="")
    # Plagin nusxasi repozitoriydan tashqarida: `tools/` ni o'zi topa olmaydi.
    monkeypatch.setenv("SRV1_AVRDUDE_EXE", str(AVRDUDE_EXE))
    fake_serial(monkeypatch, busy=busy)
    async with serve_app(paths) as served, served.client() as client:
        yield Lab(client, served, firmware, flasher, paths)


# --- portlar va platalar --------------------------------------------------------------
async def test_ports_are_identified_by_usb_id(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with _lab(paths, plugin_root, monkeypatch) as lab:
        ports = {row["port"]: row for row in await lab.get("/ports")}
        assert (ports["COM7"]["chip"], ports["COM7"]["usb"]) == ("CH340", "1A86:7523")
        assert ports["COM7"]["board"] == ""  # ko'prik orqasidagi plata USB'dan bilinmaydi
        assert (ports["COM8"]["chip"], ports["COM8"]["board"]) == ("Arduino Uno", "uno")
        assert (ports["COM9"]["usb"], ports["COM9"]["chip"]) == ("", "")
        assert [ports[name]["allowed"] for name in ("COM7", "COM8", "COM9")] == [True, True, False]
        assert not any(row["monitor"] or row["flashing"] for row in ports.values())

        boards = {row["key"]: row for row in await lab.get("/boards")}
        assert boards["esp32"] == {
            "key": "esp32",
            "title": "ESP32",
            "tool": "esptool",
            "file": ".bin",
            "offset": "0x10000",
        }
        assert (boards["uno"]["tool"], boards["uno"]["file"]) == ("avrdude", ".hex")
        assert boards["esp8266"]["offset"] == "0x0"

        status = await lab.get("/status")
        assert (status["esptool"], status["avrdude"]) == ("custom", "custom")
        assert (status["flash_state"], status["allowed_ports"]) == ("idle", ["COM7", "COM8"])
        files = {row["name"]: row["size"] for row in await lab.get("/firmware")}
        assert files == {"app.bin": len(BIN), "sketch.hex": len(HEX)}


def test_serial_helpers_without_hardware() -> None:
    assert serialport.probe_port("loop://") is None
    reason = serialport.probe_port("COM254")
    assert reason is not None and "COM254" in reason
    for row in serialport.available_ports():
        assert {"port", "description", "vid", "pid", "manufacturer"} <= set(row)


# --- serial monitor -----------------------------------------------------------------
async def test_monitor_open_write_read_close(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with _lab(paths, plugin_root, monkeypatch) as lab:
        events = lab.served.core.bus.subscribe("plugin.electronics.serial")
        assert (await lab.post("/monitor/open", port="COM9")).status_code == 403
        for bad in ("socket://10.0.0.1:23", "..\\COM7", "/dev/ttyUSB0"):
            assert (await lab.post("/monitor/open", port=bad)).status_code == 400, bad
        assert (await lab.post("/monitor/write", port="COM7", text="x")).status_code == 404

        opened = await lab.post("/monitor/open", port="com7")
        assert opened.json() == {"port": "COM7", "baudrate": 115200, "open": True}
        assert (await lab.post("/monitor/open", port="COM7")).status_code == 409
        await lab.post("/monitor/write", port="COM7", text="salom")
        await lab.post("/monitor/write", port="COM7", text="yarim ", newline=False)
        await lab.post("/monitor/write", port="COM7", text="satr")
        lines = await _eventually(
            lambda: lab.get("/monitor/lines", port="COM7"), lambda got: len(got) == 2, "satrlar"
        )
        assert lines == ["salom", "yarim satr"]
        event = await asyncio.wait_for(anext(events), 5)
        assert event.data == {"port": "COM7", "line": "salom"}

        ports = {row["port"]: row for row in await lab.get("/ports")}
        assert (ports["COM7"]["monitor"], ports["COM7"]["baudrate"]) == (True, 115200)
        assert (await lab.get("/status"))["monitors"] == 1
        assert (await lab.post("/monitor/close", port="COM7")).json()["open"] is False
        assert (await lab.post("/monitor/close", port="COM7")).status_code == 404

        custom = await lab.post("/monitor/open", port="loop://", baudrate=9600)
        assert custom.json()["baudrate"] == 9600


# --- proshivka: soxta dastur bilan ------------------------------------------------------
async def test_flash_esp_with_backup(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with _lab(paths, plugin_root, monkeypatch) as lab:
        events = lab.served.core.bus.subscribe("plugin.electronics.flash")
        started = await lab.flash(port="COM7", board="esp32", file="app.bin", backup=True)
        assert started.status_code == 202, started.text
        assert started.json()["state"] == "running"
        job = await lab.finished()
        assert (job["state"], job["error"], job["file"]) == ("done", None, "app.bin")
        assert job["sha256"] == hashlib.sha256(BIN).hexdigest()
        assert job["size"] == len(BIN)

        backup, write = await lab.commands()
        target = lab.firmware / job["backup"]
        assert backup == [
            "--chip",
            "esp32",
            "--port",
            "COM7",
            "--baud",
            "460800",
            "read-flash",
            "0",
            "ALL",
            str(target),
        ]
        assert target.read_bytes() == b"eski proshivka"
        assert write == [
            "--chip",
            "esp32",
            "--port",
            "COM7",
            "--baud",
            "460800",
            "write-flash",
            "0x10000",
            str(lab.firmware / "app.bin"),
        ]
        log = "\n".join(await lab.get("/flash/log"))
        # `\r` bilan yangilangan foiz satrlari alohida; rang kodlari olib tashlangan
        assert "Writing 10 %" in log and "Writing 100 %" in log and "\x1b" not in log
        assert "Hash of data verified." in log and "[srv1] natija: done" in log

        assert lab.audit() == [
            ("process.spawn", lab.flasher.prefix[0], 1),
            ("process.spawn", lab.flasher.prefix[0], 1),
            ("firmware.flash", "COM7", 1),
        ]
        states = [(await asyncio.wait_for(anext(events), 5)).data["state"] for _ in range(2)]
        assert states == ["running", "done"]
        history = await lab.get("/flash/history")
        assert [(row["port"], row["state"]) for row in history] == [("COM7", "done")]
        assert job["backup"] in {row["name"] for row in await lab.get("/firmware")}

        # boshqa manzil, tezlik va to'liq o'chirish
        again = await lab.flash(
            port="COM7", board="esp8266", file="app.bin", offset="0x0", baudrate=115200, erase=True
        )
        assert again.status_code == 202, again.text
        assert (await lab.finished())["state"] == "done"
        assert (await lab.commands())[0][:8] == [
            "--chip",
            "esp8266",
            "--port",
            "COM7",
            "--baud",
            "115200",
            "write-flash",
            "--erase-all",
        ]


async def test_flash_avr_runs_in_firmware_folder(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with _lab(paths, plugin_root, monkeypatch) as lab:
        assert (await lab.flash(port="COM8", board="uno", file="sketch.hex")).status_code == 202
        assert (await lab.finished())["state"] == "done"
        assert await lab.commands() == [
            [
                "-p",
                "atmega328p",
                "-c",
                "arduino",
                "-P",
                "COM8",
                "-b",
                "115200",
                "-D",
                "-U",
                "flash:w:sketch.hex:i",
            ]
        ]
        log: list[str] = await lab.get("/flash/log")
        cwd = next(json.loads(line.split("CWD ", 1)[1]) for line in log if "CWD " in line)
        assert Path(cwd) == lab.firmware

        old = await lab.flash(port="COM8", board="nano_old", file="sketch.hex")
        assert old.status_code == 202
        await lab.finished()
        assert (await lab.commands())[0][6:8] == ["-b", "57600"]
        for extra in ({"backup": True}, {"erase": True}, {"offset": "0x0"}, {"baudrate": 115200}):
            refused = await lab.flash(port="COM8", board="uno", file="sketch.hex", **extra)
            assert refused.status_code == 400, extra


async def test_flash_failure_timeout_and_cancel(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with _lab(paths, plugin_root, monkeypatch, timeout_s=1.5) as lab:
        assert (await lab.post("/flash/cancel")).status_code == 409

        lab.flasher.mode("fail")
        await lab.flash(port="COM7", board="esp32", file="app.bin", backup=True)
        failed = await lab.finished()
        assert failed["state"] == "failed" and "kod 2" in failed["error"]
        assert failed["step"] == "backup"  # zaxira o'tmasa, yozishga o'tilmaydi
        assert len(await lab.commands()) == 1
        assert "A fatal error occurred" in "\n".join(await lab.get("/flash/log"))
        assert lab.audit()[-1] == ("firmware.flash", "COM7", 0)

        lab.flasher.mode("hang")
        await lab.flash(port="COM7", board="esp32", file="app.bin")
        timed_out = await lab.finished()
        assert timed_out["state"] == "failed" and "vaqt tugadi" in timed_out["error"]
        pid = lab.flasher.pid()
        assert pid is not None and not psutil.pid_exists(pid)

    async with _lab_again(paths, monkeypatch, timeout_s=60) as lab:
        lab.flasher.mode("hang")
        await lab.flash(port="COM7", board="esp32", file="app.bin")
        await _eventually(lab.commands, lambda found: len(found) == 1, "dastur ishga tushishi")
        assert (await lab.flash(port="COM8", board="uno", file="sketch.hex")).status_code == 409
        assert (await lab.post("/monitor/open", port="COM7")).status_code == 409
        ports = {row["port"]: row["flashing"] for row in await lab.get("/ports")}
        assert ports == {"COM7": True, "COM8": False, "COM9": False}

        cancelled = await lab.post("/flash/cancel")
        assert cancelled.json()["state"] == "cancelled"
        pid = lab.flasher.pid()
        assert pid is not None and not psutil.pid_exists(pid)
        assert lab.audit()[-1] == ("firmware.flash", "COM7", 0)
        assert (await lab.get("/status"))["flash_state"] == "cancelled"


@asynccontextmanager
async def _lab_again(
    paths: DataPaths, monkeypatch: pytest.MonkeyPatch, **config: object
) -> AsyncGenerator[Lab]:
    """O'rnatilgan plagin bilan yadroni boshqa sozlamada qayta ishga tushiradi."""
    data = paths.root / "plugins" / "electronics" / "data"
    flasher = FakeFlasher(paths.root / "fake-tool")
    settings = {"esptool": flasher.prefix, "avrdude": flasher.prefix, **config}
    (data / "electronics.json").write_text(json.dumps({"config": settings}), encoding="utf-8")
    fake_serial(monkeypatch)
    async with serve_app(paths) as served, served.client() as client:
        yield Lab(client, served, data / "firmware", flasher, paths)


async def test_core_stop_kills_running_flasher(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with _lab(paths, plugin_root, monkeypatch) as lab:
        lab.flasher.mode("hang")
        await lab.flash(port="COM7", board="esp32", file="app.bin")
        await _eventually(lab.commands, lambda found: len(found) == 1, "dastur ishga tushishi")
        pid = lab.flasher.pid()
        assert pid is not None and psutil.pid_exists(pid)
    assert not psutil.pid_exists(pid)
    assert lab.audit()[-1] == ("firmware.flash", "COM7", 0)


# --- proshivka: rad etishlar ------------------------------------------------------------
async def test_flash_refusals_start_nothing(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    outside = tmp_path / "tashqarida.bin"
    outside.write_bytes(BIN)
    async with _lab(paths, plugin_root, monkeypatch) as lab:
        (lab.firmware / "bosh.bin").write_bytes(b"")
        cases: list[tuple[int, dict[str, object]]] = [
            (400, {"port": "COM7", "board": "stm32", "file": "app.bin"}),
            (403, {"port": "COM9", "board": "esp32", "file": "app.bin"}),
            (400, {"port": "loop://", "board": "esp32", "file": "app.bin"}),
            (404, {"port": "COM7", "board": "esp32", "file": "yoq.bin"}),
            (400, {"port": "COM7", "board": "esp32", "file": "sketch.hex"}),
            (400, {"port": "COM8", "board": "uno", "file": "app.bin"}),
            (400, {"port": "COM7", "board": "esp32", "file": "bosh.bin"}),
            (400, {"port": "COM7", "board": "esp32", "file": "../electronics.json"}),
            (403, {"port": "COM7", "board": "esp32", "file": "../../../../auth.token"}),
            (403, {"port": "COM7", "board": "esp32", "file": str(outside)}),
            (403, {"port": "COM7", "board": "esp32", "file": "C:/Windows/win.ini"}),
            (400, {"port": "COM7", "board": "esp32", "file": "app.bin", "baudrate": 123456}),
            (422, {"port": "COM7", "board": "esp32", "file": "app.bin", "offset": "4096"}),
            (422, {"port": "COM7", "board": "esp32; rm", "file": "app.bin"}),
            (422, {"port": "COM7", "board": "esp32"}),
        ]
        for expected, body in cases:
            response = await lab.flash(**body)
            assert response.status_code == expected, (body, response.text)
        assert (await lab.get("/flash")) == {"state": "idle"}
        assert lab.spawned() == 0
        assert await lab.get("/flash/history") == []


async def test_flash_refuses_missing_and_busy_port(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with _lab(paths, plugin_root, monkeypatch, busy=frozenset({"COM8"})) as lab:
        busy = await lab.flash(port="COM8", board="uno", file="sketch.hex")
        assert busy.status_code == 409
        assert "band" in busy.json()["detail"] and "iot" in busy.json()["detail"]

        def no_ports() -> list[dict[str, Any]]:
            return []

        monkeypatch.setattr(serialport, "available_ports", no_ports)
        missing = await lab.flash(port="COM7", board="esp32", file="app.bin")
        assert missing.status_code == 404 and "ulanmagan" in missing.json()["detail"]
        assert lab.spawned() == 0


async def test_flash_closes_own_monitor_first(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with _lab(paths, plugin_root, monkeypatch) as lab:
        assert (await lab.post("/monitor/open", port="COM7")).status_code == 200
        assert (await lab.flash(port="COM7", board="esp32", file="app.bin")).status_code == 202
        assert (await lab.finished())["state"] == "done"
        ports = {row["port"]: row["monitor"] for row in await lab.get("/ports")}
        assert ports["COM7"] is False
        assert (await lab.post("/monitor/close", port="COM7")).status_code == 404


# --- proshivka: haqiqiy dasturlar (plata yo'q — port ochilmasligi kerak) -----------------
async def test_real_esptool_accepts_our_commands(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Haqiqiy esptool buyruq satrimizni qabul qiladi va portni ochishgacha boradi."""
    async with _lab(paths, plugin_root, monkeypatch, real_tools=True) as lab:
        assert (await lab.get("/status"))["esptool"][0].isdigit()
        for extra in ({}, {"backup": True}, {"erase": True, "offset": "0x0"}):
            started = await lab.flash(port="COM7", board="esp32c3", file="app.bin", **extra)
            assert started.status_code == 202, started.text
            job = await lab.finished(60)
            log = "\n".join(await lab.get("/flash/log"))
            assert job["state"] == "failed" and "kod" in job["error"], log
            assert "Could not open COM7" in log, log
            assert "Usage:" not in log and "Invalid value" not in log, log


@pytest.mark.skipif(not AVRDUDE_EXE.is_file(), reason="tools/avrdude/avrdude.exe yo'q")
async def test_real_avrdude_accepts_our_commands(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with _lab(paths, plugin_root, monkeypatch, real_tools=True) as lab:
        assert (await lab.get("/status"))["avrdude"] == "ready"
        for board in ("uno", "nano_old", "mega2560"):
            started = await lab.flash(port="COM8", board=board, file="sketch.hex")
            assert started.status_code == 202, started.text
            job = await lab.finished(60)
            log = "\n".join(await lab.get("/flash/log"))
            assert job["state"] == "failed" and "kod" in job["error"], log
            assert "unable to open port COM8" in log, log
            assert "Usage:" not in log and "invalid" not in log.lower(), log
