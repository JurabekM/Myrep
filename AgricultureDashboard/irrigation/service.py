"""Irrigation analytics: usage by region/crop/method, efficiency metrics."""
from __future__ import annotations

import pandas as pd

from core.cache import cached
from database.engine import read_df


@cached(ttl=120)
def usage_by_region(year: int) -> pd.DataFrame:
    """Total water (million m³) and irrigated area per region."""
    return read_df(
        "SELECT r.name AS region,"
        " ROUND(SUM(i.water_m3)/1000000.0, 2) AS water_mln_m3,"
        " ROUND(SUM(DISTINCT f.area_ha), 0) AS area"
        " FROM irrigation_records i"
        " JOIN fields f ON f.id = i.field_id"
        " JOIN farms fa ON fa.id = f.farm_id"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " WHERE strftime('%Y', i.date) = :y"
        " GROUP BY r.name ORDER BY water_mln_m3 DESC", {"y": str(year)},
    )


@cached(ttl=120)
def usage_by_method(year: int) -> pd.DataFrame:
    """Water split by irrigation method (drip vs furrow vs sprinkler...)."""
    return read_df(
        "SELECT method, ROUND(SUM(water_m3)/1000000.0, 2) AS water_mln_m3,"
        " COUNT(*) AS events"
        " FROM irrigation_records WHERE strftime('%Y', date) = :y"
        " GROUP BY method ORDER BY water_mln_m3 DESC", {"y": str(year)},
    )


@cached(ttl=120)
def monthly_usage(year: int) -> pd.DataFrame:
    """Monthly water usage profile."""
    return read_df(
        "SELECT CAST(strftime('%m', date) AS INTEGER) AS month,"
        " ROUND(SUM(water_m3)/1000000.0, 2) AS water_mln_m3"
        " FROM irrigation_records WHERE strftime('%Y', date) = :y"
        " GROUP BY month ORDER BY month", {"y": str(year)},
    )


@cached(ttl=120)
def efficiency_by_crop(year: int) -> pd.DataFrame:
    """Water productivity: m³ of water per tonne of produce, by crop."""
    df = read_df(
        "SELECT c.name AS crop, SUM(y.production_t) AS production,"
        " SUM(iw.water) AS water_m3"
        " FROM yield_records y"
        " JOIN crops c ON c.id = y.crop_id"
        " JOIN (SELECT field_id, CAST(strftime('%Y', date) AS INTEGER) AS yr,"
        "        SUM(water_m3) AS water FROM irrigation_records"
        "        GROUP BY field_id, yr) iw"
        "   ON iw.field_id = y.field_id AND iw.yr = y.year"
        " WHERE y.year = :y GROUP BY c.name", {"y": year},
    )
    if df.empty:
        return df
    df["m3_per_tonne"] = (df["water_m3"] / df["production"].clip(lower=0.1)).round(0)
    return df.sort_values("m3_per_tonne")
