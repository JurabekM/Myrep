"""Irrigation analytics page."""
from __future__ import annotations

from nicegui import ui

from analytics.kpi import available_years, latest_year
from app import charts, layout
from irrigation.service import (
    efficiency_by_crop, monthly_usage, usage_by_method, usage_by_region,
)

MONTHS_UZ = {4: "Aprel", 5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust"}


@ui.page("/irrigation")
def irrigation_page() -> None:
    user = layout.require_login()
    if user is None:
        return
    with layout.shell(user, "Sug'orish tahlili"):
        state = {"year": latest_year()}
        container = ui.column().classes("w-full gap-4")

        def render() -> None:
            year = state["year"]
            container.clear()
            with container:
                regions = usage_by_region(year)
                methods = usage_by_method(year)
                monthly = monthly_usage(year)

                total = float(regions["water_mln_m3"].sum()) if not regions.empty else 0
                with ui.row().classes("w-full flex-wrap gap-3"):
                    layout.kpi_card("water_drop", f"{total:,.1f} mln m³",
                                    f"Jami sug'orish suvi, {year}")
                    if not methods.empty:
                        drip = methods[methods.method == "tomchilatib"]
                        share = (float(drip["water_mln_m3"].iloc[0]) / total * 100
                                 if not drip.empty and total else 0)
                        layout.kpi_card("opacity", f"{share:.1f}%",
                                        "Tomchilatib sug'orish ulushi", "secondary")

                with ui.grid(columns=2).classes("w-full gap-4"):
                    layout.chart(charts.bar_chart(
                        f"Viloyatlar bo'yicha suv sarfi, {year} (mln m³)",
                        regions["region"].tolist(),
                        {"mln m³": regions["water_mln_m3"].tolist()},
                        horizontal=True))
                    layout.chart(charts.pie_chart(
                        "Sug'orish usullari bo'yicha taqsimot",
                        [(row.method, row.water_mln_m3)
                         for row in methods.itertuples()]))

                with ui.grid(columns=2).classes("w-full gap-4"):
                    layout.chart(charts.bar_chart(
                        f"Oylik suv sarfi, {year} (mln m³)",
                        [MONTHS_UZ.get(int(m), str(m))
                         for m in monthly["month"].tolist()],
                        {"mln m³": monthly["water_mln_m3"].tolist()}))
                    with ui.card().classes("chart-card"):
                        layout.df_table(
                            efficiency_by_crop(year)[
                                ["crop", "production", "m3_per_tonne"]],
                            title="Suv samaradorligi: 1 tonna mahsulotga m³")

        ui.select(available_years(), value=state["year"], label="Yil",
                  on_change=lambda e: (state.update(year=e.value), render())) \
            .classes("w-32")
        render()
