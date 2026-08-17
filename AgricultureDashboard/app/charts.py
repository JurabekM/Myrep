"""ECharts option builders (rendered offline via NiceGUI's bundled ECharts)."""
from __future__ import annotations

from typing import Any, Sequence

from app.theme import PALETTE

_BASE: dict[str, Any] = {
    "animationDuration": 400,
    "grid": {"left": 60, "right": 24, "top": 48, "bottom": 42},
    "tooltip": {"trigger": "axis"},
}


def _title(text: str) -> dict[str, Any]:
    return {"text": text, "textStyle": {"fontSize": 14}}


def line_chart(title: str, x: Sequence, series: dict[str, Sequence],
               y_name: str = "", dashed: set[str] | None = None) -> dict[str, Any]:
    """Multi-series line chart; names in ``dashed`` render as dashed lines."""
    dashed = dashed or set()
    return {
        **_BASE,
        "title": _title(title),
        "color": PALETTE,
        "legend": {"top": 24},
        "xAxis": {"type": "category", "data": list(x)},
        "yAxis": {"type": "value", "name": y_name},
        "series": [
            {
                "name": name, "type": "line", "smooth": True,
                "data": [None if v is None else round(float(v), 3) for v in values],
                "lineStyle": {"type": "dashed" if name in dashed else "solid"},
                "connectNulls": False,
            }
            for name, values in series.items()
        ],
    }


def bar_chart(title: str, x: Sequence, series: dict[str, Sequence],
              horizontal: bool = False, y_name: str = "") -> dict[str, Any]:
    """Vertical or horizontal bar chart."""
    category_axis = {"type": "category", "data": list(x)}
    value_axis = {"type": "value", "name": y_name}
    return {
        **_BASE,
        "title": _title(title),
        "color": PALETTE,
        "legend": {"top": 24} if len(series) > 1 else {"show": False},
        "xAxis": value_axis if horizontal else category_axis,
        "yAxis": category_axis if horizontal else value_axis,
        "series": [
            {"name": name, "type": "bar",
             "data": [round(float(v), 2) for v in values]}
            for name, values in series.items()
        ],
    }


def pie_chart(title: str, pairs: list[tuple[str, float]]) -> dict[str, Any]:
    """Donut chart for share breakdowns."""
    return {
        "title": _title(title),
        "color": PALETTE,
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {"orient": "vertical", "left": "left", "top": 40,
                   "textStyle": {"fontSize": 10}},
        "series": [{
            "type": "pie", "radius": ["38%", "68%"], "center": ["60%", "55%"],
            "itemStyle": {"borderRadius": 6},
            "label": {"show": False},
            "data": [{"name": name, "value": round(float(value), 1)}
                     for name, value in pairs],
        }],
    }


def heatmap_chart(title: str, x_labels: Sequence[str], y_labels: Sequence[str],
                  points: list[list[float]], unit: str = "") -> dict[str, Any]:
    """Matrix heatmap; points are [x_index, y_index, value]."""
    values = [p[2] for p in points] or [0]
    return {
        "title": _title(title),
        "tooltip": {"position": "top"},
        "grid": {"left": 110, "right": 30, "top": 40, "bottom": 90},
        "xAxis": {"type": "category", "data": list(x_labels),
                  "axisLabel": {"rotate": 45, "fontSize": 10}},
        "yAxis": {"type": "category", "data": list(y_labels),
                  "axisLabel": {"fontSize": 10}},
        "visualMap": {
            "min": min(values), "max": max(values), "calculable": True,
            "orient": "horizontal", "left": "center", "bottom": 0,
            "inRange": {"color": ["#c62828", "#f9a825", "#2e7d32"]},
        },
        "series": [{"type": "heatmap", "data": points,
                    "label": {"show": True, "fontSize": 9, "formatter": "{@[2]}"},
                    "tooltip": {"valueFormatter": f"value => value + ' {unit}'"}}],
    }


def scatter_chart(title: str, points: list[list[float]], x_name: str,
                  y_name: str) -> dict[str, Any]:
    """Scatter plot for correlation views."""
    return {
        "title": _title(title),
        "color": PALETTE,
        "tooltip": {"trigger": "item"},
        "grid": {"left": 60, "right": 30, "top": 48, "bottom": 48},
        "xAxis": {"type": "value", "name": x_name, "nameLocation": "middle",
                  "nameGap": 28},
        "yAxis": {"type": "value", "name": y_name},
        "series": [{"type": "scatter", "symbolSize": 9, "data": points,
                    "itemStyle": {"opacity": 0.75}}],
    }


def gauge_chart(title: str, value: float, max_value: float = 100,
                unit: str = "%") -> dict[str, Any]:
    """Single-value gauge (e.g. disease-risk probability)."""
    return {
        "title": _title(title),
        "series": [{
            "type": "gauge", "min": 0, "max": max_value,
            "progress": {"show": True, "width": 14},
            "axisLine": {"lineStyle": {"width": 14}},
            "axisTick": {"show": False}, "splitLine": {"length": 8},
            "detail": {"formatter": f"{{value}}{unit}", "fontSize": 20},
            "data": [{"value": round(value, 1)}],
            "color": ["#2e7d32"],
        }],
    }
