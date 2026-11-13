"""Ogohlantirish qoidalari. Sof mantiq: kirish — o'lchov va chegaralar, chiqish — o'tishlar.

Har qoida ikki holatli (tinch / faol). Faol holatga o'tishda `raised`, qaytishda
`cleared` yozuvi chiqadi; orada takror yozuv bo'lmaydi. Chegara atrofida tebranish
yozuvlarni ko'paytirmasligi uchun qaytish chegarasi sal uzoqroq (gisterezis).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from .models import GB, Sample, Thresholds

# Foizli qoidalar: chegaradan shuncha foiz-band pastga tushgandagina tinchlanadi.
HYSTERESIS_PERCENT = 5.0
# Disk: bo'sh joy chegaradan shuncha marta ko'p bo'lgandagina tinchlanadi.
DISK_RECOVERY_FACTOR = 1.1
FAILED_STATES = frozenset({"crashed", "error"})

State = Literal["raised", "cleared"]


@dataclass(frozen=True, slots=True)
class Alert:
    ts: float
    key: str
    state: State
    # Qiymat va chegara: `memory`/`cpu` — foiz, `disk:*` — GB. Plagin hodisasida yo'q.
    value: float | None = None
    limit: float | None = None
    note: str = ""


def disk_key(mount: str) -> str:
    return f"disk:{mount}"


def plugin_key(name: str) -> str:
    return f"plugin:{name}"


class Evaluator:
    def __init__(self, active: Iterable[str] = ()) -> None:
        self.active: set[str] = set(active)
        self._cpu_since: float | None = None

    def _move(
        self, out: list[Alert], ts: float, key: str, on: bool, off: bool, value: float, limit: float
    ) -> None:
        if key not in self.active and on:
            self.active.add(key)
            out.append(Alert(ts, key, "raised", round(value, 1), limit))
        elif key in self.active and off:
            self.active.discard(key)
            out.append(Alert(ts, key, "cleared", round(value, 1), limit))

    def _cpu(self, out: list[Alert], sample: Sample, limits: Thresholds) -> None:
        limit = limits.cpu_percent
        over = limit > 0 and sample.cpu >= limit
        if over:
            if self._cpu_since is None:
                self._cpu_since = sample.ts
        elif "cpu" not in self.active:
            self._cpu_since = None
        held = self._cpu_since is not None and sample.ts - self._cpu_since >= (
            limits.cpu_minutes * 60
        )
        off = limit <= 0 or sample.cpu < limit - HYSTERESIS_PERCENT
        self._move(out, sample.ts, "cpu", over and held, off, sample.cpu, limit)
        if "cpu" not in self.active and not over:
            self._cpu_since = None

    def _disks(self, out: list[Alert], sample: Sample, limits: Thresholds) -> None:
        limit = limits.disk_free_gb
        seen: set[str] = set()
        for disk in sample.disks:
            key = disk_key(disk.mount)
            seen.add(key)
            free = disk.free / GB
            on = limit > 0 and free < limit
            off = limit <= 0 or free >= limit * DISK_RECOVERY_FACTOR
            self._move(out, sample.ts, key, on, off, free, limit)
        # Disk yo'qolgan (uzilgan) bo'lsa, uning ogohlantirishi abadiy faol qolmasin.
        for key in sorted(k for k in self.active if k.startswith("disk:") and k not in seen):
            self.active.discard(key)
            out.append(Alert(sample.ts, key, "cleared", None, limit, "disk topilmadi"))

    def check(self, sample: Sample, limits: Thresholds) -> list[Alert]:
        """O'lchovni qoidalarga soladi; holati o'zgargan qoidalar uchun yozuv qaytaradi."""
        out: list[Alert] = []
        limit = limits.memory_percent
        self._move(
            out,
            sample.ts,
            "memory",
            limit > 0 and sample.memory >= limit,
            limit <= 0 or sample.memory < limit - HYSTERESIS_PERCENT,
            sample.memory,
            limit,
        )
        self._cpu(out, sample, limits)
        self._disks(out, sample, limits)
        return out

    def plugin_state(self, ts: float, name: str, status: str, error: str) -> Alert | None:
        """Boshqa plagin yiqilsa `raised`, qayta ishga tushsa yoki o'chirilsa `cleared`."""
        key = plugin_key(name)
        if status in FAILED_STATES and key not in self.active:
            self.active.add(key)
            return Alert(ts, key, "raised", note=error[:200])
        if status in {"running", "stopped"} and key in self.active:
            self.active.discard(key)
            return Alert(ts, key, "cleared", note=status)
        return None
