"""`NetService`: ushlash ishchisini boshqarish, natijani saqlash va signallarni tarqatish."""

import asyncio
import json
import os
import sys
import time
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from functools import partial
from pathlib import Path
from typing import Any, cast

from srv1_sdk.context import PluginContext
from srv1_sdk.process import ManagedProcess

from ..models import MB, MonitorError
from .engine import normalize_ip
from .ifaces import NPCAP_URL, list_interfaces, npcap_installed
from .journal import Journal
from .models import CONFIG_FILE, MAX_EXCLUDED, NetConfig, load_config, save_config
from .notices import STOPPED_TITLE, net_notice
from .store import NetStore

DB_FILE = "netcap.db"
OPTIONS_FILE = "netcap-worker.json"
ENV_WORKER = "SRV1_NETCAP_WORKER"
ALERTS_KEPT = 2000
READY_TIMEOUT_S = 15.0
STOP_TIMEOUT_S = 3.0
QUEUE_MAX = 120
# Bildirishnomalar orasidagi eng kam vaqt: signal ko'p bo'lsa ham ekran to'lib ketmaydi.
NOTIFY_GAP_S = 10.0
PLUGIN_DIR = Path(__file__).resolve().parents[1]

NPCAP_MISSING = (
    "Npcap o'rnatilmagan. Paketlarni ushlash uchun uni o'rnating "
    f"({NPCAP_URL}), so'ng qayta urinib ko'ring."
)


def _base_python() -> str:
    # venv'dagi python.exe — ishga tushirgich; haqiqiy interpretator to'g'ridan-to'g'ri chaqiriladi.
    return getattr(sys, "_base_executable", sys.executable)


def worker_command(options_file: Path) -> list[str]:
    override = os.environ.get(ENV_WORKER, "").strip()
    if override:  # sinov: soxta ishchi skripti
        return [_base_python(), override, str(options_file)]
    return [_base_python(), "-m", "netcap.worker", str(options_file)]


def worker_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("SRV1_", "PYTHON"))}
    if _base_python() != sys.executable:
        env["__PYVENV_LAUNCHER__"] = sys.executable  # asosiy interpretator venv'ni ko'rsin
    env |= {
        "PYTHONPATH": str(PLUGIN_DIR),
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    return env


class NetService:
    def __init__(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self._config_file = ctx.data_path(CONFIG_FILE)
        self.config: NetConfig = load_config(self._config_file)
        self._thread = ThreadPoolExecutor(max_workers=1, thread_name_prefix="netcap")
        self._store: NetStore | None = None
        self._lock = asyncio.Lock()
        self._process: ManagedProcess | None = None
        self._queue: asyncio.Queue[dict[str, Any] | None] | None = None
        self._consumer: asyncio.Task[None] | None = None
        self._watcher: asyncio.Task[None] | None = None
        self._ready = asyncio.Event()
        self._state = "stopped"  # stopped | starting | running | paused | error
        self._error = ""
        self._last_text = ""
        self._interface = ""
        self._stats: dict[str, Any] = {}
        self._hosts: list[dict[str, Any]] = []
        self._lost_ticks = 0
        self._last_notify = 0.0
        self._journal = Journal(ctx.log, 0, "")

    # --- hayot sikli ------------------------------------------------------
    async def _run[T](self, func: Callable[..., T], *args: Any) -> T:  # noqa: ANN401
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._thread, partial(func, *args))

    @property
    def store(self) -> NetStore:
        if self._store is None:
            raise MonitorError(503, "tarmoq ombori hali tayyor emas")
        return self._store

    async def open(self) -> None:
        self._store = await self._run(NetStore, self.ctx.data_path(DB_FILE))

    async def close(self) -> None:
        with suppress(MonitorError):
            await self.stop()
        if self._store is not None:
            await self._run(self._store.close)
            self._store = None
        self._thread.shutdown(wait=False)

    # --- ushlashni boshqarish ---------------------------------------------
    @property
    def state(self) -> str:
        """`stopped` | `starting` | `running` | `paused` | `error`."""
        return self._state

    @property
    def capturing(self) -> bool:
        return self._process is not None and self._process.running

    async def start(self, name: str) -> dict[str, Any]:
        async with self._lock:
            if self.capturing:
                raise MonitorError(409, "ushlash allaqachon ishlayapti")
            if not npcap_installed():
                raise MonitorError(409, NPCAP_MISSING)
            if name not in {item["name"] for item in list_interfaces()}:
                raise MonitorError(404, f"interfeys topilmadi: {name}")
            await self._save(self.config.model_copy(update={"interface": name}))
            await self._launch(name)
        return await self.status()

    async def _launch(self, name: str) -> None:
        options_file = self.ctx.data_path(OPTIONS_FILE)
        options = json.dumps(self.config.worker_options(name))
        await asyncio.to_thread(options_file.write_text, options, encoding="utf-8")
        self._state, self._error, self._last_text = "starting", "", ""
        self._interface, self._stats, self._hosts, self._lost_ticks = name, {}, [], 0
        self._ready = asyncio.Event()
        self._journal = Journal(self.ctx.log, self.config.log_interval_s, name)
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=QUEUE_MAX)
        self._queue = queue
        try:
            process = await self.ctx.spawn(
                worker_command(options_file),
                cwd=self.ctx.data_dir,
                env=worker_env(),
                memory_limit_mb=self.config.worker_memory_mb,
                on_line=self._on_line,
                accept_input=True,
            )
        except OSError as exc:  # ruxsat yo'qligi (`PermissionDenied`) ham shu yerga tushadi
            self._state, self._error = "error", str(exc)
            raise MonitorError(500, f"ushlash jarayoni ishga tushmadi: {exc}") from exc
        self._process = process
        self._consumer = asyncio.create_task(self._consume(queue))
        self._watcher = asyncio.create_task(self._watch(process))
        with suppress(TimeoutError):
            await asyncio.wait_for(self._ready.wait(), READY_TIMEOUT_S)
        if self.state != "running":  # holatni ishchining `ready` xabari o'zgartiradi
            error = self._error or self._last_text or "ushlash boshlanmadi (javob kelmadi)"
            await self._shutdown(process)
            self._state, self._error = "error", error
            await self._audit("net.capture_start", name, ok=False, error=error)
            raise MonitorError(502, error)
        self.ctx.log("info", "netcap_started", interface=name, pid=process.pid)
        await self._audit(
            "net.capture_start",
            name,
            filter=self.config.bpf_filter,
            store_payload=self.config.store_payload,
            geo=self.config.geo,
        )

    async def stop(self) -> dict[str, Any]:
        async with self._lock:
            process = self._process
            if process is not None:
                await self._shutdown(process)
                self._state = "stopped"
                self.ctx.log("info", "netcap_stopped", interface=self._interface)
                await self._audit("net.capture_stop", self._interface, packets=self._total())
        return await self.status()

    async def _shutdown(self, process: ManagedProcess) -> None:
        """Ishchini tartibli to'xtatadi (kutmasa — o'ldiradi) va qolgan natijani yozib bo'ladi."""
        self._process = None  # `_watch` buni kutilgan to'xtash deb biladi
        if await process.send_line('{"c":"stop"}'):
            with suppress(TimeoutError):
                await asyncio.wait_for(process.wait(), STOP_TIMEOUT_S)
        await process.stop()
        if self._watcher is not None:
            await asyncio.gather(self._watcher, return_exceptions=True)
            self._watcher = None
        if self._queue is not None and self._consumer is not None:
            await self._queue.put(None)
            await asyncio.gather(self._consumer, return_exceptions=True)
        self._queue, self._consumer = None, None

    async def pause(self) -> dict[str, Any]:
        return await self._command("pause", "paused")

    async def resume(self) -> dict[str, Any]:
        return await self._command("resume", "running")

    async def _command(self, name: str, state: str) -> dict[str, Any]:
        process = self._process
        if process is None or self._state not in ("running", "paused"):
            raise MonitorError(409, "ushlash ishlamayapti")
        if not await process.send_line(json.dumps({"c": name})):
            raise MonitorError(502, "ushlash jarayoni javob bermayapti")
        self._state = state
        self.ctx.log("info", f"netcap_{state}", interface=self._interface)
        return await self.status()

    # --- ishchidan kelgan satrlar -----------------------------------------
    def _on_line(self, line: str) -> None:
        try:
            message = json.loads(line)
        except ValueError:
            message = None
        if not isinstance(message, dict):
            if line.strip():  # scapy ogohlantirishi yoki xato izi: tashxis uchun oxirgisi saqlanadi
                self._last_text = line.strip()[:300]
            return
        data = cast(dict[str, Any], message)
        kind = data.get("t")
        if kind == "ready":
            self._state = "running"
            self._ready.set()
        elif kind == "error":
            self._error = str(data.get("error", ""))[:300]
            self._ready.set()
        elif kind == "tick" and self._queue is not None:
            try:
                self._queue.put_nowait(data)
            except asyncio.QueueFull:
                self._lost_ticks += 1

    async def _consume(self, queue: asyncio.Queue[dict[str, Any] | None]) -> None:
        while True:
            message = await queue.get()
            if message is None:
                return
            try:
                await self._apply(message)
            except Exception as exc:
                self.ctx.log("warning", "netcap_tick_failed", error=f"{type(exc).__name__}: {exc}")

    async def _apply(self, message: Mapping[str, Any]) -> None:
        packets = _dicts(message.get("packets"))
        alerts = _dicts(message.get("alerts"))
        if packets or alerts:
            await self._run(self.store.add, packets, alerts, self.config.max_packets, ALERTS_KEPT)
        self._hosts = _dicts(message.get("hosts"))
        self._stats = {key: value for key, value in message.items() if _is_scalar(value)}
        if self._state in ("running", "paused"):
            self._state = "paused" if message.get("paused") else "running"
        self.ctx.publish(
            "net",
            {"ts": message.get("ts"), "pps": message.get("pps", 0), "total": self._total()},
        )
        for alert in alerts:
            self._announce(alert)
        self._journal.feed(message, packets, len(alerts))

    def _announce(self, alert: Mapping[str, Any]) -> None:
        fields = {key: str(alert.get(key, ""))[:200] for key in ("kind", "src", "dst", "note")}
        self.ctx.log("warning", "netcap_alert", **fields)
        self.ctx.publish("net_alert", {"ts": alert.get("ts"), **fields})
        now = time.monotonic()
        if now - self._last_notify >= NOTIFY_GAP_S:
            self._last_notify = now
            title, text = net_notice(fields)
            self.ctx.notify(title, text)

    async def _watch(self, process: ManagedProcess) -> None:
        code = await process.wait()
        if self._process is not process:
            return  # `stop()` chaqirilgan
        # Ishchi o'zi tugadi: xato yoki xotira limiti.
        self._process = None
        await process.stop()
        if self._queue is not None:
            await self._queue.put(None)
        error = self._error or self._last_text or f"ishchi jarayon to'xtadi (kod {code})"
        starting = self._state == "starting"
        self._state, self._error = "error", error
        self._ready.set()
        if starting:
            return  # `_launch` kutib turibdi: xatoni o'zi qayd etadi
        self.ctx.log("warning", "netcap_died", interface=self._interface, code=code, error=error)
        await self._audit("net.capture_stop", self._interface, ok=False, error=error, code=code)
        self.ctx.notify(STOPPED_TITLE, error, level="error")

    async def _audit(self, action: str, target: str, *, ok: bool = True, **detail: Any) -> None:  # noqa: ANN401
        await self.ctx.audit(action, target or "-", ok=ok, detail=detail)

    def _total(self) -> int:
        total = self._stats.get("total", 0)
        return total if isinstance(total, int) else 0

    # --- sozlama ----------------------------------------------------------
    async def _save(self, config: NetConfig) -> None:
        self.config = config
        await asyncio.to_thread(save_config, self._config_file, config)

    async def exclude(self, addresses: list[str]) -> list[dict[str, str]]:
        """Manzillarni kuzatuvdan chiqaradi; ushlash ishlab turgan bo'lsa darhol kuchga kiradi."""
        try:
            added = [normalize_ip(item) for item in addresses if item.strip()]
        except ValueError as exc:
            raise MonitorError(422, f"yaroqsiz IP manzil: {exc}") from exc
        if not added:
            raise MonitorError(422, "IP manzil kiritilmadi")
        merged = tuple(dict.fromkeys((*self.config.excluded, *added)))
        if len(merged) > MAX_EXCLUDED:
            raise MonitorError(422, f"ro'yxat {MAX_EXCLUDED} tadan oshmasligi kerak")
        await self._set_excluded(merged)
        return self.excluded()

    async def unexclude(self, address: str) -> list[dict[str, str]]:
        try:
            target = normalize_ip(address)
        except ValueError as exc:
            raise MonitorError(422, f"yaroqsiz IP manzil: {address}") from exc
        if target not in self.config.excluded:
            raise MonitorError(404, f"ro'yxatda yo'q: {target}")
        await self._set_excluded(tuple(item for item in self.config.excluded if item != target))
        return self.excluded()

    async def _set_excluded(self, excluded: tuple[str, ...]) -> None:
        await self._save(self.config.model_copy(update={"excluded": excluded}))
        self.ctx.log("info", "netcap_excluded", count=len(excluded))
        if self._process is not None:
            await self._process.send_line(json.dumps({"c": "exclude", "ips": list(excluded)}))

    def excluded(self) -> list[dict[str, str]]:
        return [{"ip": item} for item in self.config.excluded]

    async def update_settings(self, changes: Mapping[str, Any]) -> dict[str, Any]:
        """Sozlamani almashtiradi.

        Ishchiga tegishli sozlama o'zgarsa, ushlash yangisi bilan qayta boshlanadi. Faqat
        plagin tomoni (jurnal oralig'i, saqlanadigan paketlar soni) o'zgarsa — to'xtamaydi.
        """
        merged = self.config.model_dump() | dict(changes)
        config = NetConfig.model_validate(merged)
        previous = self.config
        payload_enabled = config.store_payload and not previous.store_payload
        name = self._interface
        restart = (
            config.worker_options(name) != previous.worker_options(name)
            or config.worker_memory_mb != previous.worker_memory_mb
        )
        async with self._lock:
            await self._save(config)
            if payload_enabled:
                await self._audit("net.payload_store", "on")
            process = self._process
            if process is not None and restart:
                await self._shutdown(process)
                self._state = "stopped"
                await self._launch(name)
            elif config.log_interval_s != previous.log_interval_s:
                self._journal = Journal(self.ctx.log, config.log_interval_s, name)
        return self.settings()

    def settings(self) -> dict[str, Any]:
        config = self.config
        return {
            "bpf_filter": config.bpf_filter,
            "store_payload": config.store_payload,
            "geo": config.geo,
            "suspicious_ports": ", ".join(str(port) for port in config.suspicious_ports),
            "scan_ports": config.scan_ports,
            "scan_window_s": config.scan_window_s,
            "max_packets": config.max_packets,
            "log_interval_s": config.log_interval_s,
        }

    # --- o'qish -----------------------------------------------------------
    async def status(self) -> dict[str, Any]:
        stats = self._stats
        process = self._process
        packets, alerts = await self._run(self.store.counts)
        return {
            "state": self._state,
            "interface": self._interface or self.config.interface,
            "npcap": npcap_installed(),
            "error": self._error,
            "total": self._total(),
            "pps": stats.get("pps", 0),
            "bytes": stats.get("bytes", 0),
            "ignored": stats.get("ignored", 0),
            "skipped": stats.get("skipped", 0),
            "errors": stats.get("errors", 0),
            "last_error": stats.get("last_error", ""),
            "suppressed": stats.get("suppressed", 0),
            "lost_ticks": self._lost_ticks,
            "stored_packets": packets,
            "stored_alerts": alerts,
            "store_bytes": await self._run(self.store.size),
            "worker_mb": round(process.memory_bytes() / MB, 1) if process is not None else 0,
            "excluded": len(self.config.excluded),
            "store_payload": "on" if self.config.store_payload else "off",
            "geo": "on" if self.config.geo else "off",
            "marked": stats.get("marked", 0),
            "log_interval_s": self.config.log_interval_s,
        }

    def summary(self) -> list[dict[str, str]]:
        """Bitta qatorli jadval: holat va matnli qiymatlar (panel uchun)."""
        interval = self.config.log_interval_s
        return [
            {
                "state": self._state,
                "interface": self._interface or self.config.interface,
                "npcap": "ok" if npcap_installed() else "—",
                "store_payload": "on" if self.config.store_payload else "off",
                "geo": "on" if self.config.geo else "off",
                "journal": f"{interval} s" if interval else "off",
                "error": self._error,
            }
        ]

    def interfaces(self) -> list[dict[str, Any]]:
        active = self._interface if self.capturing else ""
        return [
            {**item, "capturing": "●" if item["name"] == active else ""}
            for item in list_interfaces()
        ]

    async def packets(self, limit: int, ip: str, proto: str) -> list[dict[str, Any]]:
        address = ""
        if ip.strip():
            try:
                address = normalize_ip(ip)
            except ValueError as exc:
                raise MonitorError(422, f"yaroqsiz IP manzil: {ip}") from exc
        return await self._run(self.store.packets, limit, address, proto.strip())

    async def alerts(self, limit: int) -> list[dict[str, Any]]:
        return await self._run(self.store.alerts, limit)

    def hosts(self) -> list[dict[str, Any]]:
        return self._hosts

    async def clear(self) -> dict[str, int]:
        packets, alerts = await self._run(self.store.clear)
        await self._audit("net.data_clear", DB_FILE, packets=packets, alerts=alerts)
        return {"packets": packets, "alerts": alerts}


def _is_scalar(value: object) -> bool:
    return isinstance(value, str | int | float | bool)


def _dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = cast(list[object], value)
    return [cast(dict[str, Any], item) for item in items if isinstance(item, dict)]
