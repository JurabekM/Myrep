"""Market page: latest prices, history, forecast, manual entry."""
from __future__ import annotations

from nicegui import ui

from app import charts, layout
from core.security import has_permission
from market.service import (
    add_price, crop_options, latest_prices, price_forecast, price_history,
)


@ui.page("/market")
def market_page() -> None:
    user = layout.require_login()
    if user is None:
        return
    with layout.shell(user, "Bozor narxlari"):
        crops = crop_options()
        state = {"crop": next(iter(crops))}

        with ui.grid(columns=2).classes("w-full gap-4"):
            with ui.card().classes("chart-card"):
                layout.df_table(latest_prices(),
                                title="So'nggi narxlar (30 kunlik o'zgarish bilan)",
                                rows_per_page=12)

            with ui.column().classes("gap-4 w-full"):
                chart_box = ui.column().classes("w-full")

                def render_chart() -> None:
                    chart_box.clear()
                    with chart_box:
                        history = price_history(state["crop"], days=540)
                        if history.empty:
                            ui.label("Narx tarixi topilmadi.").classes("opacity-70")
                            return
                        forecast = price_forecast(state["crop"], periods=8)
                        x = [str(d)[:10] for d in history["date"].tolist()[-26:]]
                        x += [f"+{i + 1} hafta" for i in range(8)]
                        pad = [None] * (len(forecast["history"]) - 1)
                        layout.chart(charts.line_chart(
                            f"{crops[state['crop']]} — narx dinamikasi va prognoz "
                            f"(so'm/kg)", x,
                            {
                                "Narx": forecast["history"] + [None] * 8,
                                "Prognoz": pad + [forecast["history"][-1]]
                                + forecast["forecast"],
                            },
                            dashed={"Prognoz"}))

                ui.select(crops, value=state["crop"], label="Ekin",
                          on_change=lambda e: (state.update(crop=e.value),
                                               render_chart())) \
                    .classes("w-64")
                render_chart()

                if has_permission(user["role"], "edit_data"):
                    with ui.card().classes("chart-card p-4 gap-2"):
                        ui.label("Narx kiritish (qo'lda)").classes("section-title")
                        entry_crop = ui.select(crops, value=next(iter(crops)),
                                               label="Ekin").classes("w-full")
                        entry_price = ui.number("Narx (so'm/kg)", value=5000,
                                                min=1).classes("w-full")
                        entry_market = ui.input("Bozor nomi",
                                                value="Chorsu bozori") \
                            .classes("w-full")

                        def save_price() -> None:
                            add_price(int(entry_crop.value),
                                      float(entry_price.value or 0),
                                      entry_market.value or "Qo'lda kiritilgan")
                            ui.notify("Narx saqlandi.", type="positive")
                            ui.navigate.reload()

                        ui.button("Saqlash", icon="save", on_click=save_price) \
                            .props("unelevated")
                        ui.label("CSV/Excel orqali ommaviy import — "
                                 "Hisobotlar sahifasida.").classes("text-xs opacity-60")
