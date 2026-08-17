"""Business KPI computations backed by SQL + pandas."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core.cache import cached
from database.engine import read_df


@dataclass
class KPISummary:
    """Headline figures shown on the main dashboard."""

    year: int
    total_area_ha: float
    farms: int
    farmers: int
    fields: int
    crops: int
    avg_yield_t_ha: float
    production_t: float
    income: float
    expense: float
    profit: float
    roi_percent: float
    avg_ndvi: float
    water_million_m3: float


@cached(ttl=120)
def latest_year() -> int:
    """Most recent year that has yield records."""
    df = read_df("SELECT MAX(year) AS y FROM yield_records")
    value = df.iloc[0]["y"]
    return int(value) if pd.notna(value) else pd.Timestamp.now().year


@cached(ttl=120)
def available_years() -> list[int]:
    df = read_df("SELECT DISTINCT year FROM yield_records ORDER BY year")
    return [int(y) for y in df["year"].tolist()]


@cached(ttl=120)
def compute_kpi(year: int | None = None) -> KPISummary:
    """Aggregate the platform-wide KPI card values for a given year."""
    year = year or latest_year()
    counts = read_df(
        "SELECT (SELECT COUNT(*) FROM farms) AS farms,"
        " (SELECT COUNT(*) FROM farmers) AS farmers,"
        " (SELECT COUNT(*) FROM fields) AS fields,"
        " (SELECT COUNT(*) FROM crops) AS crops,"
        " (SELECT COALESCE(SUM(area_ha),0) FROM fields) AS area"
    ).iloc[0]
    yields = read_df(
        "SELECT COALESCE(AVG(yield_t_ha),0) AS avg_yield,"
        " COALESCE(SUM(production_t),0) AS production"
        " FROM yield_records WHERE year = :y", {"y": year},
    ).iloc[0]
    finance = read_df(
        "SELECT category, COALESCE(SUM(amount),0) AS total FROM finance_records"
        " WHERE year = :y GROUP BY category", {"y": year},
    ).set_index("category")["total"]
    income = float(finance.get("income", 0.0))
    expense = float(finance.get("expense", 0.0))
    profit = income - expense
    ndvi = read_df(
        "SELECT COALESCE(AVG(ndvi),0) AS ndvi FROM satellite_indices"
        " WHERE date >= date('now','-60 day')"
    ).iloc[0]["ndvi"]
    water = read_df(
        "SELECT COALESCE(SUM(water_m3),0) AS w FROM irrigation_records"
        " WHERE strftime('%Y', date) = :y", {"y": str(year)},
    ).iloc[0]["w"]

    return KPISummary(
        year=year,
        total_area_ha=round(float(counts["area"]), 1),
        farms=int(counts["farms"]), farmers=int(counts["farmers"]),
        fields=int(counts["fields"]), crops=int(counts["crops"]),
        avg_yield_t_ha=round(float(yields["avg_yield"]), 2),
        production_t=round(float(yields["production"]), 0),
        income=income, expense=expense, profit=profit,
        roi_percent=round(profit / expense * 100, 1) if expense else 0.0,
        avg_ndvi=round(float(ndvi), 3),
        water_million_m3=round(float(water) / 1_000_000, 2),
    )


@cached(ttl=120)
def yield_trend() -> pd.DataFrame:
    """Average yield and total production per year."""
    return read_df(
        "SELECT year, ROUND(AVG(yield_t_ha),2) AS avg_yield,"
        " ROUND(SUM(production_t),0) AS production"
        " FROM yield_records GROUP BY year ORDER BY year"
    )


@cached(ttl=120)
def yield_by_region(year: int | None = None) -> pd.DataFrame:
    """Average yield / production / area grouped by region for a year."""
    year = year or latest_year()
    return read_df(
        "SELECT r.name AS region, ROUND(AVG(y.yield_t_ha),2) AS avg_yield,"
        " ROUND(SUM(y.production_t),0) AS production,"
        " ROUND(SUM(y.area_ha),0) AS area"
        " FROM yield_records y"
        " JOIN fields f ON f.id = y.field_id"
        " JOIN farms fa ON fa.id = f.farm_id"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " WHERE y.year = :y GROUP BY r.name ORDER BY production DESC", {"y": year},
    )


@cached(ttl=120)
def crop_distribution(year: int | None = None) -> pd.DataFrame:
    """Sown area share per crop for a year."""
    year = year or latest_year()
    return read_df(
        "SELECT c.name AS crop, ROUND(SUM(y.area_ha),0) AS area,"
        " ROUND(SUM(y.production_t),0) AS production,"
        " ROUND(AVG(y.yield_t_ha),2) AS avg_yield"
        " FROM yield_records y JOIN crops c ON c.id = y.crop_id"
        " WHERE y.year = :y GROUP BY c.name ORDER BY area DESC", {"y": year},
    )


@cached(ttl=120)
def region_crop_matrix(year: int | None = None) -> pd.DataFrame:
    """Region x crop average-yield pivot used for the analytics heatmap."""
    year = year or latest_year()
    df = read_df(
        "SELECT r.name AS region, c.name AS crop, AVG(y.yield_t_ha) AS avg_yield"
        " FROM yield_records y"
        " JOIN crops c ON c.id = y.crop_id"
        " JOIN fields f ON f.id = y.field_id"
        " JOIN farms fa ON fa.id = f.farm_id"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " WHERE y.year = :y GROUP BY r.name, c.name", {"y": year},
    )
    if df.empty:
        return df
    return df.pivot_table(index="region", columns="crop", values="avg_yield").round(2)


@cached(ttl=120)
def rainfall_yield_correlation() -> tuple[pd.DataFrame, float]:
    """Season rainfall vs average yield per district-year, plus correlation."""
    df = read_df(
        "SELECT d.id AS district_id, d.name AS district, y.year,"
        " AVG(y.yield_t_ha) AS avg_yield"
        " FROM yield_records y"
        " JOIN fields f ON f.id = y.field_id"
        " JOIN farms fa ON fa.id = f.farm_id"
        " JOIN districts d ON d.id = fa.district_id"
        " GROUP BY d.id, y.year"
    )
    rain = read_df(
        "SELECT district_id, CAST(strftime('%Y', date) AS INTEGER) AS year,"
        " SUM(precipitation_mm) AS precip"
        " FROM weather_records"
        " WHERE CAST(strftime('%m', date) AS INTEGER) BETWEEN 4 AND 9"
        " GROUP BY district_id, year"
    )
    merged = df.merge(rain, on=["district_id", "year"], how="inner")
    corr = float(merged["precip"].corr(merged["avg_yield"])) if len(merged) > 2 else 0.0
    return merged, round(corr, 3)


@cached(ttl=120)
def top_farms(year: int | None = None, limit: int = 10) -> pd.DataFrame:
    """Most productive farms of the year."""
    year = year or latest_year()
    return read_df(
        "SELECT fa.name AS farm, r.name AS region,"
        " ROUND(SUM(y.production_t),0) AS production,"
        " ROUND(AVG(y.yield_t_ha),2) AS avg_yield"
        " FROM yield_records y"
        " JOIN fields f ON f.id = y.field_id"
        " JOIN farms fa ON fa.id = f.farm_id"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " WHERE y.year = :y GROUP BY fa.id ORDER BY production DESC LIMIT :n",
        {"y": year, "n": limit},
    )
