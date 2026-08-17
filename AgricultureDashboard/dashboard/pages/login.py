"""Login page with rate limiting and audit logging."""
from __future__ import annotations

from nicegui import app, ui

from app import theme
from config import settings
from core.security import audit, login_limiter, verify_password
from database.engine import session_scope
from database.models import User


def _attempt_login(username: str, password: str) -> None:
    username = (username or "").strip().lower()
    if not username or not password:
        ui.notify("Login va parolni kiriting.", type="warning")
        return
    if login_limiter.is_locked(username):
        ui.notify("Juda ko'p muvaffaqiyatsiz urinish. "
                  f"{settings.LOGIN_LOCK_MINUTES} daqiqadan so'ng qayta urining.",
                  type="negative")
        return
    with session_scope() as session:
        user = session.query(User).filter_by(username=username, active=True).first()
    if user is None or not verify_password(password, user.password_hash):
        login_limiter.register_failure(username)
        audit("login_failed", username)
        ui.notify("Login yoki parol noto'g'ri.", type="negative")
        return
    login_limiter.register_success(username)
    app.storage.user["auth"] = {
        "username": user.username, "name": user.full_name or user.username,
        "role": user.role,
    }
    audit("login", user.username)
    ui.navigate.to("/")


@ui.page("/login")
def login_page() -> None:
    theme.apply()
    ui.query("body").classes("bg-green-1")
    with ui.column().classes("absolute-center items-center gap-4"):
        with ui.card().classes("p-8 items-center gap-3 rounded-2xl shadow-6 w-96"):
            ui.icon("agriculture").classes("text-6xl text-primary")
            ui.label(settings.APP_NAME).classes("text-2xl font-bold text-primary")
            ui.label("Qishloq xo'jaligi analitik platformasi") \
                .classes("text-sm opacity-70 text-center")
            username = ui.input("Login").props("outlined dense") \
                .classes("w-full")
            password = ui.input("Parol", password=True,
                                password_toggle_button=True) \
                .props("outlined dense").classes("w-full")
            password.on("keydown.enter",
                        lambda: _attempt_login(username.value, password.value))
            ui.button("Kirish",
                      on_click=lambda: _attempt_login(username.value, password.value)) \
                .props("unelevated size=lg").classes("w-full")
            with ui.expansion("Demo hisoblar").classes("w-full text-xs"):
                ui.markdown(
                    "| Login | Parol | Rol |\n|---|---|---|\n"
                    "| `admin` | `admin123` | Administrator |\n"
                    "| `menejer` | `manager123` | Menejer |\n"
                    "| `kuzatuvchi` | `viewer123` | Kuzatuvchi |"
                )
