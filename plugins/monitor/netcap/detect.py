"""Xavf tekshiruvlari. Sof Python: scapy'siz sinaladi.

Har tekshiruv bitta paket yozuvini (`Record`) oladi. Bir xil signal (`tur`, manba,
manzil) `quiet_s` ichida takror chiqmaydi — jurnal va bildirishnoma toshib ketmasin.
"""

from collections import OrderedDict
from dataclasses import dataclass, field

from .text import find_secret

MAX_TRACKED = 5000


@dataclass(slots=True)
class Record:
    """Tahlil qilingan bitta paket."""

    ts: float
    proto: str
    src: str
    dst: str
    sport: int | None = None
    dport: int | None = None
    length: int = 0
    flags: str = ""
    info: str = ""
    payload: bytes = b""
    mark: str = ""


@dataclass(slots=True, frozen=True)
class Alert:
    ts: float
    # port | null_scan | fin_scan | xmas_scan | port_scan | secret
    kind: str
    src: str
    dst: str
    note: str = ""


@dataclass(slots=True, frozen=True)
class Limits:
    suspicious_ports: frozenset[int] = frozenset()
    # Bitta manbadan bitta manzilga `scan_window_s` ichida shuncha turli portga
    # yangi ulanish urinishi (SYN) — port skanerlash.
    scan_ports: int = 15
    scan_window_s: float = 10.0
    quiet_s: float = 60.0


@dataclass(slots=True)
class _Window:
    started: float
    ports: set[int] = field(default_factory=set[int])


def _is_syn(record: Record) -> bool:
    return record.proto == "TCP" and "S" in record.flags and "A" not in record.flags


class Detector:
    def __init__(self, limits: Limits) -> None:
        self.limits = limits
        self._scans: OrderedDict[tuple[str, str], _Window] = OrderedDict()
        self._last: OrderedDict[tuple[str, str, str], float] = OrderedDict()
        self.suppressed = 0

    def check(self, record: Record) -> list[Alert]:
        """Paketni tekshiradi; `record.mark` ga topilgan sir turini yozadi."""
        found: list[Alert] = []
        if record.proto == "TCP":
            self._flags(record, found)
            if _is_syn(record):
                self._port_scan(record, found)
        self._suspicious_port(record, found)
        if record.payload:
            record.mark = find_secret(record.payload)
            if record.mark:
                note = record.mark if record.dport is None else f"{record.mark} → :{record.dport}"
                found.append(Alert(record.ts, "secret", record.src, record.dst, note))
        return [alert for alert in found if self._allow(alert)]

    def _flags(self, record: Record, found: list[Alert]) -> None:
        kind = {"": "null_scan", "F": "fin_scan", "FPU": "xmas_scan"}.get(record.flags)
        if kind is not None:
            found.append(Alert(record.ts, kind, record.src, record.dst, f":{record.dport}"))

    def _suspicious_port(self, record: Record, found: list[Alert]) -> None:
        # Faqat **manzil** porti va faqat yangi murojaat: javob paketlari signal bermaydi.
        if record.dport not in self.limits.suspicious_ports:
            return
        if _is_syn(record) or record.proto == "UDP":
            note = f"{record.proto} :{record.dport}"
            found.append(Alert(record.ts, "port", record.src, record.dst, note))

    def _port_scan(self, record: Record, found: list[Alert]) -> None:
        if record.dport is None:
            return
        key = (record.src, record.dst)
        window = self._scans.get(key)
        # Oyna birinchi urinishdan boshlanadi va har paketda uzaymaydi.
        if window is None or record.ts - window.started > self.limits.scan_window_s:
            window = _Window(record.ts)
            self._scans[key] = window
            self._scans.move_to_end(key)
            while len(self._scans) > MAX_TRACKED:
                self._scans.popitem(last=False)
        window.ports.add(record.dport)
        if len(window.ports) >= self.limits.scan_ports:
            del self._scans[key]
            note = f"{len(window.ports)} port / {record.ts - window.started:.1f} s"
            found.append(Alert(record.ts, "port_scan", record.src, record.dst, note))

    def _allow(self, alert: Alert) -> bool:
        key = (alert.kind, alert.src, alert.dst)
        last = self._last.get(key)
        if last is not None and alert.ts - last < self.limits.quiet_s:
            self.suppressed += 1
            return False
        self._last[key] = alert.ts
        self._last.move_to_end(key)
        while len(self._last) > MAX_TRACKED:
            self._last.popitem(last=False)
        return True
