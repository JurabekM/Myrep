"""`hosting` tunneli: haqiqiy yadro va Caddy, lekin soxta cloudflared.

Haqiqiy tunnel ataylab ochilmaydi: u saytni internetga chiqaradi. Soxta dastur
cloudflared kabi manzilni jurnalga yozadi; uning argumentlari tekshiriladi.
"""

import json
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path
from typing import Any

import httpx
import psutil
import pytest

from conftest import serve_app
from hosting_helpers import (
    CADDY_EXE,
    FAKE_TUNNEL_URL,
    HostingPorts,
    install_hosting,
    write_fake_cloudflared,
)
from srv1_core.paths import DataPaths
from srv1_core.plugins.registry import BUILTIN_DIR

API = "/api/v1/plugins/hosting/api"
REAL_CLOUDFLARED = BUILTIN_DIR.parent / "tools" / "cloudflared.exe"
PUBLIC_URL = FAKE_TUNNEL_URL


class Fake:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.command = write_fake_cloudflared(directory)

    def mode(self, value: str) -> None:
        (self.directory / "mode.txt").write_text(value, encoding="utf-8")

    def calls(self) -> list[dict[str, Any]]:
        path = self.directory / "calls.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def alive(self) -> list[int]:
        return [call["pid"] for call in self.calls() if psutil.pid_exists(call["pid"])]


@pytest.fixture
def fake(tmp_path: Path) -> Fake:
    return Fake(tmp_path / "fake-cloudflared")


@pytest.fixture
def ports(
    paths: DataPaths, plugin_root: Path, fake: Fake, monkeypatch: pytest.MonkeyPatch
) -> HostingPorts:
    monkeypatch.setenv("SRV1_CADDY_EXE", str(CADDY_EXE))
    return install_hosting(
        plugin_root,
        paths.plugin_data_dir("hosting"),
        tunnel_command=fake.command,
        tunnel_timeout_s=3,
        tunnel_max=1,
    )


async def _post(client: httpx.AsyncClient, operation: str, **body: object) -> httpx.Response:
    return await client.post(f"{API}{operation}", json=body)


async def _site(client: httpx.AsyncClient, name: str) -> dict[str, Any]:
    response = await _post(client, "/projects", name=name, kind="static")
    assert response.status_code == 201, response.text
    return response.json()


def _audit(paths: DataPaths) -> list[tuple[str, str, int]]:
    with closing(sqlite3.connect(paths.db_file)) as conn:
        return conn.execute(
            "SELECT action, target, ok FROM audit_log WHERE action LIKE 'hosting.tunnel%' "
            "ORDER BY id"
        ).fetchall()


async def test_tunnel_opens_and_closes(paths: DataPaths, ports: HostingPorts, fake: Fake) -> None:
    async with serve_app(paths) as served, served.client() as client:
        assert (await _site(client, "sayt"))["public_url"] is None
        status = (await client.get(f"{API}/status")).json()
        assert (status["cloudflared"], status["tunnels"]) == ("available", 0)

        opened = await _post(client, "/tunnel/open", name="sayt")
        assert opened.status_code == 200, opened.text
        assert opened.json()["public_url"] == PUBLIC_URL
        # cloudflared mahalliy Caddy'ga ulanadi va loyihani Host sarlavhasi bilan tanlaydi.
        argv = fake.calls()[0]["argv"]
        assert argv[:2] == ["tunnel", "--no-autoupdate"]
        assert argv[argv.index("--url") + 1] == f"http://127.0.0.1:{ports.listen}"
        assert argv[argv.index("--http-host-header") + 1] == "sayt.localhost"

        # Qayta ochish — o'sha tunnel, yangi jarayon emas.
        again = await _post(client, "/tunnel/open", name="sayt")
        assert again.json()["public_url"] == PUBLIC_URL
        assert len(fake.calls()) == 1
        status = (await client.get(f"{API}/status")).json()
        assert status["tunnels"] == 1
        assert status["tunnel_memory"] > 0

        # Chegara: bir vaqtda bitta (tunnel_max = 1).
        await _site(client, "ikkinchi")
        limited = await _post(client, "/tunnel/open", name="ikkinchi")
        assert limited.status_code == 409
        assert "ko'pi bilan 1" in limited.json()["detail"]

        closed = await _post(client, "/tunnel/close", name="sayt")
        assert closed.status_code == 200
        assert closed.json()["public_url"] is None
        assert fake.alive() == []
        assert (await _post(client, "/tunnel/close", name="sayt")).status_code == 409
        assert "internetga ochildi" in "\n".join(
            (await client.get(f"{API}/log", params={"name": "sayt"})).json()
        )
    assert _audit(paths) == [
        ("hosting.tunnel_open", "sayt", 1),
        ("hosting.tunnel_open", "ikkinchi", 0),
        ("hosting.tunnel_close", "sayt", 1),
    ]


async def test_stopping_or_removing_project_closes_tunnel(
    paths: DataPaths, ports: HostingPorts, fake: Fake
) -> None:
    async with serve_app(paths) as served, served.client() as client:
        await _site(client, "sayt")
        assert (await _post(client, "/tunnel/open", name="sayt")).status_code == 200
        stopped = await _post(client, "/stop", name="sayt")
        assert stopped.json()["public_url"] is None
        assert fake.alive() == []

        # To'xtatilgan loyiha ochilmaydi; yo'q loyiha — 404.
        refused = await _post(client, "/tunnel/open", name="sayt")
        assert refused.status_code == 409
        assert "avval loyihani ishga tushiring" in refused.json()["detail"]
        assert (await _post(client, "/tunnel/open", name="yoq")).status_code == 404
        assert len(fake.calls()) == 1

        await _post(client, "/start", name="sayt")
        assert (await _post(client, "/tunnel/open", name="sayt")).status_code == 200
        assert len(fake.alive()) == 1
        assert (await _post(client, "/remove", name="sayt")).status_code == 200
        assert fake.alive() == []


async def test_tunnel_dies_with_plugin(paths: DataPaths, ports: HostingPorts, fake: Fake) -> None:
    async with serve_app(paths) as served, served.client() as client:
        await _site(client, "sayt")
        assert (await _post(client, "/tunnel/open", name="sayt")).status_code == 200
        assert len(fake.alive()) == 1
        await client.post("/api/v1/plugins/hosting/disable")
        assert fake.alive() == []
        # Tunnel saqlanmaydi: plagin qayta yoqilganda yopiq.
        await client.post("/api/v1/plugins/hosting/enable")
        rows = (await client.get(f"{API}/projects")).json()
        assert [row["public_url"] for row in rows] == [None]
        assert len(fake.calls()) == 1


@pytest.mark.parametrize(
    ("mode", "expected"),
    [("die", "cloudflared darhol tugadi"), ("silent", "manzil 3 s ichida kelmadi")],
)
async def test_tunnel_failure_is_reported(
    paths: DataPaths, ports: HostingPorts, fake: Fake, mode: str, expected: str
) -> None:
    fake.mode(mode)
    async with serve_app(paths) as served, served.client() as client:
        await _site(client, "sayt")
        async with httpx.AsyncClient(
            base_url=served.http_url, headers=served.headers, timeout=20
        ) as slow:
            failed = await _post(slow, "/tunnel/open", name="sayt")
        assert failed.status_code == 502
        assert expected in failed.json()["detail"]
        if mode == "die":
            assert "sinov xatosi" in failed.json()["detail"]
        assert fake.alive() == []
        assert (await client.get(f"{API}/status")).json()["tunnels"] == 0
        # Loyihaning o'zi ishlayveradi.
        site = await client.get(ports.site_url(), headers=ports.host_header("sayt"))
        assert site.status_code == 200
    assert _audit(paths) == [("hosting.tunnel_open", "sayt", 0)]


async def test_missing_cloudflared_is_reported(
    paths: DataPaths, plugin_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SRV1_CADDY_EXE", str(CADDY_EXE))
    monkeypatch.setenv("SRV1_CLOUDFLARED_EXE", str(tmp_path / "yoq" / "cloudflared.exe"))
    install_hosting(plugin_root, paths.plugin_data_dir("hosting"))
    async with serve_app(paths) as served, served.client() as client:
        await _site(client, "sayt")
        assert (await client.get(f"{API}/status")).json()["cloudflared"] == "missing"
        missing = await _post(client, "/tunnel/open", name="sayt")
        assert missing.status_code == 503
        assert "cloudflared.exe topilmadi" in missing.json()["detail"]


@pytest.mark.skipif(not REAL_CLOUDFLARED.is_file(), reason="tools/cloudflared.exe yo'q")
def test_real_cloudflared_accepts_our_flags() -> None:
    """Haqiqiy cloudflared ishga tushadi va biz beradigan bayroqlarni biladi (tunnel ochilmaydi)."""
    version = subprocess.run(
        [str(REAL_CLOUDFLARED), "--version"], capture_output=True, text=True, timeout=30, check=True
    )
    assert "cloudflared version" in version.stdout
    usage = subprocess.run(
        [str(REAL_CLOUDFLARED), "tunnel", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout
    for flag in ("--url", "--http-host-header", "--no-autoupdate"):
        assert flag in usage, flag
