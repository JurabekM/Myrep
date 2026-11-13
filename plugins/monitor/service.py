"""`MonitorService`: o'lchash, saqlash, qoidalarni tekshirish va ogohlantirish nashri."""

import asyncio
import os
import time
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

from srv1_sdk.context import PluginContext

from .alerts import Alert, Evaluator, disk_key
from .models import (
    GB,
    MB,
    STORE_FILE,
    MonitorError,
    Sample,
    Store,
    Thresholds,
    load_store,
    save_store,
)
from .notices import notice
from .probe import measure
from .store import History

HISTORY_FILE = "monitor.db"
ALERTS_KEPT = 1000
DAY_S = 86400.0
FIRST_CPU_INTERVAL_S = 0.2


def _gb(size: int) -> float:
    return round(size / GB, 1)


class MonitorService:
    def __init__(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self._store_file = ctx.data_path(STORE_FILE)
        self.store: Store = load_store(self._store_file)
        self._thread = ThreadPoolExecutor(max_workers=1, thread_name_prefix="monitor")
        self._history: History | None = None
        self._evaluator = Evaluator()
        self._lock = asyncio.Lock()
        self._last: Sample | None = None
        # SRV_1 jarayonlar daraxtining ildizi: alohida jarayonda plaginning otasi — yadro.
        subprocess_mode = ctx.manifest.mode == "subprocess"
        self._root_pid = os.getppid() if subprocess_mode else os.getpid()

    # --- hayot sikli ------------------------------------------------------
    async def _run[T](self, func: Callable[..., T], *args: Any) -> T:  # noqa: ANN401
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._thread, partial(func, *args))

    @property
    def history(self) -> History:
        if self._history is None:
            raise MonitorError(503, "tarix ombori hali tayyor emas")
        return self._history

    async def start(self) -> None:
        self._history = await self._run(History, self.ctx.data_path(HISTORY_FILE))
        self._evaluator = Evaluator(await self._run(self.history.active_keys))
        await self.purge()
        # Birinchi o'lchov darhol: panel bo'sh turmasin. CPU qisqa oraliqda o'lchanadi.
        await self.sample(cpu_interval_s=FIRST_CPU_INTERVAL_S)

    async def stop(self) -> None:
        if self._history is not None:
            await self._run(self._history.close)
            self._history = None
        self._thread.shutdown(wait=False)

    # --- o'lchash -----------------------------------------------------------
    async def sample(self, cpu_interval_s: float | None = None) -> Sample:
        """Bitta o'lchov: saqlaydi, qoidalarni tekshiradi, hodisalarni nashr qiladi."""
        async with self._lock:
            sample = await self._run(measure, self._root_pid, cpu_interval_s)
            alerts = self._evaluator.check(sample, self.store.config.thresholds)
            await self._run(self.history.add, sample, alerts)
            self._last = sample
        self.ctx.publish(
            "sample",
            {
                "ts": sample.ts,
                "cpu": sample.cpu,
                "memory": sample.memory,
                "srv1_mb": round(sample.srv1_rss / MB, 1),
            },
        )
        for alert in alerts:
            self._announce(alert)
        return sample

    def _announce(self, alert: Alert) -> None:
        level = "warning" if alert.state == "raised" else "info"
        self.ctx.log(level, "monitor_alert", key=alert.key, state=alert.state, value=alert.value)
        self.ctx.publish(
            "alert",
            {
                "ts": alert.ts,
                "key": alert.key,
                "state": alert.state,
                "value": alert.value,
                "limit": alert.limit,
                "note": alert.note,
            },
        )
        title, message = notice(alert)
        self.ctx.notify(title, message, level=level)

    async def on_plugin_state(self, data: Mapping[str, Any]) -> None:
        """Yadroning `plugins.state` hodisasi: boshqa plagin yiqilsa ogohlantirish yoziladi."""
        name, status = str(data.get("name", "")), str(data.get("status", ""))
        if not name or name == self.ctx.name or self._history is None:
            return
        async with self._lock:
            error = str(data.get("error") or "")
            alert = self._evaluator.plugin_state(time.time(), name, status, error)
            if alert is not None:
                await self._run(self.history.add_alert, alert)
        if alert is not None:
            self._announce(alert)

    async def purge(self) -> None:
        cutoff = time.time() - self.store.config.retention_days * DAY_S
        removed = await self._run(self.history.purge, cutoff, ALERTS_KEPT)
        if removed:
            self.ctx.log("info", "monitor_purged", samples=removed)

    # --- o'qish ---------------------------------------------------------------
    async def status(self) -> dict[str, Any]:
        last = self._last
        config = self.store.config
        result: dict[str, Any] = {
            "cpu_percent": None,
            "memory_percent": None,
            "memory_used_gb": None,
            "disk_free_gb": None,
            "srv1_mb": None,
            "measured": None,
            "active_alerts": len(self._evaluator.active),
            "samples": await self._run(self.history.count),
            "history_bytes": await self._run(self.history.size),
            "interval_s": config.interval_s,
            "retention_days": config.retention_days,
        }
        if last is not None:
            result |= {
                "cpu_percent": round(last.cpu, 1),
                "memory_percent": round(last.memory, 1),
                "memory_used_gb": _gb(last.memory_used),
                "disk_free_gb": min((_gb(d.free) for d in last.disks), default=None),
                "srv1_mb": round(last.srv1_rss / MB, 1),
                "measured": last.ts,
            }
        return result

    async def series(self, minutes: float, limit: int) -> list[dict[str, Any]]:
        return await self._run(self.history.series, time.time() - minutes * 60, limit)

    async def alerts(self, limit: int) -> list[dict[str, Any]]:
        return await self._run(self.history.alerts, limit)

    def disks(self) -> list[dict[str, Any]]:
        last = self._last
        if last is None:
            return []
        return [
            {
                "mount": disk.mount,
                "free": disk.free,
                "total": disk.total,
                "used_percent": round(100 * (1 - disk.free / disk.total), 1) if disk.total else 0,
            }
            for disk in last.disks
        ]

    def rules(self) -> list[dict[str, Any]]:
        """Har qoida: hozirgi qiymat, chegara va holat (`ok` | `alert` | `off`)."""
        limits = self.store.config.thresholds
        last = self._last
        active = self._evaluator.active

        def row(key: str, now: float | None, limit: float, unit: str, sign: str) -> dict[str, Any]:
            state = "off" if limit <= 0 else ("alert" if key in active else "ok")
            return {
                "key": key,
                "now": "" if now is None else f"{now:.1f} {unit}",
                "limit": "" if limit <= 0 else f"{sign} {limit:g} {unit}",
                "state": state,
            }

        rows = [row("memory", last and last.memory, limits.memory_percent, "%", "≥")]
        rows.append(row("cpu", last and last.cpu, limits.cpu_percent, "%", "≥"))
        if limits.cpu_percent > 0:
            rows[-1]["limit"] += f", {limits.cpu_minutes:g} min"
        for disk in last.disks if last is not None else ():
            rows.append(row(disk_key(disk.mount), disk.free / GB, limits.disk_free_gb, "GB", "<"))
        for key in sorted(k for k in active if k.startswith("plugin:")):
            rows.append({"key": key, "now": "", "limit": "", "state": "alert"})
        return rows

    # --- o'zgartirish -----------------------------------------------------------
    async def set_thresholds(self, changes: Mapping[str, float]) -> Thresholds:
        """Berilgan maydonlarni almashtiradi; qolganlari o'zgarmaydi."""
        merged = self.store.config.thresholds.model_dump() | dict(changes)
        thresholds = Thresholds.model_validate(merged)
        config = self.store.config.model_copy(update={"thresholds": thresholds})
        self.store = Store(config=config)
        await asyncio.to_thread(save_store, self._store_file, self.store)
        self.ctx.log("info", "monitor_thresholds", **thresholds.model_dump())
        return thresholds

    async def clear_history(self) -> dict[str, int]:
        async with self._lock:
            samples, alerts = await self._run(self.history.clear)
            # Faol holatlar ham unutiladi: hali buzilgan qoida keyingi o'lchovda qayta yoziladi.
            self._evaluator = Evaluator()
        await self.ctx.audit(
            "monitor.history_clear",
            str(self.ctx.data_path(HISTORY_FILE)),
            detail={"samples": samples, "alerts": alerts},
        )
        return {"samples": samples, "alerts": alerts}
