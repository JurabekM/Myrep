"""Tizim holati (psutil): CPU, RAM, disklar, yadro jarayoni."""

import os
import time

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


def take_snapshot() -> SystemSnapshot:
    """Bloklovchi chaqiruv: event loop'dan `asyncio.to_thread` orqali chaqiring."""
    return SystemSnapshot(
        ts=time.time(), cpu=_cpu(), memory=_memory(), disks=_disks(), process=_process()
    )
