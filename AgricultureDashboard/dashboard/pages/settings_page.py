"""Settings page: theme, language, providers, API keys, ML, optional packages."""
from __future__ import annotations

import pandas as pd
from nicegui import app, ui

from app import layout
from core import background
from core.i18n import LANGUAGES
from core.optional import optional_status
from core.security import audit
from database.engine import get_setting, set_setting


@ui.page("/settings")
def settings_page() -> None:
    user = layout.require_login("manage_settings")
    if user is None:
        return
    with layout.shell(user, "Sozlamalar"):
        with ui.grid(columns=2).classes("w-full gap-4"):
            # ---------------- Appearance & language -----------------------
            with ui.card().classes("chart-card p-4 gap-3"):
                ui.label("Ko'rinish va til").classes("section-title")
                theme_select = ui.select(
                    {"light": "Kunduzgi (light)", "dark": "Tungi (dark)"},
                    value=get_setting("theme", "light"),
                    label="Standart mavzu").classes("w-full")
                language_select = ui.select(
                    LANGUAGES, value=get_setting("language", "uz"),
                    label="Interfeys tili").classes("w-full")
                offline_select = ui.select(
                    {"auto": "Avto (internetni tekshirish)",
                     "on": "Majburiy offlayn", "off": "Majburiy onlayn"},
                    value=get_setting("offline_mode", "auto"),
                    label="Offlayn rejim").classes("w-full")

            # ---------------- Integrations --------------------------------
            with ui.card().classes("chart-card p-4 gap-3"):
                ui.label("Integratsiyalar (API)").classes("section-title")
                weather_select = ui.select(
                    {"open-meteo": "Open-Meteo (kalitsiz)",
                     "nasa-power": "NASA POWER"},
                    value=get_setting("weather_provider", "open-meteo"),
                    label="Ob-havo provayderi").classes("w-full")
                gee_account = ui.input(
                    "Google Earth Engine service account",
                    value=get_setting("gee_service_account")).classes("w-full")
                gee_key = ui.input(
                    "GEE kalit fayli yo'li (.json)",
                    value=get_setting("gee_key_file")).classes("w-full")
                planet_key = ui.input(
                    "Planet API kaliti (plagin)",
                    value=get_setting("planet_api_key")).classes("w-full")
                ui.label("Kalitlar bo'sh qolsa, platforma lokal demo "
                         "provayderlarda to'liq ishlaydi.") \
                    .classes("text-xs opacity-60")

        with ui.grid(columns=2).classes("w-full gap-4"):
            # ---------------- ML & backup ----------------------------------
            with ui.card().classes("chart-card p-4 gap-3"):
                ui.label("ML va zaxira").classes("section-title")
                retrain_days = ui.number(
                    "ML avtomatik qayta o'qitish (kun)",
                    value=int(get_setting("ml_auto_retrain_days", "30")),
                    min=1, max=365).classes("w-full")
                backup_keep = ui.number(
                    "Saqlanadigan zaxiralar soni",
                    value=int(get_setting("backup_keep", "20")),
                    min=3, max=100).classes("w-full")
                backup_hours = ui.number(
                    "Avtomatik zaxira oralig'i (soat)",
                    value=float(get_setting("auto_backup_hours", "24")),
                    min=1, max=168).classes("w-full")

                def retrain_now() -> None:
                    from ml.service import train_all

                    ui.notify("Modellar fonda qayta o'qitilmoqda...", type="info")
                    background.submit(train_all, True)

                ui.button("ML modellarini hozir qayta o'qitish",
                          icon="model_training", on_click=retrain_now) \
                    .props("outline")

            # ---------------- Optional packages ----------------------------
            with ui.card().classes("chart-card p-4 gap-2"):
                ui.label("Ixtiyoriy paketlar holati").classes("section-title")
                status = optional_status()
                frame = pd.DataFrame({
                    "paket": list(status.keys()),
                    "holat": ["✅ o'rnatilgan" if ok else "— yo'q"
                              for ok in status.values()],
                })
                layout.df_table(frame, rows_per_page=8)
                ui.label("Yetishmayotgan paketni o'rnatish: "
                         "pip install <paket nomi>").classes("text-xs opacity-60")

        def save() -> None:
            set_setting("theme", theme_select.value)
            set_setting("language", language_select.value)
            set_setting("offline_mode", offline_select.value)
            set_setting("weather_provider", weather_select.value)
            set_setting("gee_service_account", gee_account.value or "")
            set_setting("gee_key_file", gee_key.value or "")
            set_setting("planet_api_key", planet_key.value or "")
            set_setting("ml_auto_retrain_days", str(int(retrain_days.value or 30)))
            set_setting("backup_keep", str(int(backup_keep.value or 20)))
            set_setting("auto_backup_hours", str(float(backup_hours.value or 24)))
            app.storage.user["language"] = language_select.value
            audit("settings_saved", user["username"])
            ui.notify("Sozlamalar saqlandi.", type="positive")

        ui.button("Barchasini saqlash", icon="save", on_click=save) \
            .props("unelevated size=lg")
