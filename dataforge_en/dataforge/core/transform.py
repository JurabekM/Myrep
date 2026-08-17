"""Data transformation operations (transform engine) and undo/redo history.

Every operation is a pure function in the ``OPS`` registry: ``fn(df, **params) -> df``.
The GUI reads that registry and builds the input form automatically.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd

from ..config import MAX_CATEGORY_ONEHOT, MAX_HISTORY

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
@dataclass
class OpSpec:
    key: str
    label: str
    group: str
    fn: Callable[..., pd.DataFrame]
    params: list[dict[str, Any]] = field(default_factory=list)
    doc: str = ""


OPS: dict[str, OpSpec] = {}


def op(key: str, label: str, group: str, params: list[dict[str, Any]] | None = None,
       doc: str = "") -> Callable:
    def deco(fn: Callable[..., pd.DataFrame]) -> Callable[..., pd.DataFrame]:
        OPS[key] = OpSpec(key, label, group, fn, params or [], doc or (fn.__doc__ or "").strip())
        return fn

    return deco


def apply_op(df: pd.DataFrame, key: str, **params: Any) -> pd.DataFrame:
    """Apply an operation from the registry."""
    spec = OPS.get(key)
    if spec is None:
        raise KeyError(f"Unknown operation: {key}")
    out = spec.fn(df, **params)
    if not isinstance(out, pd.DataFrame):
        raise TypeError(f"Operation '{key}' did not return a DataFrame")
    return out


def describe_op(key: str, params: dict[str, Any]) -> str:
    spec = OPS.get(key)
    label = spec.label if spec else key
    if not params:
        return label
    shown = ", ".join(f"{k}={v}" for k, v in params.items() if v not in (None, "", []))
    return f"{label}" + (f" ({shown})" if shown else "")


# Parameter types: col, cols, text, number, choice, bool, numcol, catcol, dtcol
C = lambda n, label, **kw: dict(name=n, label=label, **kw)  # noqa: E731


# ---------------------------------------------------------------------------
# Row operations
# ---------------------------------------------------------------------------
@op("filter_query", "Filter by expression (query)", "Filter",
    [C("expr", "Expression", type="text", placeholder="status >= 400 and method == 'POST'")])
def filter_query(df: pd.DataFrame, expr: str) -> pd.DataFrame:
    """Filter rows using pandas.query syntax."""
    if not expr or not expr.strip():
        return df
    return df.query(expr, engine="python")


@op("filter_contains", "Text search", "Filter",
    [C("column", "Column", type="col"),
     C("pattern", "Text / regex", type="text"),
     C("regex", "Regex", type="bool", default=False),
     C("case", "Case sensitive", type="bool", default=False),
     C("invert", "Invert (non-matching)", type="bool", default=False)])
def filter_contains(df: pd.DataFrame, column: str, pattern: str,
                    regex: bool = False, case: bool = False,
                    invert: bool = False) -> pd.DataFrame:
    """Search a column by text or regular expression."""
    mask = df[column].astype(str).str.contains(pattern, case=case, regex=regex, na=False)
    return df[~mask] if invert else df[mask]


@op("filter_range", "Numeric range", "Filter",
    [C("column", "Column", type="numcol"),
     C("low", "From", type="number", optional=True),
     C("high", "To", type="number", optional=True)])
def filter_range(df: pd.DataFrame, column: str, low: float | None = None,
                 high: float | None = None) -> pd.DataFrame:
    """Filter a numeric column by range."""
    s = pd.to_numeric(df[column], errors="coerce")
    mask = pd.Series(True, index=df.index)
    if low is not None:
        mask &= s >= float(low)
    if high is not None:
        mask &= s <= float(high)
    return df[mask.fillna(False)]


@op("filter_time", "Time range", "Filter",
    [C("column", "Time column", type="dtcol"),
     C("start", "Start", type="text", placeholder="2024-01-01", optional=True),
     C("end", "End", type="text", placeholder="2024-12-31", optional=True)])
def filter_time(df: pd.DataFrame, column: str, start: str | None = None,
                end: str | None = None) -> pd.DataFrame:
    """Slice a time column by range."""
    s = pd.to_datetime(df[column], errors="coerce")
    mask = pd.Series(True, index=df.index)
    if start:
        mask &= s >= pd.Timestamp(start)
    if end:
        mask &= s <= pd.Timestamp(end)
    return df[mask.fillna(False)]


@op("drop_duplicates", "Drop duplicates", "Cleaning",
    [C("subset", "Columns (empty = all)", type="cols", optional=True),
     C("keep", "Which one to keep", type="choice", options=["first", "last", "none"],
       default="first")])
def drop_duplicates(df: pd.DataFrame, subset: list[str] | None = None,
                    keep: str = "first") -> pd.DataFrame:
    """Remove duplicated rows."""
    k: Any = False if keep == "none" else keep
    return df.drop_duplicates(subset=subset or None, keep=k)


@op("dropna", "Drop empty rows", "Cleaning",
    [C("subset", "Columns (empty = all)", type="cols", optional=True),
     C("how", "Condition", type="choice", options=["any", "all"], default="any")])
def dropna(df: pd.DataFrame, subset: list[str] | None = None, how: str = "any") -> pd.DataFrame:
    """Remove rows that contain missing values."""
    return df.dropna(subset=subset or None, how=how)


@op("drop_rows", "Drop selected rows", "Cleaning",
    [C("indices", "Indices", type="text", hidden=True)])
def drop_rows(df: pd.DataFrame, indices: list[int] | str) -> pd.DataFrame:
    """Drop the rows at the given positions."""
    if isinstance(indices, str):
        idx = [int(x) for x in re.findall(r"\d+", indices)]
    else:
        idx = list(indices)
    keep = df.index.difference(df.index[idx])
    return df.loc[keep]


@op("sort", "Sort", "Ordering",
    [C("by", "Column(s)", type="cols"),
     C("ascending", "Ascending", type="bool", default=True)])
def sort_values(df: pd.DataFrame, by: list[str] | str, ascending: bool = True) -> pd.DataFrame:
    """Sort by one or more columns."""
    return df.sort_values(by=[by] if isinstance(by, str) else list(by),
                          ascending=ascending, kind="stable")


@op("sample", "Random sample", "Ordering",
    [C("n", "Row count", type="number", default=1000),
     C("random_state", "Random seed", type="number", default=42)])
def sample(df: pd.DataFrame, n: int = 1000, random_state: int = 42) -> pd.DataFrame:
    """Take a random sample."""
    n = int(min(int(n), len(df)))
    return df.sample(n=n, random_state=int(random_state)) if n else df


@op("head", "First N rows", "Ordering", [C("n", "N", type="number", default=1000)])
def head(df: pd.DataFrame, n: int = 1000) -> pd.DataFrame:
    """Keep only the first N rows."""
    return df.head(int(n))


# ---------------------------------------------------------------------------
# Column operations
# ---------------------------------------------------------------------------
@op("select_cols", "Select columns", "Columns", [C("columns", "Columns", type="cols")])
def select_cols(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Keep only the selected columns."""
    return df[[c for c in columns if c in df.columns]]


@op("drop_cols", "Drop columns", "Columns", [C("columns", "Columns", type="cols")])
def drop_cols(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Drop the selected columns."""
    return df.drop(columns=[c for c in columns if c in df.columns])


@op("rename", "Rename column", "Columns",
    [C("column", "Column", type="col"), C("new_name", "New name", type="text")])
def rename(df: pd.DataFrame, column: str, new_name: str) -> pd.DataFrame:
    """Rename a column."""
    return df.rename(columns={column: new_name})


@op("astype", "Change type", "Columns",
    [C("column", "Column", type="col"),
     C("dtype", "New type", type="choice",
       options=["float", "integer", "text", "datetime", "boolean", "category"])])
def astype(df: pd.DataFrame, column: str, dtype: str) -> pd.DataFrame:
    """Force a column into another type."""
    out = df.copy()
    s = out[column]
    if dtype == "float":
        out[column] = pd.to_numeric(s, errors="coerce")
    elif dtype == "integer":
        out[column] = pd.to_numeric(s, errors="coerce").astype("Int64")
    elif dtype == "text":
        out[column] = s.astype(str)
    elif dtype == "datetime":
        from .logparse import parse_timestamp_series

        out[column] = parse_timestamp_series(s)
    elif dtype == "boolean":
        mapping = {"true": True, "1": True, "yes": True, "t": True,
                   "false": False, "0": False, "no": False, "f": False}
        out[column] = s.astype(str).str.lower().str.strip().map(mapping)
    elif dtype == "category":
        out[column] = s.astype("category")
    return out


@op("fillna", "Fill missing values", "Cleaning",
    [C("columns", "Columns (empty = all)", type="cols", optional=True),
     C("method", "Method", type="choice",
       options=["value", "mean", "median", "mode", "forward fill", "backward fill",
                "zero", "linear interpolation"], default="median"),
     C("value", "Value", type="text", optional=True)])
def fillna(df: pd.DataFrame, columns: list[str] | None = None,
           method: str = "median", value: Any = None) -> pd.DataFrame:
    """Fill empty cells using the chosen strategy."""
    out = df.copy()
    cols = columns or list(out.columns)
    for c in cols:
        if c not in out.columns:
            continue
        s = out[c]
        if method == "value":
            out[c] = s.fillna(value)
        elif method == "zero":
            out[c] = s.fillna(0)
        elif method == "forward fill":
            out[c] = s.ffill()
        elif method == "backward fill":
            out[c] = s.bfill()
        elif method == "mean" and pd.api.types.is_numeric_dtype(s):
            out[c] = s.fillna(s.mean())
        elif method == "median" and pd.api.types.is_numeric_dtype(s):
            out[c] = s.fillna(s.median())
        elif method == "linear interpolation" and pd.api.types.is_numeric_dtype(s):
            out[c] = s.interpolate(limit_direction="both")
        elif method == "mode":
            m = s.mode()
            if not m.empty:
                out[c] = s.fillna(m.iloc[0])
    return out


@op("replace", "Find and replace", "Text",
    [C("column", "Column", type="col"),
     C("find", "Find", type="text"),
     C("repl", "Replace with", type="text"),
     C("regex", "Regex", type="bool", default=False)])
def replace(df: pd.DataFrame, column: str, find: str, repl: str,
            regex: bool = False) -> pd.DataFrame:
    """Replace text inside a column."""
    out = df.copy()
    out[column] = out[column].astype(str).str.replace(find, repl, regex=regex)
    return out


@op("str_op", "String operation", "Text",
    [C("column", "Column", type="col"),
     C("action", "Action", type="choice",
       options=["lowercase", "uppercase", "title case", "trim whitespace",
                "remove digits", "digits only", "length",
                "strip special characters"])])
def str_op(df: pd.DataFrame, column: str, action: str) -> pd.DataFrame:
    """Apply a standard string operation to a text column."""
    out = df.copy()
    s = out[column].astype(str)
    ops = {
        "lowercase": lambda: s.str.lower(),
        "uppercase": lambda: s.str.upper(),
        "title case": lambda: s.str.title(),
        "trim whitespace": lambda: s.str.strip().str.replace(r"\s+", " ", regex=True),
        "remove digits": lambda: s.str.replace(r"\d+", "", regex=True),
        "digits only": lambda: pd.to_numeric(
            s.str.replace(r"[^\d.\-]", "", regex=True), errors="coerce"),
        "length": lambda: s.str.len(),
        "strip special characters": lambda: s.str.replace(r"[^\w\s]", "", regex=True),
    }
    out[column] = ops[action]()
    return out


@op("split_col", "Split column", "Text",
    [C("column", "Column", type="col"),
     C("sep", "Separator", type="text", default=" "),
     C("maxsplit", "Max splits", type="number", default=2)])
def split_col(df: pd.DataFrame, column: str, sep: str = " ", maxsplit: int = 2) -> pd.DataFrame:
    """Split a text column into several columns by a separator."""
    out = df.copy()
    parts = out[column].astype(str).str.split(sep, n=int(maxsplit), expand=True)
    for i in range(parts.shape[1]):
        out[f"{column}_{i + 1}"] = parts[i]
    return out


@op("extract", "Extract with regex", "Text",
    [C("column", "Column", type="col"),
     C("pattern", "Regex (with a group)", type="text", placeholder=r"(\d+)ms"),
     C("new_name", "New column name", type="text", optional=True)])
def extract(df: pd.DataFrame, column: str, pattern: str,
            new_name: str | None = None) -> pd.DataFrame:
    """Create a new column from a regex capture group."""
    out = df.copy()
    res = out[column].astype(str).str.extract(pattern, expand=True)
    if res.shape[1] == 1:
        out[new_name or f"{column}_extract"] = res[0]
    else:
        for i in range(res.shape[1]):
            out[f"{new_name or column}_g{i + 1}"] = res[i]
    return out


@op("derive", "New column (expression)", "Compute",
    [C("new_name", "New column name", type="text"),
     C("expr", "Expression", type="text", placeholder="bytes / 1024")])
def derive(df: pd.DataFrame, new_name: str, expr: str) -> pd.DataFrame:
    """Compute a new column from a pandas.eval expression."""
    out = df.copy()
    try:
        out[new_name] = out.eval(expr, engine="python")
    except Exception:
        # restricted fallback for expressions eval cannot handle
        env = {c: out[c] for c in out.columns}
        env.update({"np": np, "pd": pd, "abs": abs, "min": min, "max": max,
                    "round": round, "len": len})
        out[new_name] = eval(expr, {"__builtins__": {}}, env)  # noqa: S307
    return out


@op("datetime_parts", "Extract date parts", "Compute",
    [C("column", "Time column", type="dtcol"),
     C("parts", "Parts", type="multichoice",
       options=["year", "month", "day", "hour", "minute", "weekday", "week",
                "quarter", "date", "daypart"],
       default=["year", "month", "day", "hour"])])
def datetime_parts(df: pd.DataFrame, column: str, parts: list[str]) -> pd.DataFrame:
    """Derive features such as year/month/hour from a time column."""
    out = df.copy()
    d = pd.to_datetime(out[column], errors="coerce")
    mapping = {
        "year": lambda: d.dt.year, "month": lambda: d.dt.month, "day": lambda: d.dt.day,
        "hour": lambda: d.dt.hour, "minute": lambda: d.dt.minute,
        "weekday": lambda: d.dt.dayofweek,
        "week": lambda: d.dt.isocalendar().week.astype("Int64"),
        "quarter": lambda: d.dt.quarter, "date": lambda: d.dt.date.astype(str),
        "daypart": lambda: pd.cut(
            d.dt.hour, bins=[-1, 5, 11, 17, 21, 24],
            labels=["night", "morning", "afternoon", "evening", "late night"]).astype(str),
    }
    for p in parts:
        if p in mapping:
            out[f"{column}_{p}"] = mapping[p]()
    return out


@op("bin_numeric", "Bin numeric column", "Compute",
    [C("column", "Column", type="numcol"),
     C("bins", "Bin count", type="number", default=5),
     C("strategy", "Strategy", type="choice", options=["equal width", "quantile"],
       default="quantile")])
def bin_numeric(df: pd.DataFrame, column: str, bins: int = 5,
                strategy: str = "quantile") -> pd.DataFrame:
    """Discretise a continuous column into bins."""
    out = df.copy()
    s = pd.to_numeric(out[column], errors="coerce")
    if strategy == "quantile":
        out[f"{column}_bin"] = pd.qcut(s, q=int(bins), duplicates="drop").astype(str)
    else:
        out[f"{column}_bin"] = pd.cut(s, bins=int(bins)).astype(str)
    return out


@op("scale", "Scale", "Compute",
    [C("columns", "Columns", type="numcols"),
     C("method", "Method", type="choice",
       options=["standard (z-score)", "min-max", "robust", "log1p"],
       default="standard (z-score)"),
     C("inplace", "Replace the column", type="bool", default=True)])
def scale(df: pd.DataFrame, columns: list[str], method: str = "standard (z-score)",
          inplace: bool = True) -> pd.DataFrame:
    """Normalise numeric columns."""
    out = df.copy()
    for c in columns:
        s = pd.to_numeric(out[c], errors="coerce")
        if method == "standard (z-score)":
            sd = s.std(ddof=0)
            res = (s - s.mean()) / (sd if sd else 1.0)
        elif method == "min-max":
            rng = s.max() - s.min()
            res = (s - s.min()) / (rng if rng else 1.0)
        elif method == "robust":
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            res = (s - s.median()) / (iqr if iqr else 1.0)
        else:
            res = np.log1p(s.clip(lower=0))
        out[c if inplace else f"{c}_scaled"] = res
    return out


@op("clip_outliers", "Handle outliers", "Cleaning",
    [C("columns", "Columns", type="numcols"),
     C("method", "Method", type="choice", options=["IQR", "quantile 1–99", "z-score 3"],
       default="IQR"),
     C("action", "Action", type="choice", options=["clip", "drop rows"],
       default="clip")])
def clip_outliers(df: pd.DataFrame, columns: list[str], method: str = "IQR",
                  action: str = "clip") -> pd.DataFrame:
    """Clip outlying values or drop the rows containing them."""
    out = df.copy()
    mask_drop = pd.Series(False, index=out.index)
    for c in columns:
        s = pd.to_numeric(out[c], errors="coerce")
        if method == "IQR":
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        elif method == "quantile 1–99":
            lo, hi = s.quantile(0.01), s.quantile(0.99)
        else:
            mu, sd = s.mean(), s.std(ddof=0) or 1.0
            lo, hi = mu - 3 * sd, mu + 3 * sd
        if action == "clip":
            out[c] = s.clip(lo, hi)
        else:
            mask_drop |= (s < lo) | (s > hi)
    return out[~mask_drop.fillna(False)] if action != "clip" else out


@op("onehot", "One-hot encode", "Encoding",
    [C("columns", "Columns", type="catcols"),
     C("drop_first", "Drop the first level", type="bool", default=False)])
def onehot(df: pd.DataFrame, columns: list[str], drop_first: bool = False) -> pd.DataFrame:
    """Turn categorical columns into binary indicator columns."""
    safe = [c for c in columns if df[c].nunique(dropna=True) <= MAX_CATEGORY_ONEHOT]
    if not safe:
        raise ValueError(
            f"The selected columns have more than {MAX_CATEGORY_ONEHOT} distinct values")
    return pd.get_dummies(df, columns=safe, drop_first=drop_first, dtype=int)


@op("label_encode", "Label encode", "Encoding", [C("columns", "Columns", type="catcols")])
def label_encode(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Convert categories into integer codes."""
    out = df.copy()
    for c in columns:
        out[f"{c}_code"] = out[c].astype("category").cat.codes.replace(-1, np.nan)
    return out


# ---------------------------------------------------------------------------
# Structural operations
# ---------------------------------------------------------------------------
@op("groupby_agg", "Group and aggregate", "Structure",
    [C("by", "Group by", type="cols"),
     C("value", "Value column", type="numcol", optional=True),
     C("aggs", "Functions", type="multichoice",
       options=["count", "sum", "mean", "median", "min", "max", "std", "nunique"],
       default=["count", "mean"])])
def groupby_agg(df: pd.DataFrame, by: list[str], value: str | None = None,
                aggs: list[str] | None = None) -> pd.DataFrame:
    """Build an aggregated summary table (the result is a new table)."""
    aggs = aggs or ["count"]
    by = [by] if isinstance(by, str) else list(by)
    g = df.groupby(by, dropna=False, observed=False)
    if not value:
        return g.size().reset_index(name="count")
    return g[value].agg(aggs).reset_index()


@op("pivot", "Pivot table", "Structure",
    [C("index", "Row column", type="col"),
     C("columns", "Column column", type="col"),
     C("values", "Value", type="numcol"),
     C("aggfunc", "Function", type="choice",
       options=["mean", "sum", "count", "median", "max", "min"], default="mean")])
def pivot(df: pd.DataFrame, index: str, columns: str, values: str,
          aggfunc: str = "mean") -> pd.DataFrame:
    """Build a pivot (cross-tab) table."""
    out = pd.pivot_table(df, index=index, columns=columns, values=values,
                         aggfunc=aggfunc, observed=False)
    out.columns = [str(c) for c in out.columns]
    return out.reset_index()


@op("melt", "Wide → long (melt)", "Structure",
    [C("id_vars", "Columns to keep", type="cols"),
     C("value_vars", "Columns to melt", type="cols", optional=True)])
def melt(df: pd.DataFrame, id_vars: list[str],
         value_vars: list[str] | None = None) -> pd.DataFrame:
    """Reshape a wide table into long form."""
    return df.melt(id_vars=id_vars, value_vars=value_vars or None,
                   var_name="variable", value_name="value")


@op("resample", "Resample over time", "Structure",
    [C("column", "Time column", type="dtcol"),
     C("freq", "Frequency", type="choice",
       options=["1s", "10s", "1min", "5min", "15min", "1h", "6h", "1D", "1W", "1ME"],
       default="1h"),
     C("value", "Value column", type="numcol", optional=True),
     C("agg", "Function", type="choice",
       options=["count", "mean", "sum", "median", "min", "max"], default="count")])
def resample(df: pd.DataFrame, column: str, freq: str = "1h",
             value: str | None = None, agg: str = "count") -> pd.DataFrame:
    """Aggregate a time series at the given frequency."""
    from .profile import time_series

    return time_series(df, column, freq=freq, value=value, agg=agg)


@op("remove_constant", "Drop constant columns", "Cleaning", [])
def remove_constant(df: pd.DataFrame) -> pd.DataFrame:
    """Remove columns that hold a single distinct value."""
    keep = [c for c in df.columns if df[c].nunique(dropna=False) > 1]
    return df[keep] if keep else df


@op("reset_index", "Reset index", "Structure", [])
def reset_index(df: pd.DataFrame) -> pd.DataFrame:
    """Renumber the index from 0."""
    return df.reset_index(drop=True)


@op("transpose", "Transpose", "Structure", [])
def transpose(df: pd.DataFrame) -> pd.DataFrame:
    """Swap rows and columns."""
    out = df.T.reset_index()
    out.columns = [str(c) for c in out.columns]
    return out


def op_groups() -> dict[str, list[OpSpec]]:
    """Return the operations grouped for the GUI."""
    groups: dict[str, list[OpSpec]] = {}
    for spec in OPS.values():
        groups.setdefault(spec.group, []).append(spec)
    for lst in groups.values():
        lst.sort(key=lambda s: s.label)
    return groups


# ---------------------------------------------------------------------------
# Undo / redo history
# ---------------------------------------------------------------------------
@dataclass
class HistoryEntry:
    label: str
    df: pd.DataFrame
    shape: tuple[int, int]


class History:
    """A depth-limited undo/redo stack."""

    def __init__(self, df: pd.DataFrame, label: str = "Loaded",
                 max_len: int = MAX_HISTORY) -> None:
        self.max_len = max_len
        self._stack: list[HistoryEntry] = [HistoryEntry(label, df, df.shape)]
        self._idx = 0

    # ---- state
    @property
    def current(self) -> pd.DataFrame:
        return self._stack[self._idx].df

    @property
    def current_label(self) -> str:
        return self._stack[self._idx].label

    @property
    def can_undo(self) -> bool:
        return self._idx > 0

    @property
    def can_redo(self) -> bool:
        return self._idx < len(self._stack) - 1

    def labels(self) -> list[str]:
        return [e.label for e in self._stack]

    def entries(self) -> list[HistoryEntry]:
        return list(self._stack)

    @property
    def index(self) -> int:
        return self._idx

    # ---- actions
    def push(self, df: pd.DataFrame, label: str) -> None:
        del self._stack[self._idx + 1:]
        self._stack.append(HistoryEntry(label, df, df.shape))
        if len(self._stack) > self.max_len:
            self._stack.pop(0)
        self._idx = len(self._stack) - 1

    def undo(self) -> pd.DataFrame:
        if self.can_undo:
            self._idx -= 1
        return self.current

    def redo(self) -> pd.DataFrame:
        if self.can_redo:
            self._idx += 1
        return self.current

    def goto(self, idx: int) -> pd.DataFrame:
        self._idx = max(0, min(idx, len(self._stack) - 1))
        return self.current

    def reset(self, df: pd.DataFrame, label: str = "Loaded") -> None:
        self._stack = [HistoryEntry(label, df, df.shape)]
        self._idx = 0
