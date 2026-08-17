"""The application must start every way a user is likely to launch it.

A direct `python app/main.py` puts `app/` on ``sys.path`` instead of the project
root, which used to raise ``ModuleNotFoundError: No module named 'app'``. These
tests run each entry point in a real subprocess and fail on any import error.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: Every documented way of starting the application.
ENTRY_POINTS: list[list[str]] = [
    [sys.executable, "run.py"],
    [sys.executable, "-m", "app.main"],
    [sys.executable, str(Path("app") / "main.py")],
]


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Start the GUI headless and stop it as soon as it is up."""
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    # The window never closes on its own, so give it a moment and then kill it.
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        output, _ = process.communicate(timeout=25)
        return subprocess.CompletedProcess(command, process.returncode, output, "")
    except subprocess.TimeoutExpired:
        # Still running after startup: that is the success case for a GUI.
        process.kill()
        output, _ = process.communicate()
        return subprocess.CompletedProcess(command, 0, output, "")


@pytest.mark.parametrize("command", ENTRY_POINTS, ids=lambda c: " ".join(c[1:]))
def test_entry_point_starts(command: list[str]) -> None:
    result = _run(command, ROOT)
    assert "ModuleNotFoundError" not in result.stdout, result.stdout
    assert "Traceback" not in result.stdout, result.stdout
    assert result.returncode == 0, result.stdout


def test_entry_point_starts_from_another_directory(tmp_path: Path) -> None:
    """`python <abs path>/run.py` must work with any working directory."""
    result = _run([sys.executable, str(ROOT / "run.py")], tmp_path)
    assert "ModuleNotFoundError" not in result.stdout, result.stdout
    assert result.returncode == 0, result.stdout
