"""Plaginlar registri: topish, holat (bazada), yoqish/o'chirish, hodisa va vazifalarni ulash."""

import asyncio
from collections.abc import Coroutine, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import select

from srv1_core.audit import AuditLogger
from srv1_core.db import Database, PluginState
from srv1_core.events import EventBus, Subscription
from srv1_core.log_setup import get_logger
from srv1_core.paths import DataPaths
from srv1_core.plugins.runners import (
    CoreBackend,
    InprocessRunner,
    PluginStartError,
    Runner,
    SubprocessRunner,
)
from srv1_core.plugins.scheduler import Scheduler
from srv1_sdk.asgi import AsgiResponse
from srv1_sdk.manifest import (
    MANIFEST_FILE,
    ManifestError,
    Permissions,
    PluginManifest,
    load_manifest,
)
from srv1_sdk.panel import PanelSpec
from srv1_sdk.types import EventHandler

STATE_TOPIC = "plugins.state"
BUILTIN_DIR = Path(__file__).resolve().parents[3] / "plugins"

Source = Literal["builtin", "extra", "user"]
Status = Literal["stopped", "running", "error", "crashed", "invalid"]


class PluginNotFoundError(KeyError):
    """Bunday nomli plagin topilmagan."""


class PluginUnavailableError(RuntimeError):
    """Plagin bor, lekin so'ralgan amal hozirgi holatida mumkin emas."""


class PluginInfo(BaseModel):
    name: str
    source: Source
    status: Status
    enabled: bool
    error: str | None
    version: str | None
    description: str
    mode: Literal["inprocess", "subprocess"] | None
    heavy: bool
    memory_limit_mb: int | None
    permissions: Permissions | None
    pid: int | None
    has_panel: bool
    jobs: list[str]
    subscriptions: list[str]


@dataclass(slots=True)
class _Entry:
    name: str
    directory: Path
    source: Source
    manifest: PluginManifest | None
    error: str | None = None
    enabled: bool = False
    status: Status = "stopped"
    runner: Runner | None = None
    subscriptions: list[Subscription] = field(default_factory=list[Subscription])
    tasks: list[asyncio.Task[None]] = field(default_factory=list[asyncio.Task[None]])


def discover(dirs: Sequence[tuple[Path, Source]]) -> list[_Entry]:
    """`plugin.toml` bor papkalarni topadi. Yaroqsiz manifest ro'yxatda `invalid` bo'lib qoladi."""
    found: dict[str, _Entry] = {}
    for root, source in dirs:
        if not root.is_dir():
            continue
        for directory in sorted(p for p in root.iterdir() if (p / MANIFEST_FILE).is_file()):
            if directory.name in found:
                continue  # birinchi topilgani ustun (builtin > extra > user)
            try:
                entry = _Entry(directory.name, directory, source, load_manifest(directory))
            except ManifestError as exc:
                entry = _Entry(directory.name, directory, source, None, str(exc), status="invalid")
            found[directory.name] = entry
    return list(found.values())


class PluginRegistry:
    def __init__(
        self,
        *,
        dirs: Sequence[tuple[Path, Source]],
        paths: DataPaths,
        db: Database,
        bus: EventBus,
        audit: AuditLogger,
        scheduler: Scheduler,
    ) -> None:
        self._dirs = dirs
        self._paths = paths
        self._db = db
        self._bus = bus
        self._audit = audit
        self._scheduler = scheduler
        self._entries: dict[str, _Entry] = {}
        self._lock = asyncio.Lock()
        self._background: set[asyncio.Task[None]] = set()
        self._log = get_logger("srv1.plugins")

    # --- hayot sikli ------------------------------------------------------
    async def start(self) -> None:
        """Plaginlarni topadi va yoqilganlarini ishga tushiradi. Xato yadroni to'xtatmaydi."""
        saved = await self._load_states()
        async with self._lock:
            self._entries = {entry.name: entry for entry in discover(self._dirs)}
            for entry in self._entries.values():
                if entry.manifest is None:
                    self._log.warning("plugin_invalid", plugin=entry.name, error=entry.error)
                    continue
                # heavy plaginlar standart holatda o'chiq.
                entry.enabled = saved.get(entry.name, not entry.manifest.heavy)
                if entry.enabled:
                    await self._start(entry)

    async def stop(self) -> None:
        async with self._lock:
            for entry in self._entries.values():
                if entry.runner is not None:
                    await self._stop(entry, "stopped")
        if self._background:
            await asyncio.gather(*self._background, return_exceptions=True)

    # --- o'qish -------------------------------------------------------------
    def list(self) -> list[PluginInfo]:
        return [self._info(entry) for entry in sorted(self._entries.values(), key=lambda e: e.name)]

    def process_ids(self) -> dict[str, int]:
        """Alohida jarayonda ishlayotgan plaginlar: nom -> pid."""
        return {
            entry.name: entry.runner.pid
            for entry in self._entries.values()
            if entry.runner is not None and entry.runner.pid is not None
        }

    def get(self, name: str) -> PluginInfo:
        return self._info(self._entry(name))

    def panel(self, name: str) -> PanelSpec:
        runner = self._running(name)
        if runner.panel is None:
            raise PluginNotFoundError(f"plagin {name!r} panel bermagan")
        return runner.panel

    async def request(
        self,
        name: str,
        *,
        method: str,
        path: str,
        query: bytes,
        headers: Sequence[tuple[str, str]],
        body: bytes,
    ) -> AsgiResponse:
        return await self._running(name).request(
            method=method, path=path, query=query, headers=headers, body=body
        )

    # --- yoqish / o'chirish ---------------------------------------------------
    async def enable(self, name: str) -> PluginInfo:
        async with self._lock:
            entry = self._valid(name)
            entry.enabled = True
            await self._save_state(name, True)
            if entry.runner is None:
                await self._start(entry)
            ok = entry.status == "running"
            await self._audit.record("plugin.enable", name, ok=ok, detail={"error": entry.error})
            return self._info(entry)

    async def disable(self, name: str) -> PluginInfo:
        async with self._lock:
            entry = self._valid(name)
            entry.enabled = False
            await self._save_state(name, False)
            if entry.runner is not None:
                await self._stop(entry, "stopped")
            entry.status, entry.error = "stopped", None
            await self._audit.record("plugin.disable", name)
            self._publish_state(entry)
            return self._info(entry)

    # --- ichki: ishga tushirish va to'xtatish ----------------------------------
    def _make_runner(self, entry: _Entry, manifest: PluginManifest) -> Runner:
        data_dir = self._paths.plugin_data_dir(entry.name)
        data_dir.mkdir(parents=True, exist_ok=True)
        backend = CoreBackend(entry.name, self._bus, self._audit)
        if manifest.mode == "inprocess":
            return InprocessRunner(entry.directory, manifest, data_dir, backend)

        def on_exit(reason: str) -> None:
            self._spawn(self._handle_crash(entry.name, reason))

        return SubprocessRunner(entry.directory, manifest, data_dir, backend, on_exit)

    async def _start(self, entry: _Entry) -> None:
        manifest = entry.manifest
        if manifest is None:
            return
        runner = self._make_runner(entry, manifest)
        try:
            await runner.start()
            self._wire(entry, runner)
        except (PluginStartError, ValueError) as exc:
            entry.runner = runner
            await self._stop(entry, "error")
            entry.error = str(exc)
            self._log.error("plugin_start_failed", plugin=entry.name, error=entry.error)
        else:
            entry.runner, entry.status, entry.error = runner, "running", None
            self._log.info("plugin_started", plugin=entry.name, mode=manifest.mode, pid=runner.pid)
        if manifest.mode == "subprocess":
            await self._audit.record(
                "process.spawn",
                str(entry.directory),
                ok=entry.status == "running",
                detail={
                    "plugin": entry.name,
                    "pid": runner.pid,
                    "limit_mb": manifest.memory_limit_mb,
                },
            )
        self._publish_state(entry)

    def _wire(self, entry: _Entry, runner: Runner) -> None:
        for job in runner.jobs:
            self._scheduler.add(entry.name, job)
        for handler in runner.handlers:
            subscription = self._bus.subscribe(handler.pattern)
            entry.subscriptions.append(subscription)
            entry.tasks.append(asyncio.create_task(self._pump(entry.name, subscription, handler)))

    async def _pump(self, name: str, subscription: Subscription, handler: EventHandler) -> None:
        async for event in subscription:
            try:
                await handler.handler(event.topic, event.data)
            except Exception:
                self._log.exception("plugin_event_handler_failed", plugin=name, topic=event.topic)

    async def _stop(self, entry: _Entry, status: Status) -> None:
        self._scheduler.remove_owner(entry.name)
        for subscription in entry.subscriptions:
            self._bus.unsubscribe(subscription)
        if entry.tasks:
            await asyncio.gather(*entry.tasks, return_exceptions=True)
        entry.subscriptions, entry.tasks = [], []
        runner, entry.runner = entry.runner, None
        if runner is not None:
            try:
                await runner.stop()
            except Exception:
                self._log.exception("plugin_stop_failed", plugin=entry.name)
        entry.status = status

    async def _handle_crash(self, name: str, reason: str) -> None:
        async with self._lock:
            entry = self._entries.get(name)
            if entry is None or entry.runner is None:
                return
            await self._stop(entry, "crashed")
            entry.error = reason
            self._log.error("plugin_crashed", plugin=name, reason=reason)
            await self._audit.record("plugin.crashed", name, ok=False, detail={"reason": reason})
            self._publish_state(entry)

    # --- ichki: yordamchilar -----------------------------------------------------
    def _spawn(self, coro: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(coro)
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    def _entry(self, name: str) -> _Entry:
        entry = self._entries.get(name)
        if entry is None:
            raise PluginNotFoundError(f"plagin topilmadi: {name!r}")
        return entry

    def _valid(self, name: str) -> _Entry:
        entry = self._entry(name)
        if entry.manifest is None:
            raise PluginUnavailableError(f"plagin {name!r} manifesti yaroqsiz: {entry.error}")
        return entry

    def _running(self, name: str) -> Runner:
        entry = self._entry(name)
        if entry.runner is None or entry.status != "running":
            raise PluginUnavailableError(f"plagin {name!r} ishlamayapti (holat: {entry.status})")
        return entry.runner

    def _publish_state(self, entry: _Entry) -> None:
        self._bus.publish(
            STATE_TOPIC, {"name": entry.name, "status": entry.status, "error": entry.error}
        )

    def _info(self, entry: _Entry) -> PluginInfo:
        manifest, runner = entry.manifest, entry.runner
        return PluginInfo(
            name=entry.name,
            source=entry.source,
            status=entry.status,
            enabled=entry.enabled,
            error=entry.error,
            version=None if manifest is None else manifest.version,
            description="" if manifest is None else manifest.description,
            mode=None if manifest is None else manifest.mode,
            heavy=manifest is not None and manifest.heavy,
            memory_limit_mb=(
                manifest.memory_limit_mb if manifest and manifest.mode == "subprocess" else None
            ),
            permissions=None if manifest is None else manifest.permissions,
            pid=None if runner is None else runner.pid,
            has_panel=runner is not None and runner.panel is not None,
            jobs=self._scheduler.job_ids(entry.name),
            subscriptions=[] if runner is None else [h.pattern for h in runner.handlers],
        )

    async def _load_states(self) -> dict[str, bool]:
        async with self._db.session() as session:
            rows = await session.execute(select(PluginState.name, PluginState.enabled))
            return {name: enabled for name, enabled in rows.all()}

    async def _save_state(self, name: str, enabled: bool) -> None:
        async with self._db.session() as session, session.begin():
            await session.merge(
                PluginState(name=name, enabled=enabled, updated_at=datetime.now(UTC))
            )
