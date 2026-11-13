"""Dashboard data layer and (if PyQt6 is installed) offscreen rendering."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os

import pytest

from qoravul.dashboard.data import load
from qoravul.sim.run import run_fleet
from qoravul.tinyml.model import QuantAE

from .test_edge import MODEL_PATH


@pytest.fixture(scope="module")
def export(tmp_path_factory):
    d = tmp_path_factory.mktemp("export")
    rep = asyncio.run(run_fleet(nodes=4, thieves=2, hours=3, seed=21, model=QuantAE.load(MODEL_PATH),
                                export_dir=d))
    assert rep["detected"] == 2
    return d


def test_dashboard_data(export):
    data = load(export)
    assert len(data.nodes) == 4 and len(data.rows) == 2 and data.chain_ok
    assert all(r.sig_ok for r in data.rows) and data.sig_failures == 0
    assert {i.node for i in data.incidents} == {r.node for r in data.rows}
    assert len(data.kwh_slots) == 3 * 60 // 15 and data.total_kwh > 0
    assert abs(sum(sum(v) for v in data.kwh_node.values()) - data.total_kwh) < 1e-9


def test_dashboard_flags_tampering(export, tmp_path):
    for name in ("nodes.json", "summaries.json", "ledger.jsonl"):
        (tmp_path / name).write_bytes((export / name).read_bytes())
    lines = (tmp_path / "ledger.jsonl").read_text().splitlines()
    e = json.loads(lines[0])
    e["record"]["evidence"] = e["record"]["evidence"].replace('"score":', '"score":1')
    (tmp_path / "ledger.jsonl").write_text("\n".join([json.dumps(e)] + lines[1:]) + "\n")
    data = load(tmp_path)
    assert not data.chain_ok and data.sig_failures == 1


@pytest.mark.skipif(importlib.util.find_spec("PyQt6") is None or importlib.util.find_spec("pyqtgraph") is None,
                    reason="PyQt6 / pyqtgraph not installed")
def test_dashboard_renders_offscreen(export, tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError as e:  # e.g. missing libEGL on a headless box
        pytest.skip(str(e))
    from qoravul.dashboard.app import build_window

    app = QApplication.instance() or QApplication([])
    win = build_window(load(export), "uz")
    win.show()
    app.processEvents()
    assert win.table.rowCount() == 2 and win.inc_table.rowCount() == 2
    assert win.kpi_labels["ZANJIR"].text() == "BUTUN"
    win.toggle_lang()
    app.processEvents()
    assert win.kpi_labels["CHAIN"].text() == "INTACT"
    out = tmp_path / "shot.png"
    assert win.grab().save(str(out)) and out.stat().st_size > 10_000
    win.close()
