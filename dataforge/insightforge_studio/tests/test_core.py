from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from insightforge.core import Workspace
from insightforge.core import charts, importer, logs, ml, persistence, pipeline, profiling, reporting


@pytest.fixture
def frame() -> pd.DataFrame:
    rng = np.random.default_rng(10)
    n = 240
    return pd.DataFrame({
        "time": pd.date_range("2025-01-01", periods=n, freq="h"),
        "region": rng.choice(["north", "south", "west"], n),
        "sales": rng.normal(100, 20, n).round(2),
        "cost": rng.normal(65, 12, n).round(2),
        "orders": rng.integers(1, 8, n),
        "converted": rng.integers(0, 2, n),
        "message": [f"request {i} from 10.0.0.{i % 20} completed" for i in range(n)],
    })


def test_workspace_lifecycle(frame):
    workspace = Workspace(history_limit=3)
    dataset = workspace.add("sales", frame)
    assert workspace.active is dataset
    workspace.commit(dataset.id, frame.head(20), "head")
    assert len(workspace.active.frame) == 20
    workspace.undo(dataset.id)
    assert len(workspace.active.frame) == len(frame)
    workspace.redo(dataset.id)
    assert len(workspace.active.frame) == 20
    assert workspace.summary()["audit_events"] == 4


def test_workspace_unique_names(frame):
    workspace = Workspace()
    workspace.add("data", frame)
    assert workspace.add("data", frame).name == "data (2)"


def test_import_csv_and_json(tmp_path, frame):
    csv = tmp_path / "data.csv"
    frame.to_csv(csv, index=False)
    assert importer.load_file(csv).frame.shape == frame.shape
    result = importer.load_text(json.dumps([{"x": 1}, {"x": 2}]))
    assert result.frame["x"].tolist() == [1, 2]


def test_sqlite_readonly(tmp_path, frame):
    path = tmp_path / "data.sqlite"
    with sqlite3.connect(path) as connection:
        frame.head(12).to_sql("sales", connection, index=False)
    assert importer.sqlite_tables(path) == ["sales"]
    assert len(importer.load_sqlite(path).frame) == 12


def test_export_formats(tmp_path, frame):
    for suffix in ("csv", "json", "jsonl", "parquet", "xlsx", "html"):
        path = importer.export_frame(frame.head(10), tmp_path / f"out.{suffix}")
        assert path.stat().st_size > 0


def test_pipeline_operations(frame):
    flow = pipeline.Pipeline("clean")
    flow.add("contains", column="region", text="north")
    flow.add("select", columns=["region", "sales", "cost"])
    flow.add("normalize", columns=["sales", "cost"], method="zscore")
    result = flow.run(frame)
    assert list(result.frame.columns) == ["region", "sales", "cost"]
    assert abs(result.frame["sales"].mean()) < 1e-9
    assert len(result.log) == 3
    assert len(pipeline.OPERATIONS) >= 35


def test_pipeline_save_load(tmp_path):
    flow = pipeline.Pipeline("p")
    flow.add("sample", rows=5)
    path = flow.save(tmp_path / "p.json")
    loaded = pipeline.Pipeline.load(path)
    assert loaded.name == "p" and loaded.steps[0].params["rows"] == 5


def test_profile_and_correlations(frame):
    damaged = frame.copy()
    damaged.loc[:100, "cost"] = np.nan
    bad = pd.concat([damaged, damaged.head(3)], ignore_index=True)
    result = profiling.profile_frame(bad)
    assert result.rows == 243
    assert result.duplicate_rows >= 3
    assert 0 <= result.health_score <= 100
    assert not profiling.strongest_correlations(frame).empty


def test_drift(frame):
    current = frame.copy()
    current["sales"] += 100
    result = profiling.drift_score(frame, current)
    assert result.iloc[0]["drift"] > 1


def test_logs():
    lines = [f'10.0.0.{i} - - [01/May/2025:10:00:01 +0500] "GET /api/{i} HTTP/1.1" 200 512' for i in range(12)]
    frame, parser = logs.parse_log_lines(lines)
    assert parser == "apache" and len(frame) == 12
    templates = logs.mine_templates(pd.Series(lines))
    assert templates.iloc[0]["count"] == 12
    assert "<IP>" in templates.iloc[0]["template"]


@pytest.mark.parametrize("kind,kwargs", [
    ("line", {"x": "time", "y": "sales"}),
    ("bar", {"x": "region", "y": "sales"}),
    ("scatter", {"x": "sales", "y": "cost", "color": "region"}),
    ("histogram", {"x": "sales"}), ("box", {"x": "region", "y": "sales"}),
    ("area", {"x": "time", "y": "sales"}), ("pie", {"x": "region"}),
    ("correlation", {}), ("missing", {}),
])
def test_all_charts(frame, kind, kwargs):
    figure = charts.build_chart(frame, kind, **kwargs)
    assert len(charts.to_base64(figure)) > 100


def test_extended_chart_catalog(frame):
    assert len(charts.CHARTS) >= 25
    for kind, kwargs in [
        ("step", {"x": "time", "y": "sales"}),
        ("donut", {"x": "region"}),
        ("hexbin", {"x": "sales", "y": "cost"}),
        ("ecdf", {"x": "sales"}),
        ("violin", {"x": "region", "y": "sales"}),
        ("heatmap", {"x": "region", "y": "converted"}),
        ("calendar", {"x": "time"}),
    ]:
        assert charts.build_chart(frame, kind, **kwargs) is not None


def test_automl_classification(frame):
    run = ml.train_automl(frame.drop(columns=["message", "time"]), "converted")
    assert run.task == ml.CLASSIFICATION
    assert len(run.leaderboard) == 5
    assert "prediction" in run.predictions


def test_anomaly_and_cluster(frame):
    anomalous = ml.anomaly_detection(frame, ["sales", "cost", "orders"], contamination=.05)
    assert anomalous["_anomaly"].sum() > 0
    clustered, info = ml.cluster(frame, ["sales", "cost", "orders"], 3)
    assert clustered["_cluster"].nunique() == 3
    assert -1 <= info["silhouette"] <= 1


def test_model_trust_guard(tmp_path):
    with pytest.raises(PermissionError):
        ml.load_trusted_model(tmp_path / "missing.joblib")


def test_workspace_roundtrip(tmp_path, frame):
    workspace = Workspace()
    dataset = workspace.add("Sales", frame)
    dataset.tags = ["demo", "commerce"]
    path = persistence.save_workspace(workspace, tmp_path / "session")
    restored = persistence.load_workspace(path)
    assert restored.active.name == "Sales"
    assert restored.active.tags == ["demo", "commerce"]
    assert restored.active.frame.shape == frame.shape


def test_html_report(tmp_path, frame):
    content = reporting.build_html_report(frame, "Test report",
                                          figures=[("Sales", charts.build_chart(frame, "histogram", x="sales"))])
    path = reporting.save_html(content, tmp_path / "report")
    assert "INSIGHTFORGE" in content and "data:image/png;base64" in content
    assert path.stat().st_size > 3000
