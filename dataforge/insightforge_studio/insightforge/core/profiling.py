from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(slots=True)
class QualityIssue:
    severity: str
    title: str
    column: str | None
    detail: str
    count: int = 0


@dataclass(slots=True)
class Profile:
    rows: int
    columns: int
    memory_bytes: int
    duplicate_rows: int
    missing_cells: int
    health_score: float
    column_stats: pd.DataFrame
    issues: list[QualityIssue] = field(default_factory=list)


def profile_frame(frame: pd.DataFrame) -> Profile:
    rows, cols = frame.shape
    memory = int(frame.memory_usage(index=True, deep=True).sum())
    duplicates = int(frame.duplicated().sum()) if rows else 0
    missing = int(frame.isna().sum().sum())
    issues: list[QualityIssue] = []
    stats: list[dict[str, Any]] = []

    for col in frame.columns:
        series = frame[col]
        nulls = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))
        kind = column_kind(series)
        record: dict[str, Any] = {
            "column": str(col), "kind": kind, "dtype": str(series.dtype),
            "missing": nulls, "missing_%": round(nulls / max(rows, 1) * 100, 2),
            "unique": unique, "unique_%": round(unique / max(rows, 1) * 100, 2),
        }
        if kind == "numeric":
            values = pd.to_numeric(series, errors="coerce")
            record.update({"min": values.min(), "max": values.max(),
                           "mean": values.mean(), "median": values.median(),
                           "std": values.std(), "skew": values.skew()})
            if values.notna().sum() >= 8:
                q1, q3 = values.quantile([.25, .75])
                spread = q3 - q1
                outliers = int(((values < q1 - 1.5 * spread) |
                                (values > q3 + 1.5 * spread)).sum())
                record["outliers"] = outliers
                if outliers / max(values.notna().sum(), 1) > .10:
                    issues.append(QualityIssue("warning", "Ko'p chet qiymatlar", str(col),
                                               f"{outliers:,} ta IQR outlier", outliers))
        elif kind in {"categorical", "text", "boolean"}:
            counts = series.astype("string").value_counts(dropna=True)
            record["top"] = counts.index[0] if not counts.empty else None
            record["top_count"] = int(counts.iloc[0]) if not counts.empty else 0
            probs = counts / counts.sum() if counts.sum() else counts
            record["entropy"] = float(-(probs * np.log2(probs)).sum()) if len(probs) else 0.0
        elif kind == "datetime":
            dates = pd.to_datetime(series, errors="coerce")
            record["min"] = dates.min()
            record["max"] = dates.max()

        if rows and nulls / rows >= .25:
            issues.append(QualityIssue("danger" if nulls / rows >= .60 else "warning",
                                       "Bo'sh qiymatlar ko'p", str(col),
                                       f"{nulls / rows:.1%} qiymat bo'sh", nulls))
        if rows > 1 and unique <= 1:
            issues.append(QualityIssue("warning", "Doimiy ustun", str(col),
                                       "Ustun tahlilga axborot qo'shmaydi", rows))
        if rows >= 20 and unique == rows:
            issues.append(QualityIssue("info", "ID-ga o'xshash ustun", str(col),
                                       "Har bir qiymat unikal", unique))
        stats.append(record)

    if duplicates:
        issues.append(QualityIssue("warning", "Dublikat qatorlar", None,
                                   f"{duplicates:,} ta bir xil qator", duplicates))
    penalty = sum({"danger": 14, "warning": 6, "info": 1}[i.severity] for i in issues)
    missing_ratio = missing / max(rows * cols, 1)
    score = max(0.0, min(100.0, 100 - penalty - missing_ratio * 35))
    return Profile(rows, cols, memory, duplicates, missing, round(score, 1),
                   pd.DataFrame(stats), issues)


def column_kind(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    unique = series.nunique(dropna=True)
    ratio = unique / max(len(series), 1)
    return "categorical" if unique <= 50 or ratio <= .08 else "text"


def correlations(frame: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    numeric = frame.select_dtypes(include=np.number)
    return numeric.corr(method=method) if not numeric.empty else pd.DataFrame()


def strongest_correlations(frame: pd.DataFrame, limit: int = 15) -> pd.DataFrame:
    matrix = correlations(frame)
    rows: list[dict[str, Any]] = []
    for i, left in enumerate(matrix.columns):
        for right in matrix.columns[i + 1:]:
            value = matrix.loc[left, right]
            if pd.notna(value):
                rows.append({"left": left, "right": right, "correlation": float(value),
                             "strength": abs(float(value))})
    return pd.DataFrame(rows).sort_values("strength", ascending=False).head(limit) \
        if rows else pd.DataFrame(columns=["left", "right", "correlation", "strength"])


def segment_summary(frame: pd.DataFrame, category: str, metrics: list[str]) -> pd.DataFrame:
    numeric = [col for col in metrics if col in frame and pd.api.types.is_numeric_dtype(frame[col])]
    if not numeric:
        return frame.groupby(category, dropna=False).size().rename("rows").reset_index()
    result = frame.groupby(category, dropna=False)[numeric].agg(["count", "mean", "median", "sum"])
    result.columns = [f"{column}_{stat}" for column, stat in result.columns]
    return result.reset_index()


def drift_score(reference: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    common = [col for col in reference.columns if col in current.columns]
    for col in common:
        if pd.api.types.is_numeric_dtype(reference[col]) and pd.api.types.is_numeric_dtype(current[col]):
            a, b = reference[col].dropna(), current[col].dropna()
            scale = max(float(a.std()), 1e-9)
            score = abs(float(b.mean()) - float(a.mean())) / scale if len(a) and len(b) else math.nan
            rows.append({"column": col, "kind": "numeric", "drift": score})
        else:
            a = reference[col].astype("string").value_counts(normalize=True)
            b = current[col].astype("string").value_counts(normalize=True)
            cats = a.index.union(b.index)
            score = float((a.reindex(cats, fill_value=0) - b.reindex(cats, fill_value=0)).abs().sum() / 2)
            rows.append({"column": col, "kind": "categorical", "drift": score})
    return pd.DataFrame(rows).sort_values("drift", ascending=False)

