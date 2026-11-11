"""Haqiqiy jarayon sinovi: `python -m srv1_core` + HTTP + WebSocket (uvicorn orqali)."""

import json
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
from websockets.exceptions import InvalidStatus
from websockets.sync.client import connect

from conftest import free_port

STARTUP_TIMEOUT_S = 20.0


@dataclass(frozen=True)
class LiveServer:
    port: int
    token: str

    @property
    def http(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def ws(self) -> str:
        return f"ws://127.0.0.1:{self.port}/ws/events"

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


def _wait_healthy(url: str, process: subprocess.Popen[bytes], stderr_file: Path) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_S
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            if httpx.get(f"{url}/api/v1/health", timeout=1.0).status_code == 200:
                return
        except httpx.HTTPError:
            time.sleep(0.1)
    process.kill()
    pytest.fail(
        f"yadro ishga tushmadi:\n{stderr_file.read_text(encoding='utf-8', errors='replace')}"
    )


@pytest.fixture(scope="module")
def live(tmp_path_factory: pytest.TempPathFactory) -> Iterator[LiveServer]:
    data_dir = tmp_path_factory.mktemp("live-data")
    stderr_file = data_dir / "stderr.txt"
    port = free_port()
    env = {key: value for key, value in os.environ.items() if not key.startswith("SRV1_")}
    env |= {
        "SRV1_DATA_DIR": str(data_dir),
        "SRV1_SERVER__PORT": str(port),
        "SRV1_EVENTS__STATS_INTERVAL_S": "0.5",
        "SRV1_PLUGINS__LOAD_BUILTIN": "false",
    }
    with stderr_file.open("wb") as stderr:
        process = subprocess.Popen([sys.executable, "-m", "srv1_core"], env=env, stderr=stderr)
        try:
            _wait_healthy(f"http://127.0.0.1:{port}", process, stderr_file)
            token = (data_dir / "auth.token").read_text(encoding="ascii").strip()
            yield LiveServer(port=port, token=token)
        finally:
            process.kill()
            process.wait(timeout=10)


def test_live_http(live: LiveServer) -> None:
    assert httpx.get(f"{live.http}/api/v1/system").status_code == 401
    response = httpx.get(f"{live.http}/api/v1/system", headers=live.headers)
    assert response.status_code == 200
    assert response.json()["process"]["pid"] != os.getpid()
    assert "server" not in response.headers


def test_live_ws_receives_system_stats(live: LiveServer) -> None:
    with connect(f"{live.ws}?topics=system.*", additional_headers=live.headers) as ws:
        message = json.loads(ws.recv(timeout=10))
    assert message["topic"] == "system.stats"
    assert message["data"]["memory"]["total"] > 0


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer " + "x" * 43}])
def test_live_ws_rejects_bad_token(live: LiveServer, headers: dict[str, str]) -> None:
    with pytest.raises(InvalidStatus) as excinfo, connect(live.ws, additional_headers=headers):
        pass
    assert excinfo.value.response.status_code == 403


def test_live_only_listens_on_loopback(live: LiveServer) -> None:
    import psutil

    listeners = [
        conn.laddr.ip
        for conn in psutil.net_connections(kind="tcp")
        if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port == live.port
    ]
    assert listeners == ["127.0.0.1"]
