"""`itops` plagini: haqiqiy yadro, haqiqiy jarayonlar va xizmatlar ro'yxati.

Skaner faqat 127.0.0.0/8 da (soxta serverlar) sinaladi — haqiqiy tarmoq skanerlanmaydi.
Xizmatlarni haqiqatan to'xtatish/ishga tushirish sinalmaydi (tizimga ta'sir qiladi).
"""

import asyncio
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager, closing
from dataclasses import dataclass
from ipaddress import IPv4Interface, IPv4Network
from pathlib import Path
from typing import Any

import httpx
import psutil
import pytest

from conftest import Served, free_port, serve_app
from srv1_core.paths import DataPaths
from srv1_core.plugins.registry import BUILTIN_DIR

API = "/api/v1/plugins/itops/api"
PYTHON = getattr(sys, "_base_executable", sys.executable)
SLEEPER = "import time; time.sleep(120)"


def install_itops(
    plugin_root: Path, paths: DataPaths, manifest: str = "", **config: object
) -> None:
    """Plaginni nusxalaydi; `manifest` — `[permissions]` dagi almashtirishlar (`eski=>yangi`)."""
    target = plugin_root / "itops"
    shutil.copytree(BUILTIN_DIR / "itops", target, ignore=shutil.ignore_patterns("__pycache__"))
    file = target / "plugin.toml"
    text = file.read_text(encoding="utf-8")
    for change in filter(None, manifest.split(";")):
        old, new = change.split("=>")
        assert old in text, old
        text = text.replace(old, new)
    file.write_text(text, encoding="utf-8")
    data = paths.plugin_data_dir("itops")
    data.mkdir(parents=True, exist_ok=True)
    settings = {"backup_cron": "", **config}
    (data / "itops.json").write_text(json.dumps({"config": settings}), encoding="utf-8")


async def _eventually[T](
    probe: Callable[[], Awaitable[T]], accept: Callable[[T], bool], what: str, timeout_s: float = 20
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


@dataclass
class Ops:
    client: httpx.AsyncClient
    served: Served
    paths: DataPaths

    async def get(self, path: str, **params: str | float) -> Any:  # noqa: ANN401
        response = await self.client.get(f"{API}{path}", params=params)
        assert response.status_code == 200, response.text
        return response.json()

    async def post(self, operation: str, /, **body: object) -> httpx.Response:
        return await self.client.post(f"{API}{operation}", json=body)

    def audit(self) -> list[tuple[str, str, int]]:
        with closing(sqlite3.connect(self.paths.db_file)) as conn:
            return conn.execute(
                "SELECT action, target, ok FROM audit_log WHERE actor = 'plugin:itops' ORDER BY id"
            ).fetchall()

    async def backup(self) -> dict[str, Any]:
        started = await self.post("/backups/run")
        assert started.status_code == 202, started.text
        status = await _eventually(
            lambda: self.get("/backups/status"), lambda s: s["state"] != "running", "zaxira"
        )
        assert status["state"] == "done", status
        return status["last"]

    async def scan(self, **body: object) -> dict[str, Any]:
        started = await self.post("/scan", **body)
        assert started.status_code == 202, started.text
        return await _eventually(
            lambda: self.get("/scan"), lambda s: s["state"] != "running", "skanerlash", 40
        )


@asynccontextmanager
async def _ops(
    paths: DataPaths, plugin_root: Path, manifest: str = "", **config: object
) -> AsyncGenerator[Ops]:
    install_itops(plugin_root, paths, manifest, **config)
    async with serve_app(paths) as served, served.client() as client:
        yield Ops(client, served, paths)


def _orphan() -> psutil.Process:
    """Yadroga qarindosh bo'lmagan jarayon: oraliq ota darhol tugaydi."""
    code = (
        "import subprocess, sys;"
        "n = subprocess.DEVNULL;"  # quvur meros qolmasin, aks holda `run` nevarani kutadi
        f"p = subprocess.Popen([sys.executable, '-c', {SLEEPER!r}], stdin=n, stdout=n, stderr=n);"
        "print(p.pid)"
    )
    out = subprocess.run([PYTHON, "-c", code], capture_output=True, text=True, check=True)
    return psutil.Process(int(out.stdout.strip()))


# --- jarayonlar -------------------------------------------------------------------------
async def test_process_list_search_and_sort(paths: DataPaths, plugin_root: Path) -> None:
    async with _ops(paths, plugin_root) as ops:
        rows = await ops.get("/processes")
        assert len(rows) > 10
        assert {"pid", "name", "user", "cpu", "memory", "started", "protected"} <= set(rows[0])
        memory = [row["memory"] for row in rows]
        assert memory == sorted(memory, reverse=True)
        me = next(
            row for row in await ops.get("/processes", limit=1000) if row["pid"] == os.getpid()
        )
        assert me["protected"] is True and me["memory"] > 10 * 1024 * 1024

        found = await ops.get("/processes", search="PYTHON", sort="name")
        assert found and all("python" in row["name"].lower() for row in found)
        assert len(await ops.get("/processes", limit=3)) == 3
        by_pid = [row["pid"] for row in await ops.get("/processes", sort="pid")]
        assert by_pid == sorted(by_pid)
        bad = await ops.client.get(f"{API}/processes", params={"sort": "rm -rf"})
        assert bad.status_code == 422


async def test_kill_orphan_but_not_protected(paths: DataPaths, plugin_root: Path) -> None:
    victim = _orphan()
    child = subprocess.Popen([PYTHON, "-c", SLEEPER])  # noqa: ASYNC220 — sinov qurboni
    try:
        async with _ops(paths, plugin_root) as ops:
            rows = {row["pid"]: row for row in await ops.get("/processes", limit=1000)}
            assert rows[victim.pid]["protected"] is False
            assert rows[child.pid]["protected"] is True  # yadroning bolasi

            for pid in (os.getpid(), child.pid, 4):
                refused = await ops.post("/processes/kill", pid=pid)
                assert refused.status_code == 403, refused.text
            assert psutil.pid_exists(child.pid)
            stale = await ops.post("/processes/kill", pid=victim.pid, started=1.0)
            assert stale.status_code == 409 and victim.is_running()

            started, name = rows[victim.pid]["started"], rows[victim.pid]["name"]
            killed = await ops.post("/processes/kill", pid=victim.pid, started=started)
            assert killed.json() == {"pid": victim.pid, "name": name, "killed": True}
            assert not victim.is_running()
            assert (await ops.post("/processes/kill", pid=victim.pid)).status_code == 404
            assert (await ops.post("/processes/kill", pid=0)).status_code == 422

            audit = [(target, ok) for action, target, ok in ops.audit() if action == "process.kill"]
            assert audit == [
                (str(os.getpid()), 0),
                (str(child.pid), 0),
                ("4", 0),
                (str(victim.pid), 0),
                (str(victim.pid), 1),
                (str(victim.pid), 0),
            ]
    finally:
        child.kill()
        if victim.is_running():
            victim.kill()


# --- xizmatlar ----------------------------------------------------------------------------
async def test_services_list_and_safe_refusals(paths: DataPaths, plugin_root: Path) -> None:
    async with _ops(paths, plugin_root) as ops:
        rows = await ops.get("/services")
        assert len(rows) > 20
        assert {"name", "title", "state", "start", "pid", "protected"} <= set(rows[0])
        names = [row["name"].lower() for row in rows]
        assert names == sorted(names)
        log = await ops.get("/services", search="eventlog")
        assert [(row["name"].lower(), row["protected"]) for row in log] == [("eventlog", True)]
        running = await ops.get("/services", state="running")
        assert running and all(row["state"] == "running" and row["pid"] for row in running)

        # muhim xizmat to'xtatilmaydi; yo'q xizmat — 404; nom tekshiriladi
        assert (await ops.post("/services/stop", name="EventLog")).status_code == 403
        assert (await ops.post("/services/restart", name="RpcSs")).status_code == 403
        assert (await ops.post("/services/stop", name="srv1_yoq_xizmat")).status_code == 404
        assert (await ops.post("/services/start", name="a;b")).status_code == 422

        # ishlab turgan xizmatni «ishga tushirish» zararsiz: administratorsiz — 403,
        # administrator bilan — 409 (allaqachon ishlayapti). Hech narsa o'zgarmaydi.
        target = next(row["name"] for row in running if not row["protected"])
        again = await ops.post("/services/start", name=target)
        assert again.status_code in (403, 409), again.text
        after = await ops.get("/services", search=target)
        assert next(row for row in after if row["name"] == target)["state"] == "running"
        audit = ops.audit()
        assert ("service.stop", "EventLog", 0) in audit
        assert ("service.start", target, 0) in audit


async def test_permissions_are_required(paths: DataPaths, plugin_root: Path) -> None:
    manifest = "system = true=>system = false;data_root = true=>data_root = false"
    async with _ops(paths, plugin_root, manifest, scan_loopback=True) as ops:
        assert len(await ops.get("/processes")) > 10  # ko'rish — ruxsatsiz ham
        assert (await ops.post("/processes/kill", pid=99999)).status_code == 403
        assert (await ops.post("/services/start", name="Spooler")).status_code == 403
        assert (await ops.post("/scan", network="127.0.0.0/30")).status_code == 403
        assert (await ops.post("/backups/run")).status_code == 403
        assert ops.audit() == []


# --- tarmoq skaneri -----------------------------------------------------------------------
async def _listener(host: str, port: int) -> asyncio.Server:
    async def close(_reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        writer.close()

    return await asyncio.start_server(close, host, port)


async def test_scan_finds_open_ports_on_loopback(paths: DataPaths, plugin_root: Path) -> None:
    web, other = free_port(), free_port()
    servers = [
        await _listener("127.0.0.2", web),
        await _listener("127.0.0.5", web),
        await _listener("127.0.0.5", other),
    ]
    try:
        async with _ops(paths, plugin_root, scan_loopback=True, scan_timeout_s=1.0) as ops:
            events = ops.served.core.bus.subscribe("plugin.itops.scan")
            networks = await ops.get("/networks")
            assert {"network": "127.0.0.0/24", "address": "127.0.0.1"} in networks

            done = await ops.scan(network="127.0.0.0/29", ports=[other, web, web])
            assert (done["state"], done["network"]) == ("done", "127.0.0.0/29")
            assert done["ports"] == sorted([web, other])
            assert done["progress"] == "12/12"  # 6 manzil x 2 port
            hosts = {row["ip"]: row for row in await ops.get("/scan/hosts")}
            with_ports = {ip: row["ports"] for ip, row in hosts.items() if row["ports"]}
            assert with_ports == {
                "127.0.0.2": str(web),
                "127.0.0.5": ", ".join(str(port) for port in sorted([web, other])),
            }
            assert hosts["127.0.0.2"]["seen"] == "tcp"
            assert (await asyncio.wait_for(anext(events), 5)).data["state"] == "done"
            assert ("network.scan", "127.0.0.0/29", 1) in ops.audit()
            assert (await ops.get("/status"))["scan_hosts"] == len(hosts)
    finally:
        for server in servers:
            server.close()


async def test_scan_is_limited_to_own_small_networks(paths: DataPaths, plugin_root: Path) -> None:
    async with _ops(
        paths, plugin_root, scan_loopback=True, scan_timeout_s=3.0, scan_concurrency=2
    ) as ops:
        for network, expected in (
            ("8.8.8.0/24", 403),
            ("1.1.1.1/32", 403),
            ("127.0.0.0/16", 403),  # /24 dan katta
            ("203.0.113.0/30", 403),
            ("tarmoq", 400),
            ("127.0.0.1/24", 400),  # tarmoq manzili emas
        ):
            response = await ops.post("/scan", network=network)
            assert response.status_code == expected, (network, response.text)
        assert (await ops.post("/scan", ports=[0])).status_code == 422
        assert (await ops.post("/scan/cancel")).status_code == 409
        assert await ops.get("/scan") == {"state": "idle"}

        # uzoq skaner: ikkinchisi rad etiladi, bekor qilish ishlaydi
        port = free_port()
        assert (await ops.post("/scan", network="127.0.0.0/24", ports=[port])).status_code == 202
        assert (await ops.post("/scan", network="127.0.0.0/30")).status_code == 409
        cancelled = await ops.post("/scan/cancel")
        assert cancelled.json()["state"] == "cancelled"
        assert (await ops.post("/scan", network="127.0.0.0/30", ports=[port])).status_code == 202


async def test_loopback_is_refused_by_default(paths: DataPaths, plugin_root: Path) -> None:
    async with _ops(paths, plugin_root) as ops:
        assert (await ops.post("/scan", network="127.0.0.0/29")).status_code == 403
        assert all(not row["network"].startswith("127.") for row in await ops.get("/networks"))


def test_scan_range_rules() -> None:
    sys.path.insert(0, str(BUILTIN_DIR.parent))
    try:
        from plugins.itops import netscan
    finally:
        sys.path.pop(0)
    wide = IPv4Interface("172.17.112.9/20")
    assert netscan.scan_range(wide) == IPv4Network("172.17.112.0/24")
    assert netscan.scan_range(IPv4Interface("192.168.8.171/24")) == IPv4Network("192.168.8.0/24")
    assert netscan.allowed_range(IPv4Network("172.17.113.0/24"), [wide])
    assert not netscan.allowed_range(IPv4Network("172.17.112.0/20"), [wide])
    assert not netscan.allowed_range(IPv4Network("172.18.0.0/24"), [wide])
    for interface in netscan.local_interfaces():
        assert interface.ip.is_private and not interface.ip.is_loopback
    for ip, mac in netscan.arp_table().items():
        assert ip.count(".") == 3 and len(mac) == 17, (ip, mac)


# --- zaxira nusxa -------------------------------------------------------------------------
def _seed(paths: DataPaths) -> None:
    notes = paths.plugin_data_dir("hello")
    notes.mkdir(parents=True, exist_ok=True)
    (notes / "notes.txt").write_text("muhim yozuv\n", encoding="utf-8")
    (notes / "yarim.tmp").write_text("x", encoding="utf-8")
    (notes / "tmp").mkdir()
    (notes / "tmp" / "kesh.bin").write_bytes(b"k" * 100)
    with closing(sqlite3.connect(notes / "plagin.db")) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE t (v TEXT)")
        conn.execute("INSERT INTO t VALUES ('wal ichidagi yozuv')")
        conn.commit()
    site = paths.projects_dir / "sayt"
    site.mkdir(parents=True, exist_ok=True)
    (site / "index.html").write_text("<h1>sayt</h1>", encoding="utf-8")


def _archive(paths: DataPaths, name: str, directory: Path | None = None) -> zipfile.ZipFile:
    folder = directory or paths.plugin_data_dir("itops") / "backups"
    return zipfile.ZipFile(io.BytesIO((folder / name).read_bytes()))


async def test_backup_contents_secrets_and_databases(paths: DataPaths, plugin_root: Path) -> None:
    async with _ops(paths, plugin_root) as ops:
        _seed(paths)
        token = paths.token_file.read_text(encoding="ascii").strip()
        last = await ops.backup()
        assert last["skipped"] == 0 and last["databases"] == 2 and last["removed"] == []
        rows = await ops.get("/backups")
        assert [row["name"] for row in rows] == [last["name"]] and rows[0]["size"] == last["size"]

        with _archive(paths, last["name"]) as archive:
            names = set(archive.namelist())
            assert {"srv1.db", "backup.json", "plugins/hello/data/notes.txt"} <= names
            assert {"plugins/hello/data/plagin.db", "plugins/itops/data/itops.json"} <= names
            leaked = [n for n in names if n.endswith((".token", ".tmp", "-wal", "-shm"))]
            assert leaked == []
            assert not any(n.startswith(("projects/", "logs/")) or "/tmp/" in n for n in names)  # noqa: S108
            assert not any("backups" in n for n in names)
            assert all(token.encode() not in archive.read(n) for n in names)
            manifest = json.loads(archive.read("backup.json"))
            assert manifest["databases"] == ["srv1.db", "plugins/hello/data/plagin.db"]
            assert manifest["files"] == len(names) - 1 and manifest["projects"] is False
            restored = paths.root.parent / "tiklangan"
            archive.extractall(restored)
        # bazalar izchil: WAL'dagi yozuv ham, ishlab turgan yadro bazasi ham o'qiladi
        with closing(
            sqlite3.connect(restored / "plugins" / "hello" / "data" / "plagin.db")
        ) as conn:
            assert conn.execute("SELECT v FROM t").fetchall() == [("wal ichidagi yozuv",)]
            assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        with closing(sqlite3.connect(restored / "srv1.db")) as conn:
            assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] >= 1
        assert (
            "backup.create",
            str(paths.plugin_data_dir("itops") / "backups" / last["name"]),
            1,
        ) in (ops.audit())


async def test_backup_options_retention_and_removal(paths: DataPaths, plugin_root: Path) -> None:
    async with _ops(
        paths, plugin_root, backup_keep=2, backup_projects=True, backup_logs=True
    ) as ops:
        _seed(paths)
        first = await ops.backup()
        with _archive(paths, first["name"]) as archive:
            names = set(archive.namelist())
        assert "projects/sayt/index.html" in names
        assert any(name.startswith("logs/") for name in names)

        second = await ops.backup()
        third = await ops.backup()
        assert third["removed"] == [first["name"]]
        assert [row["name"] for row in await ops.get("/backups")] == [third["name"], second["name"]]
        status = await ops.get("/status")
        assert (status["backup_count"], status["backup_last"]) == (2, third["name"])
        assert (status["backup_state"], status["backup_cron"]) == ("done", "—")

        for bad in ("../../auth.token", "srv1-backup-x.zip", "itops.json"):
            assert (await ops.post("/backups/remove", name=bad)).status_code == 400, bad
        assert (await ops.post("/backups/remove", name=first["name"])).status_code == 404
        removed = await ops.post("/backups/remove", name=second["name"])
        assert removed.json() == {"removed": second["name"]}
        assert [row["name"] for row in await ops.get("/backups")] == [third["name"]]
        assert ops.audit()[-1][0] == "file.delete"


async def test_backup_destination_needs_manifest_path(
    paths: DataPaths, plugin_root: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "boshqa-disk"
    async with _ops(paths, plugin_root, backup_destination=str(outside)) as ops:
        assert (await ops.post("/backups/run")).status_code == 403
        assert not outside.exists()

    shutil.rmtree(plugin_root / "itops")
    allowed = f"paths = []=>paths = [{json.dumps(str(outside))}]"
    async with _ops(paths, plugin_root, allowed, backup_destination=str(outside)) as ops:
        last = await ops.backup()
        assert [path.name for path in outside.iterdir()] == [last["name"]]
        with _archive(paths, last["name"], outside) as archive:
            assert "srv1.db" in archive.namelist()
        assert not (paths.plugin_data_dir("itops") / "backups").exists()


async def test_backup_runs_on_cron_schedule(paths: DataPaths, plugin_root: Path) -> None:
    """Haqiqiy cron: har daqiqada. Keyingi daqiqa boshini kutadi (60 s gacha)."""
    async with _ops(paths, plugin_root, backup_cron="* * * * *") as ops:
        info = (await ops.client.get("/api/v1/plugins/itops")).json()
        assert info["jobs"] == ["itops:backup"]
        assert (await ops.get("/status"))["backup_cron"] == "* * * * *"
        rows = await _eventually(lambda: ops.get("/backups"), lambda r: len(r) >= 1, "cron", 70)
        with _archive(paths, rows[0]["name"]) as archive:
            assert "srv1.db" in archive.namelist()
