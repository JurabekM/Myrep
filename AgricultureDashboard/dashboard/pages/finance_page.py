"""Finance page: P&L, ROI, credits & subsidies."""
from __future__ import annotations

from nicegui import ui

from analytics.kpi import available_years, latest_year
from app import charts, layout
from finance.service import (
    by_region, credits_and_subsidies, farm_profitability, yearly_summary,
)


@ui.page("/finance")
def finance_page() -> None:
    user = layout.require_login("view_finance")
    if user is None:
        return
    with layout.shell(user, "Moliya va iqtisod"):
        state = {"year": latest_year()}
        container = ui.column().classes("w-full gap-4")

        def render() -> None:
            year = state["year"]
            container.clear()
            with container:
                summary = yearly_summary()
                row = summary[summary.year == year]
                if not row.empty:
                    record = row.iloc[0]
                    with ui.row().classes("w-full flex-wrap gap-3"):
                        layout.kpi_card("trending_up",
                                        f"{record.income / 1e9:,.1f} mlrd",
                                        f"Daromad, {year} (so'm)")
                        layout.kpi_card("trending_down",
                                        f"{record.expense / 1e9:,.1f} mlrd",
                                        "Xarajat (so'm)", "warning")
                        layout.kpi_card("savings",
                                        f"{record.profit / 1e9:,.1f} mlrd",
                                        "Sof foyda (so'm)",
                                        "positive" if record.profit >= 0
                                        else "negative")
                        layout.kpi_card("percent", f"{record.roi}%", "ROI")
                        layout.kpi_card("account_balance",
                                        f"{record.credit / 1e9:,.1f} mlrd",
                                        "Kreditlar (so'm)", "info")
                        layout.kpi_card("volunteer_activism",
                                        f"{record.subsidy / 1e9:,.1f} mlrd",
                                        "Subsidiyalar (so'm)", "secondary")

                years = [str(y) for y in summary["year"].tolist()]
                with ui.grid(columns=2).classes("w-full gap-4"):
                    layout.chart(charts.bar_chart(
                        "Daromad va xarajat dinamikasi (mlrd so'm)", years,
                        {"Daromad": (summary["income"] / 1e9).round(1).tolist(),
                         "Xarajat": (summary["expense"] / 1e9).round(1).tolist(),
                         "Foyda": (summary["profit"] / 1e9).round(1).tolist()}))
                    layout.chart(charts.line_chart(
                        "ROI trendi (%)", years,
                        {"ROI": summary["roi"].tolist()}))

                regions = by_region(year)
                if not regions.empty:
                    layout.chart(charts.bar_chart(
                        f"Viloyatlar bo'yicha sof foyda, {year} (mlrd so'm)",
                        regions["region"].tolist(),
                        {"Foyda": (regions["profit"] / 1e9).round(2).tolist()},
                        horizontal=True), height="h-96")

                with ui.grid(columns=2).classes("w-full gap-4"):
                    with ui.card().classes("chart-card"):
                        farms = farm_profitability(year)
                        display = farms.assign(
                            income=(farms["income"] / 1e6).round(0),
                            expense=(farms["expense"] / 1e6).round(0),
                            profit=(farms["profit"] / 1e6).round(0),
                        ).rename(columns={"income": "daromad_mln",
                                          "expense": "xarajat_mln",
                                          "profit": "foyda_mln"})
                        layout.df_table(display,
                                        title=f"Xo'jaliklar reytingi, {year} "
                                              f"(mln so'm)")
                    with ui.card().classes("chart-card"):
                        credits = credits_and_subsidies(year)
                        if not credits.empty:
                            credits = credits.assign(
                                amount=(credits["amount"] / 1e6).round(1))
                            credits = credits.rename(
                                columns={"amount": "summa_mln"})
                        layout.df_table(credits,
                                        title=f"Kredit va subsidiyalar, {year} "
                                              f"(mln so'm)")

        ui.select(available_years(), value=state["year"], label="Yil",
                  on_change=lambda e: (state.update(year=e.value), render())) \
            .classes("w-32")
        render()
