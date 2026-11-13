"""SDK: jarayon ishga tushirish (`ctx.spawn`), `projects` ruxsati va `log` vidjeti."""

import asyncio
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import psutil
import pytest

from srv1_sdk.context import LogLevel, PluginContext
from srv1_sdk.manifest import PluginManifest
from srv1_sdk.panel import LogWidget, PanelSpec
from srv1_sdk.types import PermissionDenied

PYTHON: str = getattr(sys, "_base_executable", sys.executable)


class _Backend:
    def __init__(self) -> None:
        self.audits: list[tuple[str, str, bool, Mapping[str, Any]]] = []
        self.denied: list[str] = []

    def publish(self, topic: str, data: Mapping[str, Any]) -> None:
        return None

    async def audit(self, action: str, target: str, ok: bool, detail: Mapping[str, Any]) -> None:
        self.audits.append((action, target, ok, detail))

    def log(self, level: LogLevel, event: str, fields: Mapping[str, Any]) -> None:
        if event == "permission_denied":
            self.denied.append(str(fields["kind"]))


def _context(tmp_path: Path, **permissions: object) -> tuple[PluginContext, _Backend]:
    manifest = PluginManifest.model_validate(
        {"name": "demo", "version": "1.0.0", "permissions": permissions}
    )
    data_dir, projects_dir = tmp_path / "data", tmp_path / "projects"
    data_dir.mkdir(parents=True)
    projects_dir.mkdir(parents=True)
    backend = _Backend()
    return PluginContext(manifest, data_dir, backend, projects_dir), backend


def test_new_permissions_default_to_off() -> None:
    manifest = PluginManifest.model_validate({"name": "demo", "version": "1.0.0"})
    assert (manifest.permissions.spawn, manifest.permissions.projects) == (False, False)


def test_projects_dir_needs_permission(tmp_path: Path) -> None:
    denied, backend = _context(tmp_path)
    with pytest.raises(PermissionDenied):
        _ = denied.projects_dir
    with pytest.raises(PermissionDenied):
        denied.resolve_path(tmp_path / "projects" / "sayt" / "index.html")
    assert backend.denied == ["projects", "path"]

    allowed, _ = _context(tmp_path / "ikkinchi", projects=True)
    assert allowed.projects_dir == tmp_path / "ikkinchi" / "projects"
    inside = allowed.projects_dir / "sayt" / "index.html"
    assert allowed.resolve_path(inside) == inside.resolve()
    with pytest.raises(PermissionDenied):
        allowed.resolve_path(allowed.projects_dir / ".." / "boshqa.txt")


async def test_spawn_needs_permission_and_allowed_cwd(tmp_path: Path) -> None:
    lines: list[str] = []
    denied, backend = _context(tmp_path)
    with pytest.raises(PermissionDenied):
        await denied.spawn(
            [PYTHON, "-V"], cwd=denied.data_dir, env={}, memory_limit_mb=64, on_line=lines.append
        )
    assert (backend.denied, backend.audits) == (["spawn"], [])

    allowed, backend = _context(tmp_path / "ikkinchi", spawn=True)
    with pytest.raises(PermissionDenied):
        await allowed.spawn(
            [PYTHON, "-V"], cwd=tmp_path, env={}, memory_limit_mb=64, on_line=lines.append
        )
    assert backend.audits == []


async def test_spawn_runs_in_job_captures_output_and_audits(tmp_path: Path) -> None:
    ctx, backend = _context(tmp_path, spawn=True)
    lines: list[str] = []
    code = "import os, sys; print('salom', os.getcwd()); print('xato', file=sys.stderr)"
    process = await ctx.spawn(
        [PYTHON, "-c", code],
        cwd=ctx.data_dir,
        env={"SYSTEMROOT": "C:\\Windows"},
        memory_limit_mb=128,
        on_line=lines.append,
    )
    assert await process.wait() == 0
    await process.stop()
    # stdout va stderr bitta oqimga qo'shiladi; ular orasidagi tartib kafolatlanmagan
    assert sorted(lines) == sorted([f"salom {ctx.data_dir}", "xato"])
    action, target, ok, detail = backend.audits[0]
    assert (action, target, ok) == ("process.spawn", PYTHON, True)
    assert detail["argv"] == [PYTHON, "-c", code]
    assert detail["limit_mb"] == 128
    assert isinstance(detail["pid"], int)


async def test_stop_kills_whole_process_tree(tmp_path: Path) -> None:
    """Bola o'zi yana jarayon tug'dirsa ham, `stop()` hammasini o'ldiradi (job yopiladi)."""
    ctx, _ = _context(tmp_path, spawn=True)
    lines: list[str] = []
    child = "import time; time.sleep(60)"
    parent = (
        "import subprocess, sys, time; "
        f"p = subprocess.Popen([sys.executable, '-c', {child!r}]); "
        "print(p.pid, flush=True); time.sleep(60)"
    )
    process = await ctx.spawn(
        [PYTHON, "-c", parent],
        cwd=ctx.data_dir,
        env={"SYSTEMROOT": "C:\\Windows"},
        memory_limit_mb=128,
        on_line=lines.append,
    )
    async with asyncio.timeout(10):
        while not lines:
            await asyncio.sleep(0.05)
    parent_pid, grandchild_pid = process.pid, int(lines[0])
    assert parent_pid is not None
    assert psutil.pid_exists(grandchild_pid)
    assert process.memory_bytes() > psutil.Process(parent_pid).memory_info().rss

    await process.stop()
    async with asyncio.timeout(5):
        while psutil.pid_exists(grandchild_pid) or psutil.pid_exists(parent_pid):
            await asyncio.sleep(0.05)
    assert not process.running


async def test_spawn_failure_is_audited(tmp_path: Path) -> None:
    ctx, backend = _context(tmp_path, spawn=True)
    with pytest.raises(OSError):
        await ctx.spawn(
            [str(tmp_path / "yoq.exe")],
            cwd=ctx.data_dir,
            env={},
            memory_limit_mb=64,
            on_line=lambda _line: None,
        )
    assert [(action, ok) for action, _target, ok, _detail in backend.audits] == [
        ("process.spawn", False)
    ]


def test_log_widget_in_panel() -> None:
    panel = PanelSpec.model_validate(
        {
            "title": "T",
            "widgets": [
                {
                    "type": "log",
                    "label": {"uz": "Jurnal", "ru": "Журнал", "en": "Log"},
                    "source": "/log",
                    "filters": [{"name": "name", "label": "Nom"}],
                }
            ],
        }
    )
    widget = panel.widgets[0]
    assert isinstance(widget, LogWidget)
    assert (widget.refresh_s, widget.filters[0].required) == (3.0, True)
    with pytest.raises(ValueError, match="source"):
        PanelSpec.model_validate(
            {"title": "T", "widgets": [{"type": "log", "label": "L", "source": "http://x/log"}]}
        )
