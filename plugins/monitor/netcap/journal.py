"""Jurnalga chiqish: davriy xulosa satri va belgilangan (shubhali) paketlar.

Yadro jurnali diskdagi faylga ham yoziladi va hajmi cheklangan, shuning uchun:
- oddiy paketlar yozilmaydi — ular faqat xulosada sanaladi;
- belgilangan paketlar bitta oraliqda `PACKETS_PER_INTERVAL` tadan oshmaydi (skan yoki
  hujum paytida minglab satr yozilmasin); qolgani xulosada `unlogged` bo'lib ko'rinadi;
- tarmoq jim bo'lsa, bo'sh xulosa bir marta yoziladi, keyin trafik qaytguncha sukut.
Paket ichidagi matn hech qachon yozilmaydi; manzillar yoziladi.
"""

import re
from collections.abc import Callable, Mapping
from typing import Any

PACKETS_PER_INTERVAL = 20
MAX_PROTOS = 8
STATS_EVENT = "netcap_stats"
PACKET_EVENT = "netcap_packet"
_KEY = re.compile(r"[^a-z0-9]+")
LogCall = Callable[..., None]


def _int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _endpoint(address: object, port: object) -> str:
    text = str(address or "")
    return f"{text}:{port}" if isinstance(port, int) else text


def _counts(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    items: Mapping[object, object] = value  # pyright: ignore[reportUnknownVariableType]
    return {str(name): _int(count) for name, count in items.items()}


class Journal:
    """Ishchining har `tick` xabari `feed` ga beriladi; vaqt o'lchovi — xabardagi `ts`."""

    def __init__(self, log: LogCall, interval_s: float, interface: str) -> None:
        self._log = log
        self._interval_s = interval_s
        self._interface = interface
        self._since: float | None = None
        self._total = 0
        self._bytes = 0
        self._marked_total = 0
        self._protos: dict[str, int] = {}
        self._alerts = 0
        self._logged = 0
        self._idle = False

    @property
    def enabled(self) -> bool:
        return self._interval_s > 0

    def feed(self, message: Mapping[str, Any], packets: list[dict[str, Any]], alerts: int) -> None:
        if not self.enabled:
            return
        now = message.get("ts")
        if not isinstance(now, int | float):
            return
        since = self._since
        if since is None or message.get("paused"):
            # Pauza xulosaga kirmaydi: hisob pauzadan chiqqan paytdan qayta boshlanadi.
            self._restart(float(now), message, keep_base=since is None)
            if message.get("paused"):
                return
            since = float(now)
        for packet in packets:
            if packet.get("mark") and self._logged < PACKETS_PER_INTERVAL:
                self._logged += 1
                self._log_packet(packet)
        self._alerts += alerts
        elapsed = float(now) - since
        if elapsed >= self._interval_s:
            self._summary(message, elapsed)
            self._restart(float(now), message, keep_base=False)

    def _restart(self, now: float, message: Mapping[str, Any], *, keep_base: bool) -> None:
        """Yangi oraliq. `keep_base` — birinchi tick: sanoq noldan (ushlash boshidan) boshlanadi."""
        self._since = now
        self._alerts, self._logged = 0, 0
        if keep_base:
            return
        self._total, self._bytes = _int(message.get("total")), _int(message.get("bytes"))
        self._marked_total = _int(message.get("marked"))
        self._protos = _counts(message.get("protos"))

    def _log_packet(self, packet: Mapping[str, Any]) -> None:
        # Interfeys nomi har satrda takrorlanmaydi: u xulosada va `netcap_started` da bor.
        fields: dict[str, Any] = {
            "proto": str(packet.get("proto", "")),
            "src": _endpoint(packet.get("src"), packet.get("sport")),
            "dst": _endpoint(packet.get("dst"), packet.get("dport")),
            "len": _int(packet.get("len")),
            "mark": str(packet.get("mark", ""))[:80],
        }
        info = str(packet.get("info", ""))[:120]
        if info:
            fields["info"] = info
        self._log("warning", PACKET_EVENT, **fields)

    def _summary(self, message: Mapping[str, Any], elapsed: float) -> None:
        total, size = _int(message.get("total")), _int(message.get("bytes"))
        packets = max(0, total - self._total)
        marked = max(0, _int(message.get("marked")) - self._marked_total)
        quiet = packets == 0 and marked == 0 and self._alerts == 0
        if quiet and self._idle:
            return
        self._idle = quiet
        fields: dict[str, Any] = {
            "interface": self._interface,
            "seconds": round(elapsed),
            "packets": packets,
            "pps": round(packets / elapsed, 1) if elapsed > 0 else 0.0,
            "kb": round(max(0, size - self._bytes) / 1024, 1),
            "total": total,
        }
        fields |= self._proto_fields(_counts(message.get("protos")), set(fields))
        hosts = message.get("hosts")
        if isinstance(hosts, list) and hosts and isinstance(hosts[0], Mapping):
            first: Mapping[object, object] = hosts[0]  # pyright: ignore[reportUnknownVariableType]
            fields["top"] = str(first.get("ip", ""))
        fields |= {"marked": marked, "alerts": self._alerts}
        if marked > self._logged:
            fields["unlogged"] = marked - self._logged
        self._log("info", STATS_EVENT, **fields)

    def _proto_fields(self, current: Mapping[str, int], taken: set[str]) -> dict[str, int]:
        """Oraliqdagi paketlar protokol bo'yicha, kamayish tartibida: `tcp=64 udp=20 dns=4`."""
        reserved = taken | {
            "top",
            "marked",
            "alerts",
            "unlogged",
            "event",
            "level",
            "logger",
            "timestamp",
        }
        deltas = {name: count - self._protos.get(name, 0) for name, count in current.items()}
        ordered = sorted(deltas.items(), key=lambda item: (-item[1], item[0]))
        result: dict[str, int] = {}
        for name, count in ordered:
            key = _KEY.sub("_", name.lower()).strip("_")
            if count > 0 and key and key not in reserved and key not in result:
                result[key] = count
            if len(result) >= MAX_PROTOS:
                break
        return result
