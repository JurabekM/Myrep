"""Chart building core — matplotlib figures shared by the GUI and the report.

``CHART_TYPES`` lists the supported chart types and the fields each one needs.
The GUI builds its form from that definition.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")  # the GUI canvas installs its own backend

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from ..config import CHART_COLORS, PALETTE  # noqa: E402

MAX_POINTS = 60_000
MAX_CATEGORIES = 40


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
def apply_dark_style() -> None:
    """A dark matplotlib style that matches the application theme."""
    plt.rcParams.update({
        "figure.facecolor": PALETTE["surface"],
        "axes.facecolor": PALETTE["surface"],
        "savefig.facecolor": PALETTE["surface"],
        "axes.edgecolor": PALETTE["border2"],
        "axes.labelcolor": PALETTE["text"],
        "axes.titlecolor": PALETTE["text"],
        "axes.titleweight": "600",
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": PALETTE["border"],
        "grid.alpha": 0.55,
        "grid.linewidth": 0.7,
        "text.color": PALETTE["text"],
        "xtick.color": PALETTE["muted"],
        "ytick.color": PALETTE["muted"],
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.facecolor": PALETTE["surface2"],
        "legend.edgecolor": PALETTE["border2"],
        "legend.labelcolor": PALETTE["text"],
        "legend.fontsize": 9,
        "figure.autolayout": False,
        "lines.linewidth": 1.9,
        "lines.markersize": 5,
        "patch.edgecolor": PALETTE["surface"],
        "font.size": 10,
    })


apply_dark_style()


@dataclass
class ChartSpec:
    key: str
    label: str
    group: str
    needs: list[str] = field(default_factory=list)      # required fields
    optional: list[str] = field(default_factory=list)   # optional fields
    x_kind: str = "any"     # any | num | cat | dt
    y_kind: str = "any"


CHART_TYPES: dict[str, ChartSpec] = {
    "line":       ChartSpec("line", "Line", "Basic", ["x", "y"], ["hue"]),
    "area":       ChartSpec("area", "Area", "Basic", ["x", "y"], ["hue"]),
    "step":       ChartSpec("step", "Step", "Basic", ["x", "y"], ["hue"]),
    "bar":        ChartSpec("bar", "Bar", "Basic", ["x"], ["y", "hue"], x_kind="cat"),
    "barh":       ChartSpec("barh", "Horizontal bar", "Basic", ["x"], ["y", "hue"], x_kind="cat"),
    "stacked_bar": ChartSpec("stacked_bar", "Stacked bar", "Basic", ["x", "hue"], ["y"],
                             x_kind="cat"),
    "pie":        ChartSpec("pie", "Pie", "Basic", ["x"], ["y"], x_kind="cat"),
    "donut":      ChartSpec("donut", "Donut", "Basic", ["x"], ["y"], x_kind="cat"),
    "count":      ChartSpec("count", "Count", "Basic", ["x"], ["hue"], x_kind="cat"),

    "scatter":    ChartSpec("scatter", "Scatter", "Distribution", ["x", "y"], ["hue", "size"],
                            x_kind="num", y_kind="num"),
    "bubble":     ChartSpec("bubble", "Bubble", "Distribution", ["x", "y", "size"], ["hue"],
                            x_kind="num", y_kind="num"),
    "hexbin":     ChartSpec("hexbin", "Hexbin density", "Distribution", ["x", "y"], [],
                            x_kind="num", y_kind="num"),
    "hist":       ChartSpec("hist", "Histogram", "Distribution", ["x"], ["hue"], x_kind="num"),
    "kde":        ChartSpec("kde", "Density (KDE)", "Distribution", ["x"], ["hue"], x_kind="num"),
    "ecdf":       ChartSpec("ecdf", "ECDF", "Distribution", ["x"], ["hue"], x_kind="num"),
    "box":        ChartSpec("box", "Box plot", "Distribution", ["y"], ["x", "hue"], y_kind="num"),
    "violin":     ChartSpec("violin", "Violin plot", "Distribution", ["y"], ["x"], y_kind="num"),
    "strip":      ChartSpec("strip", "Strip plot", "Distribution", ["y"], ["x"], y_kind="num"),

    "heatmap":    ChartSpec("heatmap", "Heatmap", "Relationships", ["x", "y"], ["value"]),
    "corr":       ChartSpec("corr", "Correlation matrix", "Relationships", [], []),
    "pairplot":   ChartSpec("pairplot", "Pair plot", "Relationships", [], ["hue"]),
    "missing":    ChartSpec("missing", "Missing value map", "Relationships", [], []),

    "timeseries": ChartSpec("timeseries", "Time series", "Time", ["x"], ["y", "hue"], x_kind="dt"),
    "calendar":   ChartSpec("calendar", "Hour × weekday", "Time", ["x"], ["y"], x_kind="dt"),
    "rolling":    ChartSpec("rolling", "Rolling average", "Time", ["x", "y"], [], x_kind="dt"),
}


def chart_groups() -> dict[str, list[ChartSpec]]:
    groups: dict[str, list[ChartSpec]] = {}
    for spec in CHART_TYPES.values():
        groups.setdefault(spec.group, []).append(spec)
    return groups


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _colors(n: int) -> list[str]:
    if n <= len(CHART_COLORS):
        return CHART_COLORS[:n]
    cmap = plt.get_cmap("turbo")
    return [matplotlib.colors.to_hex(cmap(i / max(1, n - 1))) for i in range(n)]


def _limit_categories(s: pd.Series, top: int = MAX_CATEGORIES) -> pd.Series:
    vc = s.value_counts()
    if len(vc) <= top:
        return s
    keep = set(vc.head(top).index)
    return s.where(s.isin(keep), other="(other)")


def _downsample(df: pd.DataFrame, limit: int = MAX_POINTS) -> pd.DataFrame:
    if len(df) <= limit:
        return df
    return df.sample(limit, random_state=42).sort_index()


def _agg_series(df: pd.DataFrame, x: str, y: str | None, agg: str) -> pd.DataFrame:
    """Group by x and aggregate y."""
    if y is None or agg == "count":
        out = df.groupby(x, dropna=False, observed=False).size().reset_index(name="value")
    else:
        g = df.groupby(x, dropna=False, observed=False)[y]
        out = getattr(g, agg)().reset_index().rename(columns={y: "value"})
    return out


def _finish(fig: Figure, ax, title: str | None, xlabel: str | None,
            ylabel: str | None, opts: dict) -> Figure:
    if title:
        ax.set_title(title, pad=12)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if opts.get("logy"):
        ax.set_yscale("log")
    if opts.get("logx"):
        ax.set_xscale("log")
    if not opts.get("grid", True):
        ax.grid(False)
    for spine in ("top", "right"):
        if spine in ax.spines:
            ax.spines[spine].set_visible(False)
    if opts.get("rotate_x"):
        for lbl in ax.get_xticklabels():
            lbl.set_rotation(45)
            lbl.set_ha("right")
    try:
        fig.tight_layout()
    except Exception:
        pass
    return fig


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------
def build_chart(df: pd.DataFrame, kind: str, x: str | None = None, y: str | None = None,
                hue: str | None = None, size: str | None = None, agg: str = "count",
                figsize: tuple[float, float] = (9.5, 5.6), dpi: int = 110,
                title: str | None = None, **opts: Any) -> Figure:
    """Build a matplotlib figure of the requested type."""
    if df is None or df.empty:
        return _empty_figure("No data", figsize, dpi)

    spec = CHART_TYPES.get(kind)
    if spec is None:
        raise ValueError(f"Unknown chart type: {kind}")
    for need in spec.needs:
        if not locals().get(need) and not opts.get(need):
            raise ValueError(f"'{spec.label}' requires the '{need}' field")

    fn = _BUILDERS.get(kind)
    if fn is None:
        raise ValueError(f"No builder found for '{kind}'")

    fig = Figure(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor(PALETTE["surface"])
    ctx = dict(df=df, x=x, y=y, hue=hue, size=size, agg=agg, opts=opts)
    ax = fn(fig, **ctx)
    if ax is None:
        return fig
    auto_title = title or _auto_title(spec, x, y, hue, agg)
    return _finish(fig, ax, auto_title, opts.get("xlabel", x), opts.get("ylabel"), opts)


def _auto_title(spec: ChartSpec, x, y, hue, agg) -> str:
    bits = [spec.label]
    if y and x:
        bits.append(f"— {y} / {x}")
    elif x:
        bits.append(f"— {x}")
    elif y:
        bits.append(f"— {y}")
    if hue:
        bits.append(f"(by {hue})")
    return " ".join(bits)


def _empty_figure(msg: str, figsize=(9.5, 5.6), dpi: int = 110) -> Figure:
    fig = Figure(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor(PALETTE["surface"])
    ax = fig.add_subplot(111)
    ax.set_facecolor(PALETTE["surface"])
    ax.text(0.5, 0.5, msg, ha="center", va="center", color=PALETTE["muted"], fontsize=13)
    ax.set_axis_off()
    return fig


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def _b_line(fig, df, x, y, hue, size, agg, opts, mode="line"):
    ax = fig.add_subplot(111)
    d = df[[c for c in {x, y, hue} if c]].dropna(subset=[x])
    d = d.sort_values(x)
    d = _downsample(d)
    if hue:
        groups = _limit_categories(d[hue].astype(str), 12)
        cats = list(pd.unique(groups))
        cols = _colors(len(cats))
        for c, color in zip(cats, cols):
            sub = d[groups == c]
            if mode == "area":
                ax.fill_between(sub[x], sub[y], alpha=0.35, color=color, label=str(c))
                ax.plot(sub[x], sub[y], color=color, linewidth=1.6)
            elif mode == "step":
                ax.step(sub[x], sub[y], where="post", color=color, label=str(c))
            else:
                ax.plot(sub[x], sub[y], color=color, label=str(c),
                        marker="o" if len(sub) < 40 else None)
        ax.legend(title=hue, frameon=True)
    else:
        color = CHART_COLORS[0]
        if mode == "area":
            ax.fill_between(d[x], d[y], alpha=0.35, color=color)
            ax.plot(d[x], d[y], color=color)
        elif mode == "step":
            ax.step(d[x], d[y], where="post", color=color)
        else:
            ax.plot(d[x], d[y], color=color, marker="o" if len(d) < 40 else None)
    ax.set_ylabel(y or "")
    return ax


def _b_bar(fig, df, x, y, hue, size, agg, opts, horizontal=False):
    ax = fig.add_subplot(111)
    d = df.copy()
    d[x] = _limit_categories(d[x].astype(str))
    if hue:
        d[hue] = _limit_categories(d[hue].astype(str), 10)
        pivot = (d.pivot_table(index=x, columns=hue, values=y, aggfunc=agg, observed=False)
                 if y else d.pivot_table(index=x, columns=hue, aggfunc="size", observed=False))
        pivot = pivot.fillna(0).head(MAX_CATEGORIES)
        cats, cols = list(pivot.columns), _colors(pivot.shape[1])
        n = len(cats)
        idx = np.arange(len(pivot))
        w = 0.8 / max(1, n)
        for i, (c, color) in enumerate(zip(cats, cols)):
            pos = idx - 0.4 + w * (i + 0.5)
            if horizontal:
                ax.barh(pos, pivot[c].to_numpy(), height=w, color=color, label=str(c))
            else:
                ax.bar(pos, pivot[c].to_numpy(), width=w, color=color, label=str(c))
        labels = [str(v) for v in pivot.index]
        if horizontal:
            ax.set_yticks(idx, labels)
        else:
            ax.set_xticks(idx, labels)
        ax.legend(title=hue, frameon=True)
    else:
        s = _agg_series(d, x, y, agg).head(MAX_CATEGORIES)
        s = s.sort_values("value", ascending=horizontal)
        color = CHART_COLORS[0]
        if horizontal:
            ax.barh([str(v) for v in s[x]], s["value"], color=color)
        else:
            ax.bar([str(v) for v in s[x]], s["value"], color=color)
            opts.setdefault("rotate_x", len(s) > 6)
        if opts.get("labels", True) and len(s) <= 25:
            for i, v in enumerate(s["value"]):
                if horizontal:
                    ax.text(v, i, f" {v:,.0f}", va="center", fontsize=8,
                            color=PALETTE["muted"])
                else:
                    ax.text(i, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=8,
                            color=PALETTE["muted"])
    ax.set_ylabel(y or "count")
    return ax


def _b_stacked_bar(fig, df, x, y, hue, size, agg, opts):
    ax = fig.add_subplot(111)
    d = df.copy()
    d[x] = _limit_categories(d[x].astype(str), 25)
    d[hue] = _limit_categories(d[hue].astype(str), 10)
    pivot = (d.pivot_table(index=x, columns=hue, values=y, aggfunc=agg, observed=False)
             if y else d.pivot_table(index=x, columns=hue, aggfunc="size", observed=False))
    pivot = pivot.fillna(0)
    if opts.get("percent"):
        total = pivot.sum(axis=1).replace(0, np.nan)
        pivot = pivot.div(total, axis=0) * 100
    bottom = np.zeros(len(pivot))
    for c, color in zip(pivot.columns, _colors(pivot.shape[1])):
        vals = pivot[c].to_numpy(dtype=float)
        ax.bar([str(v) for v in pivot.index], vals, bottom=bottom, color=color, label=str(c))
        bottom += vals
    ax.legend(title=hue, frameon=True, ncols=max(1, pivot.shape[1] // 6))
    ax.set_ylabel("%" if opts.get("percent") else (y or "count"))
    opts.setdefault("rotate_x", len(pivot) > 6)
    return ax


def _b_pie(fig, df, x, y, hue, size, agg, opts, donut=False):
    ax = fig.add_subplot(111)
    s = _agg_series(df, x, y, agg).sort_values("value", ascending=False)
    top = int(opts.get("top", 10))
    if len(s) > top:
        head = s.head(top).copy()
        rest = pd.DataFrame({x: ["(other)"], "value": [s["value"][top:].sum()]})
        s = pd.concat([head, rest], ignore_index=True)
    wedges, _, autotexts = ax.pie(
        s["value"], labels=[str(v) for v in s[x]], autopct="%1.1f%%",
        colors=_colors(len(s)), startangle=90,
        wedgeprops=dict(width=0.42 if donut else 1.0, edgecolor=PALETTE["surface"],
                        linewidth=1.5),
        textprops=dict(color=PALETTE["text"], fontsize=9),
    )
    for t in autotexts:
        t.set_color("#0B0F14" if not donut else PALETTE["text"])
        t.set_fontsize(8)
    if donut:
        ax.text(0, 0, f"{s['value'].sum():,.0f}", ha="center", va="center",
                fontsize=15, color=PALETTE["text"], fontweight="bold")
    ax.set_aspect("equal")
    ax.grid(False)
    return ax


def _b_count(fig, df, x, y, hue, size, agg, opts):
    return _b_bar(fig, df, x, None, hue, size, "count", opts, horizontal=False)


def _b_scatter(fig, df, x, y, hue, size, agg, opts):
    ax = fig.add_subplot(111)
    cols = [c for c in {x, y, hue, size} if c]
    d = _downsample(df[cols].dropna(subset=[x, y]))
    alpha = float(opts.get("alpha", 0.65 if len(d) > 500 else 0.85))
    sizes = 28
    if size:
        sv = pd.to_numeric(d[size], errors="coerce").fillna(0)
        rng = sv.max() - sv.min()
        sizes = 15 + 220 * ((sv - sv.min()) / rng if rng else 0.5)
    if hue:
        if pd.api.types.is_numeric_dtype(d[hue]) and d[hue].nunique() > 12:
            sc = ax.scatter(d[x], d[y], c=pd.to_numeric(d[hue], errors="coerce"),
                            s=sizes, alpha=alpha, cmap="viridis", linewidths=0)
            cb = fig.colorbar(sc, ax=ax)
            cb.set_label(hue, color=PALETTE["muted"])
            cb.ax.tick_params(colors=PALETTE["muted"])
        else:
            groups = _limit_categories(d[hue].astype(str), 12)
            for c, color in zip(pd.unique(groups), _colors(groups.nunique())):
                m = groups == c
                ax.scatter(d[x][m], d[y][m], s=sizes if np.isscalar(sizes) else sizes[m],
                           alpha=alpha, color=color, label=str(c), linewidths=0)
            ax.legend(title=hue, frameon=True)
    else:
        ax.scatter(d[x], d[y], s=sizes, alpha=alpha, color=CHART_COLORS[0], linewidths=0)

    if opts.get("trend", True) and len(d) > 3:
        try:
            xv = pd.to_numeric(d[x], errors="coerce")
            yv = pd.to_numeric(d[y], errors="coerce")
            ok = xv.notna() & yv.notna()
            if ok.sum() > 3:
                k, b = np.polyfit(xv[ok], yv[ok], 1)
                xs = np.linspace(xv[ok].min(), xv[ok].max(), 50)
                r = float(np.corrcoef(xv[ok], yv[ok])[0, 1])
                ax.plot(xs, k * xs + b, "--", color=PALETTE["warning"], linewidth=1.5,
                        label=f"trend (r={r:.2f})")
                ax.legend(frameon=True)
        except Exception:
            pass
    ax.set_ylabel(y)
    return ax


def _b_bubble(fig, df, x, y, hue, size, agg, opts):
    return _b_scatter(fig, df, x, y, hue, size, agg, opts)


def _b_hexbin(fig, df, x, y, hue, size, agg, opts):
    ax = fig.add_subplot(111)
    d = df[[x, y]].dropna()
    hb = ax.hexbin(pd.to_numeric(d[x], errors="coerce"),
                   pd.to_numeric(d[y], errors="coerce"),
                   gridsize=int(opts.get("gridsize", 40)), cmap="viridis",
                   mincnt=1, linewidths=0.2)
    cb = fig.colorbar(hb, ax=ax)
    cb.set_label("count", color=PALETTE["muted"])
    cb.ax.tick_params(colors=PALETTE["muted"])
    ax.set_ylabel(y)
    return ax


def _b_hist(fig, df, x, y, hue, size, agg, opts):
    ax = fig.add_subplot(111)
    bins = int(opts.get("bins", 40))
    if hue:
        groups = _limit_categories(df[hue].astype(str), 8)
        for c, color in zip(pd.unique(groups), _colors(groups.nunique())):
            vals = pd.to_numeric(df[x][groups == c], errors="coerce").dropna()
            ax.hist(vals, bins=bins, alpha=0.6, color=color, label=str(c))
        ax.legend(title=hue, frameon=True)
    else:
        vals = pd.to_numeric(df[x], errors="coerce").dropna()
        ax.hist(vals, bins=bins, color=CHART_COLORS[0], alpha=0.9,
                edgecolor=PALETTE["surface"])
        if opts.get("stats", True) and not vals.empty:
            for val, color, label in ((vals.mean(), PALETTE["warning"], "mean"),
                                      (vals.median(), PALETTE["success"], "median")):
                ax.axvline(val, color=color, linestyle="--", linewidth=1.4,
                           label=f"{label}={val:,.2f}")
            ax.legend(frameon=True)
    ax.set_ylabel("frequency")
    return ax


def _b_kde(fig, df, x, y, hue, size, agg, opts):
    from scipy.stats import gaussian_kde

    ax = fig.add_subplot(111)

    def draw(vals: pd.Series, color: str, label: str | None) -> None:
        v = pd.to_numeric(vals, errors="coerce").dropna()
        if len(v) < 5 or v.std() == 0:
            return
        kde = gaussian_kde(v)
        xs = np.linspace(v.min(), v.max(), 300)
        ys = kde(xs)
        ax.plot(xs, ys, color=color, label=label)
        ax.fill_between(xs, ys, alpha=0.28, color=color)

    if hue:
        groups = _limit_categories(df[hue].astype(str), 8)
        for c, color in zip(pd.unique(groups), _colors(groups.nunique())):
            draw(df[x][groups == c], color, str(c))
        ax.legend(title=hue, frameon=True)
    else:
        draw(df[x], CHART_COLORS[0], None)
    ax.set_ylabel("density")
    return ax


def _b_ecdf(fig, df, x, y, hue, size, agg, opts):
    ax = fig.add_subplot(111)

    def draw(vals: pd.Series, color: str, label: str | None) -> None:
        v = pd.to_numeric(vals, errors="coerce").dropna().sort_values()
        if v.empty:
            return
        ax.step(v, np.arange(1, len(v) + 1) / len(v), where="post",
                color=color, label=label)

    if hue:
        groups = _limit_categories(df[hue].astype(str), 8)
        for c, color in zip(pd.unique(groups), _colors(groups.nunique())):
            draw(df[x][groups == c], color, str(c))
        ax.legend(title=hue, frameon=True)
    else:
        draw(df[x], CHART_COLORS[0], None)
    ax.set_ylabel("F(x)")
    ax.set_ylim(0, 1.02)
    return ax


def _b_box(fig, df, x, y, hue, size, agg, opts, violin=False, strip=False):
    ax = fig.add_subplot(111)
    if x:
        groups = _limit_categories(df[x].astype(str), 20)
        cats = [c for c in pd.unique(groups)][:20]
        data = [pd.to_numeric(df[y][groups == c], errors="coerce").dropna() for c in cats]
        data = [d for d in data if len(d) > 0]
        cats = [c for c, d in zip(cats, [pd.to_numeric(df[y][groups == c],
                errors="coerce").dropna() for c in cats]) if len(d) > 0]
    else:
        data = [pd.to_numeric(df[y], errors="coerce").dropna()]
        cats = [y]
    if not data:
        ax.text(0.5, 0.5, "No data", ha="center", color=PALETTE["muted"])
        return ax

    cols = _colors(len(data))
    if strip:
        for i, (d, color) in enumerate(zip(data, cols)):
            dd = d.sample(min(len(d), 1500), random_state=42)
            jitter = np.random.RandomState(42).normal(0, 0.06, len(dd))
            ax.scatter(np.full(len(dd), i + 1) + jitter, dd, s=10, alpha=0.45,
                       color=color, linewidths=0)
        ax.set_xticks(range(1, len(cats) + 1), [str(c) for c in cats])
    elif violin:
        parts = ax.violinplot(data, showmeans=True, showextrema=False)
        for pc, color in zip(parts["bodies"], cols):
            pc.set_facecolor(color)
            pc.set_alpha(0.65)
            pc.set_edgecolor(PALETTE["border2"])
        if "cmeans" in parts:
            parts["cmeans"].set_color(PALETTE["text"])
        ax.set_xticks(range(1, len(cats) + 1), [str(c) for c in cats])
    else:
        bp = ax.boxplot(data, patch_artist=True, tick_labels=[str(c) for c in cats],
                        medianprops=dict(color=PALETTE["text"], linewidth=1.6),
                        flierprops=dict(marker="o", markersize=3,
                                        markerfacecolor=PALETTE["danger"],
                                        markeredgecolor="none", alpha=0.5),
                        whiskerprops=dict(color=PALETTE["border2"]),
                        capprops=dict(color=PALETTE["border2"]))
        for patch, color in zip(bp["boxes"], cols):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
            patch.set_edgecolor(PALETTE["border2"])
    ax.set_ylabel(y)
    opts.setdefault("rotate_x", len(cats) > 6)
    return ax


def _b_heatmap(fig, df, x, y, hue, size, agg, opts):
    ax = fig.add_subplot(111)
    value = opts.get("value")
    if value:
        pivot = df.pivot_table(index=y, columns=x, values=value,
                               aggfunc=opts.get("agg", "mean"), observed=False)
    else:
        pivot = df.pivot_table(index=y, columns=x, aggfunc="size", observed=False)
    pivot = pivot.fillna(0).iloc[:40, :40]
    im = ax.imshow(pivot.to_numpy(), cmap=opts.get("cmap", "viridis"), aspect="auto")
    ax.set_xticks(range(pivot.shape[1]), [str(c) for c in pivot.columns],
                  rotation=45, ha="right")
    ax.set_yticks(range(pivot.shape[0]), [str(i) for i in pivot.index])
    cb = fig.colorbar(im, ax=ax)
    cb.ax.tick_params(colors=PALETTE["muted"])
    if opts.get("annot", pivot.size <= 120):
        vmax = np.nanmax(pivot.to_numpy()) or 1
        for i in range(pivot.shape[0]):
            for j in range(pivot.shape[1]):
                v = pivot.iat[i, j]
                ax.text(j, i, f"{v:,.0f}", ha="center", va="center", fontsize=7,
                        color="white" if v < vmax * 0.6 else "#0B0F14")
    ax.grid(False)
    return ax


def _b_corr(fig, df, x, y, hue, size, agg, opts):
    from .profile import correlation

    ax = fig.add_subplot(111)
    corr = correlation(df, method=opts.get("method", "pearson"))
    if corr.empty:
        ax.text(0.5, 0.5, "At least 2 numeric columns are required", ha="center",
                color=PALETTE["muted"])
        ax.set_axis_off()
        return ax
    corr = corr.iloc[:30, :30]
    im = ax.imshow(corr.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr)), corr.index)
    cb = fig.colorbar(im, ax=ax)
    cb.ax.tick_params(colors=PALETTE["muted"])
    if len(corr) <= 14:
        for i in range(len(corr)):
            for j in range(len(corr)):
                v = corr.iat[i, j]
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7.5,
                        color="white" if abs(v) > 0.55 else PALETTE["text"])
    ax.grid(False)
    return ax


def _b_pairplot(fig, df, x, y, hue, size, agg, opts):
    from .profile import numeric_columns

    cols = numeric_columns(df)[:int(opts.get("max_vars", 5))]
    if len(cols) < 2:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "At least 2 numeric columns are required", ha="center",
                color=PALETTE["muted"])
        ax.set_axis_off()
        return ax
    d = df[cols + ([hue] if hue and hue in df.columns else [])].dropna()
    if len(d) > 5000:
        d = d.sample(5000, random_state=42)
    n = len(cols)
    axes = fig.subplots(n, n)
    groups = _limit_categories(d[hue].astype(str), 8) if hue else None
    cats = list(pd.unique(groups)) if groups is not None else [None]
    cols_map = _colors(len(cats))
    for i in range(n):
        for j in range(n):
            ax = axes[i][j] if n > 1 else axes
            ax.set_facecolor(PALETTE["surface"])
            for c, color in zip(cats, cols_map):
                sub = d if c is None else d[groups == c]
                if i == j:
                    ax.hist(sub[cols[i]], bins=25, color=color, alpha=0.75)
                else:
                    ax.scatter(sub[cols[j]], sub[cols[i]], s=6, alpha=0.5,
                               color=color, linewidths=0)
            ax.tick_params(labelsize=7, colors=PALETTE["muted"])
            if i == n - 1:
                ax.set_xlabel(cols[j], fontsize=8)
            if j == 0:
                ax.set_ylabel(cols[i], fontsize=8)
            ax.grid(alpha=0.25)
    fig.suptitle("Pair plot", color=PALETTE["text"])
    try:
        fig.tight_layout()
    except Exception:
        pass
    return None


def _b_missing(fig, df, x, y, hue, size, agg, opts):
    from .profile import missing_matrix

    ax = fig.add_subplot(111)
    mm = missing_matrix(df)
    if mm.empty:
        ax.text(0.5, 0.5, "No data", ha="center", color=PALETTE["muted"])
        return ax
    ax.imshow(mm.to_numpy().T, aspect="auto", cmap="magma", interpolation="nearest")
    ax.set_yticks(range(mm.shape[1]), list(mm.columns), fontsize=8)
    ax.set_xlabel("row (sampled)")
    ax.grid(False)
    pct = 100 * df.isna().sum().sum() / max(1, df.size)
    ax.set_title(f"Missing value map — {pct:.2f}% overall")
    return ax


def _b_timeseries(fig, df, x, y, hue, size, agg, opts):
    from .profile import suggest_freq, time_series

    ax = fig.add_subplot(111)
    freq = opts.get("freq") or suggest_freq(df[x])
    if hue:
        groups = _limit_categories(df[hue].astype(str), 10)
        for c, color in zip(pd.unique(groups), _colors(groups.nunique())):
            sub = df[groups == c]
            ts = time_series(sub, x, freq=freq, value=y, agg=agg if y else "count")
            if ts.empty:
                continue
            ax.plot(ts.iloc[:, 0], ts.iloc[:, 1], color=color, label=str(c))
        ax.legend(title=hue, frameon=True)
    else:
        ts = time_series(df, x, freq=freq, value=y, agg=agg if y else "count")
        ax.plot(ts.iloc[:, 0], ts.iloc[:, 1], color=CHART_COLORS[0])
        ax.fill_between(ts.iloc[:, 0], ts.iloc[:, 1], alpha=0.22, color=CHART_COLORS[0])
    ax.set_ylabel(f"{agg}({y})" if y else "event count")
    ax.set_xlabel(f"{x} · {freq}")
    opts.setdefault("rotate_x", True)
    return ax


def _b_rolling(fig, df, x, y, hue, size, agg, opts):
    from .profile import suggest_freq, time_series

    ax = fig.add_subplot(111)
    freq = opts.get("freq") or suggest_freq(df[x])
    window = int(opts.get("window", 12))
    ts = time_series(df, x, freq=freq, value=y, agg=agg if agg != "count" else "mean")
    if ts.empty:
        ax.text(0.5, 0.5, "No data", ha="center", color=PALETTE["muted"])
        return ax
    vals = ts.iloc[:, 1]
    ax.plot(ts.iloc[:, 0], vals, color=PALETTE["faint"], linewidth=1.0, label="raw")
    ax.plot(ts.iloc[:, 0], vals.rolling(window, min_periods=1).mean(),
            color=CHART_COLORS[0], linewidth=2.2, label=f"MA({window})")
    std = vals.rolling(window, min_periods=1).std().fillna(0)
    ma = vals.rolling(window, min_periods=1).mean()
    ax.fill_between(ts.iloc[:, 0], ma - 2 * std, ma + 2 * std, alpha=0.16,
                    color=CHART_COLORS[0], label="±2σ")
    ax.legend(frameon=True)
    ax.set_ylabel(y or "value")
    opts.setdefault("rotate_x", True)
    return ax


def _b_calendar(fig, df, x, y, hue, size, agg, opts):
    ax = fig.add_subplot(111)
    d = pd.to_datetime(df[x], errors="coerce").dropna()
    if d.empty:
        ax.text(0.5, 0.5, "No time data", ha="center", color=PALETTE["muted"])
        return ax
    try:
        d = d.dt.tz_localize(None)
    except (TypeError, AttributeError):
        pass
    tmp = pd.DataFrame({"hour": d.dt.hour, "day": d.dt.dayofweek})
    if y and y in df.columns:
        tmp["val"] = pd.to_numeric(df.loc[d.index, y], errors="coerce")
        pivot = tmp.pivot_table(index="day", columns="hour", values="val",
                                aggfunc=agg if agg != "count" else "mean")
    else:
        pivot = tmp.pivot_table(index="day", columns="hour", aggfunc="size")
    pivot = pivot.reindex(index=range(7), columns=range(24)).fillna(0)
    im = ax.imshow(pivot.to_numpy(), cmap="viridis", aspect="auto")
    ax.set_yticks(range(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}" for h in range(0, 24, 2)])
    ax.set_xlabel("hour")
    cb = fig.colorbar(im, ax=ax)
    cb.ax.tick_params(colors=PALETTE["muted"])
    ax.grid(False)
    return ax


_BUILDERS = {
    "line": lambda fig, **kw: _b_line(fig, **kw, mode="line"),
    "area": lambda fig, **kw: _b_line(fig, **kw, mode="area"),
    "step": lambda fig, **kw: _b_line(fig, **kw, mode="step"),
    "bar": lambda fig, **kw: _b_bar(fig, **kw, horizontal=False),
    "barh": lambda fig, **kw: _b_bar(fig, **kw, horizontal=True),
    "stacked_bar": _b_stacked_bar,
    "pie": lambda fig, **kw: _b_pie(fig, **kw, donut=False),
    "donut": lambda fig, **kw: _b_pie(fig, **kw, donut=True),
    "count": _b_count,
    "scatter": _b_scatter,
    "bubble": _b_bubble,
    "hexbin": _b_hexbin,
    "hist": _b_hist,
    "kde": _b_kde,
    "ecdf": _b_ecdf,
    "box": lambda fig, **kw: _b_box(fig, **kw, violin=False, strip=False),
    "violin": lambda fig, **kw: _b_box(fig, **kw, violin=True, strip=False),
    "strip": lambda fig, **kw: _b_box(fig, **kw, violin=False, strip=True),
    "heatmap": _b_heatmap,
    "corr": _b_corr,
    "pairplot": _b_pairplot,
    "missing": _b_missing,
    "timeseries": _b_timeseries,
    "calendar": _b_calendar,
    "rolling": _b_rolling,
}


# ---------------------------------------------------------------------------
# Charts for ML results
# ---------------------------------------------------------------------------
def confusion_figure(cm: pd.DataFrame, normalize: bool = False,
                     figsize=(6.5, 5.5)) -> Figure:
    fig = Figure(figsize=figsize, dpi=110)
    fig.patch.set_facecolor(PALETTE["surface"])
    ax = fig.add_subplot(111)
    data = cm.to_numpy(dtype=float)
    if normalize:
        row = data.sum(axis=1, keepdims=True)
        data = np.divide(data, np.where(row == 0, 1, row)) * 100
    im = ax.imshow(data, cmap="Blues")
    ax.set_xticks(range(cm.shape[1]), [str(c).replace("predicted ", "") for c in cm.columns],
                  rotation=45, ha="right")
    ax.set_yticks(range(cm.shape[0]), [str(i).replace("actual ", "") for i in cm.index])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Confusion matrix" + (" (%)" if normalize else ""))
    vmax = data.max() or 1
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{data[i, j]:.1f}" if normalize else f"{int(data[i, j]):,}",
                    ha="center", va="center", fontsize=9,
                    color="white" if data[i, j] > vmax * 0.55 else "#0B0F14")
    ax.grid(False)
    fig.tight_layout()
    return fig


def roc_figure(curves: dict[str, tuple], figsize=(6.5, 5.5)) -> Figure:
    fig = Figure(figsize=figsize, dpi=110)
    fig.patch.set_facecolor(PALETTE["surface"])
    ax = fig.add_subplot(111)
    ax.set_facecolor(PALETTE["surface"])
    for (name, (fpr, tpr, auc_v)), color in zip(curves.items(), _colors(len(curves))):
        ax.plot(fpr, tpr, color=color, label=f"{name} (AUC={auc_v:.3f})")
    ax.plot([0, 1], [0, 1], "--", color=PALETTE["faint"], linewidth=1)
    ax.set_xlabel("FPR")
    ax.set_ylabel("TPR")
    ax.set_title("ROC curve")
    ax.legend(frameon=True, fontsize=8)
    ax.grid(alpha=0.4)
    fig.tight_layout()
    return fig


def importance_figure(imp: pd.DataFrame, top: int = 20, figsize=(7.5, 5.5)) -> Figure:
    fig = Figure(figsize=figsize, dpi=110)
    fig.patch.set_facecolor(PALETTE["surface"])
    ax = fig.add_subplot(111)
    ax.set_facecolor(PALETTE["surface"])
    d = imp.head(top).iloc[::-1]
    ax.barh(d["feature"].astype(str), d["importance"], color=CHART_COLORS[0])
    ax.set_title("Feature importance")
    ax.set_xlabel("importance")
    ax.tick_params(labelsize=8)
    ax.grid(axis="x", alpha=0.4)
    fig.tight_layout()
    return fig


def residual_figure(y_true: np.ndarray, y_pred: np.ndarray, figsize=(7.5, 5.5)) -> Figure:
    fig = Figure(figsize=figsize, dpi=110)
    fig.patch.set_facecolor(PALETTE["surface"])
    axes = fig.subplots(1, 2)
    for ax in axes:
        ax.set_facecolor(PALETTE["surface"])
    axes[0].scatter(y_pred, y_true, s=14, alpha=0.55, color=CHART_COLORS[0], linewidths=0)
    lo = float(min(np.min(y_true), np.min(y_pred)))
    hi = float(max(np.max(y_true), np.max(y_pred)))
    axes[0].plot([lo, hi], [lo, hi], "--", color=PALETTE["warning"], linewidth=1.3)
    axes[0].set_xlabel("Predicted")
    axes[0].set_ylabel("Actual")
    axes[0].set_title("Actual vs Predicted")
    resid = np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)
    axes[1].scatter(y_pred, resid, s=14, alpha=0.55, color=PALETTE["accent2"], linewidths=0)
    axes[1].axhline(0, color=PALETTE["warning"], linestyle="--", linewidth=1.3)
    axes[1].set_xlabel("Predicted")
    axes[1].set_ylabel("Residual")
    axes[1].set_title("Residual distribution")
    for ax in axes:
        ax.grid(alpha=0.4)
    fig.tight_layout()
    return fig


def cluster_figure(coords: np.ndarray, labels: np.ndarray, title: str = "Clusters",
                   figsize=(8.0, 5.6)) -> Figure:
    fig = Figure(figsize=figsize, dpi=110)
    fig.patch.set_facecolor(PALETTE["surface"])
    ax = fig.add_subplot(111)
    ax.set_facecolor(PALETTE["surface"])
    uniq = sorted(set(labels))
    cols = _colors(len(uniq))
    for lab, color in zip(uniq, cols):
        m = labels == lab
        name = "noise" if lab == -1 else f"cluster {lab}"
        ax.scatter(coords[m, 0], coords[m, 1], s=14, alpha=0.65,
                   color=PALETTE["faint"] if lab == -1 else color,
                   label=f"{name} ({m.sum():,})", linewidths=0)
    ax.legend(frameon=True, fontsize=8, ncols=max(1, len(uniq) // 8))
    ax.set_title(title)
    ax.set_xlabel("component 1")
    ax.set_ylabel("component 2")
    ax.grid(alpha=0.35)
    fig.tight_layout()
    return fig


def anomaly_figure(values: pd.Series, flags: np.ndarray, scores: np.ndarray | None = None,
                   x: pd.Series | None = None, figsize=(9.5, 5.4)) -> Figure:
    fig = Figure(figsize=figsize, dpi=110)
    fig.patch.set_facecolor(PALETTE["surface"])
    ax = fig.add_subplot(111)
    ax.set_facecolor(PALETTE["surface"])
    xs = x if x is not None else pd.Series(range(len(values)))
    ax.plot(xs, values, color=CHART_COLORS[0], linewidth=1.2, label="value", alpha=0.9)
    if flags.any():
        ax.scatter(xs[flags], values[flags], color=PALETTE["danger"], s=42, zorder=5,
                   label=f"anomaly ({int(flags.sum()):,})", edgecolors="none")
    ax.legend(frameon=True)
    ax.set_title("Anomalies")
    ax.grid(alpha=0.4)
    del scores
    fig.tight_layout()
    return fig


def forecast_figure(history: pd.Series, fc: pd.DataFrame, figsize=(9.5, 5.4)) -> Figure:
    fig = Figure(figsize=figsize, dpi=110)
    fig.patch.set_facecolor(PALETTE["surface"])
    ax = fig.add_subplot(111)
    ax.set_facecolor(PALETTE["surface"])
    ax.plot(history.index, history.to_numpy(), color=CHART_COLORS[0], label="history")
    ax.plot(fc["time"], fc["forecast"], color=PALETTE["warning"], linestyle="--",
            label="forecast")
    ax.fill_between(fc["time"], fc["lower"], fc["upper"], color=PALETTE["warning"],
                    alpha=0.18, label="95% interval")
    ax.legend(frameon=True)
    ax.set_title("Time series forecast")
    ax.grid(alpha=0.4)
    for lbl in ax.get_xticklabels():
        lbl.set_rotation(30)
        lbl.set_ha("right")
    fig.tight_layout()
    return fig


def elbow_figure(scores: pd.DataFrame, figsize=(7.0, 4.6)) -> Figure:
    fig = Figure(figsize=figsize, dpi=110)
    fig.patch.set_facecolor(PALETTE["surface"])
    ax = fig.add_subplot(111)
    ax.set_facecolor(PALETTE["surface"])
    ax.plot(scores["k"], scores["silhouette"], marker="o", color=CHART_COLORS[0],
            label="silhouette")
    best = scores.loc[scores["silhouette"].idxmax()]
    ax.axvline(best["k"], color=PALETTE["success"], linestyle="--",
               label=f"optimal k={int(best['k'])}")
    ax.set_xlabel("number of clusters (k)")
    ax.set_ylabel("silhouette score")
    ax.set_title("Choosing the optimal k")
    ax.legend(frameon=True)
    ax.grid(alpha=0.4)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def figure_to_base64(fig: Figure, fmt: str = "png", dpi: int = 120) -> str:
    """Encode a figure as base64 for embedding in the HTML report."""
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def save_figure(fig: Figure, path: str, dpi: int = 150) -> str:
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    return path
