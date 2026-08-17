# -*- coding: utf-8 -*-
"""
scraper/crawler.py
==================
Rekursiv crawler. Boshlang'ich URL'dan boshlab saytni aylanib chiqadi.

Qo'llab-quvvatlanadi:
    - BFS (kenglik bo'yicha) va DFS (chuqurlik bo'yicha)
    - Sitemap.xml parsing
    - robots.txt parsing va unga rioya qilish
    - Chuqurlik cheklovi (max_depth)
    - Sahifalar soni cheklovi (max_pages)
    - Domen cheklovi (same_domain_only)
"""

from __future__ import annotations

import collections
import xml.etree.ElementTree as ET
from typing import Callable, Iterator
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

from config.settings import CONFIG
from scraper.engine import ScraperEngine, ScrapeResult
from proxy.user_agent import UA_MANAGER
from logs.logger import get_logger

log = get_logger(__name__)


class Crawler:
    """Sayt bo'ylab rekursiv aylanib chiquvchi crawler."""

    def __init__(self, engine: ScraperEngine | None = None,
                 stop_flag: Callable[[], bool] | None = None) -> None:
        self.engine = engine or ScraperEngine()
        # Tashqaridan to'xtatish uchun flag (masalan GUI dan)
        self.stop_flag = stop_flag or (lambda: False)
        self._robots_cache: dict[str, RobotFileParser] = {}

    # -----------------------------------------------------------------
    def _get_robots(self, base_url: str) -> RobotFileParser | None:
        """robots.txt ni yuklaydi va keshlaydi."""
        parsed = urlparse(base_url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        if root in self._robots_cache:
            return self._robots_cache[root]

        rp = RobotFileParser()
        rp.set_url(urljoin(root, "/robots.txt"))
        try:
            rp.read()
        except Exception as exc:  # noqa: BLE001
            log.debug("robots.txt o'qib bo'lmadi ({}): {}", root, exc)
            rp = None
        self._robots_cache[root] = rp  # type: ignore[assignment]
        return rp

    def _allowed(self, url: str) -> bool:
        """robots.txt bo'yicha URL'ga ruxsat borligini tekshiradi."""
        if not CONFIG.scraper.respect_robots:
            return True
        rp = self._get_robots(url)
        if rp is None:
            return True
        return rp.can_fetch(UA_MANAGER.get("chrome"), url)

    # -----------------------------------------------------------------
    def parse_sitemap(self, base_url: str) -> list[str]:
        """sitemap.xml dan URL'larni ajratadi (ichma-ich sitemap'larni ham)."""
        parsed = urlparse(base_url)
        sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
        urls: list[str] = []
        try:
            resp = requests.get(sitemap_url, headers=UA_MANAGER.headers(),
                                timeout=CONFIG.scraper.timeout)
            if resp.status_code != 200:
                return urls
            root = ET.fromstring(resp.content)
            # Namespace'ni e'tiborsiz qoldirib <loc> teglarni topamiz
            for loc in root.iter():
                if loc.tag.endswith("loc") and loc.text:
                    url = loc.text.strip()
                    if url.endswith(".xml"):
                        urls.extend(self._parse_sub_sitemap(url))
                    else:
                        urls.append(url)
        except (requests.RequestException, ET.ParseError) as exc:
            log.debug("Sitemap topilmadi/xato: {}", exc)
        if urls:
            log.info("Sitemap'dan {} ta URL topildi", len(urls))
        return urls

    def _parse_sub_sitemap(self, sitemap_url: str) -> list[str]:
        """Ichki sitemap faylini o'qiydi."""
        urls: list[str] = []
        try:
            resp = requests.get(sitemap_url, headers=UA_MANAGER.headers(),
                                timeout=CONFIG.scraper.timeout)
            root = ET.fromstring(resp.content)
            for loc in root.iter():
                if loc.tag.endswith("loc") and loc.text:
                    urls.append(loc.text.strip())
        except (requests.RequestException, ET.ParseError):
            pass
        return urls

    # -----------------------------------------------------------------
    def crawl(self, start_url: str,
              on_page: Callable[[ScrapeResult, int], None] | None = None
              ) -> Iterator[ScrapeResult]:
        """
        start_url'dan boshlab saytni aylanib chiqadi (generator).

        Args:
            start_url: boshlang'ich manzil.
            on_page: har bir sahifa scrape qilinganda chaqiriladigan callback
                     (result, depth). GUI progress uchun qulay.

        Yields:
            Har bir sahifa uchun ScrapeResult.
        """
        cfg = CONFIG.crawler
        base_domain = urlparse(start_url).netloc

        visited: set[str] = set()
        # (url, depth) juftliklari; BFS uchun deque, DFS uchun stack
        queue: collections.deque[tuple[str, int]] = collections.deque()
        queue.append((start_url, 0))

        # Sitemap'dagi URL'larni ham navbatga qo'shamiz (depth=1)
        if cfg.use_sitemap:
            for url in self.parse_sitemap(start_url):
                if urlparse(url).netloc == base_domain:
                    queue.append((url, 1))

        count = 0
        while queue and count < cfg.max_pages:
            if self.stop_flag():
                log.info("Crawler foydalanuvchi tomonidan to'xtatildi")
                break

            # BFS -> chapdan (popleft), DFS -> o'ngdan (pop)
            url, depth = queue.popleft() if cfg.strategy == "bfs" else queue.pop()

            if url in visited or depth > cfg.max_depth:
                continue
            visited.add(url)

            if not self._allowed(url):
                log.debug("robots.txt taqiqladi: {}", url)
                continue

            result = self.engine.scrape(url)
            count += 1
            if on_page:
                on_page(result, depth)
            yield result

            # Yangi linklarni navbatga qo'shamiz (chuqurlik yetmagan bo'lsa)
            if result.ok and depth < cfg.max_depth:
                links = result.extractor().get_links()
                candidate_links = links["internal"]
                if not cfg.same_domain_only:
                    candidate_links = candidate_links + links["external"]
                for link in candidate_links:
                    if link not in visited:
                        if cfg.same_domain_only and urlparse(link).netloc != base_domain:
                            continue
                        queue.append((link, depth + 1))

        log.info("Crawl yakunlandi: {} ta sahifa qayta ishlandi", count)
