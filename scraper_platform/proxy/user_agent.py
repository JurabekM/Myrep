# -*- coding: utf-8 -*-
"""
proxy/user_agent.py
===================
User-Agent menejeri: har bir so'rov uchun realistik User-Agent qatorini
tanlab beradi (Chrome, Firefox, Edge, Safari).

`fake-useragent` kutubxonasi mavjud bo'lsa undan, aks holda ichki
statik ro'yxatdan foydalaniladi (offline rejim uchun ishonchli).
"""

from __future__ import annotations

import random

from logs.logger import get_logger

log = get_logger(__name__)

# Offline rejim uchun ishonchli zaxira ro'yxat
_FALLBACK_AGENTS: dict[str, list[str]] = {
    "chrome": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ],
    "firefox": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    ],
    "edge": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    ],
    "safari": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    ],
}


class UserAgentManager:
    """User-Agent qatorlarini boshqaruvchi klass."""

    def __init__(self) -> None:
        self._ua = None
        try:
            from fake_useragent import UserAgent
            self._ua = UserAgent()
            log.info("fake-useragent yuklandi")
        except Exception as exc:  # noqa: BLE001 - offline yoki xatolik
            log.warning("fake-useragent mavjud emas, zaxira ro'yxat ishlatiladi: {}", exc)

    def random(self) -> str:
        """Ixtiyoriy brauzerdan tasodifiy User-Agent qaytaradi."""
        if self._ua is not None:
            try:
                return self._ua.random
            except Exception:  # noqa: BLE001
                pass
        browser = random.choice(list(_FALLBACK_AGENTS.keys()))
        return random.choice(_FALLBACK_AGENTS[browser])

    def get(self, browser: str = "chrome") -> str:
        """Berilgan brauzer uchun User-Agent qaytaradi."""
        browser = browser.lower()
        if self._ua is not None:
            try:
                return getattr(self._ua, browser)
            except Exception:  # noqa: BLE001
                pass
        return random.choice(_FALLBACK_AGENTS.get(browser, _FALLBACK_AGENTS["chrome"]))

    def headers(self, browser: str | None = None) -> dict[str, str]:
        """To'liq realistik HTTP sarlavhalarini qaytaradi."""
        ua = self.get(browser) if browser else self.random()
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }


# Global singleton
UA_MANAGER = UserAgentManager()
