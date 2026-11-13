"""Xizmat to'xtashi: NSSM yadroga konsol orqali Ctrl+C yuboradi.

Bu test aynan o'sha usulni takrorlaydi (`AttachConsole` + `GenerateConsoleCtrlEvent`):
yadro o'z konsolida ishga tushadi, tashqi jarayon unga Ctrl+C yuboradi. Yadro
tartibli yopilishi, Caddy va loyiha jarayonlari qolmasligi kerak.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil
import pytest

from hosting_helpers import CADDY_EXE, install_hosting, write_app
from srv1_core.paths import DataPaths

API = "/api/v1/plugins/hosting/api"
# NSSM kabi: nishon konsoliga ulanib, o'zini himoyalab, Ctrl+C yuboradi.
SEND_CTRL_C = """
import ctypes
import sys
import time

kernel32 = ctypes.windll.kernel32
kernel32.FreeConsole()
if not kernel32.AttachConsole(int(sys.argv[1])):
    sys.exit(2)
kernel32.SetConsoleCtrlHandler(None, True)
if not kernel32.GenerateConsoleCtrlEvent(0, 0):
    sys.exit(3)
time.sleep(1)
"""


def _wait(condition: object, timeout_s: float, what: str) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if condition():  # type: ignore[operator]
            return
        time.sleep(0.1)
    pytest.fail(f"{what}: {timeout_s:g} s ichida yuz bermadi")


def _healthy(url: str) -> bool:
    try:
        return httpx.get(f"{url}/api/v1/health", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False


def test_console_ctrl_c_stops_core_and_children(
    paths: DataPaths, plugin_root: Path, tmp_path: Path
) -> None:
    from conftest import free_port

    install_hosting(plugin_root, paths.plugin_data_dir("hosting"))
    write_app(paths.projects_dir, "ilova")
    port = free_port()
    env = {key: value for key, value in os.environ.items() if not key.startswith("SRV1_")}
    env |= {
        "SRV1_DATA_DIR": str(paths.root),
        "SRV1_SERVER__PORT": str(port),
        "SRV1_PLUGINS__LOAD_BUILTIN": "false",
        "SRV1_PLUGINS__DIRS": json.dumps([str(plugin_root)]),
        "SRV1_CADDY_EXE": str(CADDY_EXE),
    }
    hidden = subprocess.STARTUPINFO()
    hidden.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    hidden.wShowWindow = subprocess.SW_HIDE
    output = tmp_path / "core-output.txt"
    url = f"http://127.0.0.1:{port}"
    with output.open("wb") as sink:
        core = subprocess.Popen(
            [sys.executable, "-m", "srv1_core"],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=sink,
            stderr=sink,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            startupinfo=hidden,
        )
        try:
            _wait(lambda: _healthy(url), 30, "yadro ishga tushishi")
            token = paths.token_file.read_text(encoding="ascii").strip()
            with httpx.Client(
                base_url=url, headers={"Authorization": f"Bearer {token}"}, timeout=30
            ) as client:
                body = {"name": "ilova", "kind": "python", "command": "python app.py"}
                created = client.post(f"{API}/projects", json=body)
                assert created.status_code == 201, created.text
                caddy_pid = client.get(f"{API}/status").json()["caddy_pid"]
                project_pid = created.json()["pid"]
            assert psutil.pid_exists(caddy_pid)
            assert psutil.pid_exists(project_pid)

            sender = subprocess.run(
                [sys.executable, "-c", SEND_CTRL_C, str(core.pid)],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                startupinfo=hidden,
                timeout=30,
                check=False,
            )
            assert sender.returncode == 0, f"Ctrl+C yuborilmadi (kod {sender.returncode})"
            core.wait(timeout=20)  # NSSM 20 s kutadi (AppStopMethodConsole)
        finally:
            if core.poll() is None:
                for child in psutil.Process(core.pid).children(recursive=True):
                    child.kill()
                core.kill()
                core.wait(timeout=10)
    text = output.read_text(encoding="utf-8", errors="replace")
    assert "core_stopped" in text, text[-2000:]
    assert "Traceback" not in text, text[-2000:]
    assert core.returncode == 0
    _wait(
        lambda: not psutil.pid_exists(caddy_pid) and not psutil.pid_exists(project_pid),
        5,
        "Caddy va loyiha jarayonining tugashi",
    )
    assert not _healthy(url)
