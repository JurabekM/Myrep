"""Shared page shell: header, sidebar, auth guard, search, reusable widgets."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

import pandas as pd
from nicegui import app, ui

from app import theme
from config import settings
from core.i18n import translate
from core.plugin_manager import get_plugins
from core.security import audit, has_permission
from database.engine import get_setting

log = logging.getLogger(__name__)

NAV_ITEMS: list[tuple[str, str, str, str]] = [
    ("/", "space_dashboard", "Bosh sahifa", "view_dashboard"),
    ("/map", "map", "Xarita", "view_dashboard"),
    ("/analytics", "insights", "Analitika", "view_dashboard"),
    ("/ml", "psychology", "Machine Learning", "view_dashboard"),
    ("/satellite", "satellite_alt", "Sun'iy yo'ldosh", "view_dashboard"),
    ("/weather", "partly_cloudy_day", "Ob-havo", "view_dashboard"),
    ("/market", "storefront", "Bozor", "view_dashboard"),
    ("/irrigation", "water_drop", "Sug'orish", "view_dashboard"),
    ("/finance", "payments", "Moliya", "view_finance"),
    ("/ai", "smart_toy", "AI Yordamchi", "use_ai"),
    ("/reports", "description", "Hisobotlar", "export_reports"),
    ("/admin", "admin_panel_settings", "Administrator", "manage_users"),
    ("/settings", "settings", "Sozlamalar", "manage_settings"),
]


# --------------------------------------------------------------------------
# Auth helpers
# --------------------------------------------------------------------------
def current_user() -> dict | None:
    """The authenticated user dict from the per-browser session storage."""
    return app.storage.user.get("auth")


def require_login(permission: str | None = None) -> dict | None:
    """Guard for pages: redirects to /login (or /) when access is missing."""
    user = current_user()
    if user is None:
        ui.navigate.to("/login")
        return None
    if permission and not has_permission(user.get("role"), permission):
        ui.notify("Bu bo'limga ruxsatingiz yo'q.", type="negative")
        ui.navigate.to("/")
        return None
    return user


def logout() -> None:
    user = current_user()
    if user:
        audit("logout", user["username"])
    app.storage.user.clear()
    ui.navigate.to("/login")


def lang() -> str:
    return app.storage.user.get("language") or get_setting("language", "uz")


def t(text: str) -> str:
    return translate(text, lang())


# --------------------------------------------------------------------------
# Page shell
# --------------------------------------------------------------------------
@contextmanager
def shell(user: dict, title: str) -> Iterator[None]:
    """Standard chrome: header, nav drawer, content column."""
    theme.apply()
    stored_dark = app.storage.user.get("dark_mode")
    if stored_dark is None:
        stored_dark = get_setting("theme", "light") == "dark"
    dark = ui.dark_mode(value=bool(stored_dark))

    with ui.left_drawer(value=True, bordered=True).props("width=230") as drawer:
        with ui.row().classes("items-center gap-2 p-2"):
            ui.icon("agriculture").classes("text-3xl text-primary")
            with ui.column().classes("gap-0"):
                ui.label(settings.APP_NAME).classes("text-lg font-bold text-primary")
                ui.label(f"v{settings.APP_VERSION}").classes("text-xs opacity-60")
        ui.separator()
        for route, icon, label, permission in NAV_ITEMS:
            if not has_permission(user["role"], permission):
                continue
            ui.button(t(label), icon=icon,
                      on_click=lambda r=route: ui.navigate.to(r)) \
                .props("flat no-caps align=left").classes("w-full nav-btn")
        plugins = get_plugins()
        if plugins:
            ui.separator()
            ui.label("Plaginlar").classes("text-xs opacity-60 pl-3")
            for plugin in plugins:
                ui.button(plugin.name, icon=plugin.icon,
                          on_click=lambda r=plugin.route: ui.navigate.to(r)) \
                    .props("flat no-caps align=left").classes("w-full nav-btn")

    with ui.header(elevated=True).classes("items-center justify-between px-3"):
        with ui.row().classes("items-center gap-2"):
            ui.button(icon="menu", on_click=drawer.toggle) \
                .props("flat round color=white")
            ui.label(title).classes("text-lg font-medium")
        with ui.row().classes("items-center gap-2"):
            search_input = ui.input(placeholder=t("Qidiruv") + "...") \
                .props("dense standout dark clearable").classes("w-56")
            search_input.on("keydown.enter",
                            lambda: _open_search(search_input.value or ""))
            _online_chip()
            ui.button(icon="dark_mode",
                      on_click=lambda: _toggle_dark(dark)) \
                .props("flat round color=white").tooltip("Tungi/kunduzgi rejim")
            with ui.button(icon="account_circle").props("flat round color=white"):
                with ui.menu():
                    ui.menu_item(f"{user['name']} ({user['role']})") \
                        .props("disable")
                    ui.separator()
                    ui.menu_item(t("Chiqish"), on_click=logout)

    content = ui.column().classes("w-full p-4 gap-4 max-w-[1500px] mx-auto")
    with content:
        yield


def _toggle_dark(dark: ui.dark_mode) -> None:
    dark.value = not dark.value
    app.storage.user["dark_mode"] = dark.value


def _online_chip() -> None:
    from weather.service import is_online

    online = is_online()
    ui.chip(t("Onlayn") if online else t("Offlayn rejim"),
            icon="wifi" if online else "wifi_off",
            color="green-6" if online else "orange-8") \
        .props("dense text-color=white")


def _open_search(query: str) -> None:
    from utils.search import global_search

    results = global_search(query)
    with ui.dialog() as dialog, ui.card().classes("min-w-[560px]"):
        ui.label(f"Qidiruv: “{query}” — {len(results)} natija") \
            .classes("text-lg font-medium")
        if results.empty:
            ui.label("Hech narsa topilmadi.").classes("opacity-70")
        else:
            df_table(results, rows_per_page=8)
        ui.button("Yopish", on_click=dialog.close).props("flat")
    dialog.open()


# --------------------------------------------------------------------------
# Reusable widgets
# --------------------------------------------------------------------------
def kpi_card(icon: str, value: str, label: str, color: str = "primary") -> None:
    """Small KPI stat card used across dashboards."""
    with ui.card().classes("kpi-card items-start p-4"):
        ui.icon(icon).classes(f"text-2xl text-{color}")
        ui.label(value).classes("kpi-value")
        ui.label(label).classes("kpi-label")


def df_table(df: pd.DataFrame, rows_per_page: int = 10,
             title: str | None = None) -> None:
    """Render any DataFrame as a sortable, paginated table."""
    if title:
        ui.label(title).classes("section-title")
    if df is None or df.empty:
        ui.label("Ma'lumot topilmadi.").classes("opacity-70")
        return
    display = df.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].round(2)
    columns = [{"name": str(column), "label": str(column).replace("_", " ").title(),
                "field": str(column), "sortable": True, "align": "left"}
               for column in display.columns]
    ui.table(columns=columns, rows=display.to_dict(orient="records"),
             pagination=rows_per_page).classes("w-full")


def chart(options: dict, height: str = "h-80") -> None:
    """Render an ECharts options dict inside a styled card."""
    with ui.card().classes("chart-card"):
        ui.echart(options).classes(f"w-full {height}")


def download_file(path) -> None:
    """Trigger a browser download for a server-side file (NiceGUI 2/3 API)."""
    try:
        ui.download.file(str(path))  # NiceGUI >= 2.14
    except AttributeError:
        ui.download(str(path))


def raw_html(content: str) -> ui.html:
    """Render trusted server-generated HTML (e.g. folium maps) unsanitized.

    NiceGUI 3.x sanitizes ui.html by default, which strips the map iframe;
    our content never contains user input, so it is safe to disable.
    """
    try:
        return ui.html(content, sanitize=False)  # NiceGUI >= 3.0
    except TypeError:
        return ui.html(content)
