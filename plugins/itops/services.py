"""Windows xizmatlari: ro'yxat (psutil) va boshqarish (pywin32). Bloklovchi funksiyalar."""
# pywin32 tip ma'lumotisiz keladi.
# pyright: reportMissingModuleSource=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

import time
from typing import Any, Literal

import psutil
import pywintypes
import win32serviceutil

from .models import ItopsError

Action = Literal["start", "stop", "restart"]
# To'xtatilsa tizim ishdan chiqadi yoki qayta yuklashni talab qiladi.
CRITICAL = frozenset(
    name.lower()
    for name in (
        "RpcSs",
        "RpcEptMapper",
        "DcomLaunch",
        "SamSs",
        "LSM",
        "Power",
        "PlugPlay",
        "BrokerInfrastructure",
        "CoreMessagingRegistrar",
        "SystemEventsBroker",
        "gpsvc",
        "ProfSvc",
        "EventLog",
    )
)
WAIT_S = 15.0
_ERRORS = {
    5: (403, "administrator huquqi kerak (yadro oddiy foydalanuvchi nomidan ishlayapti)"),
    1051: (409, "bu xizmatga boshqa ishlayotgan xizmatlar bog'liq"),
    1052: (409, "xizmat bu buyruqni hozir qabul qilmaydi"),
    1056: (409, "xizmat allaqachon ishlayapti"),
    1058: (409, "xizmat o'chirib qo'yilgan (disabled)"),
    1060: (404, "bunday xizmat yo'q"),
    1062: (409, "xizmat ishlamayapti"),
}
_WANTED = {"start": "running", "stop": "stopped", "restart": "running"}


def list_services(search: str, state: str) -> list[dict[str, Any]]:
    needle = search.strip().lower()
    rows: list[dict[str, Any]] = []
    for service in psutil.win_service_iter():
        try:
            name, title = service.name(), service.display_name() or ""
            row: dict[str, Any] = {
                "name": name,
                "title": title,
                "state": service.status(),
                "start": service.start_type(),
                "pid": service.pid(),
                "protected": name.lower() in CRITICAL,
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue
        if state and row["state"] != state:
            continue
        if needle and needle not in name.lower() and needle not in title.lower():
            continue
        rows.append(row)
    rows.sort(key=lambda row: str(row["name"]).lower())
    return rows


def _state(name: str) -> str:
    try:
        return psutil.win_service_get(name).status()
    except psutil.NoSuchProcess as exc:
        raise ItopsError(404, f"bunday xizmat yo'q: {name}") from exc


def control_service(name: str, action: Action) -> dict[str, Any]:
    """Xizmatni boshqaradi va kerakli holatni `WAIT_S` soniyagacha kutadi."""
    before = _state(name)
    if action != "start" and name.lower() in CRITICAL:
        raise ItopsError(403, f"{name} — tizim uchun muhim xizmat, to'xtatilmaydi")
    try:
        if action == "start":
            win32serviceutil.StartService(name)
        elif action == "stop":
            win32serviceutil.StopService(name)
        else:
            win32serviceutil.RestartService(name, waitSeconds=int(WAIT_S))
    except pywintypes.error as exc:
        code = int(exc.winerror)
        status, text = _ERRORS.get(code, (502, f"Windows xatosi {code}"))
        raise ItopsError(status, f"{name}: {text}") from exc
    wanted = _WANTED[action]
    deadline = time.monotonic() + WAIT_S
    state = _state(name)
    while state != wanted and time.monotonic() < deadline:
        time.sleep(0.25)
        state = _state(name)
    if state != wanted:
        raise ItopsError(504, f"{name}: {WAIT_S:.0f} soniyada «{wanted}» holatiga o'tmadi")
    return {"name": name, "before": before, "state": state}
