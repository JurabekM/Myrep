"""Main dashboard: KPI cards, headline charts, alerts, top farms."""
from __future__ import annotations

from nicegui import ui

from analytics import kpi as kpi_module
from analytics.insights import generate_alerts
from analytics.timeseries import linear_forecast
from app import charts, layout


@ui.page("/")
def home_page() -> None:
    user = layout.require_login()
    if user is None:
        return
    with layout.shell(user, "Bosh sahifa"):
        year = kpi_module.latest_year()
        kpi = kpi_module.compute_kpi(year)

        with ui.row().classes("w-full flex-wrap gap-3"):
            layout.kpi_card("landscape", f"{kpi.total_area_ha:,.0f} ga",
                            "Umumiy yer maydoni")
            layout.kpi_card("groups", f"{kpi.farmers}", "Fermerlar")
            layout.kpi_card("home_work", f"{kpi.farms}", "Fermer xo'jaliklari")
            layout.kpi_card("grid_on", f"{kpi.fields}", "Dalalar (konturlar)")
            layout.kpi_card("agriculture", f"{kpi.avg_yield_t_ha} t/ga",
                            f"O'rtacha hosildorlik ({year})")
            layout.kpi_card("inventory", f"{kpi.production_t:,.0f} t",
                            "Ishlab chiqarish", "secondary")
            layout.kpi_card("payments", f"{kpi.profit / 1e9:,.1f} mlrd",
                            f"Sof foyda, so'm (ROI {kpi.roi_percent}%)",
                            "positive" if kpi.profit >= 0 else "negative")
            layout.kpi_card("eco", f"{kpi.avg_ndvi}", "O'rtacha NDVI (60 kun)",
                            "secondary")
            layout.kpi_card("water_drop", f"{kpi.water_million_m3} mln m³",
                            "Sug'orish suvi", "info")

        trend = kpi_module.yield_trend()
        forecast, lower, upper = linear_forecast(trend["avg_yield"].tolist(), 2)
        x_labels = [str(y) for y in trend["year"].tolist()] + \
                   [str(int(trend["year"].iloc[-1]) + i) for i in (1, 2)]
        history = trend["avg_yield"].tolist()
        forecast_series = [None] * (len(history) - 1) + [history[-1]] + forecast

        with ui.grid(columns=2).classes("w-full gap-4"):
            layout.chart(charts.line_chart(
                "Hosildorlik trendi va prognoz (t/ga)", x_labels,
                {"Haqiqiy": history + [None, None], "Prognoz": forecast_series},
                dashed={"Prognoz"}))
            layout.chart(charts.pie_chart(
                "Ekin maydonlari taqsimoti",
                [(row.crop, row.area) for row in
                 kpi_module.crop_distribution(year).head(9).itertuples()]))

        regions = kpi_module.yield_by_region(year)
        layout.chart(charts.bar_chart(
            f"Viloyatlar bo'yicha ishlab chiqarish, {year} (t)",
            regions["region"].tolist(),
            {"Ishlab chiqarish": regions["production"].tolist()},
            horizontal=True), height="h-96")

        with ui.grid(columns=2).classes("w-full gap-4"):
            with ui.card().classes("chart-card"):
                ui.label("Ogohlantirishlar va tahliliy xulosalar") \
                    .classes("section-title")
                alerts = generate_alerts()
                if not alerts:
                    ui.label("Faol ogohlantirishlar yo'q.").classes("opacity-70")
                for alert in alerts[:6]:
                    with ui.card().classes(
                            f"w-full p-3 alert-{alert['level']} shadow-1"):
                        ui.label(alert["title"]).classes("font-medium")
                        ui.label(alert["detail"]).classes("text-sm opacity-80")
            with ui.card().classes("chart-card"):
                layout.df_table(kpi_module.top_farms(year),
                                title=f"Eng samarali xo'jaliklar, {year}")
