"""Jarayonlar: ro'yxat va to'xtatish (bloklovchi funksiyalar — `asyncio.to_thread` bilan)."""

import os
from typing import Any, Literal

import psutil

from .models import ItopsError

Sort = Literal["memory", "cpu", "name", "pid"]
# To'xtatilsa Windows yiqiladi yoki seans uziladi.
CRITICAL = frozenset(
    {
        "system",
        "system idle process",
        "registry",
        "memory compression",
        "memcompression",
        "secure system",
        "smss.exe",
        "csrss.exe",
        "wininit.exe",
        "winlogon.exe",
        "services.exe",
        "lsass.exe",
        "svchost.exe",
        "dwm.exe",
        "fontdrvhost.exe",
    }
)
_ATTRS = ["pid", "name", "username", "memory_info", "create_time", "cpu_percent"]
KILL_WAIT_S = 3.0
START_TOLERANCE_S = 1.0


def own_tree() -> set[int]:
    """Yadro jarayoni, uning ishga tushirgichi va avlodlari (plaginlar, Caddy, loyihalar)."""
    me = psutil.Process(os.getpid())
    pids = {me.pid}
    try:
        parent = me.parent()
        if parent is not None and parent.name().lower() == me.name().lower():
            pids.add(parent.pid)  # venv'dagi python.exe ishga tushirgichi
        pids |= {child.pid for child in me.children(recursive=True)}
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return pids


def protected_reason(pid: int, name: str, own: set[int]) -> str | None:
    if pid in (0, 4) or name.lower() in CRITICAL:
        return "tizim jarayoni"
    if pid in own:
        return "SRV_1 ning o'z jarayoni (plaginlar sahifasidan boshqariladi)"
    return None


def _row(info: dict[str, Any], cores: int, own: set[int]) -> dict[str, Any]:
    name = str(info["name"] or "")
    memory = info["memory_info"]
    return {
        "pid": info["pid"],
        "name": name,
        "user": str(info["username"] or "").rsplit("\\", 1)[-1],
        "cpu": round((info["cpu_percent"] or 0.0) / cores, 1),
        "memory": memory.rss if memory is not None else 0,
        "started": info["create_time"] or 0.0,
        "protected": protected_reason(info["pid"], name, own) is not None,
    }


def list_processes(search: str, sort: Sort, limit: int) -> list[dict[str, Any]]:
    """CPU foizi — oldingi chaqiruvdan beri, barcha yadrolarga nisbatan (0–100)."""
    cores = psutil.cpu_count() or 1
    own = own_tree()
    needle = search.strip().lower()
    rows = [_row(proc.info, cores, own) for proc in psutil.process_iter(_ATTRS)]
    if needle:
        rows = [r for r in rows if needle in r["name"].lower() or needle in r["user"].lower()]
    if sort == "name":
        rows.sort(key=lambda row: str(row["name"]).lower())
    else:
        rows.sort(key=lambda row: row[sort], reverse=sort != "pid")
    return rows[:limit]


def release_cache() -> None:
    """`psutil.process_iter` keshini bo'shatadi.

    Kesh har jarayon uchun bittadan ochiq handle ushlab turadi (CPU foizini oldingi
    chaqiruvga nisbatan hisoblash uchun kerak). Ro'yxat so'ralmay qo'ygach bo'shatiladi;
    keyingi birinchi chaqiruvda CPU ustuni 0 ko'rsatadi.
    """
    psutil.process_iter.cache_clear()


def kill_process(pid: int, started: float | None) -> dict[str, Any]:
    """Jarayonni to'xtatadi. `started` berilsa, PID qayta ishlatilmaganini tekshiradi."""
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        created = proc.create_time()
    except psutil.NoSuchProcess as exc:
        raise ItopsError(404, f"bunday jarayon yo'q: {pid}") from exc
    except psutil.AccessDenied as exc:
        raise ItopsError(403, f"jarayonga ruxsat yo'q: {pid}") from exc
    reason = protected_reason(pid, name, own_tree())
    if reason is not None:
        raise ItopsError(403, f"{name} ({pid}) to'xtatilmaydi: {reason}")
    if started is not None and abs(created - started) > START_TOLERANCE_S:
        raise ItopsError(409, f"PID {pid} endi boshqa jarayonga tegishli; ro'yxatni yangilang")
    try:
        proc.terminate()
        proc.wait(KILL_WAIT_S)
    except psutil.NoSuchProcess:
        pass
    except psutil.AccessDenied as exc:
        raise ItopsError(403, f"{name} ({pid}) ni to'xtatishga ruxsat yo'q") from exc
    except psutil.TimeoutExpired as exc:
        raise ItopsError(504, f"{name} ({pid}) {KILL_WAIT_S:.0f} soniyada to'xtamadi") from exc
    return {"pid": pid, "name": name, "killed": True}
