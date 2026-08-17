from __future__ import annotations

import numpy as np
import pandas as pd

from insightforge.core import charts, pipeline
import pytest


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(17)
    rows = 600
    return pd.DataFrame({
        "time": pd.date_range("2025-01-01", periods=rows, freq="h"),
        "region": rng.choice(["north", "south", "west"], rows),
        "channel": rng.choice(["web", "mobile", "partner"], rows),
        "sales": rng.gamma(5, 42, rows).round(2),
        "cost": rng.gamma(4, 25, rows).round(2),
        "orders": rng.integers(1, 10, rows),
        "converted": rng.integers(0, 2, rows),
        "message": [f"request {index} from 10.0.0.{index % 20}" for index in range(rows)],
    })


def test_every_transform_operation():
    frame = demo_frame()
    params = {
        "select": {"columns": ["region", "sales"]},
        "drop": {"columns": ["message"]},
        "rename": {"column": "sales", "new_name": "revenue"},
        "filter": {"expression": "orders >= 2"},
        "contains": {"column": "region", "text": "north"},
        "sort": {"columns": ["sales"]},
        "sample": {"rows": 100},
        "drop_duplicates": {},
        "drop_empty": {},
        "fill_missing": {"columns": ["sales"], "method": "median"},
        "clip_outliers": {"columns": ["sales"]},
        "cast": {"column": "region", "dtype": "string"},
        "date_parts": {"column": "time"},
        "normalize": {"columns": ["sales", "cost"]},
        "group": {"by": ["region"], "values": ["sales"], "aggregation": "mean"},
        "pivot": {"index": "region", "columns": "channel", "values": "sales", "aggregation": "mean"},
        "melt": {"id_vars": ["region"], "value_vars": ["sales", "cost"]},
        "head": {"rows": 20},
        "tail": {"rows": 20},
        "rename_many": {"mapping": {"sales": "revenue", "cost": "expense"}},
        "reorder": {"columns": ["sales", "cost", "region"]},
        "trim": {"columns": ["region"]},
        "case": {"columns": ["region"], "mode": "upper"},
        "replace": {"column": "region", "old": "north", "new": "N"},
        "split": {"column": "message", "separator": " ", "max_parts": 3},
        "extract": {"column": "message", "pattern": r"request (\d+)", "new_name": "request_id"},
        "bin": {"column": "sales", "bins": 5},
        "rank": {"column": "sales"},
        "lag": {"column": "sales", "periods": 2},
        "rolling": {"column": "sales", "window": 12},
        "percent_change": {"column": "sales"},
        "cumulative": {"column": "sales"},
        "resample": {"timestamp": "time", "frequency": "D", "aggregation": "mean"},
        "one_hot": {"columns": ["region"]},
        "label_encode": {"columns": ["region"]},
        "transpose": {},
    }
    assert set(params) == set(pipeline.OPERATIONS)
    for key, arguments in params.items():
        result = pipeline.OPERATIONS[key].fn(frame.copy(), **arguments)
        assert isinstance(result, pd.DataFrame), key
        assert not result.empty, key


def test_filter_rejects_executable_expression():
    with pytest.raises(ValueError, match="ruxsat etilmagan"):
        pipeline.filter_rows(demo_frame(), "__import__('os').system('echo unsafe')")


def test_every_chart_type():
    frame = demo_frame()
    xy = {"x": "time", "y": "sales"}
    params = {
        "line": xy, "area": xy, "step": xy, "timeseries": xy,
        "cumulative": xy, "rolling": xy,
        "bar": {"x": "region", "y": "sales"},
        "barh": {"x": "region", "y": "sales"},
        "ranked_bar": {"x": "region", "y": "sales"},
        "count": {"x": "region"},
        "scatter": {"x": "sales", "y": "cost", "color": "region"},
        "bubble": {"x": "sales", "y": "cost", "options": {"size": "orders"}},
        "hexbin": {"x": "sales", "y": "cost"},
        "histogram": {"x": "sales"}, "kde": {"x": "sales"},
        "ecdf": {"x": "sales"},
        "box": {"x": "region", "y": "sales"},
        "violin": {"x": "region", "y": "sales"},
        "strip": {"x": "region", "y": "sales"},
        "pie": {"x": "region"}, "donut": {"x": "region"},
        "correlation": {}, "missing": {},
        "heatmap": {"x": "region", "y": "converted"},
        "stacked": {"x": "region", "color": "channel"},
        "calendar": {"x": "time"},
    }
    assert set(params) == set(charts.CHARTS)
    for key, arguments in params.items():
        figure = charts.build_chart(frame, key, **arguments)
        assert figure.axes, key
