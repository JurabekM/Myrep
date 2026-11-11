"""Tizim holati (psutil): CPU, RAM, disklar, yadro jarayoni."""

import os
import time
from collections.abc import Mapping
from typing import Literal

import psutil
from pydantic import BaseModel


class CpuInfo(BaseModel):
    percent: float
    logical: int
    physical: int | None


class MemoryInfo(BaseModel):
    total: int
    available: int
    used: int
    percent: float


class DiskInfo(BaseModel):
    mount: str
    fstype: str
    total: int
    used: int
    free: int
    percent: float


class ProcessInfo(BaseModel):
    pid: int
    rss: int
    private: int | None
    threads: int


class SystemSnapshot(BaseModel):
    ts: float
    cpu: CpuInfo
    memory: MemoryInfo
    disks: list[DiskInfo]
    process: ProcessInfo


def prime_cpu() -> None:
    """Birinchi `cpu_percent` har doim 0.0 qaytaradi; hisoblagichni oldindan ishga tushiradi."""
    psutil.cpu_percent(interval=None)


def _cpu() -> CpuInfo:
    return CpuInfo(
        percent=psutil.cpu_percent(interval=None),
        logical=psutil.cpu_count(logical=True) or 1,
        physical=psutil.cpu_count(logical=False),
    )


def _memory() -> MemoryInfo:
    mem = psutil.virtual_memory()
    return MemoryInfo(total=mem.total, available=mem.available, used=mem.used, percent=mem.percent)


def _disks() -> list[DiskInfo]:
    disks: list[DiskInfo] = []
    for part in psutil.disk_partitions(all=False):
        # Faqat qattiq disklar: tarmoq va olinadigan disklar so'rovni osib qo'yishi mumkin.
        if "fixed" not in part.opts.split(","):
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        disks.append(
            DiskInfo(
                mount=part.mountpoint,
                fstype=part.fstype,
                total=usage.total,
                used=usage.used,
                free=usage.free,
                percent=usage.percent,
            )
        )
    return disks


def _process() -> ProcessInfo:
    proc = psutil.Process(os.getpid())
    with proc.oneshot():
        mem = proc.memory_info()
        private: int | None = getattr(mem, "private", None)
        return ProcessInfo(pid=proc.pid, rss=mem.rss, private=private, threads=proc.num_threads())


class ProcessMemory(BaseModel):
    name: str
    kind: Literal["core", "plugin"]
    pid: int
    rss: int
    private: int | None


class ProcessReport(BaseModel):
    budget_bytes: int
    total_rss: int
    processes: list[ProcessMemory]


# Butun tizim (yadro + Caddy + shell) bo'sh holatda shundan oshmasligi kerak.
IDLE_BUDGET_BYTES = 350 * 1024 * 1024


def _memory_of(name: str, kind: Literal["core", "plugin"], pid: int) -> ProcessMemory | None:
    try:
        mem = psutil.Process(pid).memory_info()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None
    return ProcessMemory(
        name=name, kind=kind, pid=pid, rss=mem.rss, private=getattr(mem, "private", None)
    )


def process_report(plugin_pids: Mapping[str, int]) -> ProcessReport:
    """Yadro va bola plaginlar bo'yicha xotira. Bloklovchi: `asyncio.to_thread` bilan chaqiring."""
    candidates = [_memory_of("core", "core", os.getpid())]
    candidates += [_memory_of(name, "plugin", pid) for name, pid in sorted(plugin_pids.items())]
    processes = [item for item in candidates if item is not None]
    return ProcessReport(
        budget_bytes=IDLE_BUDGET_BYTES,
        total_rss=sum(item.rss for item in processes),
        processes=processes,
    )


def take_snapshot() -> SystemSnapshot:
    """Bloklovchi chaqiruv: event loop'dan `asyncio.to_thread` orqali chaqiring."""
    return SystemSnapshot(
        ts=time.time(), cpu=_cpu(), memory=_memory(), disks=_disks(), process=_process()
    )
