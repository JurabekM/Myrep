"""Ma'lumotni tahrirlash amallari (transform engine) va undo/redo tarixi.

Har bir amal — ``OPS`` registridagi sof funksiya: ``fn(df, **params) -> df``.
GUI shu registrni o'qib, forma maydonlarini avtomatik quradi.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd

from ..config import MAX_CATEGORY_ONEHOT, MAX_HISTORY

# ---------------------------------------------------------------------------
# Registr
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
    """Registrdagi amalni qo'llaydi."""
    spec = OPS.get(key)
    if spec is None:
        raise KeyError(f"Noma'lum amal: {key}")
    out = spec.fn(df, **params)
    if not isinstance(out, pd.DataFrame):
        raise TypeError(f"'{key}' amali DataFrame qaytarmadi")
    return out


def describe_op(key: str, params: dict[str, Any]) -> str:
    spec = OPS.get(key)
    label = spec.label if spec else key
    if not params:
        return label
    shown = ", ".join(f"{k}={v}" for k, v in params.items() if v not in (None, "", []))
    return f"{label}" + (f" ({shown})" if shown else "")


# Parametr turlari: col, cols, text, number, choice, bool, numcol, catcol, dtcol
C = lambda n, label, **kw: dict(name=n, label=label, **kw)  # noqa: E731


# ---------------------------------------------------------------------------
# Qator amallari
# ---------------------------------------------------------------------------
@op("filter_query", "Shart bo'yicha filtr (query)", "Filtr",
    [C("expr", "Ifoda", type="text", placeholder="status >= 400 and method == 'POST'")])
def filter_query(df: pd.DataFrame, expr: str) -> pd.DataFrame:
    """pandas.query sintaksisi bilan qatorlarni filtrlaydi."""
    if not expr or not expr.strip():
        return df
    return df.query(expr, engine="python")


@op("filter_contains", "Matn bo'yicha qidiruv", "Filtr",
    [C("column", "Ustun", type="col"),
     C("pattern", "Matn / regex", type="text"),
     C("regex", "Regex", type="bool", default=False),
     C("case", "Katta-kichik farqi", type="bool", default=False),
     C("invert", "Teskari (mos kelmaganlar)", type="bool", default=False)])
def filter_contains(df: pd.DataFrame, column: str, pattern: str,
                    regex: bool = False, case: bool = False,
                    invert: bool = False) -> pd.DataFrame:
    """Ustunda matn/regex bo'yicha qidiradi."""
    mask = df[column].astype(str).str.contains(pattern, case=case, regex=regex, na=False)
    return df[~mask] if invert else df[mask]


@op("filter_range", "Son oralig'i", "Filtr",
    [C("column", "Ustun", type="numcol"),
     C("low", "Dan", type="number", optional=True),
     C("high", "Gacha", type="number", optional=True)])
def filter_range(df: pd.DataFrame, column: str, low: float | None = None,
                 high: float | None = None) -> pd.DataFrame:
    """Sonli ustunni oraliq bo'yicha filtrlaydi."""
    s = pd.to_numeric(df[column], errors="coerce")
    mask = pd.Series(True, index=df.index)
    if low is not None:
        mask &= s >= float(low)
    if high is not None:
        mask &= s <= float(high)
    return df[mask.fillna(False)]


@op("filter_time", "Vaqt oralig'i", "Filtr",
    [C("column", "Vaqt ustuni", type="dtcol"),
     C("start", "Boshlanish", type="text", placeholder="2024-01-01", optional=True),
     C("end", "Tugash", type="text", placeholder="2024-12-31", optional=True)])
def filter_time(df: pd.DataFrame, column: str, start: str | None = None,
                end: str | None = None) -> pd.DataFrame:
    """Vaqt ustunini oraliq bo'yicha kesadi."""
    s = pd.to_datetime(df[column], errors="coerce")
    mask = pd.Series(True, index=df.index)
    if start:
        mask &= s >= pd.Timestamp(start)
    if end:
        mask &= s <= pd.Timestamp(end)
    return df[mask.fillna(False)]


@op("drop_duplicates", "Dublikatlarni o'chirish", "Tozalash",
    [C("subset", "Ustunlar (bo'sh = hammasi)", type="cols", optional=True),
     C("keep", "Qaysi biri qolsin", type="choice", options=["first", "last", "none"],
       default="first")])
def drop_duplicates(df: pd.DataFrame, subset: list[str] | None = None,
                    keep: str = "first") -> pd.DataFrame:
    """Takroriy qatorlarni o'chiradi."""
    k: Any = False if keep == "none" else keep
    return df.drop_duplicates(subset=subset or None, keep=k)


@op("dropna", "Bo'sh qatorlarni o'chirish", "Tozalash",
    [C("subset", "Ustunlar (bo'sh = hammasi)", type="cols", optional=True),
     C("how", "Shart", type="choice", options=["any", "all"], default="any")])
def dropna(df: pd.DataFrame, subset: list[str] | None = None, how: str = "any") -> pd.DataFrame:
    """Bo'sh qiymatli qatorlarni olib tashlaydi."""
    return df.dropna(subset=subset or None, how=how)


@op("drop_rows", "Tanlangan qatorlarni o'chirish", "Tozalash",
    [C("indices", "Indekslar", type="text", hidden=True)])
def drop_rows(df: pd.DataFrame, indices: list[int] | str) -> pd.DataFrame:
    """Berilgan pozitsiyalardagi qatorlarni o'chiradi."""
    if isinstance(indices, str):
        idx = [int(x) for x in re.findall(r"\d+", indices)]
    else:
        idx = list(indices)
    keep = df.index.difference(df.index[idx])
    return df.loc[keep]


@op("sort", "Saralash", "Tartib",
    [C("by", "Ustun(lar)", type="cols"),
     C("ascending", "O'sish tartibida", type="bool", default=True)])
def sort_values(df: pd.DataFrame, by: list[str] | str, ascending: bool = True) -> pd.DataFrame:
    """Ustun(lar) bo'yicha saralaydi."""
    return df.sort_values(by=[by] if isinstance(by, str) else list(by),
                          ascending=ascending, kind="stable")


@op("sample", "Namuna olish", "Tartib",
    [C("n", "Qator soni", type="number", default=1000),
     C("random_state", "Tasodif urug'i", type="number", default=42)])
def sample(df: pd.DataFrame, n: int = 1000, random_state: int = 42) -> pd.DataFrame:
    """Tasodifiy namuna oladi."""
    n = int(min(int(n), len(df)))
    return df.sample(n=n, random_state=int(random_state)) if n else df


@op("head", "Birinchi N qator", "Tartib", [C("n", "N", type="number", default=1000)])
def head(df: pd.DataFrame, n: int = 1000) -> pd.DataFrame:
    """Faqat birinchi N qatorni qoldiradi."""
    return df.head(int(n))


# ---------------------------------------------------------------------------
# Ustun amallari
# ---------------------------------------------------------------------------
@op("select_cols", "Ustunlarni tanlash", "Ustunlar", [C("columns", "Ustunlar", type="cols")])
def select_cols(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Faqat tanlangan ustunlarni qoldiradi."""
    return df[[c for c in columns if c in df.columns]]


@op("drop_cols", "Ustunlarni o'chirish", "Ustunlar", [C("columns", "Ustunlar", type="cols")])
def drop_cols(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Tanlangan ustunlarni o'chiradi."""
    return df.drop(columns=[c for c in columns if c in df.columns])


@op("rename", "Ustun nomini o'zgartirish", "Ustunlar",
    [C("column", "Ustun", type="col"), C("new_name", "Yangi nom", type="text")])
def rename(df: pd.DataFrame, column: str, new_name: str) -> pd.DataFrame:
    """Ustun nomini o'zgartiradi."""
    return df.rename(columns={column: new_name})


@op("astype", "Turini o'zgartirish", "Ustunlar",
    [C("column", "Ustun", type="col"),
     C("dtype", "Yangi tur", type="choice",
       options=["son", "butun son", "matn", "sana-vaqt", "mantiqiy", "kategoriya"])])
def astype(df: pd.DataFrame, column: str, dtype: str) -> pd.DataFrame:
    """Ustun turini majburiy o'zgartiradi."""
    out = df.copy()
    s = out[column]
    if dtype == "son":
        out[column] = pd.to_numeric(s, errors="coerce")
    elif dtype == "butun son":
        out[column] = pd.to_numeric(s, errors="coerce").astype("Int64")
    elif dtype == "matn":
        out[column] = s.astype(str)
    elif dtype == "sana-vaqt":
        from .logparse import parse_timestamp_series

        out[column] = parse_timestamp_series(s)
    elif dtype == "mantiqiy":
        mapping = {"true": True, "1": True, "yes": True, "ha": True, "t": True,
                   "false": False, "0": False, "no": False, "yo'q": False, "f": False}
        out[column] = s.astype(str).str.lower().str.strip().map(mapping)
    elif dtype == "kategoriya":
        out[column] = s.astype("category")
    return out


@op("fillna", "Bo'shliklarni to'ldirish", "Tozalash",
    [C("columns", "Ustunlar (bo'sh = hammasi)", type="cols", optional=True),
     C("method", "Usul", type="choice",
       options=["qiymat", "o'rtacha", "mediana", "moda", "oldingi", "keyingi",
                "nol", "chiziqli interpolyatsiya"], default="mediana"),
     C("value", "Qiymat", type="text", optional=True)])
def fillna(df: pd.DataFrame, columns: list[str] | None = None,
           method: str = "mediana", value: Any = None) -> pd.DataFrame:
    """Bo'sh kataklarni tanlangan strategiya bilan to'ldiradi."""
    out = df.copy()
    cols = columns or list(out.columns)
    for c in cols:
        if c not in out.columns:
            continue
        s = out[c]
        if method == "qiymat":
            out[c] = s.fillna(value)
        elif method == "nol":
            out[c] = s.fillna(0)
        elif method == "oldingi":
            out[c] = s.ffill()
        elif method == "keyingi":
            out[c] = s.bfill()
        elif method == "o'rtacha" and pd.api.types.is_numeric_dtype(s):
            out[c] = s.fillna(s.mean())
        elif method == "mediana" and pd.api.types.is_numeric_dtype(s):
            out[c] = s.fillna(s.median())
        elif method == "chiziqli interpolyatsiya" and pd.api.types.is_numeric_dtype(s):
            out[c] = s.interpolate(limit_direction="both")
        elif method == "moda":
            m = s.mode()
            if not m.empty:
                out[c] = s.fillna(m.iloc[0])
    return out


@op("replace", "Almashtirish", "Matn",
    [C("column", "Ustun", type="col"),
     C("find", "Nimani", type="text"),
     C("repl", "Nimaga", type="text"),
     C("regex", "Regex", type="bool", default=False)])
def replace(df: pd.DataFrame, column: str, find: str, repl: str,
            regex: bool = False) -> pd.DataFrame:
    """Ustundagi matnni almashtiradi."""
    out = df.copy()
    out[column] = out[column].astype(str).str.replace(find, repl, regex=regex)
    return out


@op("str_op", "Matn amali", "Matn",
    [C("column", "Ustun", type="col"),
     C("action", "Amal", type="choice",
       options=["kichik harf", "katta harf", "bosh harf", "probellarni kesish",
                "raqamlarni olib tashlash", "faqat raqamlar", "uzunlik",
                "maxsus belgilarni tozalash"])])
def str_op(df: pd.DataFrame, column: str, action: str) -> pd.DataFrame:
    """Matn ustuniga standart amallarni qo'llaydi."""
    out = df.copy()
    s = out[column].astype(str)
    ops = {
        "kichik harf": lambda: s.str.lower(),
        "katta harf": lambda: s.str.upper(),
        "bosh harf": lambda: s.str.title(),
        "probellarni kesish": lambda: s.str.strip().str.replace(r"\s+", " ", regex=True),
        "raqamlarni olib tashlash": lambda: s.str.replace(r"\d+", "", regex=True),
        "faqat raqamlar": lambda: pd.to_numeric(
            s.str.replace(r"[^\d.\-]", "", regex=True), errors="coerce"),
        "uzunlik": lambda: s.str.len(),
        "maxsus belgilarni tozalash": lambda: s.str.replace(r"[^\w\s]", "", regex=True),
    }
    out[column] = ops[action]()
    return out


@op("split_col", "Ustunni bo'lish", "Matn",
    [C("column", "Ustun", type="col"),
     C("sep", "Ajratgich", type="text", default=" "),
     C("maxsplit", "Maks. bo'lish", type="number", default=2)])
def split_col(df: pd.DataFrame, column: str, sep: str = " ", maxsplit: int = 2) -> pd.DataFrame:
    """Matn ustunini ajratgich bo'yicha bir nechta ustunga bo'ladi."""
    out = df.copy()
    parts = out[column].astype(str).str.split(sep, n=int(maxsplit), expand=True)
    for i in range(parts.shape[1]):
        out[f"{column}_{i + 1}"] = parts[i]
    return out


@op("extract", "Regex bilan ajratib olish", "Matn",
    [C("column", "Ustun", type="col"),
     C("pattern", "Regex (guruh bilan)", type="text", placeholder=r"(\d+)ms"),
     C("new_name", "Yangi ustun nomi", type="text", optional=True)])
def extract(df: pd.DataFrame, column: str, pattern: str,
            new_name: str | None = None) -> pd.DataFrame:
    """Regex guruhi bo'yicha yangi ustun yaratadi."""
    out = df.copy()
    res = out[column].astype(str).str.extract(pattern, expand=True)
    if res.shape[1] == 1:
        out[new_name or f"{column}_extract"] = res[0]
    else:
        for i in range(res.shape[1]):
            out[f"{new_name or column}_g{i + 1}"] = res[i]
    return out


@op("derive", "Yangi ustun (ifoda)", "Hisoblash",
    [C("new_name", "Yangi ustun nomi", type="text"),
     C("expr", "Ifoda", type="text", placeholder="bytes / 1024")])
def derive(df: pd.DataFrame, new_name: str, expr: str) -> pd.DataFrame:
    """pandas.eval ifodasidan yangi ustun hisoblaydi."""
    out = df.copy()
    try:
        out[new_name] = out.eval(expr, engine="python")
    except Exception:
        # eval qo'llab-quvvatlamaydigan ifodalar uchun cheklangan fallback
        env = {c: out[c] for c in out.columns}
        env.update({"np": np, "pd": pd, "abs": abs, "min": min, "max": max,
                    "round": round, "len": len})
        out[new_name] = eval(expr, {"__builtins__": {}}, env)  # noqa: S307
    return out


@op("datetime_parts", "Sanadan qismlar ajratish", "Hisoblash",
    [C("column", "Vaqt ustuni", type="dtcol"),
     C("parts", "Qismlar", type="multichoice",
       options=["yil", "oy", "kun", "soat", "daqiqa", "hafta kuni", "hafta",
                "chorak", "sana", "kun_vaqti"],
       default=["yil", "oy", "kun", "soat"])])
def datetime_parts(df: pd.DataFrame, column: str, parts: list[str]) -> pd.DataFrame:
    """Vaqt ustunidan yil/oy/soat kabi xususiyatlarni chiqaradi."""
    out = df.copy()
    d = pd.to_datetime(out[column], errors="coerce")
    mapping = {
        "yil": lambda: d.dt.year, "oy": lambda: d.dt.month, "kun": lambda: d.dt.day,
        "soat": lambda: d.dt.hour, "daqiqa": lambda: d.dt.minute,
        "hafta kuni": lambda: d.dt.dayofweek, "hafta": lambda: d.dt.isocalendar().week.astype("Int64"),
        "chorak": lambda: d.dt.quarter, "sana": lambda: d.dt.date.astype(str),
        "kun_vaqti": lambda: pd.cut(
            d.dt.hour, bins=[-1, 5, 11, 17, 21, 24],
            labels=["tun", "ertalab", "kunduz", "kechqurun", "tun2"]).astype(str),
    }
    for p in parts:
        if p in mapping:
            out[f"{column}_{p}"] = mapping[p]()
    return out


@op("bin_numeric", "Sonni guruhlarga bo'lish", "Hisoblash",
    [C("column", "Ustun", type="numcol"),
     C("bins", "Guruhlar soni", type="number", default=5),
     C("strategy", "Usul", type="choice", options=["teng oraliq", "kvantil"],
       default="kvantil")])
def bin_numeric(df: pd.DataFrame, column: str, bins: int = 5,
                strategy: str = "kvantil") -> pd.DataFrame:
    """Uzluksiz sonni diskret guruhlarga (bin) ajratadi."""
    out = df.copy()
    s = pd.to_numeric(out[column], errors="coerce")
    if strategy == "kvantil":
        out[f"{column}_bin"] = pd.qcut(s, q=int(bins), duplicates="drop").astype(str)
    else:
        out[f"{column}_bin"] = pd.cut(s, bins=int(bins)).astype(str)
    return out


@op("scale", "Masshtablash", "Hisoblash",
    [C("columns", "Ustunlar", type="numcols"),
     C("method", "Usul", type="choice",
       options=["standart (z-score)", "min-max", "robust", "log1p"],
       default="standart (z-score)"),
     C("inplace", "Ustunni almashtirish", type="bool", default=True)])
def scale(df: pd.DataFrame, columns: list[str], method: str = "standart (z-score)",
          inplace: bool = True) -> pd.DataFrame:
    """Sonli ustunlarni normallashtiradi."""
    out = df.copy()
    for c in columns:
        s = pd.to_numeric(out[c], errors="coerce")
        if method == "standart (z-score)":
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


@op("clip_outliers", "Chetlanuvchilarni cheklash", "Tozalash",
    [C("columns", "Ustunlar", type="numcols"),
     C("method", "Usul", type="choice", options=["IQR", "kvantil 1–99", "z-score 3"],
       default="IQR"),
     C("action", "Amal", type="choice", options=["cheklash (clip)", "o'chirish"],
       default="cheklash (clip)")])
def clip_outliers(df: pd.DataFrame, columns: list[str], method: str = "IQR",
                  action: str = "cheklash (clip)") -> pd.DataFrame:
    """Chetlanuvchi qiymatlarni cheklaydi yoki qatorini o'chiradi."""
    out = df.copy()
    mask_drop = pd.Series(False, index=out.index)
    for c in columns:
        s = pd.to_numeric(out[c], errors="coerce")
        if method == "IQR":
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        elif method == "kvantil 1–99":
            lo, hi = s.quantile(0.01), s.quantile(0.99)
        else:
            mu, sd = s.mean(), s.std(ddof=0) or 1.0
            lo, hi = mu - 3 * sd, mu + 3 * sd
        if action.startswith("cheklash"):
            out[c] = s.clip(lo, hi)
        else:
            mask_drop |= (s < lo) | (s > hi)
    return out[~mask_drop.fillna(False)] if not action.startswith("cheklash") else out


@op("onehot", "One-hot kodlash", "Kodlash",
    [C("columns", "Ustunlar", type="catcols"),
     C("drop_first", "Birinchisini tashlab yuborish", type="bool", default=False)])
def onehot(df: pd.DataFrame, columns: list[str], drop_first: bool = False) -> pd.DataFrame:
    """Kategorik ustunlarni ikkilik ustunlarga aylantiradi."""
    safe = [c for c in columns if df[c].nunique(dropna=True) <= MAX_CATEGORY_ONEHOT]
    if not safe:
        raise ValueError(
            f"Tanlangan ustunlarda {MAX_CATEGORY_ONEHOT} tadan ko'p unikal qiymat bor")
    return pd.get_dummies(df, columns=safe, drop_first=drop_first, dtype=int)


@op("label_encode", "Label kodlash", "Kodlash", [C("columns", "Ustunlar", type="catcols")])
def label_encode(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Kategoriyalarni butun son kodlariga aylantiradi."""
    out = df.copy()
    for c in columns:
        out[f"{c}_code"] = out[c].astype("category").cat.codes.replace(-1, np.nan)
    return out


# ---------------------------------------------------------------------------
# Tuzilma amallari
# ---------------------------------------------------------------------------
@op("groupby_agg", "Guruhlab jamlash", "Tuzilma",
    [C("by", "Guruhlash ustuni", type="cols"),
     C("value", "Qiymat ustuni", type="numcol", optional=True),
     C("aggs", "Funksiyalar", type="multichoice",
       options=["count", "sum", "mean", "median", "min", "max", "std", "nunique"],
       default=["count", "mean"])])
def groupby_agg(df: pd.DataFrame, by: list[str], value: str | None = None,
                aggs: list[str] | None = None) -> pd.DataFrame:
    """Guruhlab yig'ma jadval hosil qiladi (natija — yangi jadval)."""
    aggs = aggs or ["count"]
    by = [by] if isinstance(by, str) else list(by)
    g = df.groupby(by, dropna=False, observed=False)
    if not value:
        return g.size().reset_index(name="count")
    return g[value].agg(aggs).reset_index()


@op("pivot", "Pivot jadval", "Tuzilma",
    [C("index", "Qator ustuni", type="col"),
     C("columns", "Ustun ustuni", type="col"),
     C("values", "Qiymat", type="numcol"),
     C("aggfunc", "Funksiya", type="choice",
       options=["mean", "sum", "count", "median", "max", "min"], default="mean")])
def pivot(df: pd.DataFrame, index: str, columns: str, values: str,
          aggfunc: str = "mean") -> pd.DataFrame:
    """Pivot (kesishma) jadval quradi."""
    out = pd.pivot_table(df, index=index, columns=columns, values=values,
                         aggfunc=aggfunc, observed=False)
    out.columns = [str(c) for c in out.columns]
    return out.reset_index()


@op("melt", "Keng → uzun (melt)", "Tuzilma",
    [C("id_vars", "Saqlanadigan ustunlar", type="cols"),
     C("value_vars", "Yig'iladigan ustunlar", type="cols", optional=True)])
def melt(df: pd.DataFrame, id_vars: list[str],
         value_vars: list[str] | None = None) -> pd.DataFrame:
    """Keng jadvalni uzun ko'rinishga aylantiradi."""
    return df.melt(id_vars=id_vars, value_vars=value_vars or None,
                   var_name="o'zgaruvchi", value_name="qiymat")


@op("resample", "Vaqt bo'yicha qayta namunalash", "Tuzilma",
    [C("column", "Vaqt ustuni", type="dtcol"),
     C("freq", "Chastota", type="choice",
       options=["1s", "10s", "1min", "5min", "15min", "1h", "6h", "1D", "1W", "1ME"],
       default="1h"),
     C("value", "Qiymat ustuni", type="numcol", optional=True),
     C("agg", "Funksiya", type="choice",
       options=["count", "mean", "sum", "median", "min", "max"], default="count")])
def resample(df: pd.DataFrame, column: str, freq: str = "1h",
             value: str | None = None, agg: str = "count") -> pd.DataFrame:
    """Vaqt qatorini berilgan chastotada jamlaydi."""
    from .profile import time_series

    return time_series(df, column, freq=freq, value=value, agg=agg)


@op("remove_constant", "Doimiy ustunlarni o'chirish", "Tozalash", [])
def remove_constant(df: pd.DataFrame) -> pd.DataFrame:
    """Bitta unikal qiymatga ega ustunlarni olib tashlaydi."""
    keep = [c for c in df.columns if df[c].nunique(dropna=False) > 1]
    return df[keep] if keep else df


@op("reset_index", "Indeksni tiklash", "Tuzilma", [])
def reset_index(df: pd.DataFrame) -> pd.DataFrame:
    """Indeksni 0..N ga qaytaradi."""
    return df.reset_index(drop=True)


@op("transpose", "Transponatsiya", "Tuzilma", [])
def transpose(df: pd.DataFrame) -> pd.DataFrame:
    """Qator va ustunlarni almashtiradi."""
    out = df.T.reset_index()
    out.columns = [str(c) for c in out.columns]
    return out


def op_groups() -> dict[str, list[OpSpec]]:
    """Amallarni GUI uchun guruhlab qaytaradi."""
    groups: dict[str, list[OpSpec]] = {}
    for spec in OPS.values():
        groups.setdefault(spec.group, []).append(spec)
    for lst in groups.values():
        lst.sort(key=lambda s: s.label)
    return groups


# ---------------------------------------------------------------------------
# Undo / redo tarixi
# ---------------------------------------------------------------------------
@dataclass
class HistoryEntry:
    label: str
    df: pd.DataFrame
    shape: tuple[int, int]


class History:
    """Cheklangan chuqurlikdagi undo/redo steki."""

    def __init__(self, df: pd.DataFrame, label: str = "Yuklandi",
                 max_len: int = MAX_HISTORY) -> None:
        self.max_len = max_len
        self._stack: list[HistoryEntry] = [HistoryEntry(label, df, df.shape)]
        self._idx = 0

    # ---- holat
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

    # ---- amallar
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

    def reset(self, df: pd.DataFrame, label: str = "Yuklandi") -> None:
        self._stack = [HistoryEntry(label, df, df.shape)]
        self._idx = 0
