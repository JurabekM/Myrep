# -*- coding: utf-8 -*-
"""
scraper/async_engine.py
=======================
Yuqori unumdorlikli asinxron scraping dvigateli (aiohttp + asyncio).

Bir vaqtning o'zida minglab URL'ni qayta ishlashga mo'ljallangan.
Concurrency Semaphore orqali cheklanadi (CONFIG.scraper.concurrency).

Bu dvigatel STATIK sahifalar uchun optimallashtirilgan. JS render
kerak bo'lganda ScraperEngine (Playwright) ishlatilishi kerak.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from config.settings import CONFIG
from proxy.proxy_manager import PROXY_MANAGER
from proxy.user_agent import UA_MANAGER
from logs.logger import get_logger

log = get_logger(__name__)


@dataclass
class AsyncFetchResult:
    """Asinxron so'rov natijasi."""
    url: str
    status_code: int
    html: str
    content_type: str
    ok: bool
    error: str = ""


class AsyncScraper:
    """aiohttp asosidagi yuqori unumdorlikli asinxron scraper."""

    def __init__(self, concurrency: int | None = None) -> None:
        self.concurrency = concurrency or CONFIG.scraper.concurrency

    async def _fetch(self, session, url: str, sem: asyncio.Semaphore) -> AsyncFetchResult:
        """Bitta URL'ni asinxron yuklaydi (retry bilan)."""
        import aiohttp

        async with sem:
            headers = UA_MANAGER.headers()
            proxy_dict = PROXY_MANAGER.get_proxy()
            proxy = proxy_dict.get("http") if proxy_dict else None

            for attempt in range(1, CONFIG.scraper.max_retries + 1):
                try:
                    timeout = aiohttp.ClientTimeout(total=CONFIG.scraper.timeout)
                    async with session.get(
                        url, headers=headers, proxy=proxy, timeout=timeout,
                        ssl=CONFIG.scraper.verify_ssl,
                    ) as resp:
                        # 429/5xx bo'lsa qayta urinamiz
                        if resp.status == 429 or resp.status >= 500:
                            if attempt < CONFIG.scraper.max_retries:
                                await asyncio.sleep(CONFIG.scraper.retry_backoff * attempt)
                                continue
                        content_type = resp.headers.get("Content-Type", "")
                        text = await resp.text(errors="ignore")
                        return AsyncFetchResult(
                            url=url, status_code=resp.status, html=text,
                            content_type=content_type, ok=resp.status < 400,
                        )
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    if attempt < CONFIG.scraper.max_retries:
                        await asyncio.sleep(CONFIG.scraper.retry_backoff * attempt)
                        continue
                    return AsyncFetchResult(
                        url=url, status_code=0, html="", content_type="",
                        ok=False, error=str(exc),
                    )
            return AsyncFetchResult(url=url, status_code=0, html="",
                                    content_type="", ok=False, error="max retries")

    async def _run(self, urls: list[str],
                   on_result: Callable[[AsyncFetchResult], None] | None = None
                   ) -> list[AsyncFetchResult]:
        """Barcha URL'larni asinxron qayta ishlaydi."""
        import aiohttp

        sem = asyncio.Semaphore(self.concurrency)
        connector = aiohttp.TCPConnector(limit=self.concurrency, ssl=CONFIG.scraper.verify_ssl)
        results: list[AsyncFetchResult] = []

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [asyncio.ensure_future(self._fetch(session, u, sem)) for u in urls]
            for coro in asyncio.as_completed(tasks):
                res = await coro
                results.append(res)
                if on_result:
                    on_result(res)
        return results

    def scrape_many(self, urls: list[str],
                    on_result: Callable[[AsyncFetchResult], None] | None = None
                    ) -> list[AsyncFetchResult]:
        """
        Ko'p URL'ni asinxron scrape qiladi (sinxron interfeys).

        Args:
            urls: URL'lar ro'yxati.
            on_result: har bir natija uchun callback.

        Returns:
            AsyncFetchResult ro'yxati.
        """
        log.info("Asinxron scraping: {} ta URL, concurrency={}", len(urls), self.concurrency)
        try:
            return asyncio.run(self._run(urls, on_result))
        except RuntimeError:
            # Agar event loop allaqachon ishlab tursa (masalan GUI ichida)
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._run(urls, on_result))
            finally:
                loop.close()
