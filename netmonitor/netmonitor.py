"""NetMonitor — tarmoq paketlarini konsolda kuzatish va oddiy xavf tekshiruvlari.

Tanlangan interfeysdagi IPv4/IPv6 paketlarni ushlaydi (scapy + Npcap), har birini konsolga
chiqaradi, JSON Lines faylga yozadi va xavf belgilarini tekshiradi. Ushlash davomida
buyruqlar bilan boshqariladi: pause, resume, exclude, unexclude, list, status, quiet, verbose.

Faqat o'z tarmog'ingizda yoki egasining ruxsati bilan ishlating.
"""

from __future__ import annotations

import argparse
import codecs
import copy
import ipaddress
import json
import logging
import os
import queue
import re
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from scapy.config import conf as scapy_conf
from scapy.data import ETH_P_ALL
from scapy.interfaces import get_working_ifaces, resolve_iface
from scapy.layers.dns import DNS, DNSQR
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from scapy.layers.l2 import Ether
from scapy.packet import Raw
from scapy.sendrecv import sniff
from scapy.utils import PcapWriter, wrpcap

try:
    from colorama import Fore, Style
    from colorama import init as colorama_init

    colorama_init(autoreset=True)
except ImportError:  # ranglarsiz ham ishlaydi

    class _NoColor:
        def __getattr__(self, name: str) -> str:
            return ""

    Fore = Style = _NoColor()  # type: ignore[assignment]

try:
    import psutil
except ImportError:  # tizim ko'rsatkichlarisiz ham ishlaydi
    psutil = None  # type: ignore[assignment]

__version__ = "4.1.0"

APP_NAME = "NetMonitor"
NPCAP_URL = "https://npcap.com/#download"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_BAD_CONFIG = 2
EXIT_CAPTURE_FAILED = 3


# ---------------------------------------------------------------------------
# Sozlamalar
# ---------------------------------------------------------------------------

DEFAULT_SENSITIVE_KEYWORDS = [
    "password", "pass", "passwd", "pwd",
    "login", "user", "username", "auth", "authorization",
    "admin", "root", "administrator",
    "token", "session", "cookie", "key",
    "secret", "private", "confidential",
]

DEFAULT_CONFIG: dict[str, Any] = {
    "log_folder": "logs_pro",
    "packet_log_filename": "captured_packets.json",
    "log_rotation_lines": 10000,
    "max_packet_log_files": 50,
    "system_metrics_interval_sec": 120,
    "capture_filter": None,
    "capture": {
        "promiscuous": "auto",
        "probe_sec": 5,
    },
    "excluded_ips": [],
    "pcap_max_mb": 500,
    "console": {
        "show_packets": True,
        "max_lines_per_sec": 50,
        "payload_preview_bytes": 150,
    },
    "payload": {
        "mask_sensitive_values": True,
        "log_max_bytes": 2048,
        "sensitive_keywords": DEFAULT_SENSITIVE_KEYWORDS,
    },
    "geolocation": {"enabled": False},
    "security_monitoring": {
        "suspicious_ports_enabled": True,
        "suspicious_ports": [23, 4444, 5555, 6667, 31337],
        "suspicious_tcp_flags_enabled": True,
        "port_scan_detection_enabled": True,
        "port_scan_time_window_sec": 10,
        "port_scan_threshold_ports": 15,
        "suspicious_payload_enabled": True,
        "suspicious_payload_keywords": ["cmd.exe", "/etc/passwd", "union select"],
        "alert_quiet_sec": 60,
    },
}


class ConfigError(Exception):
    """config.json o'qilmadi yoki tuzilishi noto'g'ri."""


def app_dir() -> Path:
    """Dastur papkasi: exe yonida (yig'ilgan bo'lsa) yoki skript yonida."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _is_writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=folder):
            pass
    except OSError:
        return False
    return True


def data_dir(preferred: Path | None = None) -> Path:
    """Jurnal va holat fayllari uchun asos papka.

    Odatda dastur papkasi (yoki `--config` bilan berilgan fayl papkasi); u yozishga yopiq
    bo'lsa (masalan, `Program Files`) — foydalanuvchining `%LOCALAPPDATA%\\NetMonitor` papkasi.
    """
    base = preferred or app_dir()
    if _is_writable(base):
        return base
    fallback = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / APP_NAME
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _merge(defaults: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(defaults)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: Path) -> dict[str, Any]:
    """Standart sozlamalar ustiga `path` dagi qiymatlarni qo'yadi; fayl yo'q bo'lsa — standartlar."""
    if not path.is_file():
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ConfigError(f"{path}: eng yuqori daraja JSON obyekt bo'lishi kerak")
    return _merge(DEFAULT_CONFIG, loaded)


def write_default_config(path: Path) -> bool:
    try:
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


def _number(value: object, default: float, minimum: float) -> float:
    """Sozlamadagi son; noto'g'ri tur yoki chegaradan past bo'lsa — standart qiymat."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value) if value >= minimum else default


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name)
    return value if isinstance(value, dict) else {}


# ---------------------------------------------------------------------------
# Konsol: barcha chiqish bitta qulf ostida — satrlar aralashib ketmaydi
# ---------------------------------------------------------------------------


class Console:
    def __init__(self) -> None:
        self._lock = threading.RLock()

    def write(self, text: str = "") -> None:
        with self._lock:
            try:
                print(text)
            except (OSError, ValueError):  # konsol yopilgan
                pass


console = Console()


class ConsoleLogHandler(logging.Handler):
    """Jurnal xabarlarini paket satrlari bilan bir xil qulf orqali chiqaradi."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = self.format(record)
        except Exception:  # noqa: BLE001 — jurnal hech qachon dasturni to'xtatmaydi
            return
        if record.levelno >= logging.ERROR:
            text = f"{Fore.RED}{Style.BRIGHT}{text}{Style.RESET_ALL}"
        elif record.levelno >= logging.WARNING:
            text = f"{Fore.YELLOW}{text}{Style.RESET_ALL}"
        console.write(text)


def configure_stdio() -> None:
    """Konsol kodirovkasi belgini ko'rsata olmasa, dastur yiqilmaydi — belgi `\\x..` bo'lib chiqadi."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                if stream.isatty():
                    reconfigure(errors="backslashreplace")
                else:  # faylga yoki boshqa dasturga yo'naltirilgan chiqish har doim UTF-8
                    reconfigure(encoding="utf-8", errors="backslashreplace")
            except (OSError, ValueError):
                pass


def setup_logging(log_folder: Path) -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler = ConsoleLogHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    file_handler = RotatingFileHandler(
        log_folder / "system_events.log", maxBytes=1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


class Throttle:
    """Bir xil xabar `interval_s` ichida bir martadan ko'p chiqmasligi uchun."""

    def __init__(self, interval_s: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._interval_s = interval_s
        self._clock = clock
        self._next = 0.0

    def ready(self) -> bool:
        now = self._clock()
        if now < self._next:
            return False
        self._next = now + self._interval_s
        return True


# ---------------------------------------------------------------------------
# Paket matni: xavfsiz ko'rinish va ochiq uzatilgan maxfiy ma'lumotni topish
# ---------------------------------------------------------------------------


def _byte_text(byte: int) -> str:
    if byte == 0x5C:  # teskari chiziq: `\x41` yozuvi haqiqiy baytdan farqlanishi uchun
        return "\\\\"
    if 32 <= byte <= 126:
        return chr(byte)
    if byte == 0x09:
        return "\\t"
    if byte == 0x0A:
        return "\\n"
    if byte == 0x0D:
        return "\\r"
    return f"\\x{byte:02x}"


_BYTE_TEXT = tuple(_byte_text(byte) for byte in range(256))

PAYLOAD_SCAN_BYTES = 4096
MASK = "********"

# TLS yozuvi: tur (20–23), versiya 3.x — shifrlangan, ichidan so'z qidirish ma'nosiz.
_TLS_TYPES = frozenset({0x14, 0x15, 0x16, 0x17})
_QUOTED_OR = rb"\"[^\"\r\n]{0,256}\"|'[^'\r\n]{0,256}'|"
# FTP / POP3: login va parol alohida buyruq bilan ochiq matnda yuboriladi.
_LOGIN_COMMAND = re.compile(rb"(?m)^(?P<name>USER|PASS) +(?P<v1>[^\r\n]{1,256})")


def sanitize_bytes(data: bytes) -> str:
    """Baytlarni konsol uchun xavfsiz satrga aylantiradi.

    Bosiladigan ASCII o'zicha qoladi; tab, LF, CR — `\\t`, `\\n`, `\\r`; teskari chiziq —
    `\\\\`; qolgan hamma bayt (ESC va boshqa boshqaruv belgilari ham) — `\\xNN`.
    """
    return "".join(map(_BYTE_TEXT.__getitem__, data))


def is_utf8_text(data: bytes) -> bool:
    """ASCII bo'lmagan, lekin to'g'ri UTF-8 matn (masalan, kirill yozuvi)."""
    if data.isascii():
        return False
    try:
        codecs.getincrementaldecoder("utf-8")("strict").decode(data, False)
    except UnicodeDecodeError:
        return False
    return True


def sanitize_text(data: bytes, unicode_ok: bool = False) -> str:
    """`sanitize_bytes` kabi, lekin `unicode_ok` bo'lsa bosiladigan UTF-8 harflar o'qiladigan qoladi.

    Boshqaruv va format belgilari (yo'nalishni o'zgartiruvchilar ham) baribir `\\xNN` bo'ladi.
    """
    if not unicode_ok:
        return sanitize_bytes(data)
    parts: list[str] = []
    for char in data.decode("utf-8", "surrogateescape"):
        code = ord(char)
        if code < 0x80:
            parts.append(_BYTE_TEXT[code])
        elif 0xDC80 <= code <= 0xDCFF:  # UTF-8 ga to'g'ri kelmagan bayt
            parts.append(_BYTE_TEXT[code - 0xDC00])
        elif char.isprintable():
            parts.append(char)
        else:
            parts.extend(_BYTE_TEXT[byte] for byte in char.encode("utf-8"))
    return "".join(parts)


def looks_encrypted(payload: bytes) -> bool:
    return len(payload) >= 3 and payload[0] in _TLS_TYPES and payload[1] == 0x03


@dataclass(frozen=True, slots=True)
class Span:
    start: int
    end: int
    kind: str  # "name" | "value"


@dataclass(frozen=True, slots=True)
class Findings:
    spans: tuple[Span, ...] = ()
    names: tuple[str, ...] = ()  # topilgan maxfiy maydon nomlari (qiymatsiz)
    signature: str = ""  # sozlamadagi shubhali so'zlardan birinchisi


NO_FINDINGS = Findings()


class PayloadScanner:
    """Paket matnidan `nom = qiymat` ko'rinishidagi maxfiy maydonlarni va shubhali so'zlarni topadi.

    Faqat `nom=qiymat` / `nom: qiymat` shakli hisobga olinadi: `User-Agent`, `keyboard`,
    `bypass` kabi so'zlar tushmaydi.
    """

    def __init__(self, keywords: Iterable[object], signatures: Iterable[object]) -> None:
        names = sorted(
            {str(k).strip().lower() for k in keywords if str(k).strip().isascii() and str(k).strip()},
            key=lambda item: (-len(item), item),
        )
        self._pattern: re.Pattern[bytes] | None = None
        if names:
            alternatives = b"|".join(re.escape(name.encode("ascii")) for name in names)
            self._pattern = re.compile(
                rb"(?i)(?<![A-Za-z0-9])(?P<name>" + alternatives + rb")[\"']?[ \t]*(?:"
                rb"=[ \t]*(?P<v1>" + _QUOTED_OR + rb"[^\r\n&;\s\"',}]{0,256})|"
                rb":[ \t]*(?P<v2>" + _QUOTED_OR + rb"[^\r\n]{0,256}))"
            )
        self._signatures = tuple(
            text.lower().encode("utf-8") for text in (str(s).strip() for s in signatures) if text
        )

    def scan(self, raw: bytes) -> Findings:
        if not raw:
            return NO_FINDINGS
        head = raw[:PAYLOAD_SCAN_BYTES]
        signature = ""
        if self._signatures:
            lowered = head.lower()
            for candidate in self._signatures:
                if candidate in lowered:
                    signature = candidate.decode("utf-8")
                    break
        if looks_encrypted(head):
            return Findings(signature=signature) if signature else NO_FINDINGS
        matches = list(_LOGIN_COMMAND.finditer(head))
        if self._pattern is not None:
            matches.extend(self._pattern.finditer(head))
        if not matches:
            return Findings(signature=signature) if signature else NO_FINDINGS
        matches.sort(key=lambda found: found.start())
        spans: list[Span] = []
        names: list[str] = []
        position = 0
        for found in matches:
            if found.start() < position:  # oldingi topilma ichida
                continue
            position = found.end()
            spans.append(Span(found.start("name"), found.end("name"), "name"))
            group = "v1" if found.group("v1") is not None else "v2"
            if found.end(group) > found.start(group):
                spans.append(Span(found.start(group), found.end(group), "value"))
            name = found.group("name").decode("ascii").lower()
            if name not in names:
                names.append(name)
        return Findings(tuple(spans), tuple(names), signature)


def render_payload(raw: bytes, findings: Findings, limit: int, *, color: bool, mask: bool) -> str:
    """Paket matnining dastlabki `limit` bayti: xavfsiz, maxfiy nomlar bo'yalgan, qiymatlar yashirilgan."""
    unicode_ok = is_utf8_text(raw[:PAYLOAD_SCAN_BYTES])
    end = min(len(raw), limit)
    red = f"{Fore.RED}{Style.BRIGHT}" if color else ""
    reset = f"{Style.RESET_ALL}" if color else ""
    parts: list[str] = []
    position = 0
    for span in findings.spans:
        if span.start >= end:
            break
        stop = min(span.end, end)
        if span.start > position:
            parts.append(sanitize_text(raw[position : span.start], unicode_ok))
        text = MASK if span.kind == "value" and mask else sanitize_text(raw[span.start : stop], unicode_ok)
        parts.append(f"{red}{text}{reset}")
        position = stop
    parts.append(sanitize_text(raw[position:end], unicode_ok))
    if len(raw) > limit:
        parts.append("...")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Boshqaruv holati: pauza va kuzatuvdan chiqarilgan manzillar
# ---------------------------------------------------------------------------

Network = ipaddress.IPv4Network | ipaddress.IPv6Network


def parse_target(text: str) -> Network | None:
    """`192.168.1.5`, `10.0.0.0/8`, `fe80::1` kabi yozuvni tarmoqqa aylantiradi; xato bo'lsa `None`."""
    try:
        return ipaddress.ip_network(text.strip(), strict=False)
    except ValueError:
        return None


def target_label(network: Network) -> str:
    return str(network.network_address) if network.num_addresses == 1 else str(network)


class MonitorState:
    """Pauza holati va chiqarilgan manzillar. Paket oqimi qulfsiz o'qiydi (o'zgarmas nusxalar)."""

    def __init__(self, state_file: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._state_file = state_file
        self._targets: dict[str, Network] = {}
        self._hosts: frozenset[str] = frozenset()
        self._networks: tuple[Network, ...] = ()
        self.active = True
        self.show_packets = True
        self.stop = threading.Event()

    # --- pauza -------------------------------------------------------------

    def pause(self) -> bool:
        with self._lock:
            changed = self.active
            self.active = False
        return changed

    def resume(self) -> bool:
        with self._lock:
            changed = not self.active
            self.active = True
        return changed

    # --- chiqarilgan manzillar ----------------------------------------------

    def _rebuild(self) -> None:
        hosts: set[str] = set()
        networks: list[Network] = []
        for network in self._targets.values():
            if network.version == 4 and network.num_addresses == 1:
                hosts.add(str(network.network_address))
            else:
                networks.append(network)
        self._hosts = frozenset(hosts)
        self._networks = tuple(networks)

    def exclude(self, text: str) -> str:
        """`"added"`, `"exists"` yoki `"invalid"`."""
        network = parse_target(text)
        if network is None:
            return "invalid"
        label = target_label(network)
        with self._lock:
            if label in self._targets:
                return "exists"
            self._targets[label] = network
            self._rebuild()
        return "added"

    def unexclude(self, text: str) -> str:
        """`"removed"`, `"missing"` yoki `"invalid"`."""
        network = parse_target(text)
        if network is None:
            return "invalid"
        label = target_label(network)
        with self._lock:
            if label not in self._targets:
                return "missing"
            del self._targets[label]
            self._rebuild()
        return "removed"

    def excluded(self) -> list[str]:
        with self._lock:
            return sorted(self._targets)

    def is_excluded(self, ip: str) -> bool:
        if ip in self._hosts:
            return True
        networks = self._networks
        if not networks:
            return False
        try:
            address = ipaddress.ip_address(ip.split("%", 1)[0])
        except ValueError:
            return False
        return any(network.version == address.version and address in network for network in networks)

    # --- saqlash -------------------------------------------------------------

    def load(self) -> int:
        """Oldingi ishga tushirishdan qolgan ro'yxatni o'qiydi; nechta manzil qo'shilganini qaytaradi."""
        if self._state_file is None or not self._state_file.is_file():
            return 0
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0
        items = data.get("excluded") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return 0
        return sum(1 for item in items if self.exclude(str(item)) == "added")

    def save(self) -> bool:
        if self._state_file is None:
            return True
        temporary = self._state_file.with_suffix(".tmp")
        try:
            temporary.write_text(json.dumps({"excluded": self.excluded()}, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, self._state_file)
        except OSError:
            return False
        return True


# ---------------------------------------------------------------------------
# Geolokatsiya (ixtiyoriy, standart holatda o'chiq)
# ---------------------------------------------------------------------------

GEO_HOST = "ip-api.com"
GEO_URL = "http://" + GEO_HOST + "/json/{ip}?fields=status,country,city,isp"
GEO_CACHE_SIZE = 2000
GEO_QUEUE_SIZE = 200
GEO_MIN_INTERVAL_S = 1.6  # bepul chegara — daqiqasiga 45 so'rov; zaxira bilan
GEO_OK_TTL_S = 24 * 3600.0
GEO_FAIL_TTL_S = 600.0
GEO_RATE_LIMIT_PAUSE_S = 60.0
GEO_TIMEOUT_S = 3.0
GEO_PRIVATE = {"country": "Private IP", "isp": "Local Network"}

GeoInfo = dict[str, str]


class GeoRateLimited(Exception):
    """Xizmat so'rovlar chegarasi oshganini bildirdi (HTTP 429)."""


def is_public(ip: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    # Multicast manzillar `is_global` bo'lishi mumkin, lekin egasi yo'q.
    return address.is_global and not address.is_multicast


def is_private(ip: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return address.is_private and not address.is_unspecified and not address.is_multicast


def fetch_geo(ip: str) -> GeoInfo | None:
    """`ip-api.com` dan mamlakat, shahar va provayder; xizmat tanimasa yoki javob bermasa `None`."""
    address = ipaddress.ip_address(ip)  # URL ga faqat tekshirilgan manzil tushadi
    try:
        with urllib.request.urlopen(GEO_URL.format(ip=address), timeout=GEO_TIMEOUT_S) as response:  # noqa: S310
            raw: object = json.loads(response.read(4096))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise GeoRateLimited from exc
        return None
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict) or raw.get("status") != "success":
        return None
    # Javob ham tashqaridan keladi: konsolga chiqishidan oldin tozalanadi.
    return {
        key: sanitize_text(str(raw.get(key) or "").encode("utf-8"), True)[:80] for key in ("country", "city", "isp")
    }


def resolve_service_ips(host: str = GEO_HOST) -> frozenset[str]:
    try:
        return frozenset(str(item[4][0]) for item in socket.getaddrinfo(host, 80, proto=socket.IPPROTO_TCP))
    except OSError:
        return frozenset()


class GeoResolver:
    """So'rovlar alohida oqimda ketadi — paketlarni ushlash hech qachon kutib qolmaydi.

    Faqat ommaviy manzillar so'raladi; natija (muvaffaqiyatsizi ham) keshlanadi.
    `service_ips` — xizmatning o'z manzillari: ularga ketgan so'rovlar kuzatuvga tushmaydi.
    """

    def __init__(
        self,
        fetch: Callable[[str], GeoInfo | None] = fetch_geo,
        min_interval_s: float = GEO_MIN_INTERVAL_S,
        clock: Callable[[], float] = time.monotonic,
        resolve: Callable[[], frozenset[str]] = resolve_service_ips,
    ) -> None:
        self._fetch = fetch
        self._min_interval_s = min_interval_s
        self._clock = clock
        self._resolve = resolve
        self._cache: OrderedDict[str, tuple[GeoInfo | None, float]] = OrderedDict()
        self._pending: set[str] = set()
        self._queue: queue.Queue[str] = queue.Queue(maxsize=GEO_QUEUE_SIZE)
        self._lock = threading.Lock()
        self.service_ips: frozenset[str] = frozenset()
        self.requests = 0
        self.rate_limited = 0

    def start(self) -> None:
        threading.Thread(target=self._loop, name="GeoResolverThread", daemon=True).start()

    def lookup(self, ip: str) -> GeoInfo | None:
        """Keshdagi natija; yo'q bo'lsa `None` qaytarib, so'rovni navbatga qo'yadi (kutmaydi)."""
        if not is_public(ip):
            return dict(GEO_PRIVATE) if is_private(ip) else None
        with self._lock:
            cached = self._cache.get(ip)
            if cached is not None and cached[1] > self._clock():
                return cached[0]
            if ip not in self._pending:
                try:
                    self._queue.put_nowait(ip)
                except queue.Full:
                    return None
                self._pending.add(ip)
        return None

    def resolve_one(self) -> float | None:
        """Navbatdan bitta manzilni so'raydi. Keyingi so'rovgacha kutish (s); navbat bo'sh bo'lsa `None`."""
        try:
            ip = self._queue.get_nowait()
        except queue.Empty:
            return None
        pause = self._min_interval_s
        try:
            info = self._fetch(ip)
        except GeoRateLimited:
            info = None
            self.rate_limited += 1
            pause = GEO_RATE_LIMIT_PAUSE_S
        self.requests += 1
        ttl = GEO_FAIL_TTL_S if info is None else GEO_OK_TTL_S
        with self._lock:
            self._pending.discard(ip)
            self._cache[ip] = (info, self._clock() + ttl)
            self._cache.move_to_end(ip)
            while len(self._cache) > GEO_CACHE_SIZE:
                self._cache.popitem(last=False)
        return pause

    def _loop(self) -> None:
        refresh_at = 0.0
        while True:
            if self._clock() >= refresh_at:
                found = self._resolve()
                if found:
                    self.service_ips = found
                refresh_at = self._clock() + (600.0 if found else 30.0)
            if not self.service_ips:  # xizmat manzili noma'lum: so'rov o'zimizga ko'rinib qolardi
                time.sleep(1.0)
                continue
            pause = self.resolve_one()
            time.sleep(0.5 if pause is None else pause)


# ---------------------------------------------------------------------------
# Xavf tekshiruvlari
# ---------------------------------------------------------------------------

MAX_TRACKED = 5000


@dataclass(frozen=True, slots=True)
class Alert:
    kind: str  # port | null_scan | fin_scan | xmas_scan | port_scan | payload | secret
    level: int
    message: str


@dataclass(slots=True)
class _Window:
    started: float
    ports: set[int] = field(default_factory=set)


def _port_set(values: object) -> frozenset[int]:
    ports: set[int] = set()
    if isinstance(values, (list, tuple, set, frozenset)):
        for value in values:
            try:
                port = int(value)
            except (TypeError, ValueError):
                continue
            if 0 < port < 65536:
                ports.add(port)
    return frozenset(ports)


class Detector:
    """Bitta paket bo'yicha xavf belgilari.

    Bir xil signal (tur, manba, manzil) `alert_quiet_sec` ichida takror chiqmaydi.
    """

    def __init__(self, settings: dict[str, Any], clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self.ports_enabled = bool(settings.get("suspicious_ports_enabled"))
        self.ports = _port_set(settings.get("suspicious_ports"))
        self.flags_enabled = bool(settings.get("suspicious_tcp_flags_enabled"))
        self.scan_enabled = bool(settings.get("port_scan_detection_enabled"))
        self.scan_window_s = _number(settings.get("port_scan_time_window_sec"), 10.0, 0.1)
        self.scan_threshold = int(_number(settings.get("port_scan_threshold_ports"), 15, 1))
        self.payload_enabled = bool(settings.get("suspicious_payload_enabled"))
        self.quiet_s = _number(settings.get("alert_quiet_sec"), 60.0, 0.0)
        self._scans: OrderedDict[tuple[str, str], _Window] = OrderedDict()
        self._last: OrderedDict[tuple[str, str, str], float] = OrderedDict()
        self.suppressed = 0

    def check(
        self,
        proto: str,
        src: str,
        dst: str,
        dport: int | None,
        flags: str,
        findings: Findings,
    ) -> list[Alert]:
        found: list[Alert] = []
        is_syn = proto == "TCP" and "S" in flags and "A" not in flags
        if proto == "TCP" and self.flags_enabled:
            if flags == "":
                self._add(found, "null_scan", logging.WARNING, src, dst, f"NULL Scan: {src} -> {dst}")
            elif flags == "F":
                self._add(found, "fin_scan", logging.WARNING, src, dst, f"FIN Scan: {src} -> {dst}")
            elif flags == "FPU":
                self._add(found, "xmas_scan", logging.WARNING, src, dst, f"Xmas Scan: {src} -> {dst}")
        # Faqat yangi murojaat (TCP SYN yoki UDP): javob paketlari va o'tkinchi portlar tushmaydi.
        if self.ports_enabled and dport in self.ports and (is_syn or proto == "UDP"):
            self._add(found, "port", logging.WARNING, src, dst, f"Shubhali port {dport}: {src} -> {dst}")
        if self.scan_enabled and is_syn and dport is not None and self._port_scan(src, dst, dport):
            self._add(found, "port_scan", logging.CRITICAL, src, dst, f"PORT SKANERLASH: {src} -> {dst}")
        if self.payload_enabled:
            target = dst if dport is None else f"{dst}:{dport}"
            if findings.signature:
                text = f"Shubhali payload ('{findings.signature}'): {src} -> {target}"
                self._add(found, "payload", logging.WARNING, src, dst, text)
            if findings.names:
                text = f"Ochiq matnda maxfiy maydon ({', '.join(findings.names)}): {src} -> {target}"
                self._add(found, "secret", logging.WARNING, src, dst, text)
        return found

    def _port_scan(self, src: str, dst: str, dport: int) -> bool:
        """Bitta manbadan bitta manzilga oyna ichida chegaradan ko'p turli portga SYN."""
        now = self._clock()
        key = (src, dst)
        window = self._scans.get(key)
        if window is None or now - window.started > self.scan_window_s:
            window = _Window(started=now)
            self._scans[key] = window
        self._scans.move_to_end(key)
        window.ports.add(dport)
        while len(self._scans) > MAX_TRACKED:
            self._scans.popitem(last=False)
        if len(window.ports) <= self.scan_threshold:
            return False
        del self._scans[key]
        return True

    def _add(self, found: list[Alert], kind: str, level: int, src: str, dst: str, text: str) -> None:
        now = self._clock()
        key = (kind, src, dst)
        last = self._last.get(key)
        if last is not None and now - last < self.quiet_s:
            self.suppressed += 1
            return
        self._last[key] = now
        self._last.move_to_end(key)
        while len(self._last) > MAX_TRACKED:
            self._last.popitem(last=False)
        found.append(Alert(kind, level, f"[XAVF] {text}"))


# ---------------------------------------------------------------------------
# Paketlar jurnali (JSON Lines) va uning rotatsiyasi
# ---------------------------------------------------------------------------


class PacketLog:
    def __init__(self, folder: Path, filename: str, max_lines: int, max_files: int) -> None:
        self.folder = folder
        self.path = folder / filename
        self.max_lines = max(1, max_lines)
        self.max_files = max(1, max_files)
        self._lock = threading.Lock()
        self._handle: Any = None
        self._dirty = False
        self._rotate_at = self.max_lines
        self._error_throttle = Throttle(30.0)
        self.written = 0
        self.failed = 0
        try:
            with self.path.open("r", encoding="utf-8", errors="replace") as handle:
                self.line_count = sum(1 for _ in handle)
        except OSError:
            self.line_count = 0

    def write(self, data: dict[str, Any]) -> None:
        line = json.dumps(data, ensure_ascii=False)
        with self._lock:
            if self.line_count >= self._rotate_at:
                self._rotate()
            try:
                if self._handle is None:
                    self._handle = self.path.open("a", encoding="utf-8", errors="backslashreplace")
                self._handle.write(line + "\n")
            except OSError as exc:
                self.failed += 1
                self._close()
                if self._error_throttle.ready():
                    logging.error("Log xatosi: %s (yozilmagan paketlar: %d)", exc, self.failed)
                return
            self._dirty = True
            self.line_count += 1
            self.written += 1

    def flush(self) -> None:
        with self._lock:
            if self._handle is not None and self._dirty:
                try:
                    self._handle.flush()
                except OSError:
                    pass
                self._dirty = False

    def close(self) -> None:
        with self._lock:
            self._close()

    def _close(self) -> None:
        if self._handle is not None:
            try:
                self._handle.close()
            except OSError:
                pass
            self._handle = None
        self._dirty = False

    def _archive_path(self) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        candidate = self.path.with_name(f"{self.path.stem}_{stamp}{self.path.suffix}")
        number = 1
        while candidate.exists():  # bir soniyada ikkinchi rotatsiya
            candidate = self.path.with_name(f"{self.path.stem}_{stamp}-{number}{self.path.suffix}")
            number += 1
        return candidate

    def _rotate(self) -> None:
        self._close()
        try:
            if self.path.exists():
                os.rename(self.path, self._archive_path())
        except OSError as exc:
            # Fayl band (masalan, boshqa dasturda ochiq): shu faylga yozish davom etadi,
            # rotatsiya keyinroq qayta uriniladi — har paketda emas.
            self._rotate_at = self.line_count + max(100, self.max_lines // 10)
            if self._error_throttle.ready():
                logging.error("Rotatsiya xatosi: %s", exc)
            return
        self.line_count = 0
        self._rotate_at = self.max_lines
        self._prune()

    def _prune(self) -> None:
        pattern = f"{self.path.stem}_*{self.path.suffix}"
        try:
            files = sorted(self.folder.glob(pattern), key=lambda item: (item.stat().st_mtime, item.name))
        except OSError:
            return
        while len(files) > self.max_files:
            try:
                files.pop(0).unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Ilova darajasi: HTTP so'rovi va TLS ClientHello (shifrni ochmasdan sayt nomi)
# ---------------------------------------------------------------------------

_HTTP_REQUEST = re.compile(
    rb"^(GET|POST|HEAD|PUT|DELETE|OPTIONS|PATCH|CONNECT|TRACE) ([^ \r\n]{1,2048}) HTTP/1\.[01]\r\n"
)
_HTTP_HOST = re.compile(rb"(?im)^Host:[ \t]*([^\r\n]{1,255})\r?$")
MAX_NAME = 255


def parse_http_request(raw: bytes) -> dict[str, str] | None:
    """HTTP/1.x so'rovining usuli, `Host` sarlavhasi va yo'li. So'rov satri (`?` dan keyingisi) olinmaydi."""
    found = _HTTP_REQUEST.match(raw)
    if found is None:
        return None
    result = {"protocol": "HTTP", "method": found.group(1).decode("ascii")}
    host = _HTTP_HOST.search(raw[:PAYLOAD_SCAN_BYTES])
    if host is not None:
        result["host"] = sanitize_bytes(host.group(1).strip())
    # So'rov satrida ko'pincha token va parollar bo'ladi: faqat yo'lning o'zi saqlanadi.
    result["path"] = sanitize_bytes(found.group(2).split(b"?", 1)[0][:200])
    return result


def parse_tls_sni(raw: bytes) -> str | None:
    """TLS ClientHello ichidagi server nomi (SNI). ClientHello emas yoki nom yo'q bo'lsa `None`.

    Har qadamda chegara tekshiriladi: buzuq yoki kesilgan paket shunchaki `None` beradi.
    """
    # Yozuv: tur 22 (handshake), versiya 3.x, uzunlik; handshake: tur 1 (ClientHello), uzunlik (3 bayt).
    if len(raw) < 43 or raw[0] != 0x16 or raw[1] != 0x03 or raw[5] != 0x01:
        return None
    end = min(len(raw), 5 + int.from_bytes(raw[3:5], "big"))
    position = 9 + 2 + 32  # handshake sarlavhasi, versiya, tasodifiy son
    if position >= end:
        return None
    position += 1 + raw[position]  # sessiya identifikatori
    if position + 2 > end:
        return None
    position += 2 + int.from_bytes(raw[position : position + 2], "big")  # shifrlar ro'yxati
    if position + 1 > end:
        return None
    position += 1 + raw[position]  # siqish usullari
    if position + 2 > end:
        return None
    end = min(end, position + 2 + int.from_bytes(raw[position : position + 2], "big"))
    position += 2
    while position + 4 <= end:
        kind = int.from_bytes(raw[position : position + 2], "big")
        size = int.from_bytes(raw[position + 2 : position + 4], "big")
        position += 4
        if kind == 0:  # server_name: ro'yxat uzunligi (2), nom turi (1), nom uzunligi (2), nom
            if position + 5 > end or raw[position + 2] != 0:
                return None
            length = int.from_bytes(raw[position + 3 : position + 5], "big")
            name = raw[position + 5 : position + 5 + length]
            if not name or len(name) != length or length > MAX_NAME or position + 5 + length > end:
                return None
            return sanitize_bytes(name)
        position += size
    return None


class PcapOutput:
    """Qayta ishlangan paketlarni Wireshark ocha oladigan .pcap faylga yozadi (hajm chegarasi bilan)."""

    def __init__(self, path: Path, max_bytes: int) -> None:
        self.path = path
        self.max_bytes = max_bytes
        self.written = 0
        self.size = 24  # fayl sarlavhasi
        self.full = False
        self._lock = threading.Lock()
        self._closed = False
        self._writer: Any = None  # birinchi paketda ochiladi: fayl turi (Ethernet va h.k.) paketdan olinadi
        path.write_bytes(b"")  # yozib bo'lmaydigan yo'l darhol ma'lum bo'lsin
        self._error_throttle = Throttle(30.0)

    def write(self, packet: Any) -> None:
        with self._lock:
            if self._closed or self.full:
                return
            size = 16 + len(packet.original or b"")  # yozuv sarlavhasi + ushlangan baytlar
            if self.max_bytes > 0 and self.size + size > self.max_bytes:
                self.full = True
                logging.warning(
                    "pcap fayli chegaraga yetdi (%d MB): %s. Yozish to'xtatildi, monitoring davom etadi.",
                    self.max_bytes // (1024 * 1024), self.path,
                )
                return
            try:
                if self._writer is None:
                    self._writer = PcapWriter(str(self.path), append=False, sync=False)
                self._writer.write(packet)
            except Exception as exc:  # noqa: BLE001
                if self._error_throttle.ready():
                    logging.error("pcap yozishda xato: %s", exc)
                return
            self.size += size
            self.written += 1

    def flush(self) -> None:
        with self._lock:
            if self._writer is not None:
                try:
                    self._writer.flush()
                except Exception:  # noqa: BLE001
                    pass

    def close(self) -> None:
        with self._lock:
            if self._writer is not None:
                try:
                    self._writer.close()
                except Exception:  # noqa: BLE001
                    pass
                self._writer = None
            elif not self._closed and self.written == 0:
                try:
                    self.path.unlink()  # birorta paket yozilmadi: bo'sh (yaroqsiz) fayl qolmasin
                except OSError:
                    pass
            self._closed = True


class PacketClock:
    """Fayldan o'qishda vaqt — paketning o'z vaqti: skanerlash oynalari yozuvdagi vaqt bo'yicha sanaladi."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


# ---------------------------------------------------------------------------
# Paketlarni qayta ishlash
# ---------------------------------------------------------------------------

_IP_PROTOCOLS = {1: "ICMP", 2: "IGMP", 6: "TCP", 17: "UDP", 58: "ICMPv6"}


@dataclass(slots=True)
class Stats:
    seen: int = 0
    processed: int = 0
    paused: int = 0
    excluded: int = 0
    geo_self: int = 0
    non_ip: int = 0
    errors: int = 0
    alerts: int = 0
    console_skipped: int = 0
    last_packet: float = 0.0  # oxirgi paket vaqti (monotonic); 0 — hali kelmagan


def _endpoint(ip: str, port: object) -> str:
    if port is None or port == "":
        return ip
    return f"[{ip}]:{port}" if ":" in ip else f"{ip}:{port}"


def _dns_query(packet: Any) -> str | None:
    dns = packet.getlayer(DNS)
    if dns is None:
        return None
    question = getattr(dns, "qd", None)
    if isinstance(question, (list, tuple)):  # scapy 2.6+: savollar ro'yxati
        question = question[0] if question else None
    name = getattr(question, "qname", None)
    if name is None:
        return None
    if isinstance(name, str):
        name = name.encode("utf-8", "backslashreplace")
    # Nom tarmoqdan keladi: boshqaruv belgilari konsolga o'tmasligi kerak.
    return sanitize_bytes(bytes(name))


class PacketProcessor:
    def __init__(
        self,
        config: dict[str, Any],
        state: MonitorState,
        packet_log: PacketLog,
        geo: GeoResolver | None = None,
        clock: Callable[[], float] = time.monotonic,
        pcap_output: PcapOutput | None = None,
    ) -> None:
        self.state = state
        self.packet_log = packet_log
        self.geo = geo
        self.pcap_output = pcap_output
        # Fayldan o'qishda `clock` — PacketClock: vaqt har paketning o'zidan olinadi.
        self.packet_clock = clock if isinstance(clock, PacketClock) else None
        self.stats = Stats()
        self._clock = clock
        console_settings = _section(config, "console")
        payload_settings = _section(config, "payload")
        security = _section(config, "security_monitoring")
        self.max_lines_per_sec = int(_number(console_settings.get("max_lines_per_sec"), 50, 0))
        self.preview_bytes = int(_number(console_settings.get("payload_preview_bytes"), 150, 1))
        self.log_max_bytes = int(_number(payload_settings.get("log_max_bytes"), 2048, 0))
        self.mask = bool(payload_settings.get("mask_sensitive_values", True))
        keywords = payload_settings.get("sensitive_keywords")
        signatures = security.get("suspicious_payload_keywords")
        self.scanner = PayloadScanner(
            keywords if isinstance(keywords, list) else DEFAULT_SENSITIVE_KEYWORDS,
            signatures if isinstance(signatures, list) else [],
        )
        self.detector = Detector(security, clock)
        self._error_throttle = Throttle(10.0, clock)
        self._second = 0
        self._lines = 0

    def process_packet(self, packet: Any) -> None:
        """scapy har paket uchun chaqiradi. Bitta buzuq paket ushlashni to'xtatmasligi kerak."""
        try:
            self._process(packet)
        except Exception as exc:  # noqa: BLE001
            self.stats.errors += 1
            if self._error_throttle.ready():
                logging.error(
                    "Paketni qayta ishlashda xato (jami %d): %s: %s",
                    self.stats.errors, type(exc).__name__, exc,
                )

    def _process(self, packet: Any) -> None:
        stats = self.stats
        stats.seen += 1
        if self.packet_clock is not None:
            self.packet_clock.now = float(packet.time)
        stats.last_packet = self._clock()
        if not self.state.active:
            stats.paused += 1
            return
        ip_layer = packet.getlayer(IP) or packet.getlayer(IPv6)
        if ip_layer is None:
            stats.non_ip += 1
            return
        src, dst = str(ip_layer.src), str(ip_layer.dst)
        # Chiqarilgan manzillar eng avval tekshiriladi: ular uchun tahlil ham, geolokatsiya ham yo'q.
        if self.state.is_excluded(src) or self.state.is_excluded(dst):
            stats.excluded += 1
            return
        geo = self.geo
        if geo is not None and (src in geo.service_ips or dst in geo.service_ips):
            stats.geo_self += 1
            return

        if self.pcap_output is not None:
            self.pcap_output.write(packet)
        info, raw, findings = self._parse(packet, ip_layer, src, dst)
        stats.processed += 1
        transport = info.get("transport", {})
        proto = str(transport.get("type") or info["ip"]["proto"])
        alerts = self.detector.check(
            proto, src, dst, transport.get("dst_port"), str(transport.get("flags", "")), findings
        )
        if self._should_print(bool(alerts) or bool(findings.names)):
            console.write(self.format_packet_summary(info, raw, findings))
        for alert in alerts:
            stats.alerts += 1
            logging.log(alert.level, alert.message)
        self.packet_log.write(info)

    def _should_print(self, important: bool) -> bool:
        if not self.state.show_packets:
            return False
        if important or self.max_lines_per_sec <= 0:
            return True
        second = int(self._clock())
        if second != self._second:
            self._second = second
            self._lines = 0
        if self._lines >= self.max_lines_per_sec:
            self.stats.console_skipped += 1
            return False
        self._lines += 1
        return True

    def _parse(self, packet: Any, ip_layer: Any, src: str, dst: str) -> tuple[dict[str, Any], bytes, Findings]:
        moment = time.localtime(self.packet_clock.now) if self.packet_clock is not None else time.localtime()
        info: dict[str, Any] = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S", moment)}
        ether = packet.getlayer(Ether)
        if ether is not None:
            info["ethernet"] = {"src_mac": str(ether.src), "dst_mac": str(ether.dst)}
        version = int(getattr(ip_layer, "version", 4) or 4)
        number = getattr(ip_layer, "nh", None) if version == 6 else getattr(ip_layer, "proto", None)
        geo = self.geo
        info["ip"] = {
            "version": version,
            "src_ip": src,
            "dst_ip": dst,
            "proto": _IP_PROTOCOLS.get(number, "IPv6" if version == 6 else "IP"),
            "src_geo": geo.lookup(src) if geo is not None else None,
            "dst_geo": geo.lookup(dst) if geo is not None else None,
        }
        tcp = packet.getlayer(TCP)
        udp = packet.getlayer(UDP) if tcp is None else None
        if tcp is not None:
            info["transport"] = {
                "type": "TCP", "src_port": int(tcp.sport), "dst_port": int(tcp.dport), "flags": str(tcp.flags),
            }
        elif udp is not None:
            info["transport"] = {"type": "UDP", "src_port": int(udp.sport), "dst_port": int(udp.dport)}
        query = _dns_query(packet)
        if query is not None:
            info["application"] = {"protocol": "DNS", "query": query}
        raw = b""
        findings = NO_FINDINGS
        raw_layer = packet.getlayer(Raw)
        if raw_layer is not None:
            raw = bytes(raw_layer.load)
        if raw and tcp is not None and "application" not in info:
            application = parse_http_request(raw)
            if application is None:
                name = parse_tls_sni(raw)
                if name is not None:
                    application = {"protocol": "TLS", "sni": name}
            if application is not None:
                info["application"] = application
        if raw:
            findings = self.scanner.scan(raw)
            text = ""
            if self.log_max_bytes > 0:
                text = render_payload(raw, findings, self.log_max_bytes, color=False, mask=self.mask)
            payload: dict[str, Any] = {"raw": text, "size": len(raw)}
            if findings.names:
                payload["sensitive"] = list(findings.names)
            info["payload"] = payload
        return info, raw, findings

    def format_packet_summary(self, info: dict[str, Any], raw: bytes = b"", findings: Findings = NO_FINDINGS) -> str:
        timestamp = info["timestamp"].split(" ")[1]
        transport = info.get("transport", {})
        ip_info = info["ip"]
        proto = str(transport.get("type") or ip_info.get("proto") or "IP")
        proto_color = Fore.GREEN if proto == "TCP" else (Fore.YELLOW if proto == "UDP" else Fore.WHITE)
        reset = Style.RESET_ALL
        flags = f" [{transport.get('flags', '')}]" if proto == "TCP" else ""
        head = (
            f"{Style.DIM}[{timestamp}]{reset} {proto_color}{proto}{reset}: "
            f"{Fore.CYAN}{_endpoint(ip_info['src_ip'], transport.get('src_port'))}{reset} -> "
            f"{Fore.CYAN}{_endpoint(ip_info['dst_ip'], transport.get('dst_port'))}{reset}{flags}"
        )
        parts = [head]
        ether = info.get("ethernet")
        if ether:
            parts.append(f"MAC: {ether.get('src_mac')} -> {ether.get('dst_mac')}")
        application = info.get("application", {})
        if application.get("protocol") == "DNS":
            parts.append(f"DNS: {application.get('query')}")
        elif application.get("protocol") == "TLS":
            parts.append(f"TLS: {Fore.GREEN}{application.get('sni')}{reset}")
        elif application.get("protocol") == "HTTP":
            target = f"{application.get('host', '')}{application.get('path', '')}"
            parts.append(f"HTTP: {application.get('method')} {Fore.GREEN}{target}{reset}")
        for label, key in (("manba", "src_geo"), ("manzil", "dst_geo")):
            place = ip_info.get(key)
            if place and place != GEO_PRIVATE:
                text = ", ".join(str(place[name]) for name in ("country", "isp") if place.get(name))
                if text:
                    parts.append(f"GEO {label}: {text}")
        line = " | ".join(parts)
        if raw:
            if findings.names:
                prefix = f"{Fore.RED}{Style.BRIGHT}└── [XAVFLI PAYLOAD]:{reset}"
            else:
                prefix = f"{Fore.MAGENTA}└── [PAYLOAD]:{reset}"
            shown = render_payload(raw, findings, self.preview_bytes, color=True, mask=self.mask)
            line += f"\n   {prefix} {shown}"
        return line


# ---------------------------------------------------------------------------
# Fon ishlari: jurnalni diskka tushirish va tizim ko'rsatkichlari
# ---------------------------------------------------------------------------


class SystemMonitor(threading.Thread):
    """Har soniyada paketlar jurnalini diskka tushiradi; `interval` da holat xulosasini yozadi."""

    def __init__(self, processor: PacketProcessor, interval_s: float, stop: threading.Event) -> None:
        super().__init__(daemon=True, name="SystemMonitorThread")
        self.processor = processor
        self.interval_s = interval_s
        self._stop_event = stop
        self.capture: Capture | None = None

    def summary(self) -> str:
        stats = self.processor.stats
        parts: list[str] = []
        if psutil is not None:
            try:
                memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
                parts.append(
                    f"CPU {psutil.cpu_percent(interval=None):.0f}% | RAM {psutil.virtual_memory().percent:.0f}% | "
                    f"dastur {memory_mb:.0f} MB"
                )
            except Exception:  # noqa: BLE001 — ko'rsatkich olinmasa, xulosaning qolgani chiqadi
                pass
        parts.append(
            f"paketlar: ko'rildi {stats.seen}, qayta ishlandi {stats.processed}, "
            f"chiqarilgan {stats.excluded}, pauzada {stats.paused}, xato {stats.errors}, signal {stats.alerts}"
        )
        return " | ".join(parts)

    def run(self) -> None:
        if psutil is not None:
            try:
                psutil.cpu_percent(interval=None)  # birinchi o'lchov uchun boshlang'ich nuqta
            except Exception:  # noqa: BLE001
                pass
        next_report = time.monotonic() + self.interval_s
        while not self._stop_event.wait(1.0):
            self.processor.packet_log.flush()
            if self.processor.pcap_output is not None:
                self.processor.pcap_output.flush()
            if self.capture is not None:
                self.capture.check_silence()
            if self.interval_s > 0 and time.monotonic() >= next_report:
                next_report = time.monotonic() + self.interval_s
                logging.info("[TIZIM] %s", self.summary())


# ---------------------------------------------------------------------------
# Buyruqlar
# ---------------------------------------------------------------------------

COMMANDS = [
    ("pause", "Monitoringni to'xtatib turadi (paketlar e'tiborga olinmaydi)"),
    ("resume", "To'xtatilgan monitoringni qayta faollashtiradi"),
    ("exclude <IP>", "IP manzil yoki tarmoqni (10.0.0.0/8) kuzatuvdan chiqaradi"),
    ("exclude <IP1,IP2>", "Bir nechta manzilni vergul bilan ajratib chiqaradi"),
    ("unexclude <IP>", "Manzilni chiqarilganlar ro'yxatidan olib tashlaydi"),
    ("list", "Chiqarilgan manzillar ro'yxatini ko'rsatadi"),
    ("quiet", "Paket satrlarini yashiradi (signallar va fayl jurnali davom etadi)"),
    ("verbose", "Paket satrlarini qayta ko'rsatadi"),
    ("status", "Monitoringning joriy holatini ko'rsatadi"),
    ("help", "Ushbu yordam xabarini ko'rsatadi"),
    ("exit / quit", "Dasturni to'xtatadi"),
]


def show_help() -> None:
    lines = [f"\n{Fore.CYAN}{'=' * 78}", "  MONITORING BOSHQARUV BUYRUQLARI", f"{'=' * 78}{Style.RESET_ALL}"]
    lines.extend(f"  {Fore.YELLOW}{command:<20}{Style.RESET_ALL}{text}" for command, text in COMMANDS)
    lines.append(f"{Fore.CYAN}{'=' * 78}{Style.RESET_ALL}\n")
    console.write("\n".join(lines))


class CommandHandler:
    """Buyruq satrini bajaradi. Konsoldan ham, testdan ham chaqiriladi."""

    def __init__(
        self, state: MonitorState, processor: PacketProcessor | None = None, capture: Capture | None = None
    ) -> None:
        self.state = state
        self.processor = processor
        self.capture = capture

    def handle(self, line: str) -> bool:
        """`False` — dastur to'xtashi kerak."""
        parts = line.strip().split(maxsplit=1)
        if not parts:
            return True
        command = parts[0].lower()
        argument = parts[1].strip() if len(parts) > 1 else ""
        if command == "pause":
            self._pause()
        elif command == "resume":
            self._resume()
        elif command in ("exclude", "unexclude"):
            self._targets(command, argument)
        elif command == "list":
            self._list()
        elif command in ("quiet", "verbose"):
            self.state.show_packets = command == "verbose"
            text = "ko'rsatiladi" if self.state.show_packets else "yashirildi (signallar chiqaveradi)"
            console.write(f"\n{Fore.CYAN}[KONSOL]{Style.RESET_ALL} Paket satrlari {text}.")
        elif command == "status":
            self._status()
        elif command == "help":
            show_help()
        elif command in ("exit", "quit"):
            console.write(f"{Fore.RED}Dastur to'xtatilmoqda...{Style.RESET_ALL}")
            logging.info("[BOSHQARUV] Foydalanuvchi tomonidan dastur to'xtatildi.")
            return False
        else:
            console.write(
                f"{Fore.RED}[XATO] Noma'lum buyruq: '{sanitize_text(command.encode('utf-8'), True)}'. "
                f"Yordam uchun 'help' kiriting.{Style.RESET_ALL}"
            )
        return True

    def _pause(self) -> None:
        if self.state.pause():
            text = "Monitoring PAUZA rejimiga o'tkazildi. Davom ettirish uchun 'resume' buyrug'ini kiriting."
            console.write(f"\n{Fore.YELLOW}{Style.BRIGHT}[PAUZA] {text}{Style.RESET_ALL}")
            logging.info("[BOSHQARUV] %s", text)
        else:
            console.write(f"\n{Fore.YELLOW}[PAUZA] Monitoring allaqachon pauza rejimida.{Style.RESET_ALL}")

    def _resume(self) -> None:
        if self.state.resume():
            text = "Monitoring qayta FAOLLASHTIRILDI. Paketlarni qabul qilish davom etmoqda."
            console.write(f"\n{Fore.GREEN}{Style.BRIGHT}[DAVOM] {text}{Style.RESET_ALL}")
            logging.info("[BOSHQARUV] %s", text)
        else:
            console.write(f"\n{Fore.GREEN}[DAVOM] Monitoring allaqachon faol rejimda.{Style.RESET_ALL}")

    def _targets(self, command: str, argument: str) -> None:
        if not argument:
            console.write(
                f"{Fore.RED}[XATO] IP manzil(lar)ni kiriting. Masalan: {command} 192.168.1.5{Style.RESET_ALL}"
            )
            return
        changed = False
        for item in (part.strip() for part in argument.split(",")):
            if not item:
                continue
            shown = sanitize_text(item.encode("utf-8"), True)
            network = parse_target(item)
            label = target_label(network) if network is not None else shown
            result = self.state.exclude(item) if command == "exclude" else self.state.unexclude(item)
            if result == "invalid":
                console.write(
                    f"\n{Fore.RED}[XATO] Noto'g'ri manzil: '{shown}'. To'g'ri ko'rinish: 192.168.1.1, "
                    f"192.168.1.0/24 yoki fe80::1{Style.RESET_ALL}"
                )
            elif result == "exists":
                console.write(
                    f"\n{Fore.YELLOW}[MA'LUMOT] {label} allaqachon chiqarilganlar ro'yxatida.{Style.RESET_ALL}"
                )
            elif result == "missing":
                console.write(
                    f"\n{Fore.YELLOW}[MA'LUMOT] {label} chiqarilganlar ro'yxatida topilmadi.{Style.RESET_ALL}"
                )
            elif result == "added":
                changed = True
                text = f"{label} monitoring dan CHIQARILDI."
                console.write(f"\n{Fore.CYAN}{Style.BRIGHT}[CHIQARILDI] {text}{Style.RESET_ALL}")
                logging.info("[BOSHQARUV] %s", text)
            else:
                changed = True
                text = f"{label} chiqarilganlar ro'yxatidan OLIB TASHLANDI. Endi monitoring qilinadi."
                console.write(f"\n{Fore.GREEN}{Style.BRIGHT}[QAYTARILDI] {text}{Style.RESET_ALL}")
                logging.info("[BOSHQARUV] %s", text)
        if changed and not self.state.save():
            logging.warning("Chiqarilganlar ro'yxati faylga saqlanmadi (keyingi ishga tushirishda yo'qoladi).")

    def _list(self) -> None:
        targets = self.state.excluded()
        lines = [f"\n{Fore.CYAN}{'─' * 50}{Style.RESET_ALL}"]
        if not targets:
            lines.append(f"{Fore.CYAN}[RO'YXAT] Chiqarilganlar ro'yxati bo'sh.{Style.RESET_ALL}")
        else:
            lines.append(
                f"{Fore.CYAN}[RO'YXAT] Monitoring dan chiqarilgan manzillar ({len(targets)} ta):{Style.RESET_ALL}"
            )
            lines.extend(f"  {Fore.YELLOW}* {target}{Style.RESET_ALL}" for target in targets)
        lines.append(f"{Fore.CYAN}{'─' * 50}{Style.RESET_ALL}")
        console.write("\n".join(lines))

    def _status(self) -> None:
        active = f"{Fore.GREEN}FAOL{Style.RESET_ALL}" if self.state.active else f"{Fore.YELLOW}PAUZA{Style.RESET_ALL}"
        shown = "ko'rsatiladi" if self.state.show_packets else "yashirilgan"
        text = (
            f"\n{Fore.CYAN}[HOLAT]{Style.RESET_ALL} Monitoring: {active} | "
            f"Chiqarilgan manzillar: {Fore.YELLOW}{len(self.state.excluded())}{Style.RESET_ALL} | "
            f"Paket satrlari: {shown}"
        )
        if self.processor is not None:
            stats = self.processor.stats
            text += (
                f"\n        Paketlar: ko'rildi {stats.seen}, qayta ishlandi {stats.processed}, "
                f"chiqarilgan {stats.excluded}, pauzada {stats.paused}, xato {stats.errors}"
                f"\n        Signallar: {stats.alerts} (takror bostirilgan {self.processor.detector.suppressed}) | "
                f"Konsolga sig'magan satrlar: {stats.console_skipped} | "
                f"Faylga yozilgan: {self.processor.packet_log.written}"
            )
            output = self.processor.pcap_output
            if output is not None:
                state = " (chegaraga yetdi, to'xtatilgan)" if output.full else ""
                megabytes = output.size / (1024 * 1024)
                text += f"\n        pcap: {output.written} paket, {megabytes:.1f} MB{state} -> {output.path}"
            if self.capture is not None:
                if stats.last_packet:
                    age = f"oxirgi paket {max(0.0, time.monotonic() - stats.last_packet):.0f} s oldin"
                else:
                    age = "hali birorta paket kelmadi"
                text += f"\n        Ushlash rejimi: {self.capture.mode_label()} | {age}"
        console.write(text)


class CommandListener(threading.Thread):
    """Ushlash davomida konsoldan buyruq o'qiydi.

    Interfeys tanlangandan **keyin** ishga tushiriladi: ikki oqim bitta kiritishni talashmaydi.
    """

    def __init__(self, handler: CommandHandler) -> None:
        super().__init__(daemon=True, name="CommandListenerThread")
        self.handler = handler
        self.acknowledged = threading.Event()

    def run(self) -> None:
        stop = self.handler.state.stop
        while True:
            try:
                line = input()
            except EOFError:  # kiritish yopiq (masalan, fon rejimi): ushlash davom etadi
                logging.info("[BOSHQARUV] Buyruq kiritish yopildi; monitoring davom etmoqda.")
                break
            except Exception as exc:  # noqa: BLE001
                logging.error("[CommandListener] Xato: %s", exc)
                break
            if stop.is_set():  # dastur to'xtayapti: bu Enter — «o'qidim» belgisi
                break
            try:
                if not self.handler.handle(line):
                    stop.set()
                    break
            except Exception as exc:  # noqa: BLE001
                logging.error("[CommandListener] Xato: %s", exc)
        self.acknowledged.set()


# ---------------------------------------------------------------------------
# Interfeyslar va ushlash
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Interface:
    capture_name: str  # sniff() ga beriladigan nom
    label: str
    address: str


def list_interfaces() -> list[Interface]:
    """IPv4 manzili bor (loopback'dan tashqari) interfeyslar.

    Ro'yxat va ushlash nomlari scapy'ning o'z jadvalidan olinadi: Windows'da u ushlash drayveri
    (Npcap) haqiqatan ham ko'radigan qurilmalarni va ularning aniq nomlarini beradi.
    """
    result: list[Interface] = []
    for item in get_working_ifaces():
        address = str(getattr(item, "ip", "") or "")
        if address and address != "127.0.0.1" and "." in address:
            label = str(item.description or item.name)
            result.append(Interface(str(item.network_name), label, address))
    return result


def print_interfaces(interfaces: list[Interface], default: str = "") -> None:
    lines = [f"\n{Fore.CYAN}Monitoring uchun mavjud tarmoq interfeyslari:{Style.RESET_ALL}"]
    for index, item in enumerate(interfaces):
        mark = f"  {Fore.MAGENTA}<- asosiy (internet shu orqali){Style.RESET_ALL}" if item.address == default else ""
        lines.append(
            f"{Fore.YELLOW}{index}{Style.RESET_ALL}: {item.label} "
            f"({Fore.GREEN}{item.address}{Style.RESET_ALL}){mark}"
        )
    console.write("\n".join(lines))


def choose_interface(interfaces: list[Interface], requested: str | None, default: str = "") -> str | None:
    """Tanlangan interfeysning ushlash nomi; kiritish yopilsa `None`."""
    if requested is not None:
        if requested.isdigit() and int(requested) < len(interfaces):
            return interfaces[int(requested)].capture_name
        for item in interfaces:
            if requested in (item.capture_name, item.label, item.address):
                return item.capture_name
        return requested  # ro'yxatda ko'rinmaydigan nom (masalan, loopback)
    print_interfaces(interfaces, default)
    while True:
        try:
            answer = input(f"{Fore.CYAN}Monitoring uchun interfeys raqamini kiriting: {Style.RESET_ALL}")
        except EOFError:
            return None
        try:
            selected = int(answer.strip())
        except ValueError:
            console.write("Iltimos, faqat raqam kiriting.")
            continue
        if 0 <= selected < len(interfaces):
            return interfaces[selected].capture_name
        console.write("Noto'g'ri raqam kiritildi.")


def capture_available() -> bool:
    """Windows'da ushlash uchun Npcap drayveri kerak."""
    return sys.platform != "win32" or bool(scapy_conf.use_pcap)


def open_capture_socket(interface: str, bpf_filter: str | None, promiscuous: bool) -> Any:
    """Interfeysni ushlash uchun ochadi (sniff() ichkarida qiladigan ishning o'zi, rejimi aniq berilgan)."""
    options: dict[str, Any] = {"type": ETH_P_ALL, "iface": interface, "promisc": promiscuous}
    if bpf_filter:
        options["filter"] = bpf_filter
    return resolve_iface(interface).l2listen()(**options)


NO_PACKETS_WARN_S = 15.0


class Capture:
    """Paketlarni ushlash oqimi.

    `promiscuous` — `True`, `False` yoki `None` (avto). Ko'p Wi-Fi adapterlar Windows'da promiscuous
    rejimda birorta ham paket bermaydi. Avto rejimda ushlash promiscuous holda boshlanadi; `probe_s`
    ichida paket kelmasa, interfeys oddiy rejimda qayta ochiladi.
    """

    def __init__(
        self,
        interface: str,
        bpf_filter: str | None,
        promiscuous: bool | None,
        processor: PacketProcessor,
        stop: threading.Event,
        probe_s: float = 5.0,
        open_socket: Callable[[str, str | None, bool], Any] = open_capture_socket,
        run_sniff: Callable[..., Any] = sniff,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.interface = interface
        self.bpf_filter = bpf_filter
        self.modes = [True, False] if promiscuous is None else [promiscuous]
        self.processor = processor
        self.stop = stop
        self.probe_s = probe_s
        self._open_socket = open_socket
        self._run_sniff = run_sniff
        self._clock = clock
        self.failure: list[str] = []
        self.promiscuous: bool | None = None  # hozirgi rejim; None — hali ochilmagan
        self.fell_back = False
        self.started_at = 0.0
        self._warned = False

    def mode_label(self) -> str:
        if self.promiscuous is None:
            return "ochilmoqda"
        label = "promiscuous" if self.promiscuous else "oddiy (faqat shu kompyuter trafigi)"
        return f"{label}, avtomatik almashgan" if self.fell_back else label

    def run(self) -> None:
        try:
            self._capture()
            if not self.stop.is_set():
                self.failure.append("ushlash kutilmaganda tugadi")
        except Exception as exc:  # noqa: BLE001
            self.failure.append(f"{type(exc).__name__}: {exc}"[:300])
        self.stop.set()

    def _capture(self) -> None:
        stats = self.processor.stats
        for index, promiscuous in enumerate(self.modes):
            last = index == len(self.modes) - 1
            sock = self._open_socket(self.interface, self.bpf_filter, promiscuous)
            self.promiscuous = promiscuous
            self.started_at = self._clock()
            try:
                if not last:
                    # Sinov bosqichi: shu rejimda paket keladimi?
                    self._run_sniff(
                        opened_socket=sock, prn=self.processor.process_packet, store=False, timeout=self.probe_s
                    )
                    if self.stop.is_set():
                        return
                    if stats.seen == 0:
                        self.fell_back = True
                        logging.warning(
                            "Promiscuous rejimda %.0f s ichida birorta paket kelmadi (Wi-Fi adapterlarda "
                            "odatiy holat). Interfeys oddiy rejimda qayta ochilmoqda.", self.probe_s,
                        )
                        continue
                self._run_sniff(opened_socket=sock, prn=self.processor.process_packet, store=False)
                return
            finally:
                try:
                    sock.close()
                except Exception:  # noqa: BLE001
                    pass

    def check_silence(self) -> None:
        """Ushlash boshlanganidan beri paket kelmagan bo'lsa, bir marta ogohlantiradi."""
        if self._warned or self.promiscuous is None or self.processor.stats.seen > 0:
            return
        if self.promiscuous and len(self.modes) > 1:  # hali sinov bosqichi
            return
        if self._clock() - self.started_at < NO_PACKETS_WARN_S:
            return
        self._warned = True
        logging.warning(
            "Bu interfeysdan %.0f s davomida birorta paket kelmadi. Tekshiring: (1) to'g'ri interfeys "
            "tanlanganmi — internet o'tadigani ro'yxatda «asosiy» deb belgilangan; (2) Npcap «faqat "
            "administratorlar uchun» o'rnatilgan bo'lsa, dasturni administrator nomidan oching; "
            "(3) config.json dagi capture_filter juda tor emasmi.", NO_PACKETS_WARN_S,
        )


def default_address() -> str:
    """Internetga chiqadigan interfeysning IPv4 manzili (paket yuborilmaydi); aniqlanmasa `""`."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 9))
            return str(probe.getsockname()[0])
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# O'zini sinash: ushlash drayverisiz butun zanjirni tekshiradi
# ---------------------------------------------------------------------------


class _Collector(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def build_client_hello(server_name: bytes) -> bytes:
    """Sinov uchun eng kichik TLS 1.2 ClientHello (SNI kengaytmasi bilan)."""
    sni = b"\x00" + len(server_name).to_bytes(2, "big") + server_name
    extensions = b"\x00\x0b\x00\x02\x01\x00"  # ec_point_formats: SNI birinchi bo'lmasligi uchun
    extensions += b"\x00\x00" + (len(sni) + 2).to_bytes(2, "big") + len(sni).to_bytes(2, "big") + sni
    body = b"\x03\x03" + bytes(32) + b"\x00" + b"\x00\x02\x13\x01" + b"\x01\x00"
    body += len(extensions).to_bytes(2, "big") + extensions
    handshake = b"\x01" + len(body).to_bytes(3, "big") + body
    return b"\x16\x03\x01" + len(handshake).to_bytes(2, "big") + handshake


def _self_test_packets() -> list[Any]:
    mac = Ether(src="02:00:00:00:00:01", dst="02:00:00:00:00:02")
    packets: list[Any] = [
        mac / IP(src="192.168.1.10", dst="93.184.216.34") / TCP(sport=40000, dport=80, flags="PA")
        / Raw(b"POST /login?next=1 HTTP/1.1\r\nHost: sinov.example\r\nUser-Agent: test\r\n\r\n"
              b"username=ali&password=Maxfiy123"),
        mac / IP(src="192.168.1.10", dst="93.184.216.34") / TCP(sport=40006, dport=443, flags="PA")
        / Raw(build_client_hello(b"maxfiy-sayt.example")),
        mac / IP(src="192.168.1.10", dst="8.8.8.8") / UDP(sport=40001, dport=53)
        / DNS(rd=1, qd=DNSQR(qname="exa\x1b[31mmple.com")),
        mac / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=40002, dport=4000, flags="A")
        / Raw(b"\x1b[2J\x07binary\x00\\x41"),
        mac / IPv6(src="fe80::1", dst="ff02::fb") / UDP(sport=5353, dport=5353) / Raw(b"ipv6"),
        mac / IP(src="10.9.9.9", dst="192.168.1.10") / TCP(sport=40003, dport=22, flags=0),
        mac / IP(src="10.9.9.9", dst="192.168.1.10") / TCP(sport=40003, dport=22, flags="F"),
        mac / IP(src="10.9.9.9", dst="192.168.1.10") / TCP(sport=40003, dport=22, flags="FPU"),
        mac / IP(src="192.168.1.10", dst="192.168.1.77") / TCP(sport=40004, dport=23, flags="S"),
        mac / IP(src="192.168.1.66", dst="192.168.1.10") / TCP(sport=40005, dport=80, flags="PA") / Raw(b"skip"),
    ]
    # Port skanerlash: 20 ta turli portga SYN. Javob paketlari (SA) signal bermasligi kerak.
    packets.extend(
        mac / IP(src="10.7.7.7", dst="192.168.1.10") / TCP(sport=50000, dport=1000 + port, flags="S")
        for port in range(20)
    )
    packets.extend(
        mac / IP(src="93.184.216.34", dst="192.168.1.10") / TCP(sport=443, dport=51000 + port, flags="SA")
        for port in range(20)
    )
    return packets


def self_test() -> int:
    """Sun'iy paketlarni fayldan o'qib, butun zanjirdan o'tkazadi. 0 — hammasi to'g'ri."""
    problems: list[str] = []
    printed: list[str] = []
    collector = _Collector()
    root = logging.getLogger()
    old_handlers, old_level = list(root.handlers), root.level
    original_write = console.write
    with tempfile.TemporaryDirectory(prefix="netmonitor-selftest-") as folder_name:
        folder = Path(folder_name)
        root.handlers = [collector]
        root.setLevel(logging.INFO)
        console.write = printed.append  # type: ignore[method-assign]
        try:
            state = MonitorState(folder / "state.json")
            state.exclude("192.168.1.66")
            config = copy.deepcopy(DEFAULT_CONFIG)
            config["console"]["max_lines_per_sec"] = 0
            packet_log = PacketLog(folder, "captured_packets.json", 20, 5)
            saved = folder / "saved.pcap"
            pcap_output = PcapOutput(saved, 0)
            processor = PacketProcessor(config, state, packet_log, pcap_output=pcap_output)
            capture = folder / "selftest.pcap"
            wrpcap(str(capture), _self_test_packets())
            sniff(offline=str(capture), prn=processor.process_packet, store=False)
            processor.process_packet(object())  # buzuq paket: xato sanaladi, ushlash to'xtamaydi
            CommandHandler(state, processor).handle("status")
            packet_log.close()
            pcap_output.close()

            stats = processor.stats
            expected = {"seen": 51, "processed": 49, "excluded": 1, "errors": 1}
            for name, value in expected.items():
                if getattr(stats, name) != value:
                    problems.append(f"stats.{name} = {getattr(stats, name)}, kutilgan {value}")
            output = "\n".join(printed)
            if "\x1b[31mmple" in output or "\x1b[2J" in output or "\x07" in output:
                problems.append("tarmoqdan kelgan boshqaruv belgisi konsolga o'tdi")
            if "Maxfiy123" in output:
                problems.append("parol qiymati konsolda yashirilmadi")
            for kind in ("NULL Scan", "FIN Scan", "Xmas Scan", "Shubhali port 23", "Ochiq matnda maxfiy maydon"):
                if not any(kind in message for message in collector.messages):
                    problems.append(f"signal chiqmadi: {kind}")
            scans = [message for message in collector.messages if "PORT SKANERLASH" in message][:1]
            if len(scans) != 1 or "10.7.7.7" not in scans[0]:
                problems.append(f"port skanerlash signali noto'g'ri: {scans}")
            lines = [
                line
                for path in sorted(folder.glob("captured_packets*.json"))
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
            if len(lines) != 49:
                problems.append(f"jurnalda {len(lines)} satr, kutilgan 49")
            if len(list(folder.glob("captured_packets_*.json"))) != 2:
                problems.append("jurnal rotatsiyasi kutilganidek ishlamadi")
            records = [json.loads(line) for line in lines]
            if any("Maxfiy123" in line for line in lines):
                problems.append("parol qiymati jurnalda yashirilmadi")
            if not any(record["ip"]["version"] == 6 for record in records):
                problems.append("IPv6 paket jurnalga tushmadi")
            applications = [record.get("application", {}) for record in records]
            if {"protocol": "TLS", "sni": "maxfiy-sayt.example"} not in applications:
                problems.append("TLS server nomi (SNI) aniqlanmadi")
            http = {"protocol": "HTTP", "method": "POST", "host": "sinov.example", "path": "/login"}
            if http not in applications:
                problems.append("HTTP so'rovi aniqlanmadi")
            # Yozilgan .pcap ni qayta o'qish: --write-pcap va --read zanjiri.
            replay_log = PacketLog(folder, "replay.json", 1000, 5)
            replay = PacketProcessor(config, MonitorState(), replay_log, None, PacketClock())
            sniff(offline=str(saved), prn=replay.process_packet, store=False)
            replay_log.close()
            if replay.stats.processed != 49 or replay.stats.errors:
                problems.append(f"yozilgan pcap qayta o'qilganda {replay.stats.processed} paket, kutilgan 49")
            if sum("PORT SKANERLASH" in message for message in collector.messages) != 2:
                problems.append("qayta o'qishda port skanerlash signali chiqmadi")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{type(exc).__name__}: {exc}")
        finally:
            console.write = original_write  # type: ignore[method-assign]
            root.handlers = old_handlers
            root.setLevel(old_level)
    if problems:
        console.write(f"{APP_NAME} {__version__}: o'zini sinash MUVAFFAQIYATSIZ")
        for problem in problems:
            console.write(f"  - {problem}")
        return EXIT_FAILED
    console.write(f"{APP_NAME} {__version__}: o'zini sinash muvaffaqiyatli (51 paket, scapy {scapy_conf.version})")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Ishga tushirish
# ---------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=APP_NAME, description="Tarmoq paketlarini kuzatish. Faqat o'z tarmog'ingizda ishlating."
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument("--config", metavar="FAYL", help="sozlamalar fayli (standart: dastur yonidagi config.json)")
    parser.add_argument("--iface", metavar="INTERFEYS", help="interfeys raqami yoki nomi (so'ralmasin)")
    parser.add_argument("--read", metavar="PCAP", help="jonli ushlash o'rniga .pcap/.pcapng faylni tahlil qiladi")
    parser.add_argument("--write-pcap", metavar="PCAP", help="qayta ishlangan paketlarni .pcap faylga ham yozadi")
    parser.add_argument("--list-ifaces", action="store_true", help="interfeyslar ro'yxatini chiqarib, tugatadi")
    parser.add_argument("--self-test", action="store_true", help="drayversiz o'zini sinaydi va tugatadi")
    return parser.parse_args(argv)


def _wait_for_enter(listener: CommandListener | None) -> None:
    """Xato xabari o'qilmasdan oyna yopilib qolmasligi uchun (exe ikki marta bosib ochilganda)."""
    try:
        if not sys.stdin or not sys.stdin.isatty():
            return
        console.write("Chiqish uchun Enter bosing...")
        if listener is not None and listener.is_alive():
            listener.acknowledged.wait(300.0)
        else:
            input()
    except (EOFError, OSError, ValueError, KeyboardInterrupt):
        pass


def _finish(code: int, listener: CommandListener | None = None) -> int:
    if code != EXIT_OK:
        _wait_for_enter(listener)
    return code


def run(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser() if args.config else app_dir() / "config.json"
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        console.write(f"{Fore.RED}KRITIK XATO: Config fayl muammosi: {exc}{Style.RESET_ALL}")
        return _finish(EXIT_BAD_CONFIG)

    base = data_dir(config_path.resolve().parent if args.config else None)
    log_folder = Path(str(config.get("log_folder") or "logs_pro"))
    if not log_folder.is_absolute():
        log_folder = base / log_folder
    try:
        log_folder.mkdir(parents=True, exist_ok=True)
        setup_logging(log_folder)
    except OSError as exc:
        console.write(f"{Fore.RED}KRITIK XATO: jurnal papkasi ochilmadi: {exc}{Style.RESET_ALL}")
        return _finish(EXIT_BAD_CONFIG)

    console.write(f"{Fore.CYAN}{Style.BRIGHT}{APP_NAME} {__version__}{Style.RESET_ALL} — tarmoq kuzatuvi")
    console.write("Faqat o'z tarmog'ingizda yoki egasining ruxsati bilan ishlating.")
    if not config_path.is_file() and not args.config and write_default_config(config_path):
        logging.info("Sozlamalar fayli topilmadi — standart qiymatlar bilan yaratildi: %s", config_path)
    logging.info("Jurnal papkasi: %s", log_folder)

    offline = Path(args.read).expanduser() if args.read else None
    interfaces: list[Interface] = []
    interface: str | None = None
    default = ""
    if offline is not None:
        if not offline.is_file():
            logging.critical("Fayl topilmadi: %s", offline)
            return _finish(EXIT_BAD_CONFIG)
    else:
        interfaces = list_interfaces()
        default = default_address()
        if args.list_ifaces:
            print_interfaces(interfaces, default)
            return EXIT_OK
        if not capture_available():
            logging.critical(
                "Npcap drayveri topilmadi. Uni %s dan o'rnating va dasturni qayta ishga tushiring.", NPCAP_URL
            )
            return _finish(EXIT_CAPTURE_FAILED)
        if not interfaces and args.iface is None:
            logging.critical("Hech qanday aktiv (IP manzilli) tarmoq interfeysi topilmadi.")
            return _finish(EXIT_CAPTURE_FAILED)
        interface = choose_interface(interfaces, args.iface, default)
        if interface is None:
            logging.critical("Interfeys tanlanmadi (kiritish yopiq). `--iface` bilan ko'rsating.")
            return EXIT_CAPTURE_FAILED

    state = MonitorState(base / "netmonitor_state.json")
    restored = state.load()
    configured = config.get("excluded_ips")
    for item in configured if isinstance(configured, list) else []:
        if state.exclude(str(item)) == "invalid":
            logging.warning("config.json: excluded_ips ichida noto'g'ri manzil: %r", item)
    if state.excluded():
        logging.info("Kuzatuvdan chiqarilgan manzillar: %d ta (oldingi safardan %d).", len(state.excluded()), restored)
    state.show_packets = bool(_section(config, "console").get("show_packets", True))

    pcap_output: PcapOutput | None = None
    if args.write_pcap:
        target = Path(args.write_pcap).expanduser()
        try:
            if offline is not None and target.resolve() == offline.resolve():
                raise OSError("o'qilayotgan faylning o'ziga yozib bo'lmaydi")
            target.parent.mkdir(parents=True, exist_ok=True)
            pcap_output = PcapOutput(target, int(_number(config.get("pcap_max_mb"), 500, 0)) * 1024 * 1024)
        except OSError as exc:
            logging.critical("pcap fayli ochilmadi: %s", exc)
            return _finish(EXIT_BAD_CONFIG)
        logging.warning(
            "Paketlar %s ga to'liq yoziladi: unda parollar ham YASHIRILMAGAN holda bo'ladi. Faylni himoyalang.",
            target,
        )

    packet_log = PacketLog(
        log_folder,
        str(config.get("packet_log_filename") or "captured_packets.json"),
        int(_number(config.get("log_rotation_lines"), 10000, 1)),
        int(_number(config.get("max_packet_log_files"), 50, 1)),
    )
    if offline is not None:
        return _run_offline(config, offline, state, packet_log, pcap_output)

    assert interface is not None
    geo: GeoResolver | None = None
    if _section(config, "geolocation").get("enabled"):
        geo = GeoResolver()
        geo.start()
        logging.info("Geolokatsiya yoqilgan: tashqi IP manzillar %s ga (HTTP, ochiq) yuboriladi.", GEO_HOST)

    processor = PacketProcessor(config, state, packet_log, geo, pcap_output=pcap_output)
    interval = _number(config.get("system_metrics_interval_sec"), 120, 0)
    monitor = SystemMonitor(processor, interval, state.stop)
    monitor.start()

    bpf_filter = config.get("capture_filter")
    capture_settings = _section(config, "capture")
    promiscuous = capture_settings.get("promiscuous", "auto")
    capture = Capture(
        interface,
        bpf_filter if isinstance(bpf_filter, str) else None,
        promiscuous if isinstance(promiscuous, bool) else None,
        processor,
        state.stop,
        _number(capture_settings.get("probe_sec"), 5.0, 1.0),
    )
    chosen = next((item for item in interfaces if item.capture_name == interface), None)
    logging.info("Monitoring '%s' interfeysida boshlandi...", chosen.label if chosen else interface.split("_")[-1])
    if chosen is not None and default and chosen.address != default:
        logging.warning(
            "Tanlangan interfeys (%s) asosiy emas: internet trafigi %s orqali o'tadi. Bu yerda faqat shu "
            "interfeysning o'z trafigi va tarmoqdagi umumiy (broadcast) paketlar ko'rinadi.",
            chosen.address, default,
        )
    threading.Thread(target=capture.run, daemon=True, name="CaptureThread").start()
    monitor.capture = capture

    # Buyruqlar interfeys tanlangandan keyin tinglanadi: kiritish uchun poyga yo'q.
    show_help()
    listener = CommandListener(CommandHandler(state, processor, capture))
    listener.start()

    try:
        while not state.stop.wait(0.5):
            pass
    except KeyboardInterrupt:
        logging.info("[BOSHQARUV] Ctrl+C: dastur to'xtatilmoqda.")
        state.stop.set()

    code = EXIT_OK
    if capture.failure:
        code = EXIT_CAPTURE_FAILED
        logging.critical("Sniffing xatosi: %s", capture.failure[0])
    packet_log.close()
    if pcap_output is not None:
        pcap_output.close()
    state.save()
    logging.info("[TIZIM] Yakun: %s", SystemMonitor(processor, 0, state.stop).summary())
    return _finish(code, listener)


def _run_offline(
    config: dict[str, Any], source: Path, state: MonitorState, packet_log: PacketLog, pcap_output: PcapOutput | None
) -> int:
    """`--read`: faylni boshidan oxirigacha jonli trafik kabi tahlil qiladi (drayver kerak emas)."""
    processor = PacketProcessor(config, state, packet_log, None, PacketClock(), pcap_output)
    bpf_filter = config.get("capture_filter")
    if isinstance(bpf_filter, str) and bpf_filter:
        logging.warning("Fayldan o'qishda capture_filter qo'llanmaydi: hamma paket tahlil qilinadi.")
    logging.info("Fayl tahlil qilinmoqda: %s", source)
    code = EXIT_OK
    try:
        sniff(offline=str(source), prn=processor.process_packet, store=False)
    except KeyboardInterrupt:
        logging.info("[BOSHQARUV] Ctrl+C: tahlil to'xtatildi.")
    except Exception as exc:  # noqa: BLE001
        code = EXIT_CAPTURE_FAILED
        logging.critical("Faylni o'qishda xato: %s: %s", type(exc).__name__, str(exc)[:300])
    packet_log.close()
    if pcap_output is not None:
        pcap_output.close()
    stats = processor.stats
    logging.info(
        "[TIZIM] Yakun: paketlar: o'qildi %d, qayta ishlandi %d, chiqarilgan %d, IP emas %d, xato %d, signal %d",
        stats.seen, stats.processed, stats.excluded, stats.non_ip, stats.errors, stats.alerts,
    )
    return _finish(code)


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        return self_test()
    return run(args)


if __name__ == "__main__":
    exit_code = EXIT_FAILED
    try:
        exit_code = main()
    except SystemExit as exc:  # argparse: --help, --version, noto'g'ri argument
        exit_code = exc.code if isinstance(exc.code, int) else EXIT_FAILED
    except Exception:  # noqa: BLE001
        logging.critical("Kutilmagan xato", exc_info=True)
        if not logging.getLogger().handlers:
            import traceback

            traceback.print_exc()
    finally:
        # Ushlash oqimi drayver chaqiruvida, buyruq oqimi esa kiritishda kutib turgan bo'lishi
        # mumkin: jurnal yopilgach, ularni kutmasdan chiqiladi.
        logging.shutdown()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(exit_code)
