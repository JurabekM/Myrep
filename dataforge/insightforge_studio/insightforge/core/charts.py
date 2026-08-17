from __future__ import annotations

import base64
import io
from typing import Any

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from ..config import CHART_COLORS, COLORS

CHARTS = {
    "line": "Chiziqli", "bar": "Ustunli", "scatter": "Nuqtali",
    "histogram": "Gistogramma", "box": "Quti", "area": "Maydon",
    "pie": "Doiraviy", "correlation": "Korrelyatsiya", "missing": "Bo'sh qiymatlar",
    "step": "Pog'onali", "barh": "Yotiq ustun", "count": "Chastota",
    "donut": "Halqa", "bubble": "Pufakchali", "hexbin": "Hexbin",
    "kde": "Zichlik", "ecdf": "ECDF", "violin": "Skripka",
    "strip": "Strip", "heatmap": "Issiqlik xaritasi", "rolling": "Siljuvchi o'rtacha",
    "cumulative": "Kumulyativ", "timeseries": "Vaqt qatori", "stacked": "Yig'ma ustun",
    "ranked_bar": "Reyting", "calendar": "Soat × hafta kuni",
}


def build_chart(frame: pd.DataFrame, kind: str, *, x: str | None = None,
                y: str | None = None, color: str | None = None,
                title: str = "", options: dict[str, Any] | None = None) -> Figure:
    opts = options or {}
    fig = Figure(figsize=opts.get("figsize", (9, 5.2)), dpi=opts.get("dpi", 110))
    fig.patch.set_facecolor(COLORS["panel"])
    ax = fig.add_subplot(111)
    ax.set_facecolor(COLORS["panel"])
    if frame.empty:
        ax.text(.5, .5, "Ma'lumot yo'q", ha="center", color=COLORS["muted"])
        return fig

    data = frame.sample(50_000, random_state=42) if len(frame) > 50_000 else frame
    if kind in {"line", "area", "step", "timeseries", "cumulative", "rolling"}:
        _require(data, x, y)
        plot = data[[x, y] + ([color] if color else [])].dropna(subset=[x, y]).sort_values(x)
        if kind == "rolling":
            values = pd.to_numeric(plot[y], errors="coerce")
            ax.plot(plot[x], values, color=CHART_COLORS[2], alpha=.28, label="Raw")
            ax.plot(plot[x], values.rolling(opts.get("window", 12), min_periods=1).mean(), color=CHART_COLORS[0], label="Rolling")
            ax.legend()
        elif kind == "cumulative":
            ax.plot(plot[x], pd.to_numeric(plot[y], errors="coerce").cumsum(), color=CHART_COLORS[0])
        elif kind == "step":
            ax.step(plot[x], plot[y], where="post", color=CHART_COLORS[0])
        elif color:
            for index, (label, group) in enumerate(plot.groupby(color, dropna=False)):
                method = ax.fill_between if kind == "area" else ax.plot
                if kind == "area":
                    method(group[x], group[y], alpha=.35, color=CHART_COLORS[index % len(CHART_COLORS)], label=str(label))
                else:
                    method(group[x], group[y], color=CHART_COLORS[index % len(CHART_COLORS)], label=str(label))
            ax.legend()
        elif kind == "area":
            ax.fill_between(plot[x], plot[y], alpha=.45, color=CHART_COLORS[0])
        else:
            ax.plot(plot[x], plot[y], color=CHART_COLORS[0])
    elif kind in {"bar", "barh", "ranked_bar"}:
        if not x:
            raise ValueError("Kategoriya ustuni kerak")
        if y:
            plot = data.groupby(x, dropna=False)[y].agg(opts.get("aggregation", "mean")).nlargest(30)
        else:
            plot = data[x].value_counts().head(30)
        if kind in {"barh", "ranked_bar"}:
            plot = plot.sort_values()
            ax.barh(plot.index.astype(str), plot.values, color=CHART_COLORS[0])
        else:
            ax.bar(plot.index.astype(str), plot.values, color=CHART_COLORS[0])
            ax.tick_params(axis="x", rotation=35)
    elif kind == "count":
        if not x: raise ValueError("Kategoriya ustuni kerak")
        plot = data[x].astype("string").value_counts().head(30)
        ax.bar(plot.index, plot.values, color=CHART_COLORS[1]); ax.tick_params(axis="x", rotation=35)
    elif kind in {"scatter", "bubble"}:
        _require(data, x, y)
        if color:
            codes, labels = pd.factorize(data[color].astype("string"))
            points = ax.scatter(data[x], data[y], c=codes, cmap="viridis", alpha=.65, s=24)
            ax.legend(points.legend_elements()[0], labels[:10], title=color)
        else:
            sizes = pd.to_numeric(data[opts.get("size")], errors="coerce") if kind == "bubble" and opts.get("size") in data else 24
            ax.scatter(data[x], data[y], color=CHART_COLORS[1], alpha=.65, s=sizes)
    elif kind == "hexbin":
        _require(data, x, y); ax.hexbin(data[x], data[y], gridsize=30, cmap="viridis", mincnt=1)
    elif kind in {"histogram", "kde", "ecdf"}:
        if not x:
            raise ValueError("Sonli ustun kerak")
        values = pd.to_numeric(data[x], errors="coerce").dropna().sort_values()
        if kind == "ecdf":
            ax.plot(values, np.arange(1, len(values) + 1) / max(1, len(values)), color=CHART_COLORS[0])
        elif kind == "kde":
            values.plot.kde(ax=ax, color=CHART_COLORS[0], linewidth=2)
        else:
            ax.hist(values, bins=opts.get("bins", 35), color=CHART_COLORS[0], alpha=.85)
    elif kind in {"box", "violin", "strip"}:
        if not y:
            y = x
        if not y:
            raise ValueError("Sonli ustun kerak")
        if x and x != y:
            groups = [(str(label), pd.to_numeric(group[y], errors="coerce").dropna())
                      for label, group in data.groupby(x, dropna=False)]
            arrays, labels = [values for _, values in groups], [label for label, _ in groups]
            if kind == "violin":
                ax.violinplot(arrays, showmedians=True); ax.set_xticks(range(1, len(labels) + 1), labels)
            elif kind == "strip":
                for index, values in enumerate(arrays, 1): ax.scatter(np.full(len(values), index), values, alpha=.25, s=10)
                ax.set_xticks(range(1, len(labels) + 1), labels)
            else:
                ax.boxplot(arrays, tick_labels=labels, patch_artist=True)
        else:
            ax.boxplot(pd.to_numeric(data[y], errors="coerce").dropna(), patch_artist=True)
    elif kind in {"pie", "donut"}:
        if not x:
            raise ValueError("Kategoriya ustuni kerak")
        counts = data[x].astype("string").value_counts().head(10)
        ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%", colors=CHART_COLORS,
               wedgeprops={"width": .42} if kind == "donut" else None)
    elif kind == "correlation":
        matrix = data.select_dtypes(include=np.number).corr()
        image = ax.imshow(matrix, cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_xticks(range(len(matrix)), matrix.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(matrix)), matrix.columns)
        fig.colorbar(image, ax=ax, shrink=.8)
    elif kind == "heatmap":
        _require(data, x, y)
        table = pd.crosstab(data[y], data[x]); image = ax.imshow(table, cmap="viridis", aspect="auto")
        ax.set_xticks(range(len(table.columns)), table.columns, rotation=45, ha="right"); ax.set_yticks(range(len(table)), table.index); fig.colorbar(image, ax=ax)
    elif kind == "stacked":
        _require(data, x, color)
        table = pd.crosstab(data[x], data[color]).head(25); table.plot.bar(stacked=True, ax=ax, color=CHART_COLORS)
    elif kind == "calendar":
        if not x: raise ValueError("Vaqt ustuni kerak")
        dates = pd.to_datetime(data[x], errors="coerce"); table = pd.crosstab(dates.dt.dayofweek, dates.dt.hour)
        image = ax.imshow(table, cmap="magma", aspect="auto"); ax.set_xlabel("Soat"); ax.set_ylabel("Hafta kuni"); fig.colorbar(image, ax=ax)
    elif kind == "missing":
        missing = data.isna().mean().sort_values(ascending=False).head(30) * 100
        ax.barh(missing.index.astype(str), missing.values, color=CHART_COLORS[4])
        ax.set_xlabel("Bo'sh qiymat, %")
    else:
        raise ValueError(f"Noma'lum grafik: {kind}")

    ax.set_title(title or CHARTS.get(kind, kind), color=COLORS["text"], pad=14)
    ax.tick_params(colors=COLORS["muted"])
    for spine in ax.spines.values():
        spine.set_color(COLORS["border"])
    ax.grid(alpha=.12)
    fig.tight_layout()
    return fig


def to_base64(figure: Figure) -> str:
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", bbox_inches="tight", facecolor=figure.get_facecolor())
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _require(frame: pd.DataFrame, *columns: str | None) -> None:
    missing = [column for column in columns if not column or column not in frame]
    if missing:
        raise ValueError("X va Y ustunlarini tanlang")
