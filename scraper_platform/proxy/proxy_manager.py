# -*- coding: utf-8 -*-
"""
proxy/proxy_manager.py
======================
Proxy menejeri: HTTP/HTTPS/SOCKS5 proxy'larni boshqaradi.

Funksiyalar:
    - Proxy ro'yxatini fayl yoki configdan yuklash
    - Rotatsiya (navbatma-navbat proxy tanlash)
    - Health check (ishlaydigan proxy'larni tekshirish)
    - Dead (ishlamaydigan) proxy'larni avtomatik olib tashlash

Proxy formati:
    scheme://[user:pass@]host:port
    Masalan:
        http://1.2.3.4:8080
        socks5://user:pass@1.2.3.4:1080
"""

from __future__ import annotations

import itertools
import threading
from pathlib import Path

import requests

from config.settings import CONFIG, BASE_DIR
from logs.logger import get_logger

log = get_logger(__name__)

PROXY_FILE: Path = BASE_DIR / "proxy" / "proxies.txt"


class ProxyManager:
    """Proxy'larni saqlash, tekshirish va rotatsiya qilish."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proxies: list[str] = []
        self._cycle: "itertools.cycle | None" = None
        self._load()

    # -----------------------------------------------------------------
    def _load(self) -> None:
        """Proxy'larni configdan va fayldan yuklaydi."""
        proxies: list[str] = list(CONFIG.proxy.proxies)
        if PROXY_FILE.exists():
            for line in PROXY_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.append(line)
        # Takrorlanmasligini ta'minlaymiz
        self._proxies = list(dict.fromkeys(proxies))
        self._cycle = itertools.cycle(self._proxies) if self._proxies else None
        if self._proxies:
            log.info("{} ta proxy yuklandi", len(self._proxies))

    def reload(self) -> None:
        """Proxy ro'yxatini qayta yuklaydi."""
        with self._lock:
            self._load()

    # -----------------------------------------------------------------
    def get_proxy(self) -> dict[str, str] | None:
        """
        requests/httpx uchun keyingi proxy dict'ini qaytaradi.

        Returns:
            {"http": "...", "https": "..."} yoki None (proxy o'chirilgan/yo'q).
        """
        if not CONFIG.proxy.enabled or not self._cycle:
            return None
        with self._lock:
            proxy = next(self._cycle) if CONFIG.proxy.rotate else self._proxies[0]
        return {"http": proxy, "https": proxy}

    def get_raw(self) -> str | None:
        """Keyingi proxy'ni oddiy string ko'rinishida qaytaradi (Playwright uchun)."""
        if not CONFIG.proxy.enabled or not self._cycle:
            return None
        with self._lock:
            return next(self._cycle) if CONFIG.proxy.rotate else self._proxies[0]

    # -----------------------------------------------------------------
    def check_proxy(self, proxy: str) -> bool:
        """Bitta proxy ishlashini tekshiradi."""
        try:
            resp = requests.get(
                CONFIG.proxy.check_url,
                proxies={"http": proxy, "https": proxy},
                timeout=CONFIG.proxy.check_timeout,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def health_check(self) -> dict[str, int]:
        """
        Barcha proxy'larni tekshiradi va ishlamaydiganlarni olib tashlaydi.

        Returns:
            {"alive": N, "dead": M} statistikasi.
        """
        if not self._proxies:
            return {"alive": 0, "dead": 0}

        alive: list[str] = []
        dead = 0
        for proxy in list(self._proxies):
            if self.check_proxy(proxy):
                alive.append(proxy)
            else:
                dead += 1
                log.warning("Ishlamaydigan proxy olib tashlandi: {}", proxy)

        with self._lock:
            self._proxies = alive
            self._cycle = itertools.cycle(alive) if alive else None

        log.info("Proxy tekshiruvi: {} ishlaydi, {} o'chirildi", len(alive), dead)
        return {"alive": len(alive), "dead": dead}

    @property
    def count(self) -> int:
        """Mavjud proxy'lar soni."""
        return len(self._proxies)


# Global singleton
PROXY_MANAGER = ProxyManager()
