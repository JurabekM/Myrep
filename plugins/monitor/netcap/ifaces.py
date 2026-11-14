"""Tarmoq interfeyslari ro'yxati va Npcap borligini tekshirish (scapy'siz)."""

import os
import socket
from pathlib import Path
from typing import Any

import psutil

ENV_NPCAP_DLL = "SRV1_NPCAP_DLL"
NPCAP_URL = "https://npcap.com/#download"


def npcap_dll() -> Path:
    override = os.environ.get(ENV_NPCAP_DLL, "").strip()
    if override:
        return Path(override)
    windows = os.environ.get("WINDIR", "").strip() or r"C:\Windows"
    return Path(windows) / "System32" / "Npcap" / "wpcap.dll"


def npcap_installed() -> bool:
    return npcap_dll().is_file()


def list_interfaces() -> list[dict[str, Any]]:
    """Yoqilgan va manzili bor interfeyslar: `name` — ushlashni boshlash uchun kalit."""
    stats = psutil.net_if_stats()
    result: list[dict[str, Any]] = []
    for name, addresses in psutil.net_if_addrs().items():
        state = stats.get(name)
        if state is None or not state.isup:
            continue
        ipv4 = [a.address for a in addresses if a.family == socket.AF_INET]
        ipv6 = [a.address for a in addresses if a.family == socket.AF_INET6]
        if not ipv4 and not ipv6:
            continue
        result.append({"name": name, "address": (ipv4 or ipv6)[0], "speed_mbit": state.speed})
    return sorted(result, key=lambda item: str(item["name"]).lower())
