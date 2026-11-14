"""Yadro hayot sikli: kim boshqarayotgani, tashqaridan to'xtatish, band port tekshiruvi."""

import os
import socket
from collections.abc import Callable
from typing import Literal, cast

import psutil
from fastapi import FastAPI

ManagedBy = Literal["service", "standalone"]
ExitHook = Callable[[], None]
# Xizmat NSSM orqali ishlaydi: yadroning ota jarayoni shu nomda bo'ladi.
SERVICE_WRAPPER = "nssm.exe"
PORT_PROBE_TIMEOUT_S = 0.5


def managed_by() -> ManagedBy:
    """Yadro Windows xizmati ostidami (NSSM) yoki o'zi (shell yoki konsoldan) ishga tushganmi."""
    try:
        parent = psutil.Process(os.getppid()).name().lower()
    except (psutil.Error, OSError):
        return "standalone"
    return "service" if parent == SERVICE_WRAPPER else "standalone"


def set_exit_hook(app: FastAPI, hook: ExitHook) -> None:
    """`python -m srv1_core` serverni tartibli to'xtatadigan funksiyani shu yerga qo'yadi."""
    app.state.exit_hook = hook


def get_exit_hook(app: FastAPI) -> ExitHook | None:
    hook = getattr(app.state, "exit_hook", None)
    return cast(ExitHook, hook) if callable(hook) else None


def port_in_use(host: str, port: int) -> bool:
    """Manzilda kimdir tinglayaptimi. Ikkinchi yadro plaginlarni ishga tushirmasligi uchun."""
    target = "127.0.0.1" if host in ("0.0.0.0", "") else host  # noqa: S104 - bog'lanish emas
    try:
        with socket.create_connection((target, port), timeout=PORT_PROBE_TIMEOUT_S):
            return True
    except OSError:
        return False
