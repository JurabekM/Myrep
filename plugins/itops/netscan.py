"""Tarmoq skaneri: faqat mashinaning o'z mahalliy tarmoqlari, TCP ulanish + ARP jadvali.

Xom paket yuborilmaydi va administrator huquqi kerak emas. TCP urinishlari
qo'shnilarni ARP jadvaliga tushiradi — shu sabab portlari yopiq qurilma ham ko'rinadi.
"""

import asyncio
import ctypes
import socket
import struct
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from ctypes import wintypes
from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv4Interface, IPv4Network
from typing import Any

import psutil

MAX_PREFIX = 24  # bir skanerda ko'pi bilan 256 manzil
NAME_TIMEOUT_S = 2.0
_ARP_INVALID = 2
_ERROR_INSUFFICIENT_BUFFER = 122


class _ArpRow(ctypes.Structure):
    _fields_ = (
        ("index", wintypes.DWORD),
        ("mac_len", wintypes.DWORD),
        ("mac", ctypes.c_ubyte * 8),
        ("address", wintypes.DWORD),
        ("kind", wintypes.DWORD),
    )


@dataclass
class Host:
    ip: str
    ports: list[int] = field(default_factory=list[int])
    mac: str = ""
    name: str = ""
    own: bool = False
    refused: bool = False

    def describe(self) -> dict[str, Any]:
        seen = "tcp" if self.ports or self.refused else "arp"
        return {
            "ip": self.ip,
            "mac": self.mac,
            "name": self.name,
            "ports": ", ".join(str(port) for port in self.ports),
            "seen": "own" if self.own else seen,
        }


def local_interfaces(*, loopback: bool = False) -> list[IPv4Interface]:
    """Mashinaning xususiy IPv4 manzillari (tarmoq niqobi bilan)."""
    found: list[IPv4Interface] = []
    for addresses in psutil.net_if_addrs().values():
        for item in addresses:
            if item.family != socket.AF_INET or not item.netmask:
                continue
            with suppress(ValueError):
                interface = IPv4Interface(f"{item.address}/{item.netmask}")
                ip = interface.ip
                if ip.is_loopback and not loopback:
                    continue
                if ip.is_link_local or not ip.is_private:
                    continue
                found.append(interface)
    return sorted(set(found))


def scan_range(interface: IPv4Interface) -> IPv4Network:
    """Interfeys tarmog'i; /24 dan katta bo'lsa — o'z manzili atrofidagi /24."""
    if interface.network.prefixlen >= MAX_PREFIX:
        return interface.network
    return IPv4Network(f"{interface.ip}/{MAX_PREFIX}", strict=False)


def allowed_range(requested: IPv4Network, interfaces: list[IPv4Interface]) -> bool:
    """So'ralgan oraliq mashinaning o'z tarmoqlaridan birining ichida va /24 dan katta emasmi."""
    if requested.prefixlen < MAX_PREFIX:
        return False
    return any(requested.subnet_of(interface.network) for interface in interfaces)


def arp_table() -> dict[str, str]:
    """Windows ARP jadvali: `ip -> mac` (bloklovchi). Xato bo'lsa bo'sh lug'at."""
    get_table = ctypes.windll.iphlpapi.GetIpNetTable
    size = wintypes.DWORD(0)
    if get_table(None, ctypes.byref(size), False) != _ERROR_INSUFFICIENT_BUFFER:
        return {}
    buffer = ctypes.create_string_buffer(size.value)
    if get_table(buffer, ctypes.byref(size), False) != 0:
        return {}
    count = wintypes.DWORD.from_buffer(buffer).value
    rows = (_ArpRow * count).from_buffer(buffer, ctypes.sizeof(wintypes.DWORD))
    table: dict[str, str] = {}
    for row in rows:
        mac = bytes(row.mac[: row.mac_len])
        if row.kind == _ARP_INVALID or len(mac) != 6 or mac in (b"\x00" * 6, b"\xff" * 6):
            continue
        ip = socket.inet_ntoa(struct.pack("<L", row.address))
        table[ip] = ":".join(f"{byte:02X}" for byte in mac)
    return table


def _lookup(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except OSError:
        return ""


class Scanner:
    """Bitta skanerlash. `progress(done, total)` har urinishdan keyin chaqiriladi."""

    def __init__(
        self,
        network: IPv4Network,
        ports: list[int],
        *,
        timeout_s: float,
        concurrency: int,
        own: set[IPv4Address],
        progress: Callable[[int, int], None],
    ) -> None:
        self.network = network
        self.ports = sorted(set(ports))
        self._timeout = timeout_s
        self._limit = asyncio.Semaphore(concurrency)
        self._own = own
        self._progress = progress
        self._hosts: dict[str, Host] = {}
        self._done = 0
        self._names = ThreadPoolExecutor(max_workers=8, thread_name_prefix="itops-dns")

    def _targets(self) -> list[IPv4Address]:
        if self.network.prefixlen >= 31:
            return list(self.network)
        return list(self.network.hosts())

    async def _probe(self, ip: IPv4Address, port: int, total: int) -> None:
        async with self._limit:
            try:
                _reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(str(ip), port), self._timeout
                )
            except ConnectionRefusedError:
                self._hosts.setdefault(str(ip), Host(str(ip))).refused = True
            except (OSError, TimeoutError):
                pass
            else:
                self._hosts.setdefault(str(ip), Host(str(ip))).ports.append(port)
                writer.close()
                with suppress(OSError):
                    await writer.wait_closed()
        self._done += 1
        self._progress(self._done, total)

    async def _name(self, host: Host) -> None:
        loop = asyncio.get_running_loop()
        with suppress(TimeoutError):
            host.name = await asyncio.wait_for(
                loop.run_in_executor(self._names, _lookup, host.ip), NAME_TIMEOUT_S
            )

    async def run(self) -> list[Host]:
        targets = self._targets()
        total = len(targets) * len(self.ports)
        try:
            await asyncio.gather(*(self._probe(ip, p, total) for ip in targets for p in self.ports))
            wanted = {str(ip) for ip in targets}
            for ip, mac in (await asyncio.to_thread(arp_table)).items():
                if ip in wanted:
                    self._hosts.setdefault(ip, Host(ip)).mac = mac
            for host in self._hosts.values():
                host.ports.sort()
                host.own = IPv4Address(host.ip) in self._own
            await asyncio.gather(*(self._name(host) for host in self._hosts.values()))
        finally:
            self._names.shutdown(wait=False, cancel_futures=True)
        return sorted(self._hosts.values(), key=lambda host: int(IPv4Address(host.ip)))
