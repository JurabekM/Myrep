"""Interactive GIS map page with metric/region/year filters."""
from __future__ import annotations

from nicegui import ui

from analytics.kpi import available_years, latest_year
from app import layout
from gis.maps import build_map, region_options
from weather.service import is_online


@ui.page("/map")
def map_page() -> None:
    user = layout.require_login()
    if user is None:
        return
    with layout.shell(user, "Interaktiv xarita"):
        if not is_online():
            ui.chip("Offlayn rejim: xarita plitkalari internetsiz yuklanmaydi, "
                    "poligon ma'lumotlari esa to'liq ishlaydi.",
                    icon="wifi_off", color="orange-8") \
                .props("text-color=white").classes("w-full")

        state = {"metric": "yield", "region": 0, "year": latest_year()}
        container = ui.column().classes("w-full")

        def render() -> None:
            container.clear()
            with container:
                with ui.card().classes("w-full p-1 chart-card"):
                    html = build_map(metric=state["metric"],
                                     year=state["year"],
                                     region_id=state["region"] or None)
                    layout.raw_html(html).classes("w-full")

        with ui.row().classes("w-full items-end gap-4"):
            ui.select({"yield": "Hosildorlik (t/ga)", "ndvi": "NDVI indeksi"},
                      value="yield", label="Ko'rsatkich",
                      on_change=lambda e: (state.update(metric=e.value), render())) \
                .classes("w-48")
            ui.select(region_options(), value=0, label="Viloyat",
                      on_change=lambda e: (state.update(region=e.value), render())) \
                .classes("w-56")
            ui.select(available_years(), value=state["year"], label="Yil",
                      on_change=lambda e: (state.update(year=e.value), render())) \
                .classes("w-32")
            ui.label("Qatlamlar: ko'cha / sun'iy yo'ldosh / relyef, poligonlar, "
                     "klasterlar, issiqlik xaritasi — xaritaning o'ng yuqori "
                     "burchagida.").classes("text-xs opacity-60")

        render()
