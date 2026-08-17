"""Satellite & drone page: NDVI/EVI series, field health, imagery upload."""
from __future__ import annotations

from nicegui import ui

from app import charts, layout
from core.security import has_permission
from satellite.service import field_health, field_options, get_provider, ndvi_series


@ui.page("/satellite")
def satellite_page() -> None:
    user = layout.require_login()
    if user is None:
        return
    with layout.shell(user, "Sun'iy yo'ldosh va dron monitoringi"):
        provider = get_provider()
        ui.chip(f"Faol provayder: {provider.name}", icon="satellite_alt",
                color="green-6").props("dense text-color=white")

        fields = field_options()
        state = {"field": next(iter(fields))}
        chart_box = ui.column().classes("w-full")

        def render_chart() -> None:
            chart_box.clear()
            with chart_box:
                series = ndvi_series(state["field"])
                if series.empty:
                    ui.label("Bu dala uchun indeks ma'lumotlari yo'q.") \
                        .classes("opacity-70")
                    return
                layout.chart(charts.line_chart(
                    f"{fields[state['field']]} — NDVI/EVI dinamikasi",
                    [str(d)[:10] for d in series["date"].tolist()],
                    {"NDVI": series["ndvi"].tolist(),
                     "EVI": series["evi"].tolist()}))

        with ui.row().classes("w-full items-end gap-4"):
            ui.select(fields, value=state["field"], label="Dala (kontur)",
                      on_change=lambda e: (state.update(field=e.value),
                                           render_chart())) \
                .classes("w-96")
        render_chart()

        with ui.grid(columns=2).classes("w-full gap-4"):
            with ui.card().classes("chart-card"):
                health = field_health()
                if not health.empty:
                    health = health[["field", "farm", "region", "ndvi", "evi",
                                     "holat"]]
                layout.df_table(health, title="Dalalar salomatligi (so'nggi NDVI)",
                                rows_per_page=12)

            with ui.card().classes("chart-card p-4 gap-2"):
                ui.label("Dron / sun'iy yo'ldosh tasvirini yuklash") \
                    .classes("section-title")
                ui.label("Qo'llab-quvvatlanadi: GeoTIFF, TIFF, JPG, PNG "
                         "(ortomozaika, NDVI raster). 4 kanalli GeoTIFF dan "
                         "NDVI avtomatik hisoblanadi.") \
                    .classes("text-sm opacity-70")
                target_field = ui.select(fields, value=next(iter(fields)),
                                         label="Qaysi dalaga biriktirish") \
                    .classes("w-full")

                if has_permission(user["role"], "import_data"):
                    def on_upload(event) -> None:
                        from pathlib import Path

                        from config import settings
                        from satellite.service import process_drone_image

                        settings.ensure_directories()
                        target = settings.UPLOAD_DIR / event.name
                        target.write_bytes(event.content.read())
                        summary = process_drone_image(
                            Path(target), field_id=int(target_field.value),
                            username=user["username"])
                        ui.notify(summary, type="positive", timeout=8000)

                    ui.upload(on_upload=on_upload, auto_upload=True,
                              max_file_size=200_000_000) \
                        .props("accept=.tif,.tiff,.jpg,.jpeg,.png "
                               "label='Faylni tanlang yoki tashlang'") \
                        .classes("w-full")
                else:
                    ui.label("Yuklash uchun menejer yoki admin huquqi kerak.") \
                        .classes("text-sm text-orange-8")
