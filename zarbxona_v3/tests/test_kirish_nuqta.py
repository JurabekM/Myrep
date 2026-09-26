"""T14 — kirish nuqtalari uchalasi va `--selftest` (subprocess bilan)."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from conftest import ILDIZ
from core.konstanta import VERSIYA

BUYRUQLAR = [
    [sys.executable, "run.py"],
    [sys.executable, "-m", "app.main"],
    [sys.executable, os.path.join("app", "main.py")],
]


def _ishga(buyruq, *arg):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "QT_QPA_PLATFORM": "offscreen"}
    return subprocess.run([*buyruq, *arg], cwd=ILDIZ, capture_output=True, text=True,
                          encoding="utf-8", timeout=120, env=env)


@pytest.mark.parametrize("buyruq", BUYRUQLAR, ids=["run.py", "-m app.main", "app/main.py"])
def test_version(buyruq):
    r = _ishga(buyruq, "--version")
    assert r.returncode == 0, r.stderr
    assert VERSIYA in r.stdout


@pytest.mark.parametrize("buyruq", BUYRUQLAR, ids=["run.py", "-m app.main", "app/main.py"])
def test_selftest(buyruq):
    natija = ILDIZ / "selftest_natija.txt"
    natija.unlink(missing_ok=True)
    r = _ishga(buyruq, "--selftest")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "NATIJA: MUVAFFAQIYATLI" in r.stdout
    assert "TOZA" in r.stdout
    matn = natija.read_text(encoding="utf-8")
    assert "NATIJA: MUVAFFAQIYATLI" in matn and "o'z-o'zi imzolagan" in matn
    natija.unlink()


def test_selftest_qt_import_qilmaydi():
    kod = ("import sys; sys.argv=['x','--selftest']; sys.path.insert(0,'.');"
           "from app.main import main; r=main(); "
           "assert 'PySide6' not in sys.modules, 'Qt yuklandi'; raise SystemExit(r)")
    r = subprocess.run([sys.executable, "-c", kod], cwd=ILDIZ, capture_output=True, text=True,
                       encoding="utf-8", timeout=120,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, r.stdout + r.stderr
    (ILDIZ / "selftest_natija.txt").unlink(missing_ok=True)
