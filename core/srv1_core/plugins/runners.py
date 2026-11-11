"""Plagin ishlatuvchilar: jarayon ichida (`InprocessRunner`) va bolada (`SubprocessRunner`)."""

import asyncio
import itertools
import os
import sys
from collections.abc import Callable, Coroutine, Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any, Protocol

from srv1_core.audit import AuditLogger
from srv1_core.events import EventBus
from srv1_core.log_setup import get_logger
from srv1_sdk.asgi import AsgiResponse, json_error
from srv1_sdk.context import LogLevel, PluginContext, plugin_topic_prefix
from srv1_sdk.jobobject import MemoryJob
from srv1_sdk.manifest import PluginManifest
from srv1_sdk.panel import PanelSpec
from srv1_sdk.process import spawn_in_job
from srv1_sdk.protocol import (
    EXIT_LOAD_FAILED,
    EXIT_OUT_OF_MEMORY,
    LINE_LIMIT,
    Message,
    decode,
    encode,
    pack_body,
    unpack_body,
)
from srv1_sdk.runtime import LoadedPlugin
from srv1_sdk.types import EventHandler, Job, JobCallback

START_TIMEOUT_S = 20.0
REQUEST_TIMEOUT_S = 30.0
STOP_TIMEOUT_S = 5.0


class PluginStartError(RuntimeError):
    """Plagin ishga tushmadi."""


class CoreBackend:
    """`PluginContext` ortidagi yadro xizmatlari. Ikkala rejimda ham yadro jarayonida ishlaydi."""

    def __init__(self, name: str, bus: EventBus, audit: AuditLogger) -> None:
        self._name = name
        self._bus = bus
        self._audit = audit
        self._log = get_logger(f"srv1.plugin.{name}")

    def publish(self, topic: str, data: Mapping[str, Any]) -> None:
        if not topic.startswith(plugin_topic_prefix(self._name)):
            self._log.warning("publish_outside_namespace", topic=topic)
            return
        self._bus.publish(topic, data)

    async def audit(self, action: str, target: str, ok: bool, detail: Mapping[str, Any]) -> None:
        await self._audit.record(action, target, actor=f"plugin:{self._name}", ok=ok, detail=detail)

    def log(self, level: LogLevel, event: str, fields: Mapping[str, Any]) -> None:
        getattr(self._log, level)(event, **{f"p_{key}": value for key, value in fields.items()})


class Runner(Protocol):
    panel: PanelSpec | None
    handlers: Sequence[EventHandler]
    jobs: Sequence[Job]

    @property
    def pid(self) -> int | None: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def request(
        self,
        *,
        method: str,
        path: str,
        query: bytes,
        headers: Sequence[tuple[str, str]],
        body: bytes,
    ) -> AsgiResponse: ...


class InprocessRunner:
    def __init__(
        self,
        plugin_dir: Path,
        manifest: PluginManifest,
        data_dir: Path,
        backend: CoreBackend,
        projects_dir: Path,
    ) -> None:
        self._plugin = LoadedPlugin(
            plugin_dir, manifest, PluginContext(manifest, data_dir, backend, projects_dir)
        )
        self.panel: PanelSpec | None = None
        self.handlers: Sequence[EventHandler] = ()
        self.jobs: Sequence[Job] = ()

    @property
    def pid(self) -> int | None:
        return None

    async def start(self) -> None:
        try:
            self._plugin.load()
            await self._plugin.start()
        except Exception as exc:
            self._plugin.unload()
            raise PluginStartError(str(exc)) from exc
        self.panel = self._plugin.panel
        self.handlers = self._plugin.subscriptions
        self.jobs = self._plugin.jobs

    async def stop(self) -> None:
        try:
            await self._plugin.stop()
        finally:
            self._plugin.unload()

    async def request(
        self,
        *,
        method: str,
        path: str,
        query: bytes,
        headers: Sequence[tuple[str, str]],
        body: bytes,
    ) -> AsgiResponse:
        return await self._plugin.handle_request(
            method=method, path=path, query=query, headers=headers, body=body
        )


def _child_python() -> tuple[str, dict[str, str]]:
    """Bola uchun interpretator va muhit.

    venv'dagi `python.exe` — ishga tushirgich: haqiqiy Python uning bolasi bo'ladi va
    Job Object'ga biriktirishdan oldin tug'ilib qolishi mumkin. Shuning uchun asosiy
    interpretator to'g'ridan-to'g'ri ishga tushiriladi (`multiprocessing` ham shunday qiladi).
    """
    env = dict(os.environ)
    base: str = getattr(sys, "_base_executable", sys.executable)
    if base != sys.executable:
        env["__PYVENV_LAUNCHER__"] = sys.executable
    return base, env


def _exit_reason(code: int | None) -> str:
    if code == EXIT_OUT_OF_MEMORY:
        return "xotira limiti oshdi"
    if code == EXIT_LOAD_FAILED:
        return "plagin yuklanmadi"
    return f"jarayon kutilmaganda tugadi (kod {code})"


class SubprocessRunner:
    """Plaginni `python -m srv1_sdk.host` bola jarayonida, Job Object ichida ishlatadi."""

    def __init__(
        self,
        plugin_dir: Path,
        manifest: PluginManifest,
        data_dir: Path,
        backend: CoreBackend,
        projects_dir: Path,
        on_exit: Callable[[str], None],
    ) -> None:
        self._dir = plugin_dir
        self._manifest = manifest
        self._data_dir = data_dir
        self._projects_dir = projects_dir
        self._backend = backend
        self._on_exit = on_exit
        self._process: asyncio.subprocess.Process | None = None
        self._job: MemoryJob | None = None
        self._tasks: list[asyncio.Task[None]] = []
        self._background: set[asyncio.Task[None]] = set()
        self._pending: dict[int, asyncio.Future[Message]] = {}
        self._ids = itertools.count(1)
        self._ready: asyncio.Future[Message] | None = None
        self._stopping = False
        self.panel: PanelSpec | None = None
        self.handlers: Sequence[EventHandler] = ()
        self.jobs: Sequence[Job] = ()

    @property
    def pid(self) -> int | None:
        return None if self._process is None else self._process.pid

    @property
    def peak_memory_bytes(self) -> int | None:
        return None if self._job is None else self._job.peak_bytes()

    # --- hayot sikli ------------------------------------------------------
    async def start(self) -> None:
        self._job = MemoryJob(self._manifest.memory_limit_mb * 1024 * 1024)
        self._ready = asyncio.get_running_loop().create_future()
        python, env = _child_python()
        args = [python, "-X", "utf8", "-m", "srv1_sdk.host"]
        args += ["--dir", str(self._dir), "--data-dir", str(self._data_dir)]
        args += ["--projects-dir", str(self._projects_dir)]
        self._process = await spawn_in_job(
            args,
            self._job,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=LINE_LIMIT,
        )
        try:
            self._tasks = [
                asyncio.create_task(self._read_stdout()),
                asyncio.create_task(self._read_stderr()),
            ]
            ready = await asyncio.wait_for(self._ready, START_TIMEOUT_S)
            self._adopt(ready)
        except Exception as exc:
            await self.stop()
            reason = "ishga tushish vaqti tugadi" if isinstance(exc, TimeoutError) else str(exc)
            raise PluginStartError(reason) from exc

    def _adopt(self, ready: Message) -> None:
        panel = ready.get("panel")
        self.panel = None if panel is None else PanelSpec.model_validate(panel)
        self.handlers = [
            EventHandler(str(pattern), self._forward_event) for pattern in ready["subscriptions"]
        ]
        self.jobs = [
            Job(
                id=str(job["id"]),
                func=self._job_sender(str(job["id"])),
                interval_s=job.get("interval_s"),
                cron=job.get("cron"),
            )
            for job in ready["jobs"]
        ]

    async def stop(self) -> None:
        self._stopping = True
        process = self._process
        if process is not None and process.returncode is None:
            with suppress(OSError, RuntimeError):
                await self._send({"type": "stop"})
            try:
                await asyncio.wait_for(process.wait(), STOP_TIMEOUT_S)
            except TimeoutError:
                with suppress(ProcessLookupError):
                    process.kill()
                await process.wait()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks = []
        if self._job is not None:
            self._job.close()
            self._job = None

    # --- yadro -> bola ------------------------------------------------------
    async def _send(self, message: Message) -> None:
        process = self._process
        if process is None or process.stdin is None or process.returncode is not None:
            raise RuntimeError("plagin jarayoni ishlamayapti")
        process.stdin.write(encode(message))
        await process.stdin.drain()

    async def _forward_event(self, topic: str, data: Mapping[str, Any]) -> None:
        await self._send({"type": "event", "topic": topic, "data": dict(data)})

    def _job_sender(self, job_id: str) -> JobCallback:
        async def fire() -> None:
            await self._send({"type": "job", "id": job_id})

        return fire

    async def request(
        self,
        *,
        method: str,
        path: str,
        query: bytes,
        headers: Sequence[tuple[str, str]],
        body: bytes,
    ) -> AsgiResponse:
        request_id = next(self._ids)
        future: asyncio.Future[Message] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        try:
            await self._send(
                {
                    "type": "request",
                    "id": request_id,
                    "method": method,
                    "path": path,
                    "query": query.decode("latin-1"),
                    "headers": [list(pair) for pair in headers],
                    "body": pack_body(body),
                }
            )
            reply = await asyncio.wait_for(future, REQUEST_TIMEOUT_S)
        except TimeoutError:
            return json_error(504, "plagin javob bermadi")
        except (RuntimeError, OSError, ConnectionError) as exc:
            return json_error(502, f"plagin jarayoni mavjud emas: {exc}")
        finally:
            self._pending.pop(request_id, None)
        response_headers = tuple((str(k), str(v)) for k, v in reply.get("headers", []))
        return AsgiResponse(int(reply["status"]), response_headers, unpack_body(reply["body"]))

    # --- bola -> yadro ------------------------------------------------------
    async def _read_stdout(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        try:
            async for line in process.stdout:
                self._handle_line(line)
        except (ValueError, asyncio.LimitOverrunError) as exc:
            self._backend.log("error", "protocol_error", {"error": str(exc)})
            with suppress(ProcessLookupError):
                process.kill()
        code = await process.wait()
        self._fail_waiters(_exit_reason(code))
        if not self._stopping:
            self._on_exit(_exit_reason(code))

    def _handle_line(self, line: bytes) -> None:
        message = decode(line)
        kind = message["type"]
        if kind == "response":
            future = self._pending.get(int(message["id"]))
            if future is not None and not future.done():
                future.set_result(message)
        elif kind == "publish":
            self._backend.publish(str(message["topic"]), message.get("data") or {})
        elif kind == "log":
            self._backend.log(message["level"], str(message["event"]), message.get("fields") or {})
        elif kind == "audit":
            self._spawn(
                self._backend.audit(
                    str(message["action"]),
                    str(message["target"]),
                    bool(message.get("ok", True)),
                    message.get("detail") or {},
                )
            )
        elif kind == "ready" and self._ready is not None and not self._ready.done():
            self._ready.set_result(message)
        elif kind == "fatal" and self._ready is not None and not self._ready.done():
            self._ready.set_exception(PluginStartError(str(message.get("error"))))

    def _spawn(self, coro: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(coro)
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    def _fail_waiters(self, reason: str) -> None:
        if self._ready is not None and not self._ready.done():
            self._ready.set_exception(PluginStartError(reason))
        for future in self._pending.values():
            if not future.done():
                future.set_exception(RuntimeError(reason))

    async def _read_stderr(self) -> None:
        process = self._process
        if process is None or process.stderr is None:
            return
        with suppress(ValueError):
            async for line in process.stderr:
                text = line.decode("utf-8", "replace").rstrip()
                if text:
                    self._backend.log("info", "plugin_stderr", {"line": text})
