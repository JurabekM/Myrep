"""Plagin yuklovchi integratsiya testlari: haqiqiy yadro, haqiqiy bola jarayonlar."""

import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path
from typing import Any

import httpx
import psutil
import pytest
from websockets.asyncio.client import connect

from conftest import Served, free_port, serve_app, until, write_plugin
from monitor_helpers import install_monitor
from srv1_core.paths import DataPaths

MODES = ["inprocess", "subprocess"]
API = "/api/v1/plugins"


def _audit_rows(paths: DataPaths) -> list[tuple[str, str, int]]:
    with closing(sqlite3.connect(paths.db_file)) as conn:
        return conn.execute("SELECT actor, action, ok FROM audit_log ORDER BY id").fetchall()


async def _info(client: httpx.AsyncClient, name: str) -> dict[str, Any]:
    response = await client.get(f"{API}/{name}")
    assert response.status_code == 200, response.text
    return response.json()


async def _status_is(client: httpx.AsyncClient, name: str, status: str) -> dict[str, Any]:
    info: dict[str, Any] = {}

    for _ in range(500):
        info = await _info(client, name)
        if info["status"] == status:
            return info
        await asyncio.sleep(0.01)
    pytest.fail(f"{name}: {status!r} kutildi, hozir {info['status']!r} ({info['error']})")


# --- haqiqiy plagin (`monitor`), ikkala rejimda bir xil kod ---------------------------
DIE_PLUGIN = """
    import os
    from fastapi import APIRouter
    from srv1_sdk.hookspec import hookimpl

    @hookimpl
    def srv1_router(ctx):
        router = APIRouter()

        @router.post("/die")
        async def die():
            os._exit(3)

        return router
"""


async def _alerts(client: httpx.AsyncClient, count: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _ in range(500):
        rows = (await client.get(f"{API}/monitor/api/alerts")).json()
        if len(rows) >= count:
            return rows
        await asyncio.sleep(0.01)
    pytest.fail(f"{count} ta ogohlantirish kutildi, bor: {rows}")


@pytest.mark.parametrize("mode", MODES)
async def test_monitor_full_cycle(paths: DataPaths, plugin_root: Path, mode: str) -> None:
    install_monitor(plugin_root, paths.plugin_data_dir("monitor"), mode)
    write_plugin(plugin_root, "victim", DIE_PLUGIN, 'mode = "subprocess"')
    base = f"{API}/monitor/api"
    async with serve_app(paths) as served, served.client() as client:
        info = await _info(client, "monitor")
        assert (info["status"], info["enabled"], info["mode"]) == ("running", True, mode)
        assert info["jobs"] == ["monitor:sample", "monitor:purge"]
        assert info["subscriptions"] == ["plugins.state"]
        assert info["has_panel"] is True
        if mode == "subprocess":
            assert info["pid"] != os.getpid()
            assert psutil.pid_exists(info["pid"])
        else:
            assert info["pid"] is None

        # ishga tushishda bitta o'lchov bor; qiymatlar haqiqiy
        status = (await client.get(f"{base}/status")).json()
        assert (status["samples"], status["active_alerts"]) == (1, 0)
        assert 0 <= status["cpu_percent"] <= 100 and 0 < status["memory_percent"] <= 100
        # SRV_1 daraxti: kamida shu test jarayoni (yadro shu yerda ishlaydi)
        assert status["srv1_mb"] > 20
        assert status["disk_free_gb"] > 0
        disks = (await client.get(f"{base}/disks")).json()
        assert disks and all(0 < d["free"] <= d["total"] for d in disks)

        # API: JSON tana, validatsiya xatosi, noma'lum yo'l; sozlama faylga yoziladi
        too_big = await client.post(f"{base}/thresholds", json={"memory_percent": 250})
        assert too_big.status_code == 422
        assert (await client.post(f"{base}/thresholds", json={"yoq": 1})).status_code == 422
        changed = await client.post(f"{base}/thresholds", json={"memory_percent": 1})
        assert changed.json() == {
            "memory_percent": 1.0,
            "cpu_percent": 0.0,
            "cpu_minutes": 0.0,
            "disk_free_gb": 0.0,
        }
        assert (await client.get(f"{base}/yoq")).status_code == 404
        store_file = paths.plugin_data_dir("monitor") / "monitor.json"
        saved = json.loads(store_file.read_text(encoding="utf-8"))
        assert saved["config"]["thresholds"]["memory_percent"] == 1.0

        # hodisa: o'lchov va ogohlantirish WebSocket klientga yetadi
        url = served.ws_url("?topics=plugin.monitor.*")
        async with connect(url, additional_headers=served.headers) as ws:
            await until(lambda: served.core.bus.has_subscribers("plugin.monitor.x"))
            assert (await client.post(f"{base}/sample")).json()["samples"] == 2
            first, second = json.loads(await ws.recv()), json.loads(await ws.recv())
            third = json.loads(await ws.recv())
        # bildirishnoma (shell uni Windows bildirishnomasi qilib ko'rsatadi)
        assert third["topic"] == "plugin.monitor.notify"
        assert third["data"]["level"] == "warning"
        assert third["data"]["title"]["uz"] == "Xotira chegaradan oshdi"
        assert set(third["data"]["title"]) == set(third["data"]["message"]) == {"uz", "ru", "en"}
        assert third["data"]["message"]["en"].endswith("limit 1 %")
        assert first["topic"] == "plugin.monitor.sample"
        assert set(first["data"]) == {"ts", "cpu", "memory", "srv1_mb"}
        assert second["topic"] == "plugin.monitor.alert"
        assert (second["data"]["key"], second["data"]["state"]) == ("memory", "raised")
        assert second["data"]["limit"] == 1.0

        # takror yozuv yo'q: qoida faol turganda keyingi o'lchov jim
        assert (await client.post(f"{base}/sample")).json()["active_alerts"] == 1
        assert [(a["key"], a["state"]) for a in await _alerts(client, 1)] == [("memory", "raised")]
        rules = {rule["key"]: rule for rule in (await client.get(f"{base}/rules")).json()}
        assert (rules["memory"]["state"], rules["memory"]["limit"]) == ("alert", "≥ 1 %")
        assert rules["cpu"]["state"] == "off"
        history = (await client.get(f"{base}/history", params={"limit": 2})).json()
        assert len(history) == 2 and history[0]["ts"] < history[1]["ts"]

        # obuna: boshqa plagin yiqilsa (yadro hodisasi), ogohlantirish yoziladi
        assert (await client.post(f"{API}/victim/api/die")).status_code == 502
        newest = (await _alerts(client, 2))[0]
        assert (newest["key"], newest["state"]) == ("plugin:victim", "raised")
        assert "kod 3" in newest["note"]
        assert (await client.get(f"{base}/status")).json()["active_alerts"] == 2
        await client.post(f"{API}/victim/disable")
        assert (await _alerts(client, 3))[0]["state"] == "cleared"

        # qoida o'chirilsa, ogohlantirish yopiladi
        await client.post(f"{base}/thresholds", json={"memory_percent": 0})
        assert (await client.post(f"{base}/sample")).json()["active_alerts"] == 0
        latest = (await _alerts(client, 4))[0]
        assert (latest["key"], latest["state"]) == ("memory", "cleared")

        # panel va audit
        panel = (await client.get(f"{API}/monitor/panel")).json()
        assert panel["title"] == {"uz": "Kuzatuv", "ru": "Наблюдение", "en": "Monitoring"}
        kinds = {widget["type"] for widget in panel["widgets"]}
        assert kinds == {"label", "value", "chart", "button", "table", "form"}
        assert (await client.delete(f"{base}/history")).json() == {"samples": 4, "alerts": 4}
        assert (await client.get(f"{base}/status")).json()["samples"] == 0
        assert (await client.get(f"{base}/alerts")).json() == []
        await client.post(f"{base}/thresholds", json={"memory_percent": 2})

        # o'chirish: API 409, jarayon yo'qoladi
        pid = info["pid"]
        disabled = (await client.post(f"{API}/monitor/disable")).json()
        assert (disabled["status"], disabled["enabled"], disabled["pid"]) == (
            "stopped",
            False,
            None,
        )
        assert disabled["jobs"] == []
        assert (await client.get(f"{base}/status")).status_code == 409
        assert (await client.get(f"{API}/monitor/panel")).status_code == 409
        if pid is not None:
            assert not psutil.pid_exists(pid)
        assert not served.core.bus.has_subscribers("plugins.state")

    # holat va sozlama qayta ishga tushgandan keyin saqlanadi
    async with serve_app(paths) as served, served.client() as client:
        assert (await _info(client, "monitor"))["status"] == "stopped"
        enabled = (await client.post(f"{API}/monitor/enable")).json()
        assert (enabled["status"], enabled["enabled"]) == ("running", True)
        assert (await client.get(f"{base}/thresholds")).json()["memory_percent"] == 2.0
        # tozalangan tarixdan keyin: faqat shu ishga tushishdagi o'lchov va uning ogohlantirishi
        status = (await client.get(f"{base}/status")).json()
        assert (status["samples"], status["active_alerts"]) == (1, 1)

    # yana bir qayta ishga tushish: faol holat bazadan tiklanadi, takror yozuv chiqmaydi
    async with serve_app(paths) as served, served.client() as client:
        status = (await client.get(f"{base}/status")).json()
        assert (status["samples"], status["active_alerts"]) == (2, 1)
        assert len((await client.get(f"{base}/alerts")).json()) == 1

    rows = _audit_rows(paths)
    assert ("plugin:monitor", "monitor.history_clear", 1) in rows
    assert ("core", "plugin.disable", 1) in rows
    assert ("core", "plugin.enable", 1) in rows
    assert ("core", "process.spawn", 1) in rows


async def test_builtin_plugins_are_discovered(
    paths: DataPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SRV1_PLUGINS__LOAD_BUILTIN", "true")
    async with serve_app(paths) as served, served.client() as client:
        plugins = (await client.get(API)).json()
    assert [(p["name"], p["source"]) for p in plugins] == [
        ("data", "builtin"),
        ("electronics", "builtin"),
        ("files", "builtin"),
        ("hosting", "builtin"),
        ("iot", "builtin"),
        ("itops", "builtin"),
        ("monitor", "builtin"),
    ]
    # hosting standart portlarga (8080, 2019, 9099) bog'lanadi; ular band bo'lsa bu yerda
    # tekshirilmaydi — plaginning o'z testlari bo'sh portlar bilan ishlaydi.
    # data — og'ir plagin: standart holatda o'chiq.
    assert [p["status"] for p in plugins[:3]] == ["stopped", "running", "running"]


# --- API chegaralari ----------------------------------------------------------------
ECHO_PLUGIN = """
    from fastapi import APIRouter, Request
    from srv1_sdk.hookspec import hookimpl

    @hookimpl
    def srv1_router(ctx):
        router = APIRouter()

        @router.api_route("/echo", methods=["GET", "POST"])
        async def echo(request: Request):
            body = await request.body()
            return {"headers": dict(request.headers), "size": len(body), "query": request.url.query}

        return router
"""


@pytest.mark.parametrize("mode", MODES)
async def test_token_not_forwarded_and_body_limit(
    paths: DataPaths, plugin_root: Path, mode: str
) -> None:
    write_plugin(plugin_root, "echo", ECHO_PLUGIN, f'mode = "{mode}"')
    async with serve_app(paths) as served, served.client() as client:
        reply = await client.post(
            f"{API}/echo/api/echo?a=1&b=ikki", content=b"x" * 1000, headers={"X-Custom": "1"}
        )
        body = reply.json()
        assert body["size"] == 1000
        assert body["query"] == "a=1&b=ikki"
        assert "authorization" not in body["headers"]
        assert "x-custom" not in body["headers"]
        assert served.token not in reply.text

        too_big = await client.post(f"{API}/echo/api/echo", content=b"x" * (1024 * 1024 + 1))
        assert too_big.status_code == 413


async def test_plugin_api_requires_token_and_valid_name(served: Served) -> None:
    async with served.client(authorized=False) as anonymous:
        assert (await anonymous.get(API)).status_code == 401
        assert (await anonymous.get(f"{API}/monitor/api/status")).status_code == 401
        assert (await anonymous.post(f"{API}/monitor/enable")).status_code == 401
    async with served.client() as client:
        assert (await client.get(API)).json() == []
        assert (await client.get(f"{API}/yoq_plagin")).status_code == 404
        assert (await client.post(f"{API}/yoq_plagin/enable")).status_code == 404
        assert (await client.get(f"{API}/yoq_plagin/api/x")).status_code == 404
        assert (await client.get(f"{API}/Bad-Name")).status_code == 422


# --- yaroqsiz va buzuq plaginlar yadroni to'xtatmaydi ------------------------------------
async def test_broken_plugins_do_not_stop_core(paths: DataPaths, plugin_root: Path) -> None:
    write_plugin(plugin_root, "good", "")
    write_plugin(plugin_root, "import_fails", "raise RuntimeError('import paytida xato')")
    write_plugin(plugin_root, "bad_cron", BAD_CRON_PLUGIN)
    write_plugin(plugin_root, "bad_manifest", "", 'mode = "kvant"')
    write_plugin(plugin_root, "sub_fails", "import yoq_modul", 'mode = "subprocess"')
    (plugin_root / "not_a_plugin").mkdir()

    async with serve_app(paths) as served, served.client() as client:
        assert (await client.get("/api/v1/health")).status_code == 200
        plugins = {p["name"]: p for p in (await client.get(API)).json()}
        assert set(plugins) == {"good", "import_fails", "bad_cron", "bad_manifest", "sub_fails"}
        assert plugins["good"]["status"] == "running"
        assert plugins["import_fails"]["status"] == "error"
        assert "import paytida xato" in plugins["import_fails"]["error"]
        assert plugins["bad_cron"]["status"] == "error"
        assert plugins["bad_cron"]["jobs"] == []
        assert plugins["sub_fails"]["status"] == "error"
        assert "yoq_modul" in plugins["sub_fails"]["error"]
        assert plugins["sub_fails"]["pid"] is None
        assert plugins["bad_manifest"]["status"] == "invalid"
        assert plugins["bad_manifest"]["version"] is None

        assert (await client.post(f"{API}/bad_manifest/enable")).status_code == 409
        assert (await client.get(f"{API}/import_fails/api/x")).status_code == 409
        retry = (await client.post(f"{API}/import_fails/enable")).json()
        assert retry["status"] == "error"
    assert ("core", "plugin.enable", 0) in _audit_rows(paths)


BAD_CRON_PLUGIN = """
    from srv1_sdk.hookspec import hookimpl
    from srv1_sdk.types import Job

    async def nothing():
        pass

    @hookimpl
    def srv1_jobs(ctx):
        return [Job(id="x", func=nothing, cron="bu cron emas")]
"""


async def test_heavy_plugin_is_off_until_enabled(paths: DataPaths, plugin_root: Path) -> None:
    write_plugin(plugin_root, "big", "", 'mode = "subprocess"\nheavy = true\nmemory_limit_mb = 128')
    async with serve_app(paths) as served, served.client() as client:
        info = await _info(client, "big")
        assert (info["status"], info["enabled"], info["heavy"], info["pid"]) == (
            "stopped",
            False,
            True,
            None,
        )
        assert info["memory_limit_mb"] == 128
        enabled = (await client.post(f"{API}/big/enable")).json()
        assert enabled["status"] == "running"
        assert psutil.pid_exists(enabled["pid"])
        pid = enabled["pid"]
    assert not psutil.pid_exists(pid)  # yadro to'xtaganda bola ham to'xtaydi


# --- ruxsatlar -------------------------------------------------------------------------
PERMISSION_PLUGIN = """
    from fastapi import APIRouter
    from srv1_sdk.hookspec import hookimpl

    @hookimpl
    def srv1_router(ctx):
        router = APIRouter()

        @router.get("/read")
        async def read(path: str):
            return {"text": ctx.resolve_path(path).read_text(encoding="utf-8")}

        @router.get("/port")
        async def port(n: int):
            return {"port": ctx.check_port(n)}

        @router.get("/serial")
        async def serial(device: str):
            return {"device": ctx.check_serial(device)}

        return router
"""


@pytest.mark.parametrize("mode", MODES)
async def test_permissions_enforced_through_context(
    paths: DataPaths, plugin_root: Path, tmp_path: Path, mode: str
) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (allowed / "ok.txt").write_text("ruxsat bor", encoding="utf-8")
    secret = tmp_path / "secret.txt"
    secret.write_text("sir", encoding="utf-8")
    manifest = f"""
        mode = "{mode}"
        [permissions]
        paths = ['{allowed}']
        ports = ["9000-9099"]
        serial = ["COM7"]
    """
    write_plugin(plugin_root, "perm", PERMISSION_PLUGIN, manifest)

    async with serve_app(paths) as served, served.client() as client:
        base = f"{API}/perm/api"
        ok = await client.get(f"{base}/read", params={"path": str(allowed / "ok.txt")})
        assert ok.json() == {"text": "ruxsat bor"}
        for forbidden in (str(secret), str(allowed / ".." / "secret.txt"), str(paths.token_file)):
            denied = await client.get(f"{base}/read", params={"path": forbidden})
            assert denied.status_code == 403, forbidden
            assert "sir" not in denied.text
        assert (await client.get(f"{base}/port", params={"n": 9050})).status_code == 200
        assert (await client.get(f"{base}/port", params={"n": 8710})).status_code == 403
        assert (await client.get(f"{base}/serial", params={"device": "com7"})).status_code == 200
        assert (await client.get(f"{base}/serial", params={"device": "COM1"})).status_code == 403
        info = await _info(client, "perm")
        assert info["permissions"]["serial"] == ["COM7"]
    log_text = (paths.logs_dir / "srv1.log").read_text(encoding="utf-8")
    assert log_text.count("permission_denied") == 5


# --- rejalashtirilgan vazifalar va hodisa ishlovchilari ------------------------------------
JOB_PLUGIN = """
    from fastapi import APIRouter
    from srv1_sdk.hookspec import hookimpl
    from srv1_sdk.types import EventHandler, Job

    counts = {"job": 0, "seen": 0}

    @hookimpl
    def srv1_jobs(ctx):
        async def work():
            counts["job"] += 1
            ctx.publish("done", {"n": counts["job"]})
            if counts["job"] == 2:
                raise RuntimeError("vazifa ichida xato")

        return [Job(id="work", func=work, interval_s=0.1)]

    @hookimpl
    def srv1_subscriptions(ctx):
        async def on_done(topic, data):
            counts["seen"] += 1
            if data["n"] == 1:
                raise RuntimeError("ishlovchi ichida xato")

        return [EventHandler("plugin.jobs.done", on_done)]

    @hookimpl
    def srv1_router(ctx):
        router = APIRouter()

        @router.get("/counts")
        async def get_counts():
            return counts

        return router
"""


@pytest.mark.parametrize("mode", MODES)
async def test_jobs_run_survive_errors_and_stop_on_disable(
    paths: DataPaths, plugin_root: Path, mode: str
) -> None:
    write_plugin(plugin_root, "jobs", JOB_PLUGIN, f'mode = "{mode}"')
    async with serve_app(paths) as served, served.client() as client:
        counts = {"job": 0, "seen": 0}
        for _ in range(300):
            counts = (await client.get(f"{API}/jobs/api/counts")).json()
            if counts["job"] >= 4 and counts["seen"] >= 4:
                break
            await asyncio.sleep(0.02)
        else:
            pytest.fail(f"vazifa xatodan keyin davom etmadi: {counts}")

        seen: list[int] = []
        await client.post(f"{API}/jobs/disable")
        subscription = served.core.bus.subscribe("plugin.jobs.done")
        served.core.bus.publish("marker")
        async with served.client() as other:
            for _ in range(5):
                await other.get("/api/v1/health")
                await asyncio.sleep(0.05)
        served.core.bus.unsubscribe(subscription)
        seen = [event.data["n"] async for event in subscription]
        assert seen == [], "o'chirilgan plagin vazifasi ishlashda davom etdi"


# --- alohida jarayon: RAM limiti, qulash, yadro o'lganda bola ham o'ladi ----------------------
HUNGRY_PLUGIN = """
    import os
    from fastapi import APIRouter
    from srv1_sdk.hookspec import hookimpl

    hoard = []

    @hookimpl
    def srv1_router(ctx):
        router = APIRouter()

        @router.get("/ping")
        async def ping():
            return {"pid": os.getpid()}

        @router.post("/eat")
        async def eat(mb: int):
            hoard.append(bytearray(mb * 1024 * 1024))
            return {"held_mb": sum(len(block) for block in hoard) // (1024 * 1024)}

        @router.post("/die")
        async def die(code: int):
            os._exit(code)

        return router
"""


async def test_memory_limit_kills_plugin_not_core(paths: DataPaths, plugin_root: Path) -> None:
    write_plugin(plugin_root, "hungry", HUNGRY_PLUGIN, 'mode = "subprocess"\nmemory_limit_mb = 128')
    async with serve_app(paths) as served, served.client() as client:
        pid = (await client.get(f"{API}/hungry/api/ping")).json()["pid"]
        assert pid == (await _info(client, "hungry"))["pid"]
        small = await client.post(f"{API}/hungry/api/eat", params={"mb": 16})
        assert small.json() == {"held_mb": 16}

        events = served.core.bus.subscribe("plugins.state")
        big = await client.post(f"{API}/hungry/api/eat", params={"mb": 400})
        assert big.status_code == 502

        info = await _status_is(client, "hungry", "crashed")
        assert info["error"] == "xotira limiti oshdi"
        assert info["pid"] is None
        assert not psutil.pid_exists(pid)
        assert (await client.get(f"{API}/hungry/api/ping")).status_code == 409
        assert (await client.get("/api/v1/health")).status_code == 200
        state = await anext(events)
        assert state.data == {"name": "hungry", "status": "crashed", "error": "xotira limiti oshdi"}

        # qayta yoqsa, toza holatda ishga tushadi
        again = (await client.post(f"{API}/hungry/enable")).json()
        assert again["status"] == "running"
        assert again["pid"] != pid
        fresh = await client.post(f"{API}/hungry/api/eat", params={"mb": 1})
        assert fresh.json() == {"held_mb": 1}
    assert ("core", "plugin.crashed", 0) in _audit_rows(paths)


async def test_unexpected_exit_is_reported(paths: DataPaths, plugin_root: Path) -> None:
    write_plugin(plugin_root, "hungry", HUNGRY_PLUGIN, 'mode = "subprocess"')
    async with serve_app(paths) as served, served.client() as client:
        assert (await client.post(f"{API}/hungry/api/die", params={"code": 3})).status_code == 502
        info = await _status_is(client, "hungry", "crashed")
        assert info["error"] == "jarayon kutilmaganda tugadi (kod 3)"
        assert info["enabled"] is True
        assert not served.core.bus.has_subscribers("plugin.hungry.x")


def test_child_dies_with_core(tmp_path: Path) -> None:
    """Yadro `kill` qilinsa (toza to'xtamasa ham), Job Object bolani o'ldiradi."""
    data_dir = tmp_path / "data"
    root = tmp_path / "plugin-root"
    write_plugin(root, "hungry", HUNGRY_PLUGIN, 'mode = "subprocess"')
    port = free_port()
    env = {key: value for key, value in os.environ.items() if not key.startswith("SRV1_")}
    env |= {
        "SRV1_DATA_DIR": str(data_dir),
        "SRV1_SERVER__PORT": str(port),
        "SRV1_PLUGINS__LOAD_BUILTIN": "false",
        "SRV1_PLUGINS__DIRS": json.dumps([str(root)]),
    }
    core = subprocess.Popen([sys.executable, "-m", "srv1_core"], env=env, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 30
        while True:
            try:
                httpx.get(f"{base}/api/v1/health", timeout=1.0).raise_for_status()
                break
            except httpx.HTTPError:
                assert time.monotonic() < deadline, "yadro ishga tushmadi"
                assert core.poll() is None, "yadro o'ldi"
                time.sleep(0.1)
        token = (data_dir / "auth.token").read_text(encoding="ascii").strip()
        headers = {"Authorization": f"Bearer {token}"}
        child_pid = httpx.get(f"{base}{API}/hungry/api/ping", headers=headers).json()["pid"]
        # venv'dagi python.exe ishga tushirgich bo'lishi mumkin: haqiqiy yadro — bolaning otasi.
        real_core_pid = psutil.Process(child_pid).ppid()
        assert real_core_pid in {core.pid, *(c.pid for c in psutil.Process(core.pid).children())}
    finally:
        for process in [*psutil.Process(core.pid).children(), psutil.Process(core.pid)]:
            process.kill()  # toza to'xtatishsiz: faqat yadro (va ishga tushirgich), bola emas
        core.wait(timeout=10)
    deadline = time.monotonic() + 5
    while psutil.pid_exists(child_pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not psutil.pid_exists(child_pid)
    assert not psutil.pid_exists(real_core_pid)
