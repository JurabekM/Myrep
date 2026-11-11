"""Umumiy fixture'lar: vaqtinchalik ma'lumotlar papkasi, toza muhit, jarayon ichidagi server."""

import asyncio
import os
import socket
from collections.abc import AsyncGenerator, Iterator
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


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Tashqi `SRV1_*` o'zgaruvchilari testga ta'sir qilmasin; log fayli yopilsin."""
    for name in [key for key in os.environ if key.startswith("SRV1_")]:
        monkeypatch.delenv(name)
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


@pytest.fixture
async def served(paths: DataPaths) -> AsyncGenerator[Served]:
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
