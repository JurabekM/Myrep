"""Reports page: dataset exports, KPI reports, universal import."""
from __future__ import annotations

from nicegui import ui

from analytics.kpi import available_years, latest_year
from app import layout
from core.security import has_permission
from reports import exporter


@ui.page("/reports")
def reports_page() -> None:
    user = layout.require_login("export_reports")
    if user is None:
        return
    with layout.shell(user, "Hisobotlar, import va eksport"):
        with ui.grid(columns=2).classes("w-full gap-4"):
            # ---------------- KPI reports ---------------------------------
            with ui.card().classes("chart-card p-4 gap-3"):
                ui.label("Yakuniy KPI hisoboti").classes("section-title")
                year_select = ui.select(available_years(), value=latest_year(),
                                        label="Hisobot yili").classes("w-48")

                def make(report_fn, label: str) -> None:
                    path = report_fn(int(year_select.value), user["username"])
                    if path is None:
                        ui.notify(f"{label} uchun qo'shimcha paket kerak "
                                  "(README ga qarang).", type="warning")
                        return
                    layout.download_file(path)
                    ui.notify(f"{label} tayyor: {path.name}", type="positive")

                with ui.row().classes("flex-wrap gap-2"):
                    ui.button("PDF", icon="picture_as_pdf",
                              on_click=lambda: make(exporter.kpi_report_pdf, "PDF")) \
                        .props("unelevated")
                    ui.button("HTML", icon="language",
                              on_click=lambda: make(exporter.kpi_report_html, "HTML")) \
                        .props("unelevated")
                    ui.button("Word", icon="article",
                              on_click=lambda: make(exporter.kpi_report_word, "Word")) \
                        .props("unelevated")
                    ui.button("PNG (dashboard)", icon="image",
                              on_click=lambda: make(exporter.dashboard_png, "PNG")) \
                        .props("unelevated")

            # ---------------- Dataset export -------------------------------
            with ui.card().classes("chart-card p-4 gap-3"):
                ui.label("Ma'lumotlar eksporti").classes("section-title")
                dataset = ui.select(list(exporter.DATASETS.keys()),
                                    value=next(iter(exporter.DATASETS)),
                                    label="Ma'lumotlar to'plami").classes("w-full")
                format_select = ui.select(["csv", "xlsx", "json"], value="xlsx",
                                          label="Format").classes("w-40")

                def export_dataset() -> None:
                    frame = exporter.dataset_frame(dataset.value)
                    path = exporter.export_dataframe(
                        frame, dataset.value.replace(" ", "_").lower(),
                        format_select.value, user["username"])
                    layout.download_file(path)
                    ui.notify(f"Eksport tayyor: {path.name} "
                              f"({len(frame)} qator)", type="positive")

                with ui.row().classes("gap-2"):
                    ui.button("Eksport", icon="download",
                              on_click=export_dataset).props("unelevated")
                    ui.button("GeoJSON (dalalar)", icon="public",
                              on_click=lambda: (
                                  layout.download_file(
                                      exporter.export_fields_geojson(
                                          user["username"])),
                                  ui.notify("GeoJSON tayyor.", type="positive"),
                              )).props("outline")

        # ---------------- Import --------------------------------------------
        if has_permission(user["role"], "import_data"):
            with ui.card().classes("chart-card p-4 gap-2 w-full"):
                ui.label("Universal import").classes("section-title")
                ui.label("Qo'llab-quvvatlanadi: CSV, Excel, JSON, GeoJSON, "
                         "Shapefile, KML, TIFF/GeoTIFF, ZIP, SQLite. Narxlar "
                         "uchun ustunlar: [ekin, narx, sana]; hosildorlik uchun: "
                         "[ekin, yil, hosildorlik, dala].") \
                    .classes("text-sm opacity-70")
                result_label = ui.label("").classes("text-sm text-primary")

                def on_upload(event) -> None:
                    from utils.importer import handle_upload

                    summary = handle_upload(event.name, event.content.read(),
                                            user["username"])
                    result_label.text = summary
                    ui.notify(summary[:120], type="info", timeout=8000)

                ui.upload(on_upload=on_upload, auto_upload=True,
                          max_file_size=200_000_000, multiple=True) \
                    .props("label='Fayllarni tanlang yoki tashlang'") \
                    .classes("w-full")
