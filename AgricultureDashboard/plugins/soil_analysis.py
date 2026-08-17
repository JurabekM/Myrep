"""Namuna plagin: Tuproq tahlili.

Plagin kontrakti: PLUGIN metadata + register() funksiyasi. Ushbu fayl
``plugins/`` papkasiga tashlangan har qanday modul uchun shablon bo'lib
xizmat qiladi (IoT sensorlar, ERP, chorvachilik va h.k.).
"""
from __future__ import annotations

PLUGIN = {"name": "Tuproq tahlili", "icon": "grass", "route": "/plugin/soil"}

SUITABILITY = {
    "bo'z tuproq": ("Bug'doy, paxta, sabzavotlar uchun qulay", 0.85),
    "o'tloq tuproq": ("Sholi va ozuqa ekinlari uchun juda mos", 0.9),
    "sho'rlangan tuproq": ("Meliorativ ishlov talab etiladi; arpa bardoshli", 0.55),
    "qumloq tuproq": ("Poliz ekinlari uchun mos; tez-tez sug'orish kerak", 0.65),
    "gilli tuproq": ("Namlikni yaxshi saqlaydi; drenaj nazorati zarur", 0.75),
}


def register() -> None:
    from nicegui import ui

    from app import charts, layout
    from database.engine import read_df

    @ui.page(PLUGIN["route"])
    def soil_page() -> None:
        user = layout.require_login()
        if user is None:
            return
        with layout.shell(user, "Plagin: Tuproq tahlili"):
            df = read_df(
                "SELECT soil_type AS tuproq, COUNT(*) AS dalalar,"
                " ROUND(SUM(area_ha),0) AS maydon_ga,"
                " ROUND(AVG((SELECT AVG(y.yield_t_ha) FROM yield_records y"
                "            WHERE y.field_id = f.id)),2) AS ortacha_hosil"
                " FROM fields f GROUP BY soil_type ORDER BY maydon_ga DESC")
            with ui.grid(columns=2).classes("w-full gap-4"):
                layout.chart(charts.pie_chart(
                    "Tuproq turlari bo'yicha maydon (ga)",
                    [(row.tuproq, row.maydon_ga) for row in df.itertuples()]))
                with ui.card().classes("chart-card"):
                    layout.df_table(df, title="Tuproq turlari statistikasi")
            with ui.card().classes("chart-card p-4 gap-2 w-full"):
                ui.label("Agronomik baholash").classes("section-title")
                for soil, (note, score) in SUITABILITY.items():
                    with ui.row().classes("items-center gap-3 w-full"):
                        ui.label(soil).classes("font-medium w-44")
                        ui.linear_progress(score, show_value=False) \
                            .classes("w-40")
                        ui.label(note).classes("text-sm opacity-75")
