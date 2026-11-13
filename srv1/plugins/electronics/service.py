"""Elektronika xizmati: portlar, serial monitor va proshivka yozish (esptool / avrdude)."""

import asyncio
import hashlib
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from srv1_sdk import serialport
from srv1_sdk.context import PluginContext
from srv1_sdk.process import ManagedProcess
from srv1_sdk.serialport import LOOPBACK_URL, SerialPort
from srv1_sdk.types import PermissionDenied

from .flasher import (
    ESP_BAUDRATES,
    avr_write_command,
    avrdude_exe,
    clean_output,
    esp_backup_command,
    esp_write_command,
    esptool_version,
    tool_env,
    tool_prefix,
)
from .models import (
    BOARDS,
    STORE_FILE,
    Board,
    JobState,
    Store,
    identify_usb,
    load_store,
    usb_id,
)

FIRMWARE_DIR = "firmware"
BACKUP_DIR = "backups"
LOG_LINES = 500
HISTORY_KEPT = 20
TOOL_MEMORY_MB = 256
MAX_BYTES = {".bin": 32 * 1024 * 1024, ".hex": 4 * 1024 * 1024}
LINE_PREVIEW = 500


class ElectronicsError(Exception):
    """Amal bajarilmadi; `status` — klientga qaytadigan HTTP kodi."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class StepFailed(Exception):
    """Proshivka bosqichi muvaffaqiyatsiz tugadi."""


@dataclass
class FlashRequest:
    port: str
    board: str
    file: str
    offset: str = ""
    baudrate: int | None = None
    backup: bool = False
    erase: bool = False


@dataclass
class Job:
    id: int
    port: str
    board: str
    file: str
    started: float
    state: JobState = "running"
    step: str = "prepare"
    finished: float | None = None
    error: str | None = None
    backup: str | None = None
    sha256: str = ""
    size: int = 0

    def describe(self) -> dict[str, Any]:
        end = self.finished if self.finished is not None else time.time()
        return {
            "id": self.id,
            "port": self.port,
            "board": self.board,
            "file": self.file,
            "state": self.state,
            "step": self.step,
            "started": self.started,
            "finished": self.finished,
            "seconds": round(end - self.started, 1),
            "error": self.error,
            "backup": self.backup,
            "sha256": self.sha256,
            "size": self.size,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class ElectronicsService:
    def __init__(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self.store = Store()
        self.firmware_dir = ctx.data_path(FIRMWARE_DIR)
        self.backup_dir = ctx.data_path(FIRMWARE_DIR, BACKUP_DIR)
        self.monitors: dict[str, SerialPort] = {}
        self.job: Job | None = None
        self.history: deque[Job] = deque(maxlen=HISTORY_KEPT)
        self.lines: deque[str] = deque(maxlen=LOG_LINES)
        self._task: asyncio.Task[None] | None = None
        self._jobs = 0

    # --- hayot sikli ------------------------------------------------------
    def prepare(self) -> None:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.store = load_store(self.ctx.data_path(STORE_FILE))

    async def stop(self) -> None:
        await self._cancel_task()
        for port in self.monitors.values():
            await asyncio.to_thread(port.close)
        self.monitors.clear()

    # --- portlar ----------------------------------------------------------
    @property
    def flashing(self) -> bool:
        return self.job is not None and self.job.state == "running"

    async def ports(self) -> list[dict[str, Any]]:
        """Tizimdagi portlar: USB identifikatori, taxminiy plata, ruxsat va monitor holati."""
        allowed = set(self.ctx.manifest.permissions.serial)
        rows: dict[str, dict[str, Any]] = {}
        for item in await asyncio.to_thread(serialport.available_ports):
            name = str(item["port"]).upper()
            chip, board = identify_usb(item["vid"], item["pid"])
            rows[name] = {
                "port": name,
                "chip": chip,
                "board": board,
                "usb": usb_id(item["vid"], item["pid"]),
                "description": item["description"],
                "connected": True,
            }
        for name in self.monitors:
            rows.setdefault(
                name,
                {"port": name, "chip": "", "board": "", "usb": "", "description": ""}
                | {"connected": name == LOOPBACK_URL},
            )
        for name, row in rows.items():
            monitor = self.monitors.get(name)
            row["allowed"] = name in allowed or name == LOOPBACK_URL
            row["monitor"] = monitor is not None and monitor.is_open
            row["baudrate"] = monitor.baudrate if monitor is not None else None
            row["flashing"] = self.flashing and self.job is not None and self.job.port == name
        return [rows[name] for name in sorted(rows)]

    def _port_name(self, name: str, *, check: bool, loopback: bool = True) -> str:
        cleaned = name.strip()
        if cleaned == LOOPBACK_URL and loopback:
            return cleaned
        if "://" in cleaned or "/" in cleaned or "\\" in cleaned:
            raise ElectronicsError(400, "faqat COM portlar ishlatiladi (masalan: COM3)")
        return self.ctx.check_serial(cleaned) if check else cleaned.upper()

    # --- serial monitor ---------------------------------------------------
    def _monitor(self, name: str) -> SerialPort:
        monitor = self.monitors.get(self._port_name(name, check=False))
        if monitor is None:
            raise ElectronicsError(404, f"monitor ochilmagan: {name}")
        return monitor

    async def open_monitor(self, name: str, baudrate: int | None) -> dict[str, Any]:
        port_name = self._port_name(name, check=True)
        if self.flashing and self.job is not None and self.job.port == port_name:
            raise ElectronicsError(409, f"{port_name} ga hozir proshivka yozilmoqda")
        if port_name in self.monitors and self.monitors[port_name].is_open:
            raise ElectronicsError(409, f"monitor allaqachon ochiq: {port_name}")
        speed = baudrate or self.store.config.monitor_baudrate
        monitor = SerialPort(port_name, speed, self._on_monitor_line)
        try:
            await asyncio.to_thread(monitor.open)
        except (OSError, ValueError) as exc:
            raise ElectronicsError(502, f"{port_name} ochilmadi: {exc}") from exc
        self.monitors[port_name] = monitor
        self.ctx.log("info", "monitor_opened", port=port_name, baudrate=speed)
        return {"port": port_name, "baudrate": speed, "open": True}

    async def close_monitor(self, name: str) -> dict[str, Any]:
        monitor = self._monitor(name)
        await asyncio.to_thread(monitor.close)
        del self.monitors[monitor.name]
        return {"port": monitor.name, "open": False}

    async def write_monitor(self, name: str, text: str, newline: bool) -> dict[str, Any]:
        monitor = self._monitor(name)
        data = (text + ("\n" if newline else "")).encode("utf-8")
        try:
            written = await asyncio.to_thread(monitor.write, data)
        except (OSError, ValueError) as exc:
            raise ElectronicsError(502, f"{monitor.name} ga yozilmadi: {exc}") from exc
        return {"port": monitor.name, "bytes": written}

    def monitor_lines(self, name: str, tail: int) -> list[str]:
        return list(self._monitor(name).lines)[-tail:]

    def _on_monitor_line(self, name: str, line: str) -> None:
        self.ctx.publish("serial", {"port": name, "line": line[:LINE_PREVIEW]})

    # --- proshivka fayllari -----------------------------------------------
    def firmware_files(self) -> list[dict[str, Any]]:
        """`firmware` papkasidagi `.bin` va `.hex` fayllar (bloklovchi)."""
        rows: list[dict[str, Any]] = []
        for path in sorted(self.firmware_dir.rglob("*")):
            if path.suffix.lower() in MAX_BYTES and path.is_file():
                stat = path.stat()
                name = path.relative_to(self.firmware_dir).as_posix()
                rows.append({"name": name, "size": stat.st_size, "modified": stat.st_mtime})
        return rows

    def _firmware(self, name: str, board: Board) -> Path:
        """Fayl yo'lini tekshiradi: `firmware` papkasi yoki manifestdagi papkalar ichida."""
        candidate = Path(name.strip())
        if not candidate.is_absolute():
            candidate = self.firmware_dir / candidate
        path = self.ctx.resolve_path(candidate)
        if not path.is_file():
            raise ElectronicsError(404, f"fayl topilmadi: {name}")
        if path.suffix.lower() != board.suffix:
            raise ElectronicsError(400, f"{board.title} uchun {board.suffix} fayl kerak: {name}")
        size = path.stat().st_size
        if not 0 < size <= MAX_BYTES[board.suffix]:
            raise ElectronicsError(400, f"fayl hajmi yaroqsiz ({size} bayt): {name}")
        return path

    # --- proshivka yozish ---------------------------------------------------
    async def flash(self, request: FlashRequest) -> dict[str, Any]:
        """Tekshiradi va yozishni fonda boshlaydi. Xavfli amal: natijasi auditga yoziladi."""
        board = BOARDS.get(request.board)
        if board is None:
            raise ElectronicsError(400, f"noma'lum plata: {request.board}")
        if self.flashing:
            raise ElectronicsError(409, "boshqa proshivka yozilmoqda; tugashini kuting")
        port = self._port_name(request.port, check=True, loopback=False)
        file = self._firmware(request.file, board)
        steps = self._plan(board, port, file, request)
        await self._free_port(port)
        self._jobs += 1
        job = Job(self._jobs, port, board.key, file.name, time.time(), size=file.stat().st_size)
        self.job = job
        self.lines.clear()
        self._task = asyncio.create_task(self._run(job, file, steps))
        return job.describe()

    def _plan(
        self, board: Board, port: str, file: Path, request: FlashRequest
    ) -> list[tuple[str, list[str], Path]]:
        """Bosqichlar: (nom, argv, ish papkasi). Hech narsa ishga tushirilmaydi."""
        prefix = tool_prefix(board, self.store.config)
        if prefix is None:
            raise ElectronicsError(503, f"{board.tool} topilmadi (tools/README.md ga qarang)")
        if board.tool == "avrdude":
            if request.backup or request.erase or request.offset or request.baudrate:
                raise ElectronicsError(
                    400, "offset, baudrate, backup va erase faqat ESP platalari uchun"
                )
            return [("write", avr_write_command(prefix, board, port, file.name), file.parent)]
        baudrate = request.baudrate or board.baudrate
        if baudrate not in ESP_BAUDRATES:
            raise ElectronicsError(400, f"tezlik {ESP_BAUDRATES} dan biri bo'lsin")
        steps: list[tuple[str, list[str], Path]] = []
        if request.backup:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            target = self.backup_dir / f"{port}-{board.key}-{stamp}.bin"
            command = esp_backup_command(prefix, board, port, target, baudrate=baudrate)
            steps.append(("backup", command, self.backup_dir))
        command = esp_write_command(
            prefix,
            board,
            port,
            file,
            offset=request.offset or board.offset,
            baudrate=baudrate,
            erase=request.erase,
        )
        return [*steps, ("write", command, self.ctx.data_dir)]

    async def _free_port(self, port: str) -> None:
        """Port bor va bo'shligini tekshiradi; o'z monitorimiz ochiq bo'lsa, yopadi."""
        monitor = self.monitors.pop(port, None)
        if monitor is not None:
            await asyncio.to_thread(monitor.close)
        present = {
            str(item["port"]).upper()
            for item in await asyncio.to_thread(serialport.available_ports)
        }
        if port not in present:
            raise ElectronicsError(404, f"{port} topilmadi: plata ulanmagan")
        reason = await asyncio.to_thread(serialport.probe_port, port)
        if reason is not None:
            raise ElectronicsError(
                409,
                f"{port} band: uni boshqa dastur yoki `iot` plagini ochgan. "
                f"Avval o'sha yerda yoping. ({reason})",
            )

    def _write(self, line: str) -> None:
        self.lines.append(f"{time.strftime('%H:%M:%S')} {line}")

    def _on_tool_line(self, text: str) -> None:
        for line in clean_output(text):
            if not self.lines or not self.lines[-1].endswith(line):
                self._write(line)

    async def _step(self, name: str, argv: list[str], cwd: Path) -> None:
        self._write(f"[srv1] {name}: {' '.join(argv)}")
        timeout = self.store.config.timeout_s
        process: ManagedProcess = await self.ctx.spawn(
            argv,
            cwd=cwd,
            env=tool_env(),
            memory_limit_mb=TOOL_MEMORY_MB,
            on_line=self._on_tool_line,
        )
        try:
            code = await asyncio.wait_for(process.wait(), timeout)
        except TimeoutError as exc:
            raise StepFailed(f"{name}: vaqt tugadi ({timeout:.0f} s)") from exc
        finally:
            await process.stop()
        if code != 0:
            raise StepFailed(f"{name}: dastur xato bilan tugadi (kod {code})")

    async def _run(self, job: Job, file: Path, steps: list[tuple[str, list[str], Path]]) -> None:
        self.ctx.publish("flash", job.describe())
        try:
            job.sha256 = await asyncio.to_thread(_sha256, file)
            for name, argv, cwd in steps:
                job.step = name
                await self._step(name, argv, cwd)
                if name == "backup":
                    job.backup = f"{BACKUP_DIR}/{Path(argv[-1]).name}"
            job.state = "done"
        except asyncio.CancelledError:
            job.state, job.error = "cancelled", "bekor qilindi"
        except (StepFailed, OSError, PermissionDenied) as exc:
            job.state, job.error = "failed", str(exc) or type(exc).__name__
        await self._finish(job)

    async def _finish(self, job: Job) -> None:
        job.finished = time.time()
        self._write(f"[srv1] natija: {job.state}" + (f" — {job.error}" if job.error else ""))
        self.history.append(job)
        detail = {key: value for key, value in job.describe().items() if key != "port"}
        await self.ctx.audit("firmware.flash", job.port, ok=job.state == "done", detail=detail)
        self.ctx.publish("flash", job.describe())

    async def _cancel_task(self) -> None:
        task, self._task = self._task, None
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def cancel(self) -> dict[str, Any]:
        """Yozishni to'xtatadi. Plata proshivkasiz qolishi mumkin — qayta yozish kerak bo'ladi."""
        if not self.flashing or self.job is None:
            raise ElectronicsError(409, "hozir proshivka yozilmayapti")
        await self._cancel_task()
        return self.job.describe()

    def job_status(self) -> dict[str, Any]:
        if self.job is None:
            return {"state": "idle"}
        return self.job.describe()

    def job_history(self) -> list[dict[str, Any]]:
        return [job.describe() for job in reversed(self.history)]

    def log_lines(self, tail: int) -> list[str]:
        return list(self.lines)[-tail:]

    # --- holat --------------------------------------------------------------
    def status(self) -> dict[str, Any]:
        config = self.store.config
        avrdude = avrdude_exe()
        avrdude_state = "custom" if config.avrdude else "ready" if avrdude.is_file() else "missing"
        return {
            "esptool": "custom" if config.esptool else esptool_version() or "missing",
            "avrdude": avrdude_state,
            "avrdude_path": str(avrdude),
            "flash_state": self.job.state if self.job is not None else "idle",
            "flash_step": self.job.step if self.flashing and self.job is not None else "",
            "monitors": sum(monitor.is_open for monitor in self.monitors.values()),
            "allowed_ports": list(self.ctx.manifest.permissions.serial),
            "firmware_dir": str(self.firmware_dir),
            "timeout_s": config.timeout_s,
        }
