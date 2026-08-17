"""Machine Learning workbench: metrics, predictions, recommendations."""
from __future__ import annotations

from nicegui import ui

from app import charts, layout
from core import background
from database.engine import read_df
from ml import service as ml_service


def _crop_map() -> dict[int, str]:
    df = read_df("SELECT id, name, water_need_mm FROM crops ORDER BY name")
    return {int(row.id): row.name for row in df.itertuples()}


def _region_map() -> dict[int, str]:
    df = read_df("SELECT id, name FROM regions ORDER BY name")
    return {int(row.id): row.name for row in df.itertuples()}


@ui.page("/ml")
def ml_page() -> None:
    user = layout.require_login()
    if user is None:
        return
    with layout.shell(user, "Machine Learning"):
        metrics = ml_service.model_status()
        with ui.row().classes("w-full flex-wrap gap-3"):
            layout.kpi_card("agriculture",
                            f"R² = {metrics.get('yield', {}).get('r2', '-')}",
                            f"Hosil prognozi ({metrics.get('yield', {}).get('algorithm', '-')})")
            layout.kpi_card("coronavirus",
                            f"{metrics.get('disease', {}).get('accuracy', '-')}",
                            "Kasallik xavfi (aniqlik)")
            layout.kpi_card("water_drop",
                            f"R² = {metrics.get('water', {}).get('r2', '-')}",
                            "Suv ehtiyoji modeli")
            layout.kpi_card("recommend",
                            f"{metrics.get('crop', {}).get('accuracy', '-')}",
                            "Ekin tavsiyasi (aniqlik)")
            layout.kpi_card("schedule", metrics.get("trained_at", "-")[:16],
                            "So'nggi o'qitish vaqti")
        if user["role"] == "admin":
            def retrain() -> None:
                ui.notify("Modellar fonda qayta o'qitilmoqda...", type="info")
                background.submit(ml_service.train_all, True)
            ui.button("Modellarni qayta o'qitish", icon="model_training",
                      on_click=retrain).props("outline")

        crops = _crop_map()
        regions = _region_map()
        crop_needs = {int(r.id): float(r.water_need_mm) for r in read_df(
            "SELECT id, water_need_mm FROM crops").itertuples()}
        fertilities = {int(r.id): float(r.fertility) for r in read_df(
            "SELECT id, fertility FROM regions").itertuples()}

        with ui.grid(columns=2).classes("w-full gap-4"):
            # ---------------- Yield prediction ----------------------------
            with ui.card().classes("chart-card p-4 gap-2"):
                ui.label("Hosil prognozi (t/ga)").classes("section-title")
                crop_select = ui.select(crops, value=next(iter(crops)),
                                        label="Ekin").classes("w-full")
                region_select = ui.select(regions, value=next(iter(regions)),
                                          label="Viloyat").classes("w-full")
                area = ui.number("Maydon (ga)", value=50, min=1, max=1000) \
                    .classes("w-full")
                precip = ui.slider(min=30, max=500, value=150) \
                    .props("label-always").classes("w-full mt-6")
                ui.label("Mavsumiy yog'in (mm)").classes("text-xs opacity-60")
                t_avg = ui.slider(min=15, max=35, value=24, step=0.5) \
                    .props("label-always").classes("w-full mt-6")
                ui.label("O'rtacha harorat (°C)").classes("text-xs opacity-60")
                irrigation = ui.slider(min=0, max=900, value=350) \
                    .props("label-always").classes("w-full mt-6")
                ui.label("Sug'orish (mm)").classes("text-xs opacity-60")
                yield_result = ui.label("").classes("text-xl font-bold text-primary")

                def predict_yield() -> None:
                    value = ml_service.predict_yield(
                        crop_id=int(crop_select.value),
                        region_id=int(region_select.value),
                        area_ha=float(area.value or 50),
                        precip=float(precip.value), t_avg=float(t_avg.value),
                        irrigation_mm=float(irrigation.value),
                        water_need_mm=crop_needs[int(crop_select.value)],
                        fertility=fertilities[int(region_select.value)])
                    yield_result.text = f"Prognoz: {value} t/ga"

                ui.button("Bashorat qilish", icon="online_prediction",
                          on_click=predict_yield).props("unelevated")

            # ---------------- Disease risk --------------------------------
            with ui.card().classes("chart-card p-4 gap-2"):
                ui.label("Kasallik xavfi (zamburug'li)").classes("section-title")
                humidity = ui.slider(min=10, max=95, value=65) \
                    .props("label-always").classes("w-full mt-6")
                ui.label("Namlik (%)").classes("text-xs opacity-60")
                d_temp = ui.slider(min=5, max=40, value=23, step=0.5) \
                    .props("label-always").classes("w-full mt-6")
                ui.label("Harorat (°C)").classes("text-xs opacity-60")
                d_precip = ui.slider(min=0, max=200, value=60) \
                    .props("label-always").classes("w-full mt-6")
                ui.label("Oylik yog'in (mm)").classes("text-xs opacity-60")
                d_ndvi = ui.slider(min=0.05, max=0.9, value=0.5, step=0.01) \
                    .props("label-always").classes("w-full mt-6")
                ui.label("NDVI").classes("text-xs opacity-60")
                gauge_box = ui.column().classes("w-full items-center")

                def predict_disease() -> None:
                    risk = ml_service.predict_disease_risk(
                        float(humidity.value), float(d_temp.value),
                        float(d_precip.value), float(d_ndvi.value)) * 100
                    gauge_box.clear()
                    with gauge_box:
                        ui.echart(charts.gauge_chart("Xavf darajasi", risk)) \
                            .classes("w-64 h-52")
                        advice = ("Profilaktik fungitsid ishlovi tavsiya etiladi."
                                  if risk > 60 else
                                  "Monitoringni davom ettiring." if risk > 30
                                  else "Xavf past.")
                        ui.label(advice).classes("text-sm opacity-80")

                ui.button("Xavfni baholash", icon="health_and_safety",
                          on_click=predict_disease).props("unelevated")

        with ui.grid(columns=2).classes("w-full gap-4"):
            # ---------------- Water need ----------------------------------
            with ui.card().classes("chart-card p-4 gap-2"):
                ui.label("Suv ehtiyoji (mavsum, m³/ga)").classes("section-title")
                w_crop = ui.select(crops, value=next(iter(crops)), label="Ekin") \
                    .classes("w-full")
                w_precip = ui.slider(min=30, max=500, value=150) \
                    .props("label-always").classes("w-full mt-6")
                ui.label("Kutilayotgan yog'in (mm)").classes("text-xs opacity-60")
                w_temp = ui.slider(min=15, max=35, value=25, step=0.5) \
                    .props("label-always").classes("w-full mt-6")
                ui.label("O'rtacha harorat (°C)").classes("text-xs opacity-60")
                w_area = ui.number("Maydon (ga)", value=50, min=1).classes("w-full")
                water_result = ui.label("").classes("text-xl font-bold text-primary")

                def predict_water() -> None:
                    per_ha = ml_service.predict_water_need(
                        crop_needs[int(w_crop.value)], float(w_precip.value),
                        float(w_temp.value), float(w_area.value or 50))
                    total = per_ha * float(w_area.value or 50)
                    water_result.text = (f"{per_ha:,.0f} m³/ga — jami "
                                         f"{total / 1000:,.1f} ming m³")

                ui.button("Hisoblash", icon="calculate",
                          on_click=predict_water).props("unelevated")

            # ---------------- Crop recommendation -------------------------
            with ui.card().classes("chart-card p-4 gap-2"):
                ui.label("Ekin tavsiyasi (foydalilik bo'yicha)") \
                    .classes("section-title")
                r_region = ui.select(regions, value=next(iter(regions)),
                                     label="Viloyat").classes("w-full")
                recommendation_box = ui.column().classes("w-full gap-1")

                def recommend() -> None:
                    from analytics.kpi import latest_year
                    from weather.service import season_summary

                    region_name = regions[int(r_region.value)]
                    season = season_summary(region_name, latest_year()) \
                        or {"precip": 150, "t_avg": 24}
                    results = ml_service.recommend_crops(
                        int(r_region.value), season["precip"], season["t_avg"],
                        fertilities[int(r_region.value)])
                    recommendation_box.clear()
                    with recommendation_box:
                        for i, rec in enumerate(results):
                            with ui.row().classes("items-center gap-2"):
                                ui.badge(f"{i + 1}").props("color=primary")
                                ui.label(rec["crop"]).classes("font-medium")
                                ui.linear_progress(rec["confidence"] / 100,
                                                   show_value=False) \
                                    .classes("w-40")
                                ui.label(f"{rec['confidence']}%") \
                                    .classes("text-sm opacity-70")

                ui.button("Tavsiya olish", icon="recommend",
                          on_click=recommend).props("unelevated")
