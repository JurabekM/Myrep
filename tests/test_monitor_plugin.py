"""`monitor` plagini: qoidalar mantiqi, tarix ombori, o'lchov va saqlash muddati.

To'liq hayot sikli (ikkala rejimda) — `test_plugins.py::test_monitor_full_cycle`,
panel — `test_shell_gui.py`.
"""

import asyncio
import importlib
import os
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pydantic import ValidationError

from conftest import serve_app
from monitor_helpers import install_monitor
from srv1_core.paths import DataPaths
from srv1_core.plugins.registry import BUILTIN_DIR
from srv1_sdk.panel import ChartWidget

API = "/api/v1/plugins/monitor/api"
GB = 1024**3


def _module(name: str) -> ModuleType:
    sys.path.insert(0, str(BUILTIN_DIR.parent))
    try:
        return importlib.import_module(f"plugins.monitor.{name}")
    finally:
        sys.path.pop(0)


models = _module("models")
alerts = _module("alerts")
store = _module("store")
probe = _module("probe")


def _sample(
    ts: float, cpu: float = 10, memory: float = 50, disks: dict[str, float] | None = None
) -> Any:  # noqa: ANN401 — plagin moduli dinamik yuklanadi
    """`disks` — `{nom: bo'sh joy GB}`; standart: bitta 100 GB bo'sh disk."""
    free = {"C:\\": 100.0} if disks is None else disks
    listed = tuple(models.Disk(mount, int(gb * GB), 500 * GB) for mount, gb in free.items())
    return models.Sample(ts, cpu, memory, 2 * GB, 4 * GB, 100 * 1024**2, listed)


def _limits(**changes: float) -> Any:  # noqa: ANN401
    base = {"memory_percent": 0, "cpu_percent": 0, "cpu_minutes": 0, "disk_free_gb": 0}
    return models.Thresholds(**(base | changes))


def _moves(found: list[Any]) -> list[tuple[str, str]]:
    return [(alert.key, alert.state) for alert in found]


# --- qoidalar ---------------------------------------------------------------------------
def test_memory_rule_raises_once_and_clears_with_hysteresis() -> None:
    evaluator = alerts.Evaluator()
    limits = _limits(memory_percent=90)
    assert evaluator.check(_sample(0, memory=89.9), limits) == []
    raised = evaluator.check(_sample(1, memory=90.0), limits)
    assert _moves(raised) == [("memory", "raised")]
    assert (raised[0].value, raised[0].limit) == (90.0, 90)
    # faol turganda takror yozuv yo'q; chegara ostiga sal tushish ham yetarli emas
    assert evaluator.check(_sample(2, memory=97), limits) == []
    assert evaluator.check(_sample(3, memory=85.1), limits) == []
    assert _moves(evaluator.check(_sample(4, memory=84.9), limits)) == [("memory", "cleared")]
    assert evaluator.active == set()
    # tebranish: 86–90 oralig'ida yurish yozuvlarni ko'paytirmaydi
    found = [evaluator.check(_sample(5 + i, memory=m), limits) for i, m in enumerate([91, 88, 92])]
    assert [_moves(step) for step in found] == [[("memory", "raised")], [], []]


def test_cpu_rule_needs_sustained_load() -> None:
    evaluator = alerts.Evaluator()
    limits = _limits(cpu_percent=80, cpu_minutes=5)
    for ts in (0, 100, 200, 299):
        assert evaluator.check(_sample(ts, cpu=95), limits) == []
    assert _moves(evaluator.check(_sample(300, cpu=95), limits)) == [("cpu", "raised")]
    assert _moves(evaluator.check(_sample(310, cpu=10), limits)) == [("cpu", "cleared")]

    # orada bir marta pasaysa, hisob boshidan boshlanadi
    for ts, cpu in ((400, 95), (600, 50), (650, 95), (900, 95)):
        assert evaluator.check(_sample(ts, cpu=cpu), limits) == [], ts
    assert _moves(evaluator.check(_sample(950, cpu=95), limits)) == [("cpu", "raised")]

    # cpu_minutes = 0: birinchi o'lchovdayoq
    instant = alerts.Evaluator()
    now = _limits(cpu_percent=80)
    assert _moves(instant.check(_sample(0, cpu=80), now)) == [("cpu", "raised")]


def test_disk_rule_is_per_disk_and_handles_missing_disk() -> None:
    evaluator = alerts.Evaluator()
    limits = _limits(disk_free_gb=10)
    found = evaluator.check(_sample(0, disks={"C:\\": 9.5, "D:\\": 200}), limits)
    assert _moves(found) == [("disk:C:\\", "raised")]
    assert found[0].value == 9.5
    # 10 GB dan oshdi, lekin 11 GB (chegara x 1,1) ga yetmadi: hali faol
    assert evaluator.check(_sample(1, disks={"C:\\": 10.5, "D:\\": 200}), limits) == []
    cleared = evaluator.check(_sample(2, disks={"C:\\": 11, "D:\\": 5}), limits)
    assert _moves(cleared) == [("disk:C:\\", "cleared"), ("disk:D:\\", "raised")]
    # D: uzilgan: ogohlantirishi abadiy faol qolmaydi
    gone = evaluator.check(_sample(3, disks={"C:\\": 50}), limits)
    assert _moves(gone) == [("disk:D:\\", "cleared")]
    assert (gone[0].value, gone[0].note) == (None, "disk topilmadi")


def test_disabled_rule_closes_its_alert_and_zero_means_off() -> None:
    evaluator = alerts.Evaluator()
    on = _limits(memory_percent=50, cpu_percent=50, disk_free_gb=500)
    raised = evaluator.check(_sample(0, cpu=99, memory=99), on)
    assert _moves(raised) == [("memory", "raised"), ("cpu", "raised"), ("disk:C:\\", "raised")]
    closed = evaluator.check(_sample(1, cpu=99, memory=99), _limits())
    assert _moves(closed) == [("memory", "cleared"), ("cpu", "cleared"), ("disk:C:\\", "cleared")]
    assert evaluator.check(_sample(2, cpu=100, memory=100, disks={"C:\\": 0}), _limits()) == []


def test_plugin_state_alerts() -> None:
    evaluator = alerts.Evaluator()
    assert evaluator.plugin_state(0, "iot", "running", "") is None
    crashed = evaluator.plugin_state(1, "iot", "crashed", "xotira limiti oshdi")
    assert (crashed.key, crashed.state, crashed.note) == ("plugin:iot", "raised", crashed.note)
    assert crashed.note == "xotira limiti oshdi"
    assert evaluator.plugin_state(2, "iot", "crashed", "yana") is None
    assert evaluator.plugin_state(3, "iot", "starting", "") is None
    assert evaluator.plugin_state(4, "iot", "running", "").state == "cleared"
    long_error = evaluator.plugin_state(5, "data", "error", "x" * 5000)
    assert len(long_error.note) == 200


def test_restored_active_state_does_not_repeat() -> None:
    evaluator = alerts.Evaluator(["memory", "plugin:iot"])
    limits = _limits(memory_percent=90)
    assert evaluator.check(_sample(0, memory=95), limits) == []
    assert evaluator.plugin_state(1, "iot", "crashed", "") is None
    assert _moves(evaluator.check(_sample(2, memory=10), limits)) == [("memory", "cleared")]


def test_threshold_validation() -> None:
    for bad in ({"memory_percent": 101}, {"cpu_percent": -1}, {"cpu_minutes": 121}, {"yoq": 1}):
        with pytest.raises(ValidationError):
            models.Thresholds(**bad)
    with pytest.raises(ValidationError):
        models.Config(interval_s=0)
    defaults = models.Thresholds()
    assert (defaults.memory_percent, defaults.cpu_percent, defaults.cpu_minutes) == (90, 90, 5)
    assert defaults.disk_free_gb == 10


# --- ombor ------------------------------------------------------------------------------
def test_history_store_series_alerts_purge_and_clear(tmp_path: Path) -> None:
    history = store.History(tmp_path / "monitor.db")
    try:
        raised = alerts.Alert(2.0, "disk:C:\\", "raised", 9.5, 10)
        for ts in (1.0, 2.0, 3.0, 4.0):
            history.add(_sample(ts, cpu=ts, memory=ts * 10), [raised] if ts == 2.0 else [])
        history.add_alert(alerts.Alert(5.0, "plugin:iot", "raised", note="yiqildi"))
        history.add_alert(alerts.Alert(6.0, "disk:C:\\", "cleared", 12.0, 10))
        assert history.count() == 4 and history.size() > 0

        # oxirgi N ta, lekin vaqt bo'yicha o'sish tartibida
        assert [row["ts"] for row in history.series(0, 3)] == [2.0, 3.0, 4.0]
        assert [row["ts"] for row in history.series(3.0, 100)] == [3.0, 4.0]
        assert history.series(0, 1)[0] == {"ts": 4.0, "cpu": 4.0, "memory": 40.0, "srv1_mb": 100.0}

        rows = history.alerts(10)
        assert [(r["key"], r["state"]) for r in rows] == [
            ("disk:C:\\", "cleared"),
            ("plugin:iot", "raised"),
            ("disk:C:\\", "raised"),
        ]
        assert (rows[2]["value"], rows[2]["limit"]) == ("9.5 GB", "10.0 GB")
        assert (rows[1]["value"], rows[1]["note"]) == ("", "yiqildi")
        # faol: oxirgi yozuvi `raised` bo'lganlar
        assert history.active_keys() == ["plugin:iot"]

        assert history.purge(older_than=3.0, alerts_kept=2) == 2
        assert [row["ts"] for row in history.series(0, 100)] == [3.0, 4.0]
        assert len(history.alerts(10)) == 2
        assert history.clear() == (2, 2)
        assert history.count() == 0 and history.alerts(10) == []
    finally:
        history.close()


def test_same_timestamp_does_not_fail(tmp_path: Path) -> None:
    history = store.History(tmp_path / "monitor.db")
    try:
        history.add(_sample(1.0, cpu=1), [])
        history.add(_sample(1.0, cpu=2), [])
        assert history.series(0, 10) == [{"ts": 1.0, "cpu": 2, "memory": 50, "srv1_mb": 100.0}]
    finally:
        history.close()


# --- haqiqiy o'lchov ----------------------------------------------------------------------
def test_probe_measures_this_machine() -> None:
    sample = probe.measure(os.getpid(), 0.05)
    assert abs(sample.ts - time.time()) < 5
    assert 0 <= sample.cpu <= 100 and 0 < sample.memory <= 100
    assert 0 < sample.memory_used < sample.memory_total
    assert sample.srv1_rss > 10 * 1024**2
    assert sample.disks, "kamida bitta qattiq disk bo'lishi kerak"
    assert all(0 <= disk.free <= disk.total for disk in sample.disks)
    assert probe.tree_rss(2**31 - 2) == 0  # mavjud bo'lmagan jarayon xato bermaydi


# --- jadval bo'yicha o'lchov va saqlash muddati -------------------------------------------
async def test_scheduled_sampling_and_retention(paths: DataPaths, plugin_root: Path) -> None:
    data = paths.plugin_data_dir("monitor")
    install_monitor(plugin_root, data, interval_s=0.2)
    # Muddati o'tgan eski yozuv: ishga tushishda o'chirilishi kerak (standart 7 kun).
    old = store.History(data / "monitor.db")
    old.add(_sample(time.time() - 8 * 86400), [])
    old.add(_sample(time.time() - 6 * 86400), [])
    old.close()

    async with serve_app(paths) as served, served.client() as client:
        status = first = (await client.get(f"{API}/status")).json()
        assert first["samples"] == 2  # 6 kunlik yozuv + ishga tushishdagi o'lchov
        assert (first["interval_s"], first["retention_days"]) == (0.2, 7.0)
        for _ in range(100):
            status = (await client.get(f"{API}/status")).json()
            if status["samples"] >= 5:
                break
            await asyncio.sleep(0.05)
        else:
            pytest.fail(f"jadval bo'yicha o'lchov ishlamadi: {status}")
        assert status["history_bytes"] > 0 and status["measured"] > first["measured"]
        recent = (await client.get(f"{API}/history", params={"minutes": 1})).json()
        assert len(recent) == status["samples"] - 1  # 6 kunlik yozuv bir daqiqaga kirmaydi
        for bad in ({"minutes": 0}, {"limit": 0}, {"limit": 5001}):
            assert (await client.get(f"{API}/history", params=bad)).status_code == 422


# --- SDK: grafik vidjeti ------------------------------------------------------------------
def test_chart_widget_history_and_range_validation() -> None:
    plain = ChartWidget(label="x", topic="sample", field="cpu")
    assert (plain.history, plain.y_min, plain.y_max) == (None, None, None)
    full = ChartWidget(
        label="x", topic="sample", field="cpu", history="/history", y_min=0, y_max=100
    )
    assert full.history == "/history"
    for bad in (
        {"y_min": 0},
        {"y_max": 100},
        {"y_min": 5, "y_max": 5},
        {"history": "history"},
        {"history": "/a b"},
    ):
        with pytest.raises(ValidationError):
            ChartWidget(label="x", topic="sample", field="cpu", **bad)  # pyright: ignore[reportArgumentType]
