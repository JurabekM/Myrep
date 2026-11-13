"""Caddy: jarayonni boshqarish, JSON konfiguratsiya va so'rovlar jurnalidan faollikni o'qish."""

import asyncio
import json
import os
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from srv1_sdk.context import PluginContext
from srv1_sdk.process import ManagedProcess

from .models import HostingConfig

ENV_CADDY_EXE = "SRV1_CADDY_EXE"
CADDY_MEMORY_LIMIT_MB = 256
ADMIN_READY_TIMEOUT_S = 15.0
_ACCESS_LOGGER = "http.log.access"

Route = dict[str, Any]


def find_caddy() -> Path:
    """`SRV1_CADDY_EXE` yoki repozitoriydagi `tools/caddy.exe`."""
    override = os.environ.get(ENV_CADDY_EXE, "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "tools" / "caddy.exe"


def static_route(host: str, root: Path) -> Route:
    return {
        "match": [{"host": [host]}],
        "handle": [{"handler": "file_server", "root": str(root)}],
        "terminal": True,
    }


# Loyiha ulanishni rad etsa (navbati to'lgan yoki endi ishga tushyapti), Caddy shu muddat
# ichida qayta ulanib ko'radi. Faqat ulanish o'rnatilmagan so'rov qayta yuboriladi, shuning
# uchun POST ikki marta bajarilib qolmaydi.
PROXY_TRY_DURATION = "2s"
PROXY_TRY_INTERVAL = "50ms"


def proxy_route(host: str, port: int) -> Route:
    proxy = {
        "handler": "reverse_proxy",
        "upstreams": [{"dial": f"127.0.0.1:{port}"}],
        "load_balancing": {
            "try_duration": PROXY_TRY_DURATION,
            "try_interval": PROXY_TRY_INTERVAL,
        },
    }
    return {"match": [{"host": [host]}], "handle": [proxy], "terminal": True}


def message_route(status: int, body: str, host: str | None = None) -> Route:
    route: Route = {
        "handle": [
            {
                "handler": "static_response",
                "status_code": status,
                "body": body,
                "headers": {"Content-Type": ["text/plain; charset=utf-8"]},
            }
        ],
        "terminal": True,
    }
    if host is not None:
        route["match"] = [{"host": [host]}]
    return route


def build_config(cfg: HostingConfig, routes: list[Route]) -> dict[str, Any]:
    fallback = message_route(404, "SRV_1: bunday loyiha yo'q yoki u to'xtatilgan.\n")
    return {
        "admin": {"listen": f"127.0.0.1:{cfg.admin_port}"},
        "logging": {
            "logs": {
                "default": {
                    "writer": {"output": "stderr"},
                    "encoder": {"format": "json"},
                    "level": "INFO",
                }
            }
        },
        "apps": {
            "http": {
                "http_port": cfg.listen_port,
                "servers": {
                    "srv1": {
                        "listen": [f"{cfg.listen_host}:{cfg.listen_port}"],
                        "routes": [*routes, fallback],
                        "automatic_https": {"disable": True},
                        "logs": {},
                    }
                },
            }
        },
    }


class Caddy:
    """`on_access(host)` — har so'rovda chaqiriladi (uxlatish hisobi uchun)."""

    def __init__(
        self, ctx: PluginContext, cfg: HostingConfig, on_access: Callable[[str], None]
    ) -> None:
        self._ctx = ctx
        self._cfg = cfg
        self._on_access = on_access
        self._process: ManagedProcess | None = None
        self.exe = find_caddy()
        self.recent: deque[str] = deque(maxlen=50)

    @property
    def available(self) -> bool:
        return self.exe.is_file()

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.running

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process is not None and self.running else None

    def memory_bytes(self) -> int:
        return self._process.memory_bytes() if self._process is not None else 0

    @property
    def _admin_url(self) -> str:
        return f"http://127.0.0.1:{self._cfg.admin_port}"

    async def start(self, routes: list[Route]) -> None:
        """Caddy'ni boshlang'ich marshrutlar bilan ishga tushiradi va admin API'ni kutadi."""
        config_file = self._ctx.data_path("caddy.json")
        state_dir = self._ctx.data_path("caddy")
        text = json.dumps(build_config(self._cfg, routes))
        await asyncio.to_thread(self._prepare, config_file, state_dir, text)
        env = {k: v for k, v in os.environ.items() if not k.startswith("SRV1_")}
        # Caddy o'z holatini foydalanuvchi profiliga emas, plagin papkasiga yozsin.
        env |= {"XDG_DATA_HOME": str(state_dir), "XDG_CONFIG_HOME": str(state_dir)}
        self._process = await self._ctx.spawn(
            [str(self.exe), "run", "--config", str(config_file)],
            cwd=self._ctx.data_dir,
            env=env,
            memory_limit_mb=CADDY_MEMORY_LIMIT_MB,
            on_line=self._on_line,
        )
        await self._wait_admin()

    @staticmethod
    def _prepare(config_file: Path, state_dir: Path, text: str) -> None:
        state_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text(text, encoding="utf-8")

    async def _wait_admin(self) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + ADMIN_READY_TIMEOUT_S
        async with httpx.AsyncClient(timeout=2.0) as client:
            while loop.time() < deadline:
                if not self.running:
                    break
                try:
                    if (await client.get(f"{self._admin_url}/config/")).status_code == 200:
                        return
                except httpx.HTTPError:
                    await asyncio.sleep(0.1)
        tail = " | ".join(list(self.recent)[-3:])
        await self.stop()
        raise RuntimeError(f"Caddy ishga tushmadi: {tail or 'admin API javob bermadi'}")

    async def load(self, routes: list[Route]) -> None:
        """Marshrutlarni to'liq almashtiradi (Caddy buni uzilishsiz bajaradi)."""
        if not self.running:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self._admin_url}/load", json=build_config(self._cfg, routes)
            )
        if response.status_code != 200:
            raise RuntimeError(f"Caddy konfiguratsiyani rad etdi: {response.text[:300]}")

    async def stop(self) -> None:
        process, self._process = self._process, None
        if process is not None:
            await process.stop()

    def _on_line(self, line: str) -> None:
        try:
            entry: dict[str, Any] = json.loads(line)
        except ValueError:
            self.recent.append(line[:300])
            return
        if str(entry.get("logger", "")).startswith(_ACCESS_LOGGER):
            request: dict[str, Any] = entry.get("request") or {}
            host = str(request.get("host", "")).split(":", 1)[0].lower()
            if host:
                self._on_access(host)
            return
        message = f"{entry.get('level', '')}: {entry.get('msg', '')}"
        self.recent.append(message[:300])
        if entry.get("level") in ("error", "fatal", "panic"):
            self._ctx.log("error", "caddy_error", message=str(entry.get("msg", ""))[:300])
