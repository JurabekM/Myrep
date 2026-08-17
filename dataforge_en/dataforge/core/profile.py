"""Data profiling: statistical description, quality checks, correlation."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

NUMERIC = "numeric"
DATETIME = "datetime"
CATEGORICAL = "categorical"
BOOLEAN = "boolean"
TEXT = "text"
EMPTY = "empty"


def column_kind(s: pd.Series) -> str:
    """Classify a column into a semantic kind."""
    if s.dropna().empty:
        return EMPTY
    if pd.api.types.is_bool_dtype(s):
        return BOOLEAN
    if pd.api.types.is_datetime64_any_dtype(s) or isinstance(
            s.dtype, pd.PeriodDtype):
        return DATETIME
    if pd.api.types.is_numeric_dtype(s):
        return NUMERIC
    if isinstance(s.dtype, pd.CategoricalDtype):
        return CATEGORICAL
    non_null = s.dropna()
    nunique = non_null.nunique()
    ratio = nunique / max(1, len(non_null))
    avg_len = non_null.astype(str).str.len().mean()
    if nunique <= 50 or (ratio < 0.2 and avg_len < 40):
        return CATEGORICAL
    return TEXT


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
            and not pd.api.types.is_bool_dtype(df[c])]


def datetime_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]


def categorical_columns(df: pd.DataFrame, max_card: int = 200) -> list[str]:
    out = []
    for c in df.columns:
        k = column_kind(df[c])
        if k in (CATEGORICAL, BOOLEAN) and df[c].nunique(dropna=True) <= max_card:
            out.append(c)
    return out


def text_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if column_kind(df[c]) == TEXT]


def shannon_entropy(s: pd.Series) -> float:
    """Information entropy of a column (bits)."""
    vc = s.dropna().value_counts(normalize=True)
    if vc.empty:
        return 0.0
    return float(-(vc * np.log2(vc)).sum())


def iqr_outliers(s: pd.Series, k: float = 1.5) -> tuple[int, float, float]:
    """Outlier count and bounds using the IQR rule."""
    x = pd.to_numeric(s, errors="coerce").dropna()
    if x.empty:
        return 0, math.nan, math.nan
    q1, q3 = float(x.quantile(0.25)), float(x.quantile(0.75))
    iqr = q3 - q1
    lo, hi = q1 - k * iqr, q3 + k * iqr
    return int(((x < lo) | (x > hi)).sum()), lo, hi


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    kind: str
    count: int
    missing: int
    missing_pct: float
    unique: int
    unique_pct: float
    stats: dict[str, Any] = field(default_factory=dict)
    top: list[tuple[Any, int]] = field(default_factory=list)

    def as_row(self) -> dict[str, Any]:
        row = {
            "column": self.name,
            "kind": self.kind,
            "dtype": self.dtype,
            "filled": self.count,
            "missing": self.missing,
            "missing %": round(self.missing_pct, 2),
            "unique": self.unique,
            "unique %": round(self.unique_pct, 2),
        }
        for k in ("min", "max", "mean", "std", "median", "outliers", "entropy"):
            if k in self.stats:
                v = self.stats[k]
                row[k] = round(v, 4) if isinstance(v, float) else v
        return row


def profile_column(s: pd.Series, name: str | None = None) -> ColumnProfile:
    """Fully profile a single column."""
    name = name or str(s.name)
    n = len(s)
    missing = int(s.isna().sum())
    non_null = s.dropna()
    unique = int(non_null.nunique())
    kind = column_kind(s)
    stats: dict[str, Any] = {}
    top: list[tuple[Any, int]] = []

    if kind == NUMERIC:
        x = pd.to_numeric(non_null, errors="coerce").dropna()
        if not x.empty:
            desc = x.describe()
            stats.update(
                min=float(desc["min"]), max=float(desc["max"]),
                mean=float(desc["mean"]), std=float(desc.get("std", np.nan)),
                median=float(x.median()),
                q1=float(x.quantile(0.25)), q3=float(x.quantile(0.75)),
                p95=float(x.quantile(0.95)), p99=float(x.quantile(0.99)),
                sum=float(x.sum()), zeros=int((x == 0).sum()),
                negatives=int((x < 0).sum()),
                skew=float(x.skew()) if len(x) > 2 else 0.0,
                kurtosis=float(x.kurtosis()) if len(x) > 3 else 0.0,
            )
            out_n, lo, hi = iqr_outliers(x)
            stats.update(outliers=out_n, outlier_low=lo, outlier_high=hi)
    elif kind == DATETIME:
        d = pd.to_datetime(non_null, errors="coerce").dropna()
        if not d.empty:
            span = d.max() - d.min()
            stats.update(
                min=str(d.min()), max=str(d.max()),
                span_days=round(span.total_seconds() / 86400, 3),
                monotonic=bool(d.is_monotonic_increasing),
            )
            if len(d) > 1:
                deltas = d.sort_values().diff().dropna().dt.total_seconds()
                if not deltas.empty:
                    stats["median_gap_s"] = float(deltas.median())
    else:
        vc = non_null.value_counts()
        top = [(v, int(c)) for v, c in vc.head(15).items()]
        stats["entropy"] = round(shannon_entropy(non_null), 4)
        if kind in (TEXT, CATEGORICAL):
            lens = non_null.astype(str).str.len()
            stats.update(min_len=int(lens.min()), max_len=int(lens.max()),
                         mean_len=round(float(lens.mean()), 2))
        if unique:
            stats["mode"] = str(vc.index[0])
            stats["mode_freq"] = int(vc.iloc[0])

    return ColumnProfile(
        name=name, dtype=str(s.dtype), kind=kind,
        count=int(n - missing), missing=missing,
        missing_pct=100.0 * missing / n if n else 0.0,
        unique=unique, unique_pct=100.0 * unique / max(1, n - missing),
        stats=stats, top=top,
    )


@dataclass
class DatasetProfile:
    rows: int
    cols: int
    memory_mb: float
    duplicates: int
    total_missing: int
    columns: list[ColumnProfile]
    issues: list[dict[str, str]] = field(default_factory=list)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([c.as_row() for c in self.columns])

    @property
    def missing_pct(self) -> float:
        cells = self.rows * self.cols
        return 100.0 * self.total_missing / cells if cells else 0.0

    @property
    def quality_score(self) -> float:
        """Overall data quality score between 0 and 100."""
        score = 100.0
        score -= min(40.0, self.missing_pct * 1.5)
        if self.rows:
            score -= min(20.0, 100.0 * self.duplicates / self.rows)
        severity = {"high": 6.0, "medium": 3.0, "low": 1.0}
        for issue in self.issues:
            score -= severity.get(issue.get("level", "low"), 1.0)
        return max(0.0, round(score, 1))


def profile_dataframe(df: pd.DataFrame, max_cols: int = 300) -> DatasetProfile:
    """Profile the whole table and list quality problems."""
    cols = list(df.columns)[:max_cols]
    profiles = [profile_column(df[c], c) for c in cols]
    try:
        dupes = int(df.duplicated().sum())
    except TypeError:  # unhashable values present
        dupes = 0
    mem = float(df.memory_usage(deep=True).sum()) / 1024 / 1024 if len(df) else 0.0
    prof = DatasetProfile(
        rows=len(df), cols=df.shape[1], memory_mb=round(mem, 3),
        duplicates=dupes, total_missing=int(df.isna().sum().sum()),
        columns=profiles,
    )
    prof.issues = find_issues(df, prof)
    return prof


def find_issues(df: pd.DataFrame, prof: DatasetProfile) -> list[dict[str, str]]:
    """Data quality warnings."""
    issues: list[dict[str, str]] = []
    n = max(1, len(df))

    if prof.duplicates:
        issues.append({
            "level": "medium", "column": "—",
            "title": "Duplicate rows",
            "detail": f"{prof.duplicates:,} fully duplicated rows "
                      f"({100 * prof.duplicates / n:.1f}%). Try the 'Drop duplicates' operation.",
        })

    for cp in prof.columns:
        if cp.missing_pct > 50:
            issues.append({
                "level": "high", "column": cp.name,
                "title": "Mostly missing",
                "detail": f"{cp.missing_pct:.1f}% missing. Consider dropping or imputing it.",
            })
        elif cp.missing_pct > 10:
            issues.append({
                "level": "low", "column": cp.name,
                "title": "Missing values",
                "detail": f"{cp.missing_pct:.1f}% missing.",
            })
        if cp.count > 0 and cp.unique <= 1:
            issues.append({
                "level": "medium", "column": cp.name,
                "title": "Constant column",
                "detail": "Every value is identical — useless for modelling.",
            })
        if cp.kind in (CATEGORICAL, TEXT) and cp.unique_pct > 95 and cp.count > 50:
            issues.append({
                "level": "low", "column": cp.name,
                "title": "Nearly unique (ID?)",
                "detail": f"{cp.unique_pct:.0f}% unique — this looks like an identifier, "
                          f"keep it out of models.",
            })
        skew = cp.stats.get("skew")
        if isinstance(skew, float) and abs(skew) > 3:
            issues.append({
                "level": "low", "column": cp.name,
                "title": "Strong skew",
                "detail": f"skew={skew:.2f}. Consider a log or Box-Cox transform.",
            })
        out_n = cp.stats.get("outliers")
        if isinstance(out_n, int) and cp.count and out_n / cp.count > 0.05:
            issues.append({
                "level": "low", "column": cp.name,
                "title": "Many outliers",
                "detail": f"{out_n:,} values fall outside the IQR fence "
                          f"({100 * out_n / cp.count:.1f}%).",
            })
    return issues


def correlation(df: pd.DataFrame, method: str = "pearson",
                min_periods: int = 10) -> pd.DataFrame:
    """Correlation matrix across the numeric columns."""
    num = df[numeric_columns(df)]
    if num.shape[1] < 2:
        return pd.DataFrame()
    return num.corr(method=method, min_periods=min_periods)


def top_correlations(corr: pd.DataFrame, threshold: float = 0.5,
                     limit: int = 40) -> pd.DataFrame:
    """Return the strongest pairs as a list."""
    if corr.empty:
        return pd.DataFrame(columns=["A", "B", "r", "strength"])
    rows = []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            r = corr.loc[a, b]
            if pd.isna(r) or abs(r) < threshold:
                continue
            strength = ("very strong" if abs(r) >= 0.9 else
                        "strong" if abs(r) >= 0.7 else "moderate")
            rows.append({"A": a, "B": b, "r": round(float(r), 4), "strength": strength})
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=["A", "B", "r", "strength"])
    return out.reindex(out["r"].abs().sort_values(ascending=False).index).head(limit)


def cramers_v(x: pd.Series, y: pd.Series) -> float:
    """Association between two categorical columns (Cramér's V)."""
    from scipy.stats import chi2_contingency

    tab = pd.crosstab(x, y)
    if tab.size == 0 or tab.shape[0] < 2 or tab.shape[1] < 2:
        return 0.0
    try:
        chi2 = chi2_contingency(tab)[0]
    except Exception:
        return 0.0
    n = tab.to_numpy().sum()
    phi2 = chi2 / n
    r, k = tab.shape
    denom = min(r - 1, k - 1)
    return float(np.sqrt(phi2 / denom)) if denom else 0.0


def categorical_association(df: pd.DataFrame, max_cols: int = 12) -> pd.DataFrame:
    """Cramér's V matrix across categorical columns."""
    cats = categorical_columns(df, max_card=50)[:max_cols]
    if len(cats) < 2:
        return pd.DataFrame()
    m = pd.DataFrame(np.eye(len(cats)), index=cats, columns=cats)
    for i, a in enumerate(cats):
        for b in cats[i + 1:]:
            v = cramers_v(df[a], df[b])
            m.loc[a, b] = m.loc[b, a] = round(v, 4)
    return m


def missing_matrix(df: pd.DataFrame, max_rows: int = 2000) -> pd.DataFrame:
    """Map of missing values (True = missing), for visualisation."""
    step = max(1, len(df) // max_rows)
    return df.iloc[::step].isna()


def group_summary(df: pd.DataFrame, by: str | list[str], value: str | None = None,
                  aggs: list[str] | None = None) -> pd.DataFrame:
    """Grouped aggregation — the engine behind the GUI's Group/Pivot tab."""
    aggs = aggs or ["count", "mean", "median", "std", "min", "max", "sum"]
    by_list = [by] if isinstance(by, str) else list(by)
    g = df.groupby(by_list, dropna=False, observed=False)
    if value is None:
        out = g.size().reset_index(name="count")
        return out.sort_values("count", ascending=False)
    if not pd.api.types.is_numeric_dtype(df[value]):
        out = g[value].agg(["count", "nunique"]).reset_index()
        return out.sort_values("count", ascending=False)
    out = g[value].agg(aggs).reset_index()
    return out.sort_values(aggs[0], ascending=False)


def time_series(df: pd.DataFrame, ts_col: str, freq: str = "1h",
                value: str | None = None, agg: str = "count") -> pd.DataFrame:
    """Resample over time."""
    d = df[[c for c in {ts_col, value} if c]].copy()
    d[ts_col] = pd.to_datetime(d[ts_col], errors="coerce")
    d = d.dropna(subset=[ts_col])
    if d.empty:
        return pd.DataFrame(columns=[ts_col, agg])
    try:
        d[ts_col] = d[ts_col].dt.tz_localize(None)
    except (TypeError, AttributeError):
        pass
    d = d.set_index(ts_col).sort_index()
    if value is None or agg == "count":
        out = d.resample(freq).size().rename("count")
    else:
        out = getattr(d[value].resample(freq), agg)()
    return out.reset_index()


def suggest_freq(ts: pd.Series) -> str:
    """Suggest a sensible resampling frequency from the time span."""
    d = pd.to_datetime(ts, errors="coerce").dropna()
    if len(d) < 2:
        return "1h"
    span = (d.max() - d.min()).total_seconds()
    if span <= 0:
        return "1min"
    for limit, freq in ((600, "1s"), (7200, "1min"), (172800, "15min"),
                        (1209600, "1h"), (7776000, "1D"), (63072000, "1W")):
        if span <= limit:
            return freq
    return "1ME"
