"""IP manzil qayerga tegishli ekanini aniqlash (ixtiyoriy, standart holatda o'chiq).

So'rovlar alohida oqimda ketadi — paketlarni ushlash hech qachon kutib qolmaydi.
Faqat ommaviy (global) manzillar so'raladi; natija, shu jumladan muvaffaqiyatsizi ham,
keshlanadi. `ip-api.com` ning bepul xizmati faqat HTTP orqali ishlaydi: so'ralgan IP
manzillar tarmoqda ochiq ko'rinadi — shu sabab funksiya standart holatda o'chiq.
"""

import ipaddress
import json
import queue
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from collections.abc import Callable
from typing import cast

GEO_URL = "http://ip-api.com/json/{ip}?fields=status,country,city,isp"
CACHE_SIZE = 2000
QUEUE_SIZE = 200
# Bepul chegara — daqiqasiga 45 so'rov; zaxira bilan.
MIN_INTERVAL_S = 1.6
OK_TTL_S = 24 * 3600.0
FAIL_TTL_S = 600.0
TIMEOUT_S = 3.0

Fetch = Callable[[str], str | None]


def is_public(ip: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    # Multicast manzillar (224.0.0.0/4, ff00::/8) `is_global` bo'lishi mumkin, lekin egasi yo'q.
    return address.is_global and not address.is_multicast


def fetch_label(ip: str) -> str | None:
    """`Mamlakat, shahar · provayder`; xizmat javob bermasa yoki tanimasa `None`."""
    address = ipaddress.ip_address(ip)  # URL ga faqat tekshirilgan manzil tushadi
    try:
        with urllib.request.urlopen(GEO_URL.format(ip=address), timeout=TIMEOUT_S) as response:  # noqa: S310
            raw: object = json.loads(response.read(4096))
    except (OSError, ValueError, urllib.error.URLError):
        return None
    if not isinstance(raw, dict):
        return None
    data = cast(dict[str, object], raw)
    if data.get("status") != "success":
        return None
    place = ", ".join(str(data[key]) for key in ("country", "city") if data.get(key))
    isp = str(data.get("isp") or "")
    return " · ".join(part for part in (place, isp) if part)[:120]


class GeoResolver:
    def __init__(
        self,
        fetch: Fetch = fetch_label,
        min_interval_s: float = MIN_INTERVAL_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._fetch = fetch
        self._min_interval_s = min_interval_s
        self._clock = clock
        self._cache: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._pending: set[str] = set()
        self._queue: queue.Queue[str] = queue.Queue(maxsize=QUEUE_SIZE)
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self.requests = 0

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="netcap-geo", daemon=True)
        self._thread.start()

    def lookup(self, ip: str) -> str:
        """Keshdagi natija; yo'q bo'lsa `""` qaytarib, so'rovni navbatga qo'yadi (kutmaydi)."""
        if not is_public(ip):
            return ""
        with self._lock:
            cached = self._cache.get(ip)
            if cached is not None and cached[1] > self._clock():
                return cached[0]
            if ip in self._pending:
                return ""
            try:
                self._queue.put_nowait(ip)
            except queue.Full:
                return ""
            self._pending.add(ip)
        return ""

    def resolve_one(self) -> bool:
        """Navbatdan bitta manzilni so'raydi; navbat bo'sh bo'lsa `False`."""
        try:
            ip = self._queue.get_nowait()
        except queue.Empty:
            return False
        label = self._fetch(ip)
        self.requests += 1
        ttl = FAIL_TTL_S if label is None else OK_TTL_S
        with self._lock:
            self._pending.discard(ip)
            self._cache[ip] = (label or "", self._clock() + ttl)
            self._cache.move_to_end(ip)
            while len(self._cache) > CACHE_SIZE:
                self._cache.popitem(last=False)
        return True

    def _loop(self) -> None:
        while True:
            worked = self.resolve_one()
            time.sleep(self._min_interval_s if worked else 0.5)
