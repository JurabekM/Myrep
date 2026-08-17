"""Administration: users, audit log, backups, imported files, DB health."""
from __future__ import annotations

import pandas as pd
from nicegui import ui

from app import layout
from core.security import audit, hash_password
from database import backup as db_backup
from database.engine import db_stats, read_df, session_scope
from database.models import User


def _users_frame() -> pd.DataFrame:
    return read_df(
        "SELECT id, username, full_name, role, active, created_at FROM users"
        " ORDER BY id")


@ui.page("/admin")
def admin_page() -> None:
    user = layout.require_login("manage_users")
    if user is None:
        return
    with layout.shell(user, "Administrator paneli"):
        with ui.grid(columns=2).classes("w-full gap-4"):
            # ---------------- Users ---------------------------------------
            with ui.card().classes("chart-card p-4 gap-2"):
                ui.label("Foydalanuvchilar").classes("section-title")
                users_box = ui.column().classes("w-full")

                def render_users() -> None:
                    users_box.clear()
                    with users_box:
                        layout.df_table(_users_frame(), rows_per_page=8)

                with ui.row().classes("gap-2 items-end flex-wrap"):
                    new_username = ui.input("Login").classes("w-32")
                    new_name = ui.input("F.I.Sh.").classes("w-40")
                    new_password = ui.input("Parol", password=True).classes("w-32")
                    new_role = ui.select(["admin", "manager", "viewer"],
                                         value="viewer", label="Rol").classes("w-28")

                    def add_user() -> None:
                        username = (new_username.value or "").strip().lower()
                        if not username or not new_password.value:
                            ui.notify("Login va parol majburiy.", type="warning")
                            return
                        with session_scope() as session:
                            if session.query(User).filter_by(
                                    username=username).first():
                                ui.notify("Bunday login mavjud.", type="negative")
                                return
                            session.add(User(
                                username=username,
                                full_name=new_name.value or username,
                                password_hash=hash_password(new_password.value),
                                role=new_role.value))
                        audit("user_created", user["username"], username)
                        ui.notify("Foydalanuvchi qo'shildi.", type="positive")
                        render_users()

                    ui.button("Qo'shish", icon="person_add", on_click=add_user) \
                        .props("unelevated")

                with ui.row().classes("gap-2 items-end flex-wrap"):
                    toggle_login = ui.input("Login (faollik/parol)").classes("w-40")
                    reset_password = ui.input("Yangi parol", password=True) \
                        .classes("w-32")

                    def toggle_active() -> None:
                        with session_scope() as session:
                            target = session.query(User).filter_by(
                                username=(toggle_login.value or "").strip().lower()
                            ).first()
                            if target is None:
                                ui.notify("Topilmadi.", type="negative")
                                return
                            if target.username == user["username"]:
                                ui.notify("O'zingizni bloklay olmaysiz.",
                                          type="warning")
                                return
                            target.active = not target.active
                            state = "faollashtirildi" if target.active \
                                else "bloklandi"
                        audit("user_toggled", user["username"],
                              f"{toggle_login.value}: {state}")
                        ui.notify(f"Foydalanuvchi {state}.", type="positive")
                        render_users()

                    def do_reset_password() -> None:
                        if not reset_password.value:
                            ui.notify("Yangi parolni kiriting.", type="warning")
                            return
                        with session_scope() as session:
                            target = session.query(User).filter_by(
                                username=(toggle_login.value or "").strip().lower()
                            ).first()
                            if target is None:
                                ui.notify("Topilmadi.", type="negative")
                                return
                            target.password_hash = hash_password(
                                reset_password.value)
                        audit("password_reset", user["username"],
                              toggle_login.value)
                        ui.notify("Parol yangilandi.", type="positive")

                    ui.button("Faollik", icon="toggle_on",
                              on_click=toggle_active).props("outline")
                    ui.button("Parolni tiklash", icon="lock_reset",
                              on_click=do_reset_password).props("outline")
                render_users()

            # ---------------- Backups -------------------------------------
            with ui.card().classes("chart-card p-4 gap-2"):
                ui.label("Zaxira nusxalar (Backup / Restore)") \
                    .classes("section-title")
                backups_box = ui.column().classes("w-full")

                def render_backups() -> None:
                    backups_box.clear()
                    with backups_box:
                        layout.df_table(pd.DataFrame(db_backup.list_backups()),
                                        rows_per_page=6)

                encrypt_switch = ui.switch(
                    "Shifrlash (cryptography o'rnatilgan bo'lsa)")

                def create() -> None:
                    path = db_backup.create_backup(
                        "manual", encrypt=bool(encrypt_switch.value))
                    ui.notify(f"Zaxira yaratildi: {path.name}", type="positive")
                    render_backups()

                restore_name = ui.input("Tiklash uchun fayl nomi").classes("w-full")

                def restore() -> None:
                    if db_backup.restore_backup((restore_name.value or "").strip()):
                        ui.notify("Baza tiklandi. Sahifani yangilang.",
                                  type="positive")
                    else:
                        ui.notify("Tiklash muvaffaqiyatsiz — fayl nomini "
                                  "tekshiring.", type="negative")

                with ui.row().classes("gap-2"):
                    ui.button("Zaxira yaratish", icon="backup", on_click=create) \
                        .props("unelevated")
                    ui.button("Tiklash", icon="restore", on_click=restore) \
                        .props("outline color=negative")
                render_backups()

        with ui.grid(columns=2).classes("w-full gap-4"):
            with ui.card().classes("chart-card"):
                audit_df = read_df(
                    "SELECT timestamp, username, action, details FROM audit_log"
                    " ORDER BY id DESC LIMIT 200")
                layout.df_table(audit_df, title="Audit jurnali (so'nggi 200)",
                                rows_per_page=10)
            with ui.column().classes("gap-4 w-full"):
                with ui.card().classes("chart-card"):
                    imports = read_df(
                        "SELECT uploaded_at, filename, file_type, uploaded_by,"
                        " summary FROM imported_files ORDER BY id DESC LIMIT 50")
                    layout.df_table(imports, title="Import qilingan fayllar",
                                    rows_per_page=5)
                with ui.card().classes("chart-card"):
                    stats = db_stats()
                    layout.df_table(
                        pd.DataFrame({"jadval": list(stats.keys()),
                                      "yozuvlar": list(stats.values())}),
                        title="Ma'lumotlar bazasi holati", rows_per_page=13)
