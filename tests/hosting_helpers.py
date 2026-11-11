"""`hosting` plagini testlari uchun: plaginni bo'sh portlar bilan o'rnatish va namunaviy ilova."""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest

from conftest import free_port
from srv1_core.plugins.registry import BUILTIN_DIR

CADDY_EXE = BUILTIN_DIR.parent / "tools" / "caddy.exe"

# Kichik HTTP ilova: PORT'da tinglaydi, so'rovni aks ettiradi, sinov uchun yiqila oladi.
APP_PY = """
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

hoard = []


class Handler(BaseHTTPRequestHandler):
    def _send(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/die":
            os._exit(7)
        if self.path == "/eat":
            try:
                hoard.append(bytearray(400 * 1024 * 1024))
            except MemoryError:
                os._exit(9)
        self._send({"pid": os.getpid(), "path": self.path, "host": self.headers.get("Host")})

    def do_POST(self):
        size = int(self.headers.get("Content-Length", 0))
        self._send({"echo": self.rfile.read(size).decode(), "pid": os.getpid()})

    def log_message(self, *args):
        pass


print("ilova tayyor, port", os.environ["PORT"], flush=True)
ThreadingHTTPServer(("127.0.0.1", int(os.environ["PORT"])), Handler).serve_forever()
"""

SERVER_JS = """
const http = require("http");
const port = Number(process.env.PORT);
console.log("node ilova tayyor, port", port);
http.createServer((req, res) => {
  res.writeHead(200, {"Content-Type": "application/json"});
  res.end(JSON.stringify({runtime: "node", pid: process.pid, path: req.url}));
}).listen(port, "127.0.0.1");
"""


@dataclass(frozen=True)
class HostingPorts:
    listen: int
    admin: int
    wake: int
    first: int
    last: int

    def site_url(self, path: str = "/") -> str:
        return f"http://127.0.0.1:{self.listen}{path}"

    def host_header(self, name: str) -> dict[str, str]:
        return {"Host": f"{name}.localhost:{self.listen}"}


def install_hosting(
    plugin_root: Path, plugin_data_dir: Path, *, projects: int = 6, **config: object
) -> HostingPorts:
    """Plaginni `plugin_root` ga nusxalaydi (portlar ochiq) va sozlamasini yozadi."""
    if not CADDY_EXE.is_file():
        pytest.skip(f"caddy.exe yo'q: {CADDY_EXE}")
    target = plugin_root / "hosting"
    shutil.copytree(BUILTIN_DIR / "hosting", target, ignore=shutil.ignore_patterns("__pycache__"))
    manifest = target / "plugin.toml"
    text = manifest.read_text(encoding="utf-8")
    allowed = 'ports = [2019, 8080, "9000-9099"]'
    assert allowed in text
    manifest.write_text(text.replace(allowed, 'ports = ["1024-65535"]'), encoding="utf-8")

    first = free_port()
    ports = HostingPorts(
        listen=free_port(),
        admin=free_port(),
        wake=free_port(),
        first=first,
        last=first + projects - 1,
    )
    settings = {
        "listen_port": ports.listen,
        "admin_port": ports.admin,
        "wake_port": ports.wake,
        "port_first": ports.first,
        "port_last": ports.last,
        "idle_check_s": 0.2,
        "ready_timeout_s": 15,
        **config,
    }
    plugin_data_dir.mkdir(parents=True, exist_ok=True)
    (plugin_data_dir / "hosting.json").write_text(
        json.dumps({"config": settings, "projects": []}), encoding="utf-8"
    )
    return ports


def write_app(projects_dir: Path, name: str, *, node: bool = False) -> Path:
    directory = projects_dir / name
    directory.mkdir(parents=True, exist_ok=True)
    if node:
        (directory / "server.js").write_text(SERVER_JS, encoding="utf-8")
    else:
        (directory / "app.py").write_text(APP_PY, encoding="utf-8")
    return directory
