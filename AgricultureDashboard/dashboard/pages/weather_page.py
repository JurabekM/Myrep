"""Weather page: live forecast, history charts, climate profile."""
from __future__ import annotations

import pandas as pd
from nicegui import ui

from app import charts, layout
from database.engine import read_df
from weather.service import fetch_forecast, history_frame, is_online, monthly_climate

MONTHS_UZ = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn",
             "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"]


def _district_map() -> dict[int, str]:
    df = read_df(
        "SELECT d.id, d.name || ' (' || r.name || ')' AS label"
        " FROM districts d JOIN regions r ON r.id = d.region_id ORDER BY r.name")
    return {int(row.id): row.label for row in df.itertuples()}


@ui.page("/weather")
def weather_page() -> None:
    user = layout.require_login()
    if user is None:
        return
    with layout.shell(user, "Ob-havo monitoringi"):
        districts = _district_map()
        state = {"district": next(iter(districts))}
        container = ui.column().classes("w-full gap-4")

        def render() -> None:
            district_id = state["district"]
            container.clear()
            with container:
                coords = read_df(
                    "SELECT lat, lon FROM districts WHERE id = :d",
                    {"d": district_id}).iloc[0]

                # ---------------- 7-day forecast --------------------------
                forecast = fetch_forecast(float(coords.lat), float(coords.lon))
                with ui.card().classes("chart-card p-4"):
                    with ui.row().classes("items-center gap-3"):
                        ui.label("7 kunlik prognoz").classes("section-title")
                        source = forecast.get("_source", "-") if forecast else \
                            "ma'lumot yo'q (offlayn, kesh bo'sh)"
                        ui.chip(source, icon="cloud_sync",
                                color="green-6" if is_online() else "orange-8") \
                            .props("dense text-color=white")
                    if forecast and "daily" in forecast:
                        daily = forecast["daily"]
                        with ui.row().classes("w-full flex-wrap gap-2"):
                            for i, day in enumerate(daily["time"]):
                                with ui.card().classes("p-3 items-center w-28"):
                                    ui.label(day[5:]).classes("text-xs opacity-60")
                                    ui.label(
                                        f"{daily['temperature_2m_max'][i]:.0f}°"
                                        f"/{daily['temperature_2m_min'][i]:.0f}°") \
                                        .classes("font-bold")
                                    rain = daily["precipitation_sum"][i] or 0
                                    ui.label(f"{rain:.1f} mm") \
                                        .classes("text-xs text-blue-6")
                    else:
                        ui.label("Prognoz mavjud emas — internet ulanishi va "
                                 "keshni tekshiring.").classes("opacity-70")

                # ---------------- History ---------------------------------
                history = history_frame(district_id, days=365)
                if not history.empty:
                    history["date"] = history["date"].astype(str)
                    monthly = history.assign(month=history["date"].str[:7]) \
                        .groupby("month") \
                        .agg(t_max=("t_max", "mean"), t_min=("t_min", "mean"),
                             precip=("precipitation_mm", "sum"),
                             humidity=("humidity", "mean")).reset_index()
                    with ui.grid(columns=2).classes("w-full gap-4"):
                        layout.chart(charts.line_chart(
                            "Harorat, so'nggi 12 oy (°C)",
                            monthly["month"].tolist(),
                            {"Maks": monthly["t_max"].round(1).tolist(),
                             "Min": monthly["t_min"].round(1).tolist()}))
                        layout.chart(charts.bar_chart(
                            "Oylik yog'ingarchilik (mm)",
                            monthly["month"].tolist(),
                            {"Yog'in": monthly["precip"].round(1).tolist()}))

                # ---------------- Climate profile -------------------------
                climate = monthly_climate(district_id)
                if not climate.empty:
                    labels = [MONTHS_UZ[m - 1] for m in climate["month"]]
                    with ui.grid(columns=2).classes("w-full gap-4"):
                        layout.chart(charts.line_chart(
                            "Ko'p yillik iqlim profili — harorat (°C)", labels,
                            {"Maks": climate["t_max"].tolist(),
                             "Min": climate["t_min"].tolist()}))
                        layout.chart(charts.bar_chart(
                            "Ko'p yillik o'rtacha oylik yog'in (mm)", labels,
                            {"Yog'in": climate["precip"].tolist()}))

        ui.select(districts, value=state["district"], label="Tuman",
                  on_change=lambda e: (state.update(district=e.value), render())) \
            .classes("w-80")
        render()
