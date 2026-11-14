"""scapy paketini `Record` ga aylantirish. scapy faqat shu modul va `worker` da ishlatiladi."""
# scapy tip izohlarisiz: bu faylda noma'lum tiplar haqidagi tekshiruvlar o'chirilgan.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportMissingTypeStubs=false
# pyright: reportArgumentType=false, reportAttributeAccessIssue=false

from typing import Any

from scapy.layers.dns import DNS
from scapy.layers.inet import ICMP, IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from scapy.layers.l2 import ARP
from scapy.packet import Packet, Raw

from .detect import Record

_ARP_OPS = {1: "who-has", 2: "is-at"}
_ICMP_TYPES = {0: "echo-reply", 3: "unreachable", 8: "echo-request", 11: "time-exceeded"}


def _length(packet: Packet) -> int:
    # `len(packet)` paketni qayta yig'adi (sekin); simdagi uzunlik ushlash paytida ma'lum.
    wirelen = getattr(packet, "wirelen", None)
    if isinstance(wirelen, int) and wirelen > 0:
        return wirelen
    original = getattr(packet, "original", b"")
    return len(original) if original else len(packet)


def _dns_info(dns: Any) -> str:  # noqa: ANN401 — scapy qatlami
    questions = dns.qd
    if not questions:
        return "DNS"
    # scapy 2.6+ da `qd` — ro'yxat; eskisida bitta yozuv.
    first = questions[0] if hasattr(questions, "__getitem__") else questions
    name = bytes(first.qname).decode("ascii", "replace").rstrip(".")
    return f"DNS{'!' if int(dns.qr) else '?'} {name}"


def _arp(packet: Packet, arp: Any) -> Record:  # noqa: ANN401
    operation = _ARP_OPS.get(int(arp.op), f"op {int(arp.op)}")
    return Record(
        ts=float(packet.time),
        proto="ARP",
        src=str(arp.psrc),
        dst=str(arp.pdst),
        length=_length(packet),
        info=f"{operation} {arp.hwsrc}",
    )


def parse(packet: Packet) -> Record | None:
    """IPv4, IPv6 va ARP paketlari; boshqasi uchun `None`."""
    network = packet.getlayer(IP) or packet.getlayer(IPv6)
    if network is None:
        arp = packet.getlayer(ARP)
        return None if arp is None else _arp(packet, arp)
    record = Record(
        ts=float(packet.time),
        proto="IP",
        src=str(network.src),
        dst=str(network.dst),
        length=_length(packet),
    )
    tcp = network.getlayer(TCP)
    udp = None if tcp is not None else network.getlayer(UDP)
    if tcp is not None:
        record.proto = "TCP"
        record.sport, record.dport = int(tcp.sport), int(tcp.dport)
        record.flags = str(tcp.flags)
        record.info = f"[{record.flags}]"
    elif udp is not None:
        record.proto = "UDP"
        record.sport, record.dport = int(udp.sport), int(udp.dport)
        dns = udp.getlayer(DNS)
        if dns is not None:
            record.info = _dns_info(dns)
    else:
        icmp = network.getlayer(ICMP)
        if icmp is not None:
            record.proto = "ICMP"
            kind = int(icmp.type)
            record.info = _ICMP_TYPES.get(kind, f"type {kind}")
        else:
            # ICMPv6 va boshqalar: scapy qatlam nomi (masalan «ICMPv6 Neighbor Solicitation»).
            upper = network.payload
            name = str(upper.name or "")
            record.proto = "ICMPv6" if name.startswith("ICMPv6") else "IP"
            record.info = name[:60]
    raw = network.getlayer(Raw)
    if raw is not None:
        record.payload = bytes(raw.load)
    return record
