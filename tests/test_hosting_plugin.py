"""`hosting` plagini: haqiqiy yadro, haqiqiy Caddy, haqiqiy loyiha jarayonlari."""

import asyncio
import json
import shutil
import sqlite3
from collections.abc import Awaitable, Callable
from contextlib import closing
from pathlib import Path
from typing import Any

import httpx
import psutil
import pytest

from conftest import Served, serve_app
from hosting_helpers import CADDY_EXE, HostingPorts, install_hosting, write_app
from srv1_core.paths import DataPaths

API = "/api/v1/plugins/hosting/api"


@pytest.fixture
def ports(paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch) -> HostingPorts:
    monkeypatch.setenv("SRV1_CADDY_EXE", str(CADDY_EXE))
    return install_hosting(plugin_root, paths.plugin_data_dir("hosting"))


async def _eventually[T](
    probe: Callable[[], Awaitable[T]], accept: Callable[[T], bool], what: str, timeout_s: float = 15
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


class Hosting:
    """Test yordamchisi: plagin API'si va Caddy orqali saytga murojaat."""

    def __init__(self, client: httpx.AsyncClient, ports: HostingPorts) -> None:
        self.client = client
        self.ports = ports
        self.web = httpx.AsyncClient(timeout=20.0)

    async def post(self, operation: str, /, **body: object) -> httpx.Response:
        return await self.client.post(f"{API}{operation}", json=body)

    async def project(self, name: str) -> dict[str, Any]:
        rows = (await self.client.get(f"{API}/projects")).json()
        return next(row for row in rows if row["name"] == name)

    async def state_is(self, name: str, state: str) -> dict[str, Any]:
        async def probe() -> dict[str, Any]:
            return await self.project(name)

        return await _eventually(probe, lambda p: p["state"] == state, f"{name} -> {state}")

    async def site(
        self, name: str, path: str = "/", *, method: str = "GET", content: bytes | None = None
    ) -> httpx.Response:
        """Caddy orqali so'rov (brauzer kabi `Host` sarlavhasi bilan); 307 ga ergashmaydi."""
        return await self.web.request(
            method, self.ports.site_url(path), headers=self.ports.host_header(name), content=content
        )

    async def log(self, name: str) -> list[str]:
        return (await self.client.get(f"{API}/log", params={"name": name})).json()


def _audit(paths: DataPaths) -> list[tuple[str, str, int]]:
    with closing(sqlite3.connect(paths.db_file)) as conn:
        return conn.execute(
            "SELECT action, target, ok FROM audit_log WHERE actor = 'plugin:hosting' ORDER BY id"
        ).fetchall()


# --- statik sayt ---------------------------------------------------------------------
async def test_static_site_through_caddy(paths: DataPaths, ports: HostingPorts) -> None:
    async with serve_app(paths) as served, served.client() as client:
        hosting = Hosting(client, ports)
        status = (await client.get(f"{API}/status")).json()
        assert (status["caddy"], status["caddy_error"], status["projects"]) == ("running", None, 0)
        assert status["listen"] == f"127.0.0.1:{ports.listen}"
        assert psutil.pid_exists(status["caddy_pid"])

        created = await hosting.post("/projects", name="sayt", kind="static")
        assert created.status_code == 201, created.text
        info = created.json()
        assert (info["state"], info["kind"], info["port"], info["pid"]) == (
            "running",
            "static",
            None,
            None,
        )
        assert info["url"] == f"http://sayt.localhost:{ports.listen}/"

        directory = paths.projects_dir / "sayt"
        assert "<h1>sayt</h1>" in (directory / "index.html").read_text(encoding="utf-8")
        page = await hosting.site("sayt")
        assert (page.status_code, "<h1>sayt</h1>" in page.text) == (200, True)

        (directory / "salom.txt").write_text("Assalomu alaykum", encoding="utf-8")
        assert (await hosting.site("sayt", "/salom.txt")).text == "Assalomu alaykum"
        assert (await hosting.site("sayt", "/yoq.html")).status_code == 404
        assert (await hosting.site("sayt", "/../../auth.token")).status_code in (400, 404)

        unknown = await hosting.site("notanish")
        assert (unknown.status_code, "bunday loyiha yo'q" in unknown.text) == (404, True)

        assert (await hosting.post("/stop", name="sayt")).json()["state"] == "stopped"
        assert (await hosting.site("sayt")).status_code == 404
        assert (await hosting.post("/start", name="sayt")).json()["state"] == "running"
        assert (await hosting.site("sayt")).status_code == 200

        # mavjud papkadagi fayllarga tegilmaydi
        (paths.projects_dir / "tayyor").mkdir()
        (paths.projects_dir / "tayyor" / "index.html").write_text("mening saytim", encoding="utf-8")
        await hosting.post("/projects", name="tayyor", kind="static")
        assert (await hosting.site("tayyor")).text == "mening saytim"

        removed = (await hosting.post("/remove", name="sayt")).json()
        assert removed == {"removed": "sayt", "files_kept": str(directory)}
        assert (directory / "salom.txt").is_file(), "ro'yxatdan chiqarish fayllarni o'chirmaydi"
        assert (await hosting.site("sayt")).status_code == 404
        caddy_pid = status["caddy_pid"]

    assert not psutil.pid_exists(caddy_pid), "yadro to'xtaganda Caddy ham to'xtaydi"
    saved = json.loads((paths.plugin_data_dir("hosting") / "hosting.json").read_text("utf-8"))
    assert [project["name"] for project in saved["projects"]] == ["tayyor"]


# --- Python loyihasi -----------------------------------------------------------------------
async def test_python_project_lifecycle(paths: DataPaths, ports: HostingPorts) -> None:
    write_app(paths.projects_dir, "api")
    async with serve_app(paths) as served, served.client() as client:
        hosting = Hosting(client, ports)
        created = await hosting.post(
            "/projects", name="api", kind="python", command="python app.py", idle_minutes=0
        )
        assert created.status_code == 201, created.text
        info = created.json()
        assert info["state"] == "running"
        assert ports.first <= info["port"] <= ports.last
        assert psutil.pid_exists(info["pid"])
        assert info["memory"] > 1_000_000
        assert info["command"] == "python app.py"

        reply = (await hosting.site("api", "/salom?x=1")).json()
        assert reply["path"] == "/salom?x=1"
        assert reply["host"] == f"api.localhost:{ports.listen}"
        assert reply["pid"] == info["pid"] or psutil.Process(reply["pid"]).ppid() == info["pid"]
        posted = await hosting.site("api", "/yoz", method="POST", content=b"malumot")
        assert posted.json()["echo"] == "malumot"

        lines = await hosting.log("api")
        assert any("[srv1] ishga tushirilmoqda" in line for line in lines)
        assert any(f"ilova tayyor, port {info['port']}" in line for line in lines)
        log_file = paths.plugin_data_dir("hosting") / "logs" / "api.log"

        restarted = (await hosting.post("/restart", name="api")).json()
        assert restarted["state"] == "running"
        assert restarted["pid"] != info["pid"]
        assert restarted["port"] == info["port"], "port qayta ishga tushganda saqlanadi"
        assert not psutil.pid_exists(info["pid"])

        stopped = (await hosting.post("/stop", name="api")).json()
        assert (stopped["state"], stopped["pid"], stopped["memory"]) == ("stopped", None, None)
        assert not psutil.pid_exists(restarted["pid"])
        assert (await hosting.site("api")).status_code == 404

        # plagin o'chirilganda hamma jarayon to'xtaydi
        again = (await hosting.post("/start", name="api")).json()
        caddy_pid = (await client.get(f"{API}/status")).json()["caddy_pid"]
        await client.post("/api/v1/plugins/hosting/disable")
        assert not psutil.pid_exists(again["pid"])
        assert not psutil.pid_exists(caddy_pid)

    assert "ilova tayyor" in log_file.read_text(encoding="utf-8")
    audit = _audit(paths)
    spawned = [target for action, target, ok in audit if action == "process.spawn" and ok]
    assert sum(target.lower().endswith("caddy.exe") for target in spawned) == 1
    assert sum("python" in target.lower() for target in spawned) == 3
    assert ("hosting.project_create", "api", 1) in audit
    assert ("hosting.project_stop", "api", 1) in audit


async def test_autostart_and_state_survive_restart(paths: DataPaths, ports: HostingPorts) -> None:
    write_app(paths.projects_dir, "doimiy")
    async with serve_app(paths) as served, served.client() as client:
        hosting = Hosting(client, ports)
        body = {
            "name": "doimiy",
            "kind": "python",
            "command": ["python", "app.py"],
            "autostart": True,
        }
        first = (await client.post(f"{API}/projects", json=body)).json()
        await hosting.post("/projects", name="qolda", kind="static", start=False)
    async with serve_app(paths) as served, served.client() as client:
        hosting = Hosting(client, ports)
        doimiy, qolda = await hosting.project("doimiy"), await hosting.project("qolda")
        assert (doimiy["state"], doimiy["port"]) == ("running", first["port"])
        assert doimiy["pid"] != first["pid"]
        assert qolda["state"] == "stopped"
        assert (await hosting.site("doimiy")).status_code == 200


# --- uxlatish va uyg'otish -------------------------------------------------------------------
async def test_idle_project_sleeps_and_wakes_on_request(
    paths: DataPaths, ports: HostingPorts
) -> None:
    write_app(paths.projects_dir, "uyqu")
    async with serve_app(paths) as served, served.client() as client:
        hosting = Hosting(client, ports)
        created = await hosting.post(
            "/projects", name="uyqu", kind="python", command="python app.py", idle_minutes=0.02
        )
        first_pid = created.json()["pid"]

        asleep = await hosting.state_is("uyqu", "sleeping")
        assert asleep["pid"] is None
        assert not psutil.pid_exists(first_pid)
        assert any("uxlatildi" in line for line in await hosting.log("uyqu"))

        # so'rov keladi -> loyiha uyg'onadi -> 307 -> qayta so'rov ilovaga yetadi
        woke = await hosting.site("uyqu", "/sahifa?a=1")
        assert woke.status_code == 307
        assert woke.headers["location"] == "/sahifa?a=1"
        awake = await hosting.project("uyqu")
        assert awake["state"] == "running"
        assert awake["pid"] != first_pid
        reply = (await hosting.site("uyqu", woke.headers["location"])).json()
        assert reply["path"] == "/sahifa?a=1"

        # POST ham yo'qolmaydi: 307 metod va tanani saqlaydi
        await hosting.state_is("uyqu", "sleeping")
        posted = await hosting.site("uyqu", "/yoz", method="POST", content=b"tana")
        assert posted.status_code == 307
        repeated = await hosting.site(
            "uyqu", posted.headers["location"], method="POST", content=b"tana"
        )
        assert repeated.json()["echo"] == "tana"

        # bir vaqtda kelgan so'rovlar loyihani bir marta uyg'otadi
        await hosting.state_is("uyqu", "sleeping")
        answers = await asyncio.gather(*(hosting.site("uyqu", f"/{i}") for i in range(5)))
        assert {answer.status_code for answer in answers} <= {307, 200}
        spawned = [t for action, t, _ok in _audit(paths) if action == "process.spawn"]
        assert sum("python" in target.lower() for target in spawned) == 4


async def test_requests_keep_project_awake(paths: DataPaths, ports: HostingPorts) -> None:
    write_app(paths.projects_dir, "band")
    async with serve_app(paths) as served, served.client() as client:
        hosting = Hosting(client, ports)
        created = await hosting.post(
            "/projects", name="band", kind="python", command="python app.py", idle_minutes=0.03
        )
        pid = created.json()["pid"]
        for _ in range(12):  # 3,6 s — uxlatish muddatidan (1,8 s) ikki baravar uzoq
            assert (await hosting.site("band")).status_code == 200
            await asyncio.sleep(0.3)
        info = await hosting.project("band")
        assert (info["state"], info["pid"]) == ("running", pid)
        await hosting.state_is("band", "sleeping")

        # idle_minutes = 0: hech qachon uxlamaydi
        write_app(paths.projects_dir, "doim")
        await hosting.post(
            "/projects", name="doim", kind="python", command="python app.py", idle_minutes=0
        )
        await asyncio.sleep(2)
        assert (await hosting.project("doim"))["state"] == "running"


# --- xato holatlari -----------------------------------------------------------------------------
async def test_failures_are_reported_not_hidden(
    paths: DataPaths, ports: HostingPorts, plugin_root: Path
) -> None:
    settings_file = paths.plugin_data_dir("hosting") / "hosting.json"
    settings = json.loads(settings_file.read_text(encoding="utf-8"))
    settings["config"]["ready_timeout_s"] = 2
    settings_file.write_text(json.dumps(settings), encoding="utf-8")
    write_app(paths.projects_dir, "yiqiladi")
    (paths.projects_dir / "skript").mkdir()
    (paths.projects_dir / "skript" / "run.cmd").write_text("@echo off\r\n", encoding="utf-8")

    async with serve_app(paths) as served, served.client() as client:
        hosting = Hosting(client, ports)

        missing = await hosting.post(
            "/projects", name="yoq-dastur", kind="python", command="yoq_dastur_xyz"
        )
        assert (missing.status_code, "dastur topilmadi" in missing.text) == (400, True)
        assert (await hosting.project("yoq-dastur"))["state"] == "failed"

        script = await hosting.post("/projects", name="skript", kind="node", command="run.cmd")
        assert (script.status_code, "skript" in script.json()["detail"]) == (400, True)

        exits = await hosting.post(
            "/projects",
            name="chiqadi",
            kind="python",
            command=["python", "-c", "raise SystemExit(3)"],
        )
        assert exits.status_code == 502
        assert exits.json()["detail"] == "jarayon darhol tugadi (kod 3)"

        silent = await hosting.post(
            "/projects",
            name="jim",
            kind="python",
            command=["python", "-c", "import time; time.sleep(60)"],
        )
        assert silent.status_code == 502
        assert "ochilmadi" in silent.json()["detail"]
        jim = await hosting.project("jim")
        assert (jim["state"], jim["pid"]) == ("failed", None)
        unavailable = await hosting.site("jim")
        assert (unavailable.status_code, "ishga tushmadi" in unavailable.text) == (503, True)

        # ishlab turib yiqilgan loyiha
        await hosting.post("/projects", name="yiqiladi", kind="python", command="python app.py")
        pid = (await hosting.project("yiqiladi"))["pid"]
        died = await hosting.site("yiqiladi", "/die")
        assert died.status_code == 502, "ilova javobsiz uzilsa, Caddy 502 qaytaradi"
        crashed = await hosting.state_is("yiqiladi", "failed")
        assert crashed["error"] == "jarayon kutilmaganda tugadi (kod 7)"
        assert not psutil.pid_exists(pid)
        assert any("xato:" in line for line in await hosting.log("yiqiladi"))
        assert (await hosting.site("yiqiladi")).status_code == 503
        recovered = (await hosting.post("/start", name="yiqiladi")).json()
        assert (recovered["state"], recovered["error"]) == ("running", None)

        status = (await client.get(f"{API}/status")).json()
        assert (status["failed"], status["running"]) == (4, 1)
        assert (await client.get("/api/v1/health")).status_code == 200


async def test_memory_limit_stops_project(paths: DataPaths, ports: HostingPorts) -> None:
    write_app(paths.projects_dir, "ochkoz")
    async with serve_app(paths) as served, served.client() as client:
        hosting = Hosting(client, ports)
        created = await hosting.post(
            "/projects", name="ochkoz", kind="python", command="python app.py", memory_limit_mb=64
        )
        assert created.json()["memory_limit_mb"] == 64
        assert (await hosting.site("ochkoz")).status_code == 200
        eaten = await hosting.site("ochkoz", "/eat")  # 400 MB so'raydi, limit 64 MB
        assert eaten.status_code == 502
        failed = await hosting.state_is("ochkoz", "failed")
        assert failed["error"] == "jarayon kutilmaganda tugadi (kod 9)"
        assert (await client.get("/api/v1/health")).status_code == 200


async def test_validation_and_conflicts(paths: DataPaths, ports: HostingPorts) -> None:
    async with serve_app(paths) as served, served.client() as client:
        hosting = Hosting(client, ports)
        bad_bodies: list[dict[str, object]] = [
            {"name": "Bad_Name", "kind": "static"},
            {"name": "-boshida", "kind": "static"},
            {"name": "ok", "kind": "php"},
            {"name": "ok", "kind": "static", "command": "python app.py"},
            {"name": "ok", "kind": "python"},
            {"name": "ok", "kind": "python", "command": "python app.py", "memory_limit_mb": 8},
            {"name": "ok", "kind": "static", "unknown": 1},
        ]
        for body in bad_bodies:
            assert (await client.post(f"{API}/projects", json=body)).status_code == 422, body
        escape = await hosting.post("/projects", name="qochoq", kind="static", root="../..")
        assert escape.status_code == 400
        assert (await client.get(f"{API}/projects")).json() == []

        assert (await hosting.post("/projects", name="bir", kind="static")).status_code == 201
        assert (await hosting.post("/projects", name="bir", kind="static")).status_code == 409
        for operation in ("/start", "/stop", "/restart", "/remove"):
            assert (await hosting.post(operation, name="yoq")).status_code == 404
        assert (await client.get(f"{API}/log", params={"name": "yoq"})).status_code == 404
        assert (await client.get(f"{API}/log", params={"name": "../x"})).status_code == 422

        ichki = paths.projects_dir / "ichki"
        (ichki / "public").mkdir(parents=True)
        (ichki / "public" / "index.html").write_text("ochiq", encoding="utf-8")
        (ichki / "maxfiy.txt").write_text("yopiq", encoding="utf-8")
        await hosting.post("/projects", name="ichki", kind="static", root="public")
        assert (await hosting.site("ichki")).text == "ochiq"
        assert (await hosting.site("ichki", "/../maxfiy.txt")).status_code in (400, 404)


async def test_ports_run_out_gracefully(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SRV1_CADDY_EXE", str(CADDY_EXE))
    ports = install_hosting(plugin_root, paths.plugin_data_dir("hosting"), projects=1)
    write_app(paths.projects_dir, "birinchi")
    write_app(paths.projects_dir, "ikkinchi")
    async with serve_app(paths) as served, served.client() as client:
        hosting = Hosting(client, ports)
        first = await hosting.post(
            "/projects", name="birinchi", kind="python", command="python app.py"
        )
        assert first.json()["port"] == ports.first
        second = await hosting.post(
            "/projects", name="ikkinchi", kind="python", command="python app.py"
        )
        assert (second.status_code, "bo'sh port qolmadi" in second.text) == (503, True)
        await hosting.post("/stop", name="birinchi")
        assert (await hosting.post("/start", name="ikkinchi")).json()["port"] == ports.first


# --- Node loyihasi -----------------------------------------------------------------------------
@pytest.mark.skipif(shutil.which("node") is None, reason="Node o'rnatilmagan")
async def test_node_project(paths: DataPaths, ports: HostingPorts) -> None:
    write_app(paths.projects_dir, "tugun", node=True)
    async with serve_app(paths) as served, served.client() as client:
        hosting = Hosting(client, ports)
        created = await hosting.post(
            "/projects", name="tugun", kind="node", command="node server.js"
        )
        assert created.status_code == 201, created.text
        reply = (await hosting.site("tugun", "/salom")).json()
        assert (reply["runtime"], reply["path"]) == ("node", "/salom")
        assert any("node ilova tayyor" in line for line in await hosting.log("tugun"))
        npm = await hosting.post("/projects", name="npmli", kind="node", command="npm start")
        assert (npm.status_code, "skript" in npm.json()["detail"]) == (400, True)


# --- Caddy'siz va noto'g'ri sozlama ----------------------------------------------
async def test_missing_caddy_is_reported(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ports = install_hosting(plugin_root, paths.plugin_data_dir("hosting"))
    monkeypatch.setenv("SRV1_CADDY_EXE", str(tmp_path / "yoq" / "caddy.exe"))
    write_app(paths.projects_dir, "yakka")
    async with serve_app(paths) as served, served.client() as client:
        hosting = Hosting(client, ports)
        status = (await client.get(f"{API}/status")).json()
        assert (status["caddy"], status["caddy_pid"]) == ("missing", None)
        assert "caddy.exe topilmadi" in status["caddy_error"]
        assert (await client.get("/api/v1/plugins/hosting")).json()["status"] == "running"
        created = await hosting.post(
            "/projects", name="yakka", kind="python", command="python app.py"
        )
        direct = await hosting.web.get(f"http://127.0.0.1:{created.json()['port']}/")
        assert direct.status_code == 200, "Caddy'siz ham loyiha o'z portida ishlaydi"


async def _plugin_status(served: Served, client: httpx.AsyncClient) -> dict[str, Any]:
    return (await client.get("/api/v1/plugins/hosting")).json()


async def test_non_loopback_listen_needs_explicit_flag(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SRV1_CADDY_EXE", str(CADDY_EXE))
    data_dir = paths.plugin_data_dir("hosting")
    install_hosting(plugin_root, data_dir, listen_host="0.0.0.0")  # noqa: S104
    async with serve_app(paths) as served, served.client() as client:
        info = await _plugin_status(served, client)
        assert info["status"] == "error"
        assert "loopback emas" in info["error"]
        assert (await client.get("/api/v1/health")).status_code == 200
        assert (await client.get(f"{API}/status")).status_code == 409
