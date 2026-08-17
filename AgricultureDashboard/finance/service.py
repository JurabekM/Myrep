"""Financial analytics: P&L, ROI, credits and subsidies."""
from __future__ import annotations

import pandas as pd

from core.cache import cached
from database.engine import read_df


@cached(ttl=120)
def yearly_summary() -> pd.DataFrame:
    """Income / expense / profit / ROI per year (platform-wide)."""
    df = read_df(
        "SELECT year,"
        " SUM(CASE WHEN category='income' THEN amount ELSE 0 END) AS income,"
        " SUM(CASE WHEN category='expense' THEN amount ELSE 0 END) AS expense,"
        " SUM(CASE WHEN category='credit' THEN amount ELSE 0 END) AS credit,"
        " SUM(CASE WHEN category='subsidy' THEN amount ELSE 0 END) AS subsidy"
        " FROM finance_records GROUP BY year ORDER BY year"
    )
    if df.empty:
        return df
    df["profit"] = df["income"] - df["expense"]
    df["roi"] = (df["profit"] / df["expense"].clip(lower=1) * 100).round(1)
    return df


@cached(ttl=120)
def by_region(year: int) -> pd.DataFrame:
    """Regional profitability table."""
    df = read_df(
        "SELECT r.name AS region,"
        " SUM(CASE WHEN fr.category='income' THEN fr.amount ELSE 0 END) AS income,"
        " SUM(CASE WHEN fr.category='expense' THEN fr.amount ELSE 0 END) AS expense,"
        " SUM(CASE WHEN fr.category='credit' THEN fr.amount ELSE 0 END) AS credit,"
        " SUM(CASE WHEN fr.category='subsidy' THEN fr.amount ELSE 0 END) AS subsidy"
        " FROM finance_records fr"
        " JOIN farms fa ON fa.id = fr.farm_id"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " WHERE fr.year = :y GROUP BY r.name", {"y": year},
    )
    if df.empty:
        return df
    df["profit"] = df["income"] - df["expense"]
    df["roi"] = (df["profit"] / df["expense"].clip(lower=1) * 100).round(1)
    return df.sort_values("profit", ascending=False)


@cached(ttl=120)
def farm_profitability(year: int, limit: int = 15) -> pd.DataFrame:
    """Per-farm profit ranking for the given year."""
    df = read_df(
        "SELECT fa.name AS farm, r.name AS region,"
        " SUM(CASE WHEN fr.category='income' THEN fr.amount ELSE 0 END) AS income,"
        " SUM(CASE WHEN fr.category='expense' THEN fr.amount ELSE 0 END) AS expense"
        " FROM finance_records fr"
        " JOIN farms fa ON fa.id = fr.farm_id"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " WHERE fr.year = :y GROUP BY fa.id", {"y": year},
    )
    if df.empty:
        return df
    df["profit"] = df["income"] - df["expense"]
    df["roi"] = (df["profit"] / df["expense"].clip(lower=1) * 100).round(1)
    return df.sort_values("profit", ascending=False).head(limit)


@cached(ttl=120)
def credits_and_subsidies(year: int) -> pd.DataFrame:
    """Credit / subsidy registry rows for the given year."""
    return read_df(
        "SELECT fa.name AS farm, fr.category, fr.amount, fr.note"
        " FROM finance_records fr JOIN farms fa ON fa.id = fr.farm_id"
        " WHERE fr.year = :y AND fr.category IN ('credit','subsidy')"
        " ORDER BY fr.amount DESC", {"y": year},
    )
