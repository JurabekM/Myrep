"""Deep analytics: trends, heatmap, correlation, seasonality, clustering."""
from __future__ import annotations

import numpy as np
import pandas as pd
from nicegui import ui
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from analytics import kpi as kpi_module
from analytics.timeseries import linear_forecast
from app import charts, layout
from database.engine import read_df


def _cluster_regions(year: int) -> pd.DataFrame:
    """K-Means segmentation of regions by yield, rainfall and water use."""
    df = read_df(
        "SELECT r.name AS region, AVG(y.yield_t_ha) AS avg_yield,"
        " SUM(y.production_t) AS production"
        " FROM yield_records y"
        " JOIN fields f ON f.id = y.field_id"
        " JOIN farms fa ON fa.id = f.farm_id"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " WHERE y.year = :y GROUP BY r.name", {"y": year},
    )
    rain = read_df(
        "SELECT r.name AS region, SUM(w.precipitation_mm)/COUNT(DISTINCT d.id) AS precip"
        " FROM weather_records w"
        " JOIN districts d ON d.id = w.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " WHERE CAST(strftime('%Y', w.date) AS INTEGER) = :y"
        " AND CAST(strftime('%m', w.date) AS INTEGER) BETWEEN 4 AND 9"
        " GROUP BY r.name", {"y": year},
    )
    df = df.merge(rain, on="region", how="left").fillna(0)
    if len(df) < 3:
        df["klaster"] = "A"
        return df
    features = StandardScaler().fit_transform(
        df[["avg_yield", "production", "precip"]])
    labels = KMeans(n_clusters=3, random_state=42, n_init=10).fit_predict(features)
    names = {0: "A — yuqori salohiyat", 1: "B — o'rtacha", 2: "C — e'tibor talab"}
    order = df.assign(_label=labels).groupby("_label")["avg_yield"].mean() \
        .sort_values(ascending=False).index.tolist()
    remap = {cluster: names[rank] for rank, cluster in enumerate(order)}
    df["klaster"] = [remap[label] for label in labels]
    return df.round(2).sort_values("klaster")


@ui.page("/analytics")
def analytics_page() -> None:
    user = layout.require_login()
    if user is None:
        return
    with layout.shell(user, "Analitika va prognozlash"):
        state = {"year": kpi_module.latest_year()}
        container = ui.column().classes("w-full gap-4")

        def render() -> None:
            year = state["year"]
            container.clear()
            with container:
                # --- Trend + forecast -------------------------------------
                trend = kpi_module.yield_trend()
                values = trend["avg_yield"].tolist()
                forecast, lower, upper = linear_forecast(values, 3)
                x = [str(y) for y in trend["year"]] + \
                    [str(int(trend["year"].iloc[-1]) + i) for i in (1, 2, 3)]
                pad = [None] * (len(values) - 1)
                with ui.grid(columns=2).classes("w-full gap-4"):
                    layout.chart(charts.line_chart(
                        "Hosildorlik: trend, prognoz va ishonch oralig'i (t/ga)", x,
                        {
                            "Haqiqiy": values + [None] * 3,
                            "Prognoz": pad + [values[-1]] + forecast,
                            "Quyi chegara": pad + [values[-1]] + lower,
                            "Yuqori chegara": pad + [values[-1]] + upper,
                        },
                        dashed={"Prognoz", "Quyi chegara", "Yuqori chegara"}))

                    regions = kpi_module.yield_by_region(year)
                    layout.chart(charts.bar_chart(
                        f"Viloyatlar — o'rtacha hosildorlik, {year} (t/ga)",
                        regions["region"].tolist(),
                        {"t/ga": regions["avg_yield"].tolist()}, horizontal=True))

                # --- Region x crop heatmap --------------------------------
                matrix = kpi_module.region_crop_matrix(year)
                if not matrix.empty:
                    top_crops = matrix.count().sort_values(ascending=False) \
                        .head(10).index.tolist()
                    matrix = matrix[top_crops]
                    points = []
                    for yi, region in enumerate(matrix.index):
                        for xi, crop in enumerate(matrix.columns):
                            value = matrix.loc[region, crop]
                            if pd.notna(value):
                                points.append([xi, yi, round(float(value), 1)])
                    layout.chart(charts.heatmap_chart(
                        f"Issiqlik xaritasi: viloyat × ekin hosildorligi, {year} (t/ga)",
                        list(matrix.columns), list(matrix.index), points, "t/ga"),
                        height="h-96")

                # --- Correlation + seasonality ----------------------------
                with ui.grid(columns=2).classes("w-full gap-4"):
                    merged, correlation = kpi_module.rainfall_yield_correlation()
                    layout.chart(charts.scatter_chart(
                        f"Yog'ingarchilik ↔ hosildorlik (r = {correlation})",
                        [[round(float(r.precip), 0), round(float(r.avg_yield), 2)]
                         for r in merged.itertuples()],
                        "Mavsumiy yog'in (mm)", "Hosildorlik (t/ga)"))

                    monthly = read_df(
                        "SELECT CAST(strftime('%m', date) AS INTEGER) AS month,"
                        " AVG(price_per_kg) AS price FROM market_prices"
                        " GROUP BY month ORDER BY month")
                    index = (monthly["price"] / monthly["price"].mean() * 100)
                    layout.chart(charts.line_chart(
                        "Narxlarning mavsumiyligi (indeks, o'rtacha=100)",
                        [f"{m:02d}" for m in monthly["month"]],
                        {"Narx indeksi": index.round(1).tolist()}))

                # --- Clustering -------------------------------------------
                with ui.card().classes("chart-card"):
                    layout.df_table(
                        _cluster_regions(year),
                        title=f"Viloyatlar segmentatsiyasi (K-Means), {year}")

        ui.select(kpi_module.available_years(), value=state["year"], label="Yil",
                  on_change=lambda e: (state.update(year=e.value), render())) \
            .classes("w-32")
        render()
