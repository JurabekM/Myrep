"""Hosting xizmati: loyihalar, jarayonlar, portlar, Caddy marshrutlari, uxlatish va uyg'otish."""

import asyncio
import os
import shutil
import socket
import sys
import time
from collections import deque
from contextlib import suppress
from pathlib import Path
from typing import Any, TextIO

from srv1_sdk.context import PluginContext
from srv1_sdk.pathsafe import PathTraversalError, safe_join
from srv1_sdk.process import ManagedProcess

from .caddy import Caddy, Route, message_route, proxy_route, static_route
from .models import (
    STORE_FILE,
    HostingError,
    ProjectConfig,
    State,
    Store,
    load_store,
    save_store,
)
from .tunnel import TunnelManager

__all__ = ["LOG_LINES", "HostingError", "HostingService", "Project"]

LOG_LINES = 500
LOG_FILE_MAX_BYTES = 1024 * 1024
WAKE_REQUEST_MAX_BYTES = 16 * 1024
_SCRIPT_SUFFIXES = (".cmd", ".bat")
PLACEHOLDER_PAGE = """<!doctype html>
<meta charset="utf-8">
<title>{name}</title>
<h1>{name}</h1>
<p>SRV_1 statik sayti. Fayllarni shu papkaga joylang.</p>
"""


class Project:
    """Loyihaning ish vaqtidagi holati."""

    def __init__(self, config: ProjectConfig, directory: Path, log_file: Path) -> None:
        self.config = config
        self.directory = directory
        self.state: State = "stopped"
        self.error: str | None = None
        self.process: ManagedProcess | None = None
        self.last_activity = time.time()
        self.lines: deque[str] = deque(maxlen=LOG_LINES)
        self.lock = asyncio.Lock()
        self._log_file = log_file
        self._log: TextIO | None = None
        self.watcher: asyncio.Task[None] | None = None

    def write(self, line: str) -> None:
        stamped = f"{time.strftime('%H:%M:%S')} {line}"
        self.lines.append(stamped)
        try:
            if self._log is None:
                self._log = self._log_file.open("a", encoding="utf-8")
            self._log.write(stamped + "\n")
            if self._log.tell() > LOG_FILE_MAX_BYTES:
                self.close_log()
                self._log_file.replace(self._log_file.with_suffix(".log.1"))
        except OSError:
            self._log = None

    def flush_log(self) -> None:
        if self._log is not None:
            with suppress(OSError):
                self._log.flush()

    def close_log(self) -> None:
        if self._log is not None:
            with suppress(OSError):
                self._log.close()
            self._log = None


def _port_is_free(port: int) -> bool:
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


async def _port_accepts(port: int) -> bool:
    try:
        _reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", port), 0.5)
    except (OSError, TimeoutError):
        return False
    writer.close()
    with suppress(OSError):
        await writer.wait_closed()
    return True


class HostingService:
    def __init__(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self._store_file = ctx.data_path(STORE_FILE)
        self._logs_dir = ctx.data_path("logs")
        self.store = Store()
        self.projects: dict[str, Project] = {}
        self.caddy: Caddy | None = None
        self.caddy_error: str | None = None
        self.tunnels = TunnelManager(ctx, self.store.config)
        self._wake_server: asyncio.Server | None = None
        self._idle_task: asyncio.Task[None] | None = None

    # --- hayot sikli ------------------------------------------------------
    def prepare(self) -> None:
        """Sinxron tayyorgarlik: papkalar va sozlamani o'qish."""
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        self.ctx.projects_dir.mkdir(parents=True, exist_ok=True)
        self.store = load_store(self._store_file)
        cfg = self.store.config
        self.tunnels = TunnelManager(self.ctx, cfg)
        for port in (cfg.listen_port, cfg.admin_port, cfg.wake_port, cfg.port_first, cfg.port_last):
            self.ctx.check_port(port)
        for config in self.store.projects:
            self.projects[config.name] = self._make_project(config)

    def _make_project(self, config: ProjectConfig) -> Project:
        directory = safe_join(self.ctx.projects_dir, config.name)
        return Project(config, directory, self._logs_dir / f"{config.name}.log")

    async def start(self) -> None:
        cfg = self.store.config
        self._wake_server = await asyncio.start_server(
            self._handle_wake, "127.0.0.1", cfg.wake_port
        )
        self.caddy = Caddy(self.ctx, cfg, self._on_access)
        if not self.caddy.available:
            self.caddy_error = f"caddy.exe topilmadi: {self.caddy.exe}"
            self.ctx.log("error", "caddy_missing", path=str(self.caddy.exe))
        else:
            try:
                await self.caddy.start(self._routes())
            except (OSError, RuntimeError) as exc:
                self.caddy_error = str(exc)
                self.ctx.log("error", "caddy_start_failed", error=str(exc))
        for project in list(self.projects.values()):
            if project.config.autostart:
                with suppress(HostingError):
                    await self.start_project(project.config.name)
        self._idle_task = asyncio.create_task(self._idle_loop())

    async def stop(self) -> None:
        if self._idle_task is not None:
            self._idle_task.cancel()
            await asyncio.gather(self._idle_task, return_exceptions=True)
        await self.tunnels.close_all()
        if self._wake_server is not None:
            self._wake_server.close()
            await self._wake_server.wait_closed()
        for project in self.projects.values():
            await self._kill(project)
            project.state = "stopped"
            project.close_log()
        if self.caddy is not None:
            await self.caddy.stop()

    # --- marshrutlar --------------------------------------------------------
    def host_of(self, name: str) -> str:
        return f"{name}.{self.store.config.domain}"

    def url_of(self, name: str) -> str:
        return f"http://{self.host_of(name)}:{self.store.config.listen_port}/"

    def _static_root(self, project: Project) -> Path:
        root = project.config.root
        return safe_join(project.directory, *root.split("/")) if root else project.directory

    def _routes(self) -> list[Route]:
        routes: list[Route] = []
        for project in self.projects.values():
            host, config = self.host_of(project.config.name), project.config
            if project.state == "running" and config.kind == "static":
                routes.append(static_route(host, self._static_root(project)))
            elif project.state == "running" and config.port is not None:
                routes.append(proxy_route(host, config.port))
            elif project.state in ("sleeping", "starting"):
                routes.append(proxy_route(host, self.store.config.wake_port))
            elif project.state == "failed":
                routes.append(message_route(503, "SRV_1: loyiha ishga tushmadi.\n", host))
        return routes

    async def _sync(self) -> None:
        if self.caddy is None or not self.caddy.running:
            return
        try:
            await self.caddy.load(self._routes())
            self.caddy_error = None
        except (RuntimeError, OSError) as exc:
            self.caddy_error = str(exc)
            self.ctx.log("error", "caddy_load_failed", error=str(exc))

    def _on_access(self, host: str) -> None:
        name = host.removesuffix("." + self.store.config.domain)
        project = self.projects.get(name)
        if project is not None:
            project.last_activity = time.time()

    # --- loyihalar ro'yxati ---------------------------------------------------
    def _project(self, name: str) -> Project:
        project = self.projects.get(name)
        if project is None:
            raise HostingError(404, f"loyiha topilmadi: {name}")
        return project

    def _save(self) -> None:
        self.store.projects = [project.config for project in self.projects.values()]
        save_store(self._store_file, self.store)

    def describe(self, project: Project) -> dict[str, Any]:
        config = project.config
        process = project.process
        return {
            "name": config.name,
            "kind": config.kind,
            "state": project.state,
            "url": self.url_of(config.name),
            "public_url": self.tunnels.url_of(config.name),
            "port": config.port,
            "pid": process.pid if process is not None and process.running else None,
            "memory": process.memory_bytes() if process is not None else None,
            "memory_limit_mb": None if config.kind == "static" else config.memory_limit_mb,
            "idle_minutes": config.idle_minutes,
            "autostart": config.autostart,
            "command": " ".join(config.command),
            "error": project.error,
            "last_activity": project.last_activity,
        }

    async def list_projects(self) -> list[dict[str, Any]]:
        projects = sorted(self.projects.values(), key=lambda p: p.config.name)
        return await asyncio.to_thread(lambda: [self.describe(project) for project in projects])

    async def status(self) -> dict[str, Any]:
        caddy = self.caddy
        running = caddy is not None and caddy.running
        states = [project.state for project in self.projects.values()]
        return {
            "caddy": "running"
            if running
            else "missing"
            if caddy and not caddy.available
            else "stopped",
            "caddy_pid": caddy.pid if caddy is not None else None,
            "caddy_memory": await asyncio.to_thread(caddy.memory_bytes) if caddy and running else 0,
            "caddy_error": self.caddy_error,
            "cloudflared": "available" if self.tunnels.available else "missing",
            "tunnels": len(self.tunnels.active()),
            "tunnel_memory": await asyncio.to_thread(self.tunnels.memory_bytes),
            "listen": f"{self.store.config.listen_host}:{self.store.config.listen_port}",
            "projects": len(states),
            "running": states.count("running"),
            "sleeping": states.count("sleeping"),
            "failed": states.count("failed"),
        }

    async def create(self, config: ProjectConfig, *, start: bool) -> dict[str, Any]:
        if config.name in self.projects:
            raise HostingError(409, f"bunday loyiha bor: {config.name}")
        try:
            project = self._make_project(config)
            if config.root:
                self._static_root(project)
        except PathTraversalError as exc:
            raise HostingError(400, f"yaroqsiz yo'l: {exc}") from exc
        await asyncio.to_thread(self._prepare_directory, project)
        self.projects[config.name] = project
        await asyncio.to_thread(self._save)
        await self.ctx.audit("hosting.project_create", config.name, detail={"kind": config.kind})
        if start:
            await self.start_project(config.name)
        return self.describe(project)

    @staticmethod
    def _prepare_directory(project: Project) -> None:
        """Papkani yaratadi; bo'sh statik saytga namunaviy sahifa qo'yadi (mavjudiga tegmaydi)."""
        project.directory.mkdir(parents=True, exist_ok=True)
        if project.config.kind == "static" and not project.config.root:
            index = project.directory / "index.html"
            if not any(project.directory.iterdir()):
                index.write_text(
                    PLACEHOLDER_PAGE.format(name=project.config.name), encoding="utf-8"
                )

    async def remove(self, name: str) -> dict[str, Any]:
        """Loyihani ro'yxatdan chiqaradi. Papkasi va fayllari o'chirilmaydi."""
        project = self._project(name)
        await self._close_tunnel(name, "loyiha ro'yxatdan chiqarildi")
        async with project.lock:
            await self._kill(project)
            project.close_log()
            del self.projects[name]
        await asyncio.to_thread(self._save)
        await self._sync()
        await self.ctx.audit(
            "hosting.project_remove", name, detail={"kept": str(project.directory)}
        )
        return {"removed": name, "files_kept": str(project.directory)}

    # --- jarayonlar -----------------------------------------------------------
    def _allocate_port(self, project: Project) -> int:
        cfg = self.store.config
        # Portni faqat tirik (yoki uyg'onishi mumkin bo'lgan) loyihalar band qiladi.
        holding = ("running", "starting", "sleeping")
        taken = {
            p.config.port for p in self.projects.values() if p is not project and p.state in holding
        }
        preferred = [project.config.port] if project.config.port is not None else []
        for port in [*preferred, *range(cfg.port_first, cfg.port_last + 1)]:
            if (
                port not in taken
                and cfg.port_first <= port <= cfg.port_last
                and _port_is_free(port)
            ):
                return self.ctx.check_port(port)
        raise HostingError(503, f"bo'sh port qolmadi ({cfg.port_first}-{cfg.port_last})")

    def _resolve_command(self, project: Project, port: int) -> list[str]:
        """Bajariladigan faylni topadi. `shell` ishlatilmaydi, `.cmd`/`.bat` rad etiladi."""
        args = [part.replace("{port}", str(port)) for part in project.config.command]
        program = args[0]
        local = project.directory / program
        if local.is_file():
            found: str | None = str(local)
        elif program.lower() in ("python", "python.exe"):
            found = getattr(sys, "_base_executable", sys.executable)
        else:
            found = shutil.which(program)
        if found is None:
            raise HostingError(400, f"dastur topilmadi: {program}")
        if found.lower().endswith(_SCRIPT_SUFFIXES):
            raise HostingError(
                400,
                f"{Path(found).name} — skript; dasturni to'g'ridan-to'g'ri bering (masalan: node)",
            )
        return [found, *args[1:]]

    async def start_project(self, name: str) -> dict[str, Any]:
        project = self._project(name)
        async with project.lock:
            if project.state != "running":
                await self._start_locked(project)
        return self.describe(project)

    async def _start_locked(self, project: Project) -> None:
        config = project.config
        project.error = None
        project.last_activity = time.time()
        if config.kind == "static":
            project.state = "running"
            await self._sync()
            return
        try:
            port = await asyncio.to_thread(self._allocate_port, project)
            command = await asyncio.to_thread(self._resolve_command, project, port)
        except HostingError as exc:
            await self._fail(project, exc.detail)
            raise
        if config.port != port:
            config.port = port
            await asyncio.to_thread(self._save)
        project.state = "starting"
        await self._sync()
        env = {k: v for k, v in os.environ.items() if not k.startswith(("SRV1_", "__PYVENV"))}
        env |= {"PORT": str(port), "HOST": "127.0.0.1", "PYTHONUNBUFFERED": "1"}
        project.write(f"[srv1] ishga tushirilmoqda: {' '.join(command)}")
        try:
            project.process = await self.ctx.spawn(
                command,
                cwd=project.directory,
                env=env,
                memory_limit_mb=config.memory_limit_mb,
                on_line=project.write,
            )
        except OSError as exc:
            await self._fail(project, f"ishga tushmadi: {exc}")
            raise HostingError(500, project.error or "ishga tushmadi") from exc
        if not await self._wait_ready(project, port):
            code = project.process.returncode
            reason = (
                f"port {port} ochilmadi ({self.store.config.ready_timeout_s:g} s)"
                if code is None
                else f"jarayon darhol tugadi (kod {code})"
            )
            await self._kill(project)
            await self._fail(project, reason)
            raise HostingError(502, reason)
        project.state = "running"
        project.watcher = asyncio.create_task(self._watch(project, project.process))
        await self._sync()

    async def _wait_ready(self, project: Project, port: int) -> bool:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.store.config.ready_timeout_s
        while loop.time() < deadline:
            if project.process is None or not project.process.running:
                return False
            if await _port_accepts(port):
                return True
            await asyncio.sleep(0.1)
        return False

    async def _watch(self, project: Project, process: ManagedProcess) -> None:
        """Jarayon o'zi tugasa (biz to'xtatmagan bo'lsak), holatni `failed` qiladi."""
        code = await process.wait()
        if project.process is process and project.state == "running":
            project.process = None
            await process.stop()
            await self._fail(project, f"jarayon kutilmaganda tugadi (kod {code})")

    async def _fail(self, project: Project, reason: str) -> None:
        project.state, project.error = "failed", reason
        project.write(f"[srv1] xato: {reason}")
        project.flush_log()
        self.ctx.publish("state", {"name": project.config.name, "state": "failed", "error": reason})
        await self._sync()

    async def _kill(self, project: Project) -> None:
        process, project.process = project.process, None
        watcher, project.watcher = project.watcher, None
        if process is not None:
            await process.stop()
        if watcher is not None and watcher is not asyncio.current_task():
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)

    async def stop_project(self, name: str, *, sleep: bool = False) -> dict[str, Any]:
        project = self._project(name)
        async with project.lock:
            await self._kill(project)
            project.state = "sleeping" if sleep else "stopped"
            project.error = None
            project.write("[srv1] uxlatildi" if sleep else "[srv1] to'xtatildi")
            project.flush_log()
            await self._sync()
        if not sleep:
            # Uxlayotgan loyiha tunnel orqali ham uyg'onadi; to'xtatilgani esa yopiladi.
            await self._close_tunnel(name, "loyiha to'xtatildi")
            await self.ctx.audit("hosting.project_stop", name)
        self.ctx.publish("state", {"name": name, "state": project.state, "error": None})
        return self.describe(project)

    async def restart_project(self, name: str) -> dict[str, Any]:
        await self.stop_project(name)
        return await self.start_project(name)

    # --- tunnel (cloudflared) -------------------------------------------------
    async def open_tunnel(self, name: str) -> dict[str, Any]:
        """Loyihani internetga ochadi. Faqat ishlayotgan yoki uxlayotgan loyiha uchun."""
        project = self._project(name)
        if self.tunnels.get(name) is not None:
            return self.describe(project)  # allaqachon ochiq — yangi jarayon ham, audit ham yo'q
        try:
            if project.state not in ("running", "sleeping"):
                raise HostingError(409, f"avval loyihani ishga tushiring (holati: {project.state})")
            if self.caddy is None or not self.caddy.running:
                raise HostingError(503, "Caddy ishlamayapti; tunnel ochib bo'lmaydi")
            cfg = self.store.config
            origin = f"http://{cfg.listen_host}:{cfg.listen_port}"
            tunnel = await self.tunnels.open(name, origin, self.host_of(name))
        except HostingError as exc:
            await self.ctx.audit(
                "hosting.tunnel_open", name, ok=False, detail={"error": exc.detail}
            )
            raise
        await self.ctx.audit("hosting.tunnel_open", name, detail={"url": tunnel.url})
        project.write(f"[srv1] internetga ochildi: {tunnel.url}")
        self.ctx.publish("tunnel", {"name": name, "url": tunnel.url})
        return self.describe(project)

    async def close_tunnel(self, name: str) -> dict[str, Any]:
        project = self._project(name)
        if not await self._close_tunnel(name, "qo'lda yopildi"):
            raise HostingError(409, f"{name} uchun ochiq tunnel yo'q")
        return self.describe(project)

    async def _close_tunnel(self, name: str, reason: str) -> bool:
        if not await self.tunnels.close(name):
            return False
        await self.ctx.audit("hosting.tunnel_close", name, detail={"reason": reason})
        project = self.projects.get(name)
        if project is not None:
            project.write(f"[srv1] tunnel yopildi: {reason}")
        self.ctx.publish("tunnel", {"name": name, "url": None})
        return True

    def log_tail(self, name: str, tail: int) -> list[str]:
        lines = list(self._project(name).lines)
        return lines[-tail:]

    # --- uxlatish va uyg'otish ----------------------------------------------------
    async def _idle_loop(self) -> None:
        while True:
            await asyncio.sleep(self.store.config.idle_check_s)
            now = time.time()
            for project in list(self.projects.values()):
                project.flush_log()
                config = project.config
                idle_s = config.idle_minutes * 60
                if (
                    project.state == "running"
                    and config.kind != "static"
                    and idle_s > 0
                    and now - project.last_activity > idle_s
                ):
                    with suppress(HostingError):
                        await self.stop_project(config.name, sleep=True)

    async def _handle_wake(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Uxlayotgan loyihaga kelgan so'rov: loyihani uyg'otib, brauzerni qayta yo'naltiradi."""
        try:
            head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, TimeoutError, OSError):
            writer.close()
            return
        status, extra, body = await self._wake_response(head[:WAKE_REQUEST_MAX_BYTES])
        payload = body.encode("utf-8")
        header = (
            f"HTTP/1.1 {status}\r\n{extra}Content-Type: text/plain; charset=utf-8\r\n"
            f"Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n"
        )
        with suppress(OSError):
            writer.write(header.encode("latin-1") + payload)
            await writer.drain()
        writer.close()

    async def _wake_response(self, head: bytes) -> tuple[str, str, str]:
        lines = head.decode("latin-1").split("\r\n")
        target = lines[0].split(" ")[1] if lines and lines[0].count(" ") >= 2 else "/"
        headers = [line for line in lines[1:] if line.lower().startswith("host:")]
        host = headers[0].split(":", 1)[1] if headers else ""
        name = host.strip().split(":", 1)[0].lower().removesuffix("." + self.store.config.domain)
        project = self.projects.get(name)
        if project is None:
            return "404 Not Found", "", "SRV_1: bunday loyiha yo'q.\n"
        if not target.startswith("/") or target.startswith("//") or "\n" in target:
            target = "/"
        try:
            await self.start_project(name)
        except HostingError as exc:
            return "503 Service Unavailable", "", f"SRV_1: loyiha uyg'onmadi: {exc.detail}\n"
        # 307: brauzer shu so'rovni (metodi va tanasi bilan) qayta yuboradi — endi loyihaga.
        return "307 Temporary Redirect", f"Location: {target}\r\n", "SRV_1: loyiha uyg'otildi.\n"
