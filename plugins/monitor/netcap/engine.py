"""Ishchi jarayonning holati: hisoblagichlar, navbat, chiqarilgan manzillar, buyruqlar.

Sof Python (scapy'siz sinaladi). `handle` ushlash oqimidan, `tick` va `command` boshqa
oqimlardan chaqiriladi — umumiy ro'yxatlar qulf ostida.
"""

import ipaddress
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .detect import Alert, Detector, Limits, Record
from .text import printable

MAX_HOSTS = 2000
TOP_HOSTS = 20
MAX_PENDING_ALERTS = 500
# Protokol nomlari soni cheklangan; kutilmagan ko'p nom kelsa, ortiqchasi `other` ga yig'iladi.
MAX_PROTOS = 24


@dataclass(slots=True, frozen=True)
class Options:
    interface: str
    bpf_filter: str = ""
    # Standart holatda paket ichidagi matn hech qayerga yozilmaydi.
    store_payload: bool = False
    payload_chars: int = 256
    geo: bool = False
    excluded: frozenset[str] = frozenset()
    limits: Limits = field(default_factory=Limits)
    # Bir soniyada jadvalga tushadigan paketlar; qolgani faqat sanaladi va tekshiriladi.
    rows_per_tick: int = 200

    @classmethod
    def from_json(cls, raw: Mapping[str, Any]) -> "Options":
        limits = Limits(
            suspicious_ports=frozenset(int(port) for port in raw.get("suspicious_ports", ())),
            scan_ports=int(raw.get("scan_ports", 15)),
            scan_window_s=float(raw.get("scan_window_s", 10.0)),
            quiet_s=float(raw.get("quiet_s", 60.0)),
        )
        return cls(
            interface=str(raw["interface"]),
            bpf_filter=str(raw.get("bpf_filter", "")),
            store_payload=bool(raw.get("store_payload", False)),
            payload_chars=int(raw.get("payload_chars", 256)),
            geo=bool(raw.get("geo", False)),
            excluded=frozenset(normalize_ips(raw.get("excluded", ()))),
            limits=limits,
            rows_per_tick=int(raw.get("rows_per_tick", 200)),
        )


def normalize_ip(value: str) -> str:
    """IPv4/IPv6 manzilning yagona ko'rinishi; yaroqsiz bo'lsa `ValueError`."""
    return str(ipaddress.ip_address(value.strip()))


def normalize_ips(values: Any) -> list[str]:  # noqa: ANN401 — JSON'dan kelgan xom qiymat
    result: list[str] = []
    for value in values if isinstance(values, (list, tuple)) else ():  # pyright: ignore[reportUnknownVariableType]
        try:
            result.append(normalize_ip(str(value)))  # pyright: ignore[reportUnknownArgumentType]
        except ValueError:
            continue
    return result


class Engine:
    def __init__(self, options: Options, geo: Callable[[str], str] | None = None) -> None:
        self.options = options
        self.detector = Detector(options.limits)
        self.excluded: frozenset[str] = options.excluded
        self.paused = False
        self.total = 0
        self.ignored = 0
        self.skipped = 0
        self.errors = 0
        self.bytes = 0
        # Belgilangan (shubhali) paketlar soni, ushlash boshidan beri.
        self.marked = 0
        self.last_error = ""
        self._geo = geo
        self._lock = threading.Lock()
        self._rows: list[dict[str, Any]] = []
        self._alerts: list[Alert] = []
        self._hosts: dict[str, list[int]] = {}
        self._protos: dict[str, int] = {}
        self._marked_rows = 0
        self._ticked_total = 0

    # --- ushlash oqimi ----------------------------------------------------
    def handle(self, record: Record | None) -> None:
        if record is None:
            return
        excluded = self.excluded
        if self.paused or record.src in excluded or record.dst in excluded:
            self.ignored += 1
            return
        self.total += 1
        self.bytes += record.length
        alerts = self.detector.check(record)
        marked = bool(record.mark)
        limit = self.options.rows_per_tick
        with self._lock:
            if alerts and len(self._alerts) < MAX_PENDING_ALERTS:
                self._alerts.extend(alerts)
            if marked:
                self.marked += 1
            # Belgilangan paket oddiylaridan ustun: jadval to'lgan bo'lsa ham tushadi. Lekin
            # toshqinda (skan, hujum) uning o'zi ham cheklanadi — tick cheksiz kattalashmasin.
            if len(self._rows) < limit or (marked and self._marked_rows < limit):
                self._rows.append(self._row(record))
                self._marked_rows += marked
            else:
                self.skipped += 1
            for address in (record.src, record.dst):
                self._count_host(address, record.length)
            self._count_proto(record.proto)

    def failed(self, error: BaseException) -> None:
        """Bitta paketni tahlil qilib bo'lmadi: sanaladi, ushlash davom etadi."""
        self.errors += 1
        self.last_error = f"{type(error).__name__}: {error}"[:200]

    def _row(self, record: Record) -> dict[str, Any]:
        row: dict[str, Any] = {
            "ts": round(record.ts, 3),
            "proto": record.proto,
            "src": record.src,
            "sport": record.sport,
            "dst": record.dst,
            "dport": record.dport,
            "len": record.length,
            "info": record.info[:120],
            "mark": record.mark,
        }
        if self.options.store_payload and record.payload:
            row["payload"] = printable(record.payload, self.options.payload_chars)
        return row

    def _count_proto(self, proto: str) -> None:
        name = proto if proto in self._protos or len(self._protos) < MAX_PROTOS else "other"
        self._protos[name] = self._protos.get(name, 0) + 1

    def _count_host(self, address: str, length: int) -> None:
        entry = self._hosts.get(address)
        if entry is None:
            if len(self._hosts) >= MAX_HOSTS:
                keep = sorted(self._hosts.items(), key=lambda item: item[1][1], reverse=True)
                self._hosts = dict(keep[: MAX_HOSTS // 2])
            entry = self._hosts[address] = [0, 0]
        entry[0] += 1
        entry[1] += length

    # --- boshqaruv --------------------------------------------------------
    def command(self, message: Mapping[str, Any]) -> bool:
        """Plagindan kelgan buyruq. `stop` uchun `False` qaytadi (ishchi yopiladi)."""
        name = message.get("c")
        if name == "stop":
            return False
        if name == "pause":
            self.paused = True
        elif name == "resume":
            self.paused = False
        elif name == "exclude":
            self.excluded = frozenset(normalize_ips(message.get("ips", ())))
        return True

    def tick(self, now: float, elapsed_s: float) -> dict[str, Any]:
        """Oxirgi `tick`dan beri to'planganini bo'shatib, plaginga yuboriladigan xabarni tuzadi."""
        with self._lock:
            rows, self._rows, self._marked_rows = self._rows, [], 0
            alerts, self._alerts = self._alerts, []
            top = sorted(self._hosts.items(), key=lambda item: item[1][1], reverse=True)
            top = top[:TOP_HOSTS]
            protos = dict(self._protos)
        delta, self._ticked_total = self.total - self._ticked_total, self.total
        geo = self._geo
        return {
            "t": "tick",
            "ts": round(now, 3),
            "paused": self.paused,
            "total": self.total,
            "ignored": self.ignored,
            "skipped": self.skipped,
            "errors": self.errors,
            "last_error": self.last_error,
            "suppressed": self.detector.suppressed,
            "bytes": self.bytes,
            "marked": self.marked,
            "pps": round(delta / elapsed_s, 1) if elapsed_s > 0 else 0.0,
            # Ushlash boshidan beri protokollar bo'yicha paketlar soni.
            "protos": protos,
            "packets": rows,
            "alerts": [
                {"ts": round(a.ts, 3), "kind": a.kind, "src": a.src, "dst": a.dst, "note": a.note}
                for a in alerts
            ],
            "hosts": [
                {
                    "ip": address,
                    "packets": counts[0],
                    "bytes": counts[1],
                    "where": geo(address) if geo is not None else "",
                }
                for address, counts in top
            ],
        }
