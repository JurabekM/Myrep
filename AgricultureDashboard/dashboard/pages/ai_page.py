"""AI assistant page: chat over the analytics database (fully offline)."""
from __future__ import annotations

from nicegui import ui

from ai.engine import assistant
from app import layout

SAMPLE_QUESTIONS = [
    "Jizzaxda bug'doy hosili nima uchun pasaydi?",
    "Kelgusi yil paxta hosildorligi prognozi qanday?",
    "Pomidor narxi qancha?",
    "Samarqand uchun qaysi ekin tavsiya etiladi?",
    "2024-yil Jizzax ob-havosi qanday bo'lgan?",
    "Viloyatlarni solishtirib bering",
    "Daromad va foyda qanday?",
]


@ui.page("/ai")
def ai_page() -> None:
    user = layout.require_login("use_ai")
    if user is None:
        return
    with layout.shell(user, "AI Yordamchi"):
        ui.label("Savolni oddiy tilda yozing — yordamchi bazadagi barcha "
                 "ma'lumotlarni tahlil qilib, dalillarga asoslangan javob beradi. "
                 "Internet talab qilinmaydi.").classes("opacity-70")

        messages = ui.column().classes(
            "w-full gap-3 min-h-[300px] max-h-[520px] overflow-y-auto p-2")

        def ask(question: str) -> None:
            question = (question or "").strip()
            if not question:
                return
            with messages:
                with ui.row().classes("w-full justify-end"):
                    with ui.card().classes("bg-primary text-white p-3 rounded-xl "
                                           "max-w-[75%]"):
                        ui.label(question)
            result = assistant.ask(question)
            with messages:
                with ui.row().classes("w-full justify-start"):
                    with ui.card().classes("p-3 rounded-xl max-w-[85%]"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("smart_toy").classes("text-primary")
                            ui.label("AgroAI").classes("font-medium text-primary")
                        ui.markdown(result["answer"].replace("\n", "\n\n"))
                        table = result.get("table")
                        if table is not None and not table.empty:
                            layout.df_table(table.head(12), rows_per_page=6)
            input_box.value = ""

        with ui.row().classes("w-full flex-wrap gap-2"):
            for sample in SAMPLE_QUESTIONS:
                ui.chip(sample, icon="help_outline",
                        on_click=lambda s=sample: ask(s)) \
                    .props("clickable outline color=primary")

        with ui.row().classes("w-full items-center gap-2"):
            input_box = ui.input(placeholder="Masalan: Jizzaxda bug'doy hosili "
                                             "nima uchun pasaydi?") \
                .props("outlined dense").classes("flex-grow")
            input_box.on("keydown.enter", lambda: ask(input_box.value))
            ui.button("So'rash", icon="send",
                      on_click=lambda: ask(input_box.value)).props("unelevated")
