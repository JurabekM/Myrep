from __future__ import annotations

import json
import ast
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import numpy as np
import pandas as pd


@dataclass(slots=True)
class Step:
    operation: str
    params: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    id: str = field(default_factory=lambda: uuid4().hex[:10])


@dataclass(slots=True)
class PipelineResult:
    frame: pd.DataFrame
    log: list[dict[str, Any]]


class Pipeline:
    def __init__(self, name: str = "Untitled pipeline", steps: list[Step] | None = None) -> None:
        self.name = name
        self.steps = steps or []

    def add(self, operation: str, **params: Any) -> Step:
        if operation not in OPERATIONS:
            raise KeyError(f"Noma'lum operatsiya: {operation}")
        step = Step(operation, params)
        self.steps.append(step)
        return step

    def remove(self, step_id: str) -> None:
        self.steps = [step for step in self.steps if step.id != step_id]

    def move(self, step_id: str, offset: int) -> None:
        index = next(i for i, step in enumerate(self.steps) if step.id == step_id)
        target = max(0, min(index + offset, len(self.steps) - 1))
        self.steps[index], self.steps[target] = self.steps[target], self.steps[index]

    def run(self, frame: pd.DataFrame,
            progress: Callable[[str, int], None] | None = None) -> PipelineResult:
        out = frame.copy()
        log: list[dict[str, Any]] = []
        active = [step for step in self.steps if step.enabled]
        for index, step in enumerate(active, 1):
            before = out.shape
            try:
                out = OPERATIONS[step.operation].fn(out, **step.params)
            except Exception as exc:
                log.append({"step": step.operation, "status": "error", "error": str(exc)})
                raise RuntimeError(f"'{step.operation}' bosqichi bajarilmadi: {exc}") from exc
            log.append({"step": step.operation, "status": "ok", "before": before,
                        "after": out.shape, "params": step.params})
            if progress:
                progress(OPERATIONS[step.operation].label, int(index / max(1, len(active)) * 100))
        return PipelineResult(out, log)

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.write_text(json.dumps({"name": self.name, "steps": [asdict(s) for s in self.steps]},
                                ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    @classmethod
    def load(cls, path: str | Path) -> "Pipeline":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(raw.get("name", "Imported pipeline"), [Step(**step) for step in raw["steps"]])


@dataclass(frozen=True, slots=True)
class Operation:
    key: str
    label: str
    group: str
    fn: Callable[..., pd.DataFrame]
    params: tuple[str, ...] = ()


OPERATIONS: dict[str, Operation] = {}


def operation(key: str, label: str, group: str, params: tuple[str, ...] = ()):
    def register(fn):
        OPERATIONS[key] = Operation(key, label, group, fn, params)
        return fn
    return register


@operation("select", "Ustunlarni tanlash", "Structure", ("columns",))
def select(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return frame[[c for c in columns if c in frame.columns]].copy()


@operation("drop", "Ustunlarni olib tashlash", "Structure", ("columns",))
def drop(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return frame.drop(columns=[c for c in columns if c in frame.columns])


@operation("rename", "Ustunni qayta nomlash", "Structure", ("column", "new_name"))
def rename(frame: pd.DataFrame, column: str, new_name: str) -> pd.DataFrame:
    if not new_name.strip():
        raise ValueError("Yangi nom bo'sh")
    return frame.rename(columns={column: new_name.strip()})


@operation("filter", "Shart bo'yicha filtrlash", "Rows", ("expression",))
def filter_rows(frame: pd.DataFrame, expression: str) -> pd.DataFrame:
    if not expression.strip():
        return frame.copy()
    _validate_filter_expression(expression, set(map(str, frame.columns)))
    return frame.query(expression, engine="python").copy()


_SAFE_FILTER_NODES = (
    ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare,
    ast.Name, ast.Load, ast.Constant, ast.List, ast.Tuple,
    ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
    ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Add, ast.Sub, ast.Mult,
    ast.Div, ast.Mod, ast.USub, ast.UAdd, ast.BitAnd, ast.BitOr,
)


def _validate_filter_expression(expression: str, columns: set[str]) -> None:
    """Reject calls, attributes and unknown names before pandas evaluates a filter."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Filtr sintaksisi noto'g'ri: {exc.msg}") from exc
    for node in ast.walk(tree):
        if not isinstance(node, _SAFE_FILTER_NODES):
            raise ValueError(f"Filtrda ruxsat etilmagan element: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in columns:
            raise ValueError(f"Noma'lum ustun: {node.id}")


@operation("contains", "Matn bo'yicha filtrlash", "Rows", ("column", "text"))
def contains(frame: pd.DataFrame, column: str, text: str, case: bool = False) -> pd.DataFrame:
    mask = frame[column].astype("string").str.contains(text, case=case, regex=False, na=False)
    return frame.loc[mask].copy()


@operation("sort", "Saralash", "Rows", ("columns",))
def sort_rows(frame: pd.DataFrame, columns: list[str], ascending: bool = True) -> pd.DataFrame:
    return frame.sort_values(columns, ascending=ascending).reset_index(drop=True)


@operation("sample", "Tasodifiy namuna", "Rows", ("rows",))
def sample(frame: pd.DataFrame, rows: int = 1000, seed: int = 42) -> pd.DataFrame:
    return frame.sample(min(len(frame), max(1, int(rows))), random_state=seed).reset_index(drop=True)


@operation("drop_duplicates", "Dublikatlarni tozalash", "Quality")
def drop_duplicates(frame: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    return frame.drop_duplicates(subset=columns or None).reset_index(drop=True)


@operation("drop_empty", "Bo'sh qatorlarni tozalash", "Quality")
def drop_empty(frame: pd.DataFrame, threshold: float = 1.0) -> pd.DataFrame:
    required = max(1, int(frame.shape[1] * max(0.0, min(1.0, threshold))))
    return frame.dropna(thresh=required).reset_index(drop=True)


@operation("fill_missing", "Bo'sh qiymatlarni to'ldirish", "Quality", ("columns", "method"))
def fill_missing(frame: pd.DataFrame, columns: list[str], method: str = "median",
                 value: Any = None) -> pd.DataFrame:
    out = frame.copy()
    for col in columns:
        if method == "median" and pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].fillna(out[col].median())
        elif method == "mean" and pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].fillna(out[col].mean())
        elif method == "mode":
            modes = out[col].mode(dropna=True)
            out[col] = out[col].fillna(modes.iloc[0] if not modes.empty else value)
        elif method == "forward":
            out[col] = out[col].ffill()
        elif method == "backward":
            out[col] = out[col].bfill()
        else:
            out[col] = out[col].fillna(value)
    return out


@operation("clip_outliers", "Chet qiymatlarni cheklash", "Quality", ("columns",))
def clip_outliers(frame: pd.DataFrame, columns: list[str], factor: float = 1.5) -> pd.DataFrame:
    out = frame.copy()
    for col in columns:
        values = pd.to_numeric(out[col], errors="coerce")
        q1, q3 = values.quantile([0.25, 0.75])
        spread = q3 - q1
        out[col] = values.clip(q1 - factor * spread, q3 + factor * spread)
    return out


@operation("cast", "Ustun turini o'zgartirish", "Enrichment", ("column", "dtype"))
def cast(frame: pd.DataFrame, column: str, dtype: str) -> pd.DataFrame:
    out = frame.copy()
    if dtype == "datetime":
        out[column] = pd.to_datetime(out[column], errors="coerce")
    elif dtype == "number":
        out[column] = pd.to_numeric(out[column], errors="coerce")
    elif dtype == "category":
        out[column] = out[column].astype("category")
    elif dtype == "boolean":
        out[column] = out[column].astype("boolean")
    else:
        out[column] = out[column].astype("string")
    return out


@operation("date_parts", "Sana qismlarini chiqarish", "Enrichment", ("column",))
def date_parts(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    out = frame.copy()
    values = pd.to_datetime(out[column], errors="coerce")
    for suffix, part in {"year": values.dt.year, "month": values.dt.month,
                         "day": values.dt.day, "weekday": values.dt.dayofweek,
                         "hour": values.dt.hour}.items():
        out[f"{column}_{suffix}"] = part
    return out


@operation("normalize", "Sonlarni masshtablash", "Enrichment", ("columns",))
def normalize(frame: pd.DataFrame, columns: list[str], method: str = "zscore") -> pd.DataFrame:
    out = frame.copy()
    for col in columns:
        values = pd.to_numeric(out[col], errors="coerce")
        if method == "minmax":
            span = values.max() - values.min()
            out[col] = (values - values.min()) / (span if span else 1)
        elif method == "robust":
            span = values.quantile(.75) - values.quantile(.25)
            out[col] = (values - values.median()) / (span if span else 1)
        else:
            std = values.std()
            out[col] = (values - values.mean()) / (std if std else 1)
    return out


@operation("group", "Guruhlash va jamlash", "Reshape", ("by", "values", "aggregation"))
def group(frame: pd.DataFrame, by: list[str], values: list[str],
          aggregation: str = "sum") -> pd.DataFrame:
    return frame.groupby(by, dropna=False)[values].agg(aggregation).reset_index()


@operation("pivot", "Pivot jadval", "Reshape", ("index", "columns", "values"))
def pivot(frame: pd.DataFrame, index: str, columns: str, values: str,
          aggregation: str = "sum") -> pd.DataFrame:
    return pd.pivot_table(frame, index=index, columns=columns, values=values,
                          aggfunc=aggregation, fill_value=0).reset_index()


@operation("melt", "Wide formatdan long formatga", "Reshape", ("id_vars", "value_vars"))
def melt(frame: pd.DataFrame, id_vars: list[str], value_vars: list[str]) -> pd.DataFrame:
    return frame.melt(id_vars=id_vars, value_vars=value_vars,
                      var_name="variable", value_name="value")


def join_frames(left: pd.DataFrame, right: pd.DataFrame, left_on: str,
                right_on: str, how: str = "left") -> pd.DataFrame:
    if how not in {"left", "right", "inner", "outer"}:
        raise ValueError("Noto'g'ri join turi")
    return left.merge(right, left_on=left_on, right_on=right_on, how=how,
                      suffixes=("_left", "_right"))


def append_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    return pd.concat(frames, ignore_index=True, sort=False)


@operation("head", "Birinchi qatorlar", "Rows", ("rows",))
def head(frame: pd.DataFrame, rows: int = 100) -> pd.DataFrame:
    return frame.head(max(1, int(rows))).copy()


@operation("tail", "Oxirgi qatorlar", "Rows", ("rows",))
def tail(frame: pd.DataFrame, rows: int = 100) -> pd.DataFrame:
    return frame.tail(max(1, int(rows))).copy()


@operation("rename_many", "Bir nechta ustunni nomlash", "Structure", ("mapping",))
def rename_many(frame: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    return frame.rename(columns={key: value for key, value in mapping.items() if key in frame})


@operation("reorder", "Ustunlarni qayta tartiblash", "Structure", ("columns",))
def reorder(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    chosen = [column for column in columns if column in frame]
    return frame[chosen + [column for column in frame if column not in chosen]].copy()


@operation("trim", "Matn bo'shliqlarini tozalash", "Text", ("columns",))
def trim(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for column in columns:
        out[column] = out[column].astype("string").str.strip()
    return out


@operation("case", "Matn registrini o'zgartirish", "Text", ("columns", "mode"))
def change_case(frame: pd.DataFrame, columns: list[str], mode: str = "lower") -> pd.DataFrame:
    out = frame.copy()
    for column in columns:
        values = out[column].astype("string").str
        out[column] = values.upper() if mode == "upper" else values.title() if mode == "title" else values.lower()
    return out


@operation("replace", "Matnni almashtirish", "Text", ("column", "old", "new"))
def replace(frame: pd.DataFrame, column: str, old: str, new: str,
            regex: bool = False) -> pd.DataFrame:
    out = frame.copy()
    out[column] = out[column].astype("string").str.replace(old, new, regex=regex)
    return out


@operation("split", "Ustunni qismlarga ajratish", "Text", ("column", "separator"))
def split(frame: pd.DataFrame, column: str, separator: str = " ", max_parts: int = 3) -> pd.DataFrame:
    out = frame.copy()
    parts = out[column].astype("string").str.split(separator, n=max(1, max_parts) - 1, expand=True)
    for index in range(parts.shape[1]):
        out[f"{column}_part_{index + 1}"] = parts[index]
    return out


@operation("extract", "Regex guruhini ajratish", "Text", ("column", "pattern", "new_name"))
def extract(frame: pd.DataFrame, column: str, pattern: str, new_name: str = "extracted") -> pd.DataFrame:
    out = frame.copy()
    values = out[column].astype("string").str.extract(pattern, expand=True)
    for index in range(values.shape[1]):
        out[new_name if values.shape[1] == 1 else f"{new_name}_{index + 1}"] = values[index]
    return out


@operation("bin", "Sonlarni intervalga ajratish", "Enrichment", ("column", "bins"))
def bin_values(frame: pd.DataFrame, column: str, bins: int = 5) -> pd.DataFrame:
    out = frame.copy()
    out[f"{column}_bin"] = pd.cut(pd.to_numeric(out[column], errors="coerce"), bins=max(2, int(bins)))
    return out


@operation("rank", "Qiymatlarni rank qilish", "Enrichment", ("column",))
def rank(frame: pd.DataFrame, column: str, ascending: bool = False) -> pd.DataFrame:
    out = frame.copy()
    out[f"{column}_rank"] = out[column].rank(ascending=ascending, method="dense")
    return out


@operation("lag", "Oldingi qiymatni chiqarish", "Time series", ("column", "periods"))
def lag(frame: pd.DataFrame, column: str, periods: int = 1) -> pd.DataFrame:
    out = frame.copy()
    out[f"{column}_lag_{periods}"] = out[column].shift(int(periods))
    return out


@operation("rolling", "Siljuvchi statistika", "Time series", ("column", "window"))
def rolling(frame: pd.DataFrame, column: str, window: int = 7,
            statistic: str = "mean") -> pd.DataFrame:
    out = frame.copy()
    roll = pd.to_numeric(out[column], errors="coerce").rolling(max(2, int(window)))
    values = roll.sum() if statistic == "sum" else roll.std() if statistic == "std" else roll.mean()
    out[f"{column}_rolling_{statistic}_{window}"] = values
    return out


@operation("percent_change", "Foiz o'zgarishi", "Time series", ("column",))
def percent_change(frame: pd.DataFrame, column: str, periods: int = 1) -> pd.DataFrame:
    out = frame.copy()
    out[f"{column}_pct_change"] = pd.to_numeric(out[column], errors="coerce").pct_change(periods) * 100
    return out


@operation("cumulative", "Kumulyativ qiymat", "Time series", ("column",))
def cumulative(frame: pd.DataFrame, column: str, mode: str = "sum") -> pd.DataFrame:
    out = frame.copy()
    values = pd.to_numeric(out[column], errors="coerce")
    out[f"{column}_cumulative_{mode}"] = values.cummax() if mode == "max" else values.cumprod() if mode == "product" else values.cumsum()
    return out


@operation("resample", "Vaqt bo'yicha agregatsiya", "Time series", ("timestamp", "frequency"))
def resample(frame: pd.DataFrame, timestamp: str, frequency: str = "D",
             aggregation: str = "sum") -> pd.DataFrame:
    out = frame.copy()
    out[timestamp] = pd.to_datetime(out[timestamp], errors="coerce")
    numeric = list(out.select_dtypes(include=np.number).columns)
    grouped = out.set_index(timestamp)[numeric].resample(frequency)
    return (grouped.mean() if aggregation == "mean" else grouped.median() if aggregation == "median" else grouped.sum()).reset_index()


@operation("one_hot", "One-hot encoding", "Enrichment", ("columns",))
def one_hot(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return pd.get_dummies(frame, columns=columns, dummy_na=False, dtype="Int8")


@operation("label_encode", "Kategoriya kodlash", "Enrichment", ("columns",))
def label_encode(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for column in columns:
        out[column] = pd.Categorical(out[column]).codes
    return out


@operation("transpose", "Jadvalni transponatsiya qilish", "Reshape")
def transpose(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.transpose().reset_index()
