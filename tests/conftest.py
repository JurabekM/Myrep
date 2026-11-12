"""Umumiy fixture'lar: vaqtinchalik ma'lumotlar papkasi, toza muhit, jarayon ichidagi server."""

import asyncio
import json
import os
import socket
import textwrap
from collections.abc import AsyncGenerator, Callable, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi import FastAPI

from srv1_core.app import create_app
from srv1_core.log_setup import shutdown_logging
from srv1_core.paths import DataPaths
from srv1_core.state import CoreState, get_core_from_app

# Qt oynalari ekranga chiqmasin; QApplication yaratilishidan oldin o'rnatilishi shart.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Tashqi `SRV1_*` o'zgaruvchilari testga ta'sir qilmasin; log fayli yopilsin."""
    for name in [key for key in os.environ if key.startswith("SRV1_")]:
        monkeypatch.delenv(name)
    # Namuna plagin yadro testlariga aralashmasin; plagin testlari o'zi yoqadi.
    monkeypatch.setenv("SRV1_PLUGINS__LOAD_BUILTIN", "false")
    yield
    shutdown_logging()


@pytest.fixture
def paths(tmp_path: Path) -> DataPaths:
    data = DataPaths(tmp_path / "data")
    data.ensure()
    return data


@dataclass(frozen=True)
class Served:
    """Test bilan bitta event loop'da ishlayotgan haqiqiy uvicorn serveri."""

    app: FastAPI
    port: int
    token: str

    @property
    def core(self) -> CoreState:
        return get_core_from_app(self.app)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    @property
    def http_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def ws_url(self, query: str = "") -> str:
        return f"ws://127.0.0.1:{self.port}/ws/events{query}"

    def client(self, *, authorized: bool = True) -> httpx.AsyncClient:
        headers = self.headers if authorized else {}
        return httpx.AsyncClient(base_url=self.http_url, headers=headers, timeout=5.0)


async def until(condition: Callable[[], bool], timeout_s: float = 5.0) -> None:
    async with asyncio.timeout(timeout_s):
        while not condition():
            await asyncio.sleep(0.01)


def write_plugin(root: Path, name: str, code: str, manifest: str = "") -> Path:
    """`root/name` da plagin yaratadi. `manifest` — `plugin.toml` ga qo'shimcha qatorlar."""
    directory = root / name
    directory.mkdir(parents=True)
    lines = [f'name = "{name}"', 'version = "1.0.0"', textwrap.dedent(manifest)]
    toml = "\n".join(lines)
    (directory / "plugin.toml").write_text(toml, encoding="utf-8")
    (directory / "__init__.py").write_text(textwrap.dedent(code), encoding="utf-8")
    return directory


@pytest.fixture
def plugin_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Bo'sh plagin papkasi; yadro uni `plugins.dirs` orqali ko'radi."""
    root = tmp_path / "plugin-root"
    root.mkdir()
    monkeypatch.setenv("SRV1_PLUGINS__DIRS", json.dumps([str(root)]))
    return root


@asynccontextmanager
async def serve_app(paths: DataPaths) -> AsyncGenerator[Served]:
    app = create_app(paths)
    port = free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None, access_log=False)
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    try:
        async with asyncio.timeout(10):
            while not server.started:
                if task.done():
                    task.result()
                await asyncio.sleep(0.01)
        token = paths.token_file.read_text(encoding="ascii").strip()
        yield Served(app=app, port=port, token=token)
    finally:
        server.should_exit = True
        await task


@pytest.fixture
async def served(paths: DataPaths) -> AsyncGenerator[Served]:
    async with serve_app(paths) as running:
        yield running
