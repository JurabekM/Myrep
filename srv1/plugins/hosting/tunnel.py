"""cloudflared tezkor tunneli: loyihani vaqtincha internetga ochadi.

Akkauntsiz «quick tunnel»: cloudflared Cloudflare'ga chiquvchi ulanish ochadi va
tasodifiy `https://<so'zlar>.trycloudflare.com` manzilini beradi. Mashinada
hech qanday port tashqariga ochilmaydi. Tunnel saqlanmaydi: yadro qayta ishga
tushsa, hamma tunnel yopiq bo'ladi.
"""

import asyncio
import os
import re
import time
from collections import deque
from pathlib import Path

from srv1_sdk.context import PluginContext
from srv1_sdk.process import ManagedProcess

from .models import HostingConfig, HostingError

ENV_CLOUDFLARED_EXE = "SRV1_CLOUDFLARED_EXE"
TUNNEL_MEMORY_LIMIT_MB = 192
_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
_TAIL_LINES = 40


def find_cloudflared() -> Path:
    """`SRV1_CLOUDFLARED_EXE` yoki repozitoriydagi `tools/cloudflared.exe`."""
    override = os.environ.get(ENV_CLOUDFLARED_EXE, "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "tools" / "cloudflared.exe"


def tunnel_command(prefix: tuple[str, ...], origin: str, host: str) -> list[str]:
    """`host` — Caddy loyihani shu Host sarlavhasi bo'yicha topadi."""
    return [
        *prefix,
        "tunnel",
        "--no-autoupdate",
        "--url",
        origin,
        "--http-host-header",
        host,
    ]


class Tunnel:
    """Bitta loyihaning ishlab turgan tunneli."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.url: str | None = None
        self.started = time.time()
        self.process: ManagedProcess | None = None
        self.lines: deque[str] = deque(maxlen=_TAIL_LINES)
        self.ready = asyncio.Event()

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.running

    def on_line(self, line: str) -> None:
        self.lines.append(line[:300])
        if self.url is None:
            found = _URL.search(line)
            if found is not None:
                self.url = found.group(0)
                self.ready.set()

    def tail(self, count: int = 3) -> str:
        return " | ".join(list(self.lines)[-count:])


class TunnelManager:
    def __init__(self, ctx: PluginContext, cfg: HostingConfig) -> None:
        self._ctx = ctx
        self._cfg = cfg
        self._tunnels: dict[str, Tunnel] = {}
        self._lock = asyncio.Lock()
        self.exe = find_cloudflared()

    @property
    def available(self) -> bool:
        return bool(self._cfg.tunnel_command) or self.exe.is_file()

    def _prefix(self) -> tuple[str, ...]:
        return self._cfg.tunnel_command or (str(self.exe),)

    def get(self, name: str) -> Tunnel | None:
        """Tirik tunnel; cloudflared o'zi tugagan bo'lsa — yo'q."""
        tunnel = self._tunnels.get(name)
        if tunnel is not None and not tunnel.running:
            del self._tunnels[name]
            return None
        return tunnel

    def url_of(self, name: str) -> str | None:
        tunnel = self.get(name)
        return tunnel.url if tunnel is not None else None

    def active(self) -> list[Tunnel]:
        return [tunnel for name in list(self._tunnels) if (tunnel := self.get(name)) is not None]

    def memory_bytes(self) -> int:
        return sum(t.process.memory_bytes() for t in self.active() if t.process is not None)

    async def open(self, name: str, origin: str, host: str) -> Tunnel:
        async with self._lock:
            existing = self.get(name)
            if existing is not None:
                return existing
            if not self.available:
                raise HostingError(503, f"cloudflared.exe topilmadi: {self.exe}")
            if len(self.active()) >= self._cfg.tunnel_max:
                raise HostingError(
                    409, f"bir vaqtda ko'pi bilan {self._cfg.tunnel_max} ta tunnel ochiladi"
                )
            return await self._start(name, origin, host)

    async def _start(self, name: str, origin: str, host: str) -> Tunnel:
        tunnel = Tunnel(name)
        env = {k: v for k, v in os.environ.items() if not k.startswith(("SRV1_", "TUNNEL_"))}
        try:
            tunnel.process = await self._ctx.spawn(
                tunnel_command(self._prefix(), origin, host),
                cwd=self._ctx.data_dir,
                env=env,
                memory_limit_mb=TUNNEL_MEMORY_LIMIT_MB,
                on_line=tunnel.on_line,
            )
        except OSError as exc:
            raise HostingError(500, f"cloudflared ishga tushmadi: {exc}") from exc
        if not await self._wait_url(tunnel):
            reason = (
                f"manzil {self._cfg.tunnel_timeout_s:g} s ichida kelmadi"
                if tunnel.running
                else "cloudflared darhol tugadi"
            )
            await tunnel.process.stop()
            raise HostingError(502, f"tunnel ochilmadi: {reason}. {tunnel.tail()}".strip())
        self._tunnels[name] = tunnel
        return tunnel

    async def _wait_url(self, tunnel: Tunnel) -> bool:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._cfg.tunnel_timeout_s
        while loop.time() < deadline and tunnel.running:
            try:
                await asyncio.wait_for(tunnel.ready.wait(), 0.2)
            except TimeoutError:
                continue
            return True
        return tunnel.ready.is_set() and tunnel.running

    async def close(self, name: str) -> bool:
        async with self._lock:
            tunnel = self._tunnels.pop(name, None)
        if tunnel is None or tunnel.process is None:
            return False
        await tunnel.process.stop()
        return True

    async def close_all(self) -> None:
        for name in list(self._tunnels):
            await self.close(name)
