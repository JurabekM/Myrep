"""Automatic insight/alert generation shown on the dashboard and used by the AI."""
from __future__ import annotations

import pandas as pd

from analytics.kpi import latest_year
from analytics.timeseries import percent_change, zscore_anomalies
from core.cache import cached
from database.engine import read_df


@cached(ttl=300)
def generate_alerts() -> list[dict[str, str]]:
    """Rule-based alerts: droughts, yield drops, price spikes, NDVI decline, losses."""
    alerts: list[dict[str, str]] = []
    year = latest_year()
    alerts.extend(_drought_alerts(year))
    alerts.extend(_yield_drop_alerts(year))
    alerts.extend(_price_spike_alerts())
    alerts.extend(_ndvi_alerts())
    alerts.extend(_loss_alerts(year))
    severity_rank = {"error": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_rank.get(a["level"], 3))
    return alerts[:12]


def _drought_alerts(year: int) -> list[dict[str, str]]:
    df = read_df(
        "SELECT r.name AS region, CAST(strftime('%Y', w.date) AS INTEGER) AS year,"
        " SUM(w.precipitation_mm) AS precip"
        " FROM weather_records w"
        " JOIN districts d ON d.id = w.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " WHERE CAST(strftime('%m', w.date) AS INTEGER) BETWEEN 4 AND 9"
        " GROUP BY r.name, year"
    )
    alerts = []
    for region, group in df.groupby("region"):
        group = group.sort_values("year")
        mean = group["precip"].mean()
        last = group[group.year == year]
        if last.empty or mean <= 0:
            continue
        value = float(last.iloc[0]["precip"])
        deficit = (mean - value) / mean * 100
        if deficit > 30:
            alerts.append({
                "level": "error", "title": f"{region}: qurg'oqchilik xavfi",
                "detail": f"{year}-yil mavsumida yog'ingarchilik o'rtachadan "
                          f"{deficit:.0f}% kam ({value:.0f} mm).",
            })
    return alerts


def _yield_drop_alerts(year: int) -> list[dict[str, str]]:
    df = read_df(
        "SELECT r.name AS region, y.year, AVG(y.yield_t_ha) AS avg_yield"
        " FROM yield_records y"
        " JOIN fields f ON f.id = y.field_id"
        " JOIN farms fa ON fa.id = f.farm_id"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " GROUP BY r.name, y.year"
    )
    alerts = []
    for region, group in df.groupby("region"):
        group = group.sort_values("year")
        if len(group) < 2:
            continue
        prev, curr = group.iloc[-2]["avg_yield"], group.iloc[-1]["avg_yield"]
        change = percent_change(float(prev), float(curr))
        if change < -12:
            alerts.append({
                "level": "warning", "title": f"{region}: hosildorlik pasaygan",
                "detail": f"{int(group.iloc[-1]['year'])}-yilda o'rtacha hosildorlik "
                          f"{change:.1f}% ga kamaydi ({prev:.2f} → {curr:.2f} t/ga).",
            })
    return alerts


def _price_spike_alerts() -> list[dict[str, str]]:
    df = read_df(
        "SELECT c.name AS crop, m.date, m.price_per_kg FROM market_prices m"
        " JOIN crops c ON c.id = m.crop_id"
        " WHERE m.date >= date('now','-180 day') ORDER BY m.date"
    )
    alerts = []
    for crop, group in df.groupby("crop"):
        prices = group["price_per_kg"].tolist()
        anomalies = zscore_anomalies(prices, threshold=2.4)
        if anomalies and anomalies[-1] >= len(prices) - 3:
            latest = prices[anomalies[-1]]
            mean = float(pd.Series(prices).mean())
            direction = "keskin oshdi" if latest > mean else "keskin tushdi"
            alerts.append({
                "level": "info", "title": f"{crop} narxi {direction}",
                "detail": f"So'nggi narx {latest:,.0f} so'm/kg "
                          f"(6 oylik o'rtacha: {mean:,.0f} so'm/kg).",
            })
    return alerts[:3]


def _ndvi_alerts() -> list[dict[str, str]]:
    df = read_df(
        "SELECT f.name AS field, fa.name AS farm, s.ndvi, s.date"
        " FROM satellite_indices s"
        " JOIN fields f ON f.id = s.field_id"
        " JOIN farms fa ON fa.id = f.farm_id"
        " WHERE s.date >= date('now','-45 day')"
    )
    if df.empty:
        return []
    latest = df.sort_values("date").groupby("field").last().reset_index()
    weak = latest[latest.ndvi < 0.25].head(3)
    return [
        {
            "level": "warning", "title": f"{row.field}: past vegetatsiya indeksi",
            "detail": f"{row.farm} dalasida NDVI={row.ndvi:.2f} — o'simlik holati zaif.",
        }
        for row in weak.itertuples()
    ]


def _loss_alerts(year: int) -> list[dict[str, str]]:
    df = read_df(
        "SELECT fa.name AS farm,"
        " SUM(CASE WHEN fr.category='income' THEN fr.amount ELSE 0 END) AS income,"
        " SUM(CASE WHEN fr.category='expense' THEN fr.amount ELSE 0 END) AS expense"
        " FROM finance_records fr JOIN farms fa ON fa.id = fr.farm_id"
        " WHERE fr.year = :y GROUP BY fa.id", {"y": year},
    )
    losers = df[df.income < df.expense]
    if losers.empty:
        return []
    worst = losers.assign(loss=losers.expense - losers.income).nlargest(2, "loss")
    return [
        {
            "level": "warning", "title": f"{row.farm}: zarar bilan ishlamoqda",
            "detail": f"{year}-yilda zarar {row.loss / 1e6:,.0f} mln so'm "
                      f"(daromad {row.income / 1e6:,.0f}, xarajat {row.expense / 1e6:,.0f} mln).",
        }
        for row in worst.itertuples()
    ]
