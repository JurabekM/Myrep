"""IT administrlash xizmati: jarayonlar, xizmatlar, tarmoq skaneri va zaxira nusxa."""

import asyncio
import re
import time
from dataclasses import dataclass, field
from ipaddress import IPv4Network
from pathlib import Path
from typing import Any, Literal

from srv1_sdk.context import PluginContext

from .backup import PREFIX, BackupOptions, create_backup, list_backups, prune
from .models import STORE_FILE, ItopsError, Store, load_store
from .netscan import Host, Scanner, allowed_range, local_interfaces, scan_range
from .processes import Sort, kill_process, list_processes
from .services import Action, control_service, list_services

BACKUP_DIR = "backups"
_BACKUP_NAME_RE = re.compile(rf"{PREFIX}\d{{8}}-\d{{6}}(-\d+)?\.zip")
TaskState = Literal["idle", "running", "done", "failed", "cancelled"]


@dataclass
class ScanJob:
    network: str
    ports: list[int]
    started: float
    state: TaskState = "running"
    done: int = 0
    total: int = 0
    finished: float | None = None
    error: str | None = None
    hosts: list[Host] = field(default_factory=list[Host])

    def describe(self) -> dict[str, Any]:
        end = self.finished if self.finished is not None else time.time()
        return {
            "state": self.state,
            "network": self.network,
            "ports": self.ports,
            "progress": f"{self.done}/{self.total}",
            "hosts": len(self.hosts),
            "seconds": round(end - self.started, 1),
            "error": self.error,
        }


@dataclass
class BackupState:
    state: TaskState = "idle"
    started: float = 0.0
    error: str | None = None
    last: dict[str, Any] | None = None


class ItopsService:
    def __init__(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self.store: Store = load_store(ctx.data_path(STORE_FILE))
        self.scan: ScanJob | None = None
        self.backup = BackupState()
        self._scan_task: asyncio.Task[None] | None = None
        self._backup_task: asyncio.Task[None] | None = None

    async def stop(self) -> None:
        for task in (self._scan_task, self._backup_task):
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    # --- jarayonlar ---------------------------------------------------------
    async def processes(self, search: str, sort: Sort, limit: int) -> list[dict[str, Any]]:
        return await asyncio.to_thread(list_processes, search, sort, limit)

    async def kill(self, pid: int, started: float | None) -> dict[str, Any]:
        """Xavfli amal: natijasi (rad etilgani ham) auditga yoziladi."""
        self.ctx.require_system("process.kill")
        try:
            result = await asyncio.to_thread(kill_process, pid, started)
        except ItopsError as exc:
            await self.ctx.audit("process.kill", str(pid), ok=False, detail={"error": exc.detail})
            raise
        await self.ctx.audit("process.kill", str(pid), detail={"name": result["name"]})
        return result

    # --- xizmatlar ----------------------------------------------------------
    async def services(self, search: str, state: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(list_services, search, state)

    async def control(self, name: str, action: Action) -> dict[str, Any]:
        self.ctx.require_system(f"service.{action}")
        try:
            result = await asyncio.to_thread(control_service, name, action)
        except ItopsError as exc:
            await self.ctx.audit(f"service.{action}", name, ok=False, detail={"error": exc.detail})
            raise
        await self.ctx.audit(f"service.{action}", name, detail={"before": result["before"]})
        return result

    # --- tarmoq skaneri -----------------------------------------------------
    def networks(self) -> list[dict[str, Any]]:
        """Skanerlash mumkin bo'lgan tarmoqlar (mashinaning o'z xususiy tarmoqlari)."""
        interfaces = local_interfaces(loopback=self.store.config.scan_loopback)
        rows = {str(scan_range(i)): str(i.ip) for i in interfaces}
        return [{"network": network, "address": address} for network, address in rows.items()]

    async def start_scan(self, network: str, ports: list[int]) -> dict[str, Any]:
        self.ctx.require_system("network.scan")
        if self.scan is not None and self.scan.state == "running":
            raise ItopsError(409, "skanerlash ketmoqda; tugashini kuting")
        config = self.store.config
        interfaces = await asyncio.to_thread(local_interfaces, loopback=config.scan_loopback)
        if not interfaces:
            raise ItopsError(409, "mahalliy tarmoq topilmadi")
        try:
            target = IPv4Network(network) if network else scan_range(interfaces[0])
        except ValueError as exc:
            raise ItopsError(400, f"tarmoq a.b.c.d/n ko'rinishida bo'lsin: {network}") from exc
        if not allowed_range(target, interfaces):
            raise ItopsError(
                403,
                f"{target}: faqat mashinaning o'z mahalliy tarmog'i (ko'pi bilan /24) skanerlanadi",
            )
        job = ScanJob(str(target), sorted(set(ports or config.scan_ports)), time.time())
        self.scan = job
        own = {interface.ip for interface in interfaces}

        def progress(done: int, total: int) -> None:
            job.done, job.total = done, total

        scanner = Scanner(
            target,
            job.ports,
            timeout_s=config.scan_timeout_s,
            concurrency=config.scan_concurrency,
            own=own,
            progress=progress,
        )
        await self.ctx.audit("network.scan", job.network, detail={"ports": job.ports})
        self._scan_task = asyncio.create_task(self._run_scan(job, scanner))
        return job.describe()

    async def _run_scan(self, job: ScanJob, scanner: Scanner) -> None:
        try:
            job.hosts = await scanner.run()
            job.state = "done"
        except asyncio.CancelledError:
            job.state, job.error = "cancelled", "bekor qilindi"
        except OSError as exc:
            job.state, job.error = "failed", str(exc) or type(exc).__name__
        job.finished = time.time()
        self.ctx.publish("scan", job.describe())

    async def cancel_scan(self) -> dict[str, Any]:
        task = self._scan_task
        if self.scan is None or self.scan.state != "running" or task is None:
            raise ItopsError(409, "hozir skanerlash ketmayapti")
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        return self.scan.describe()

    def scan_status(self) -> dict[str, Any]:
        return {"state": "idle"} if self.scan is None else self.scan.describe()

    def scan_hosts(self) -> list[dict[str, Any]]:
        return [] if self.scan is None else [host.describe() for host in self.scan.hosts]

    # --- zaxira nusxa -------------------------------------------------------
    def backup_dir(self) -> Path:
        """Zaxiralar papkasi: o'z `backups` papkasi yoki manifestda ruxsat etilgan papka."""
        configured = self.store.config.backup_destination.strip()
        if not configured:
            return self.ctx.data_path(BACKUP_DIR)
        path = Path(configured)
        if not path.is_absolute():
            raise ItopsError(400, "backup_destination mutlaq yo'l bo'lishi kerak")
        return self.ctx.resolve_path(path)

    async def start_backup(self) -> dict[str, Any]:
        if self.backup.state == "running":
            raise ItopsError(409, "zaxira nusxa olinmoqda; tugashini kuting")
        destination = self.backup_dir()
        root = self.ctx.data_root
        self.backup = BackupState("running", time.time(), last=self.backup.last)
        self._backup_task = asyncio.create_task(self._run_backup(root, destination))
        return self.backup_status()

    async def run_backup(self) -> None:
        """Jadval bo'yicha: boshlaydi va tugashini kutadi."""
        await self.start_backup()
        if self._backup_task is not None:
            await self._backup_task

    async def _run_backup(self, root: Path, destination: Path) -> None:
        config = self.store.config
        options = BackupOptions(
            projects=config.backup_projects,
            logs=config.backup_logs,
            exclude=(destination, self.ctx.data_path(BACKUP_DIR)),
        )
        state = self.backup
        try:
            result = await asyncio.to_thread(create_backup, root, destination, options)
            removed = await asyncio.to_thread(prune, destination, config.backup_keep)
        except (OSError, ValueError) as exc:
            state.state, state.error = "failed", str(exc) or type(exc).__name__
            await self.ctx.audit(
                "backup.create", str(destination), ok=False, detail={"error": state.error}
            )
            self.ctx.publish("backup", {"state": "failed", "error": state.error})
            return
        state.state, state.last = "done", result.describe() | {"removed": removed}
        if result.skipped:
            self.ctx.log("warning", "backup_skipped_files", files=result.skipped[:20])
        await self.ctx.audit("backup.create", str(result.path), detail=state.last)
        self.ctx.publish("backup", {"state": "done", **state.last})

    def backup_status(self) -> dict[str, Any]:
        state = self.backup
        return {"state": state.state, "error": state.error, "last": state.last}

    async def backups(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(list_backups, self.backup_dir())

    async def remove_backup(self, name: str) -> dict[str, Any]:
        """Arxivni o'chiradi — fayl o'chirish, auditga yoziladi."""
        if _BACKUP_NAME_RE.fullmatch(name) is None:
            raise ItopsError(400, f"zaxira nomi yaroqsiz: {name}")
        path = self.backup_dir() / name
        if not path.is_file():
            raise ItopsError(404, f"bunday zaxira yo'q: {name}")
        await asyncio.to_thread(path.unlink)
        await self.ctx.audit("file.delete", str(path))
        return {"removed": name}

    # --- holat --------------------------------------------------------------
    async def status(self) -> dict[str, Any]:
        config = self.store.config
        archives = await self.backups()
        last = archives[0] if archives else None
        return {
            "scan_state": self.scan.state if self.scan is not None else "idle",
            "scan_hosts": len(self.scan.hosts) if self.scan is not None else 0,
            "backup_state": self.backup.state,
            "backup_error": self.backup.error,
            "backup_count": len(archives),
            "backup_last": last["name"] if last is not None else "—",
            "backup_cron": config.backup_cron or "—",
            "backup_keep": config.backup_keep,
            "backup_dir": str(self.backup_dir()),
            "scan_ports": config.scan_ports,
        }
