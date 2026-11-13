"""Tizim holatini o'lchash (`psutil`). Sinxron; xizmat uni ishchi oqimda chaqiradi."""

import time

import psutil

from .models import Disk, Sample


def _disks() -> tuple[Disk, ...]:
    disks: list[Disk] = []
    for part in psutil.disk_partitions(all=False):
        # Faqat qattiq disklar: tarmoq va olinadigan disklar so'rovni osib qo'yishi mumkin.
        if "fixed" not in part.opts.split(","):
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        disks.append(Disk(mount=part.mountpoint, free=usage.free, total=usage.total))
    return tuple(disks)


def tree_rss(root_pid: int) -> int:
    """`root_pid` va uning barcha avlodlarining xotirasi (Working Set), baytlarda."""
    try:
        root = psutil.Process(root_pid)
        processes = [root, *root.children(recursive=True)]
    except psutil.Error:
        return 0
    total = 0
    for process in processes:
        try:
            total += process.memory_info().rss
        except psutil.Error:
            continue
    return total


def measure(root_pid: int, cpu_interval_s: float | None = None) -> Sample:
    """`cpu_interval_s` berilsa, CPU shu vaqt davomida o'lchanadi (chaqiruv shuncha to'xtaydi);
    aks holda oldingi chaqiruvdan beri o'tgan davr bo'yicha."""
    cpu = psutil.cpu_percent(interval=cpu_interval_s)
    memory = psutil.virtual_memory()
    return Sample(
        ts=time.time(),
        cpu=cpu,
        memory=memory.percent,
        memory_used=memory.total - memory.available,
        memory_total=memory.total,
        srv1_rss=tree_rss(root_pid),
        disks=_disks(),
    )
