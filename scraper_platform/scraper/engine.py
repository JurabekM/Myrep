# -*- coding: utf-8 -*-
"""
scraper/engine.py
=================
Asosiy scraping dvigateli. Sayt turini AVTOMATIK aniqlaydi va mos
strategiyani tanlaydi:

    1. Oddiy statik HTML   -> requests (Fetcher)
    2. JavaScript / SPA    -> Playwright renderer
    3. Cloudflare himoyasi -> cloudscraper -> undetected-chromedriver
    4. Infinite scroll     -> Playwright + avtomatik scroll
    5. AJAX/XHR            -> Playwright orqali XHR endpointlarni aniqlash

Aniqlash bosqichlari:
    - Avval yengil requests bilan urinadi
    - Cloudflare belgilarini (challenge sahifasi) tekshiradi
    - JS talab qilinishini (kam kontent, ko'p <script>) baholaydi
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from config.settings import CONFIG
from scraper.fetcher import Fetcher, FetchResult
from browser.renderer import PLAYWRIGHT_RENDERER, UNDETECTED_RENDERER
from parsers.extractor import Extractor
from logs.logger import get_logger

log = get_logger(__name__)

# Cloudflare / anti-bot challenge belgilarini aniqlash uchun namunalar
_CLOUDFLARE_MARKERS = (
    "cf-browser-verification", "cf_chl_", "Checking your browser",
    "Just a moment", "__cf_chl_", "cloudflare",
)


@dataclass
class ScrapeResult:
    """Bitta sahifani scrape qilish natijasi."""
    url: str
    final_url: str
    status_code: int
    engine_used: str
    html: str
    content_type: str
    response_time: float
    ok: bool
    error: str = ""
    xhr_endpoints: list[str] = field(default_factory=list)

    def extractor(self) -> Extractor:
        """Ushbu sahifaning HTML'i uchun Extractor obyektini qaytaradi."""
        return Extractor(self.html, base_url=self.final_url or self.url)


class ScraperEngine:
    """Sayt turini aniqlab, mos usulda sahifani yuklovchi dvigatel."""

    def __init__(self, engine: str | None = None) -> None:
        # engine: auto | requests | httpx | playwright | cloudscraper
        self.engine = engine or CONFIG.scraper.default_engine
        self.fetcher = Fetcher()
        self._cloudscraper = None

    # -----------------------------------------------------------------
    # Aniqlash yordamchilari
    # -----------------------------------------------------------------
    @staticmethod
    def _is_cloudflare(result: FetchResult) -> bool:
        """Javob Cloudflare challenge sahifasi ekanligini aniqlaydi."""
        if result.status_code in (403, 503):
            body = result.html.lower()
            return any(m.lower() in body for m in _CLOUDFLARE_MARKERS)
        return False

    @staticmethod
    def _needs_js(result: FetchResult) -> bool:
        """
        Sahifa JS render talab qiladimi, buni evristik baholaydi:
        - juda kam matn kontenti bo'lsa
        - ko'p <script> teg va kam <p>/<div> matn bo'lsa
        - umumiy SPA belgilaridan biri bo'lsa (root div, app-root)
        """
        if not result.html:
            return False
        html = result.html
        text = re.sub(r"<[^>]+>", " ", html)
        text_len = len(text.strip())
        script_count = html.lower().count("<script")

        # SPA freymvork belgilari
        spa_markers = ('id="root"', 'id="app"', "ng-app", "data-reactroot",
                       "__NEXT_DATA__", "window.__NUXT__", "v-app")
        has_spa = any(m in html for m in spa_markers)

        # Juda kam matn + ko'p script yoki SPA marker -> JS kerak
        if has_spa and text_len < 2000:
            return True
        if text_len < 500 and script_count > 3:
            return True
        return False

    def _get_cloudscraper(self):
        """cloudscraper sessiyasini lazy tarzda yaratadi."""
        if self._cloudscraper is None:
            try:
                import cloudscraper
                self._cloudscraper = cloudscraper.create_scraper()
            except ImportError:
                log.warning("cloudscraper o'rnatilmagan")
                self._cloudscraper = False
        return self._cloudscraper

    # -----------------------------------------------------------------
    # Alohida strategiyalar
    # -----------------------------------------------------------------
    def _scrape_requests(self, url: str) -> ScrapeResult:
        """Statik HTML uchun requests strategiyasi."""
        r = self.fetcher.fetch(url)
        return ScrapeResult(
            url=url, final_url=r.final_url, status_code=r.status_code,
            engine_used="requests", html=r.html, content_type=r.content_type,
            response_time=r.response_time, ok=r.ok, error=r.error,
        )

    def _scrape_cloudscraper(self, url: str) -> ScrapeResult:
        """Cloudflare uchun cloudscraper strategiyasi."""
        scraper = self._get_cloudscraper()
        if not scraper:
            # cloudscraper yo'q bo'lsa undetected-chromedriver ga o'tamiz
            return self._scrape_undetected(url)
        try:
            resp = scraper.get(url, timeout=CONFIG.scraper.timeout)
            return ScrapeResult(
                url=url, final_url=resp.url, status_code=resp.status_code,
                engine_used="cloudscraper", html=resp.text,
                content_type=resp.headers.get("Content-Type", ""),
                response_time=resp.elapsed.total_seconds(),
                ok=resp.status_code < 400,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("cloudscraper muvaffaqiyatsiz, undetected-ga o'tamiz: {}", exc)
            return self._scrape_undetected(url)

    def _scrape_undetected(self, url: str) -> ScrapeResult:
        """Kuchli himoya uchun undetected-chromedriver strategiyasi."""
        if not UNDETECTED_RENDERER.available:
            return ScrapeResult(
                url=url, final_url=url, status_code=0, engine_used="undetected",
                html="", content_type="", response_time=0.0, ok=False,
                error="undetected-chromedriver mavjud emas",
            )
        try:
            res = UNDETECTED_RENDERER.render(url)
            return ScrapeResult(
                url=url, final_url=res.final_url, status_code=res.status_code,
                engine_used="undetected", html=res.html, content_type="text/html",
                response_time=0.0, ok=bool(res.html),
            )
        except Exception as exc:  # noqa: BLE001
            return ScrapeResult(
                url=url, final_url=url, status_code=0, engine_used="undetected",
                html="", content_type="", response_time=0.0, ok=False, error=str(exc),
            )

    def _scrape_playwright(self, url: str, infinite_scroll: bool = False) -> ScrapeResult:
        """JS/SPA/AJAX uchun Playwright strategiyasi."""
        if not PLAYWRIGHT_RENDERER.available:
            log.warning("Playwright yo'q, requests bilan urinamiz")
            return self._scrape_requests(url)
        try:
            res = PLAYWRIGHT_RENDERER.render(url, infinite_scroll=infinite_scroll)
            return ScrapeResult(
                url=url, final_url=res.final_url, status_code=res.status_code,
                engine_used="playwright", html=res.html, content_type="text/html",
                response_time=0.0, ok=bool(res.html), xhr_endpoints=res.xhr_requests,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Playwright xatoligi {}: {}", url, exc)
            return ScrapeResult(
                url=url, final_url=url, status_code=0, engine_used="playwright",
                html="", content_type="", response_time=0.0, ok=False, error=str(exc),
            )

    # -----------------------------------------------------------------
    # Asosiy kirish nuqtasi
    # -----------------------------------------------------------------
    def scrape(self, url: str, infinite_scroll: bool = False) -> ScrapeResult:
        """
        URL'ni scrape qiladi. `engine=auto` bo'lsa turini avtomatik aniqlaydi.

        Args:
            url: yuklanadigan manzil.
            infinite_scroll: True bo'lsa Playwright bilan scroll qilinadi.
        """
        # Foydalanuvchi aniq dvigatel tanlagan bo'lsa
        if self.engine == "playwright":
            return self._scrape_playwright(url, infinite_scroll)
        if self.engine == "cloudscraper":
            return self._scrape_cloudscraper(url)
        if self.engine in ("requests", "httpx"):
            return self._scrape_requests(url)

        # ---- AUTO rejimi ----
        log.debug("AUTO aniqlash: {}", url)
        result = self._scrape_requests(url)

        # 1) Cloudflare?
        if self._is_cloudflare(result):
            log.info("Cloudflare aniqlandi -> cloudscraper: {}", url)
            return self._scrape_cloudscraper(url)

        # 2) So'rov muvaffaqiyatsiz yoki JS kerakmi?
        if not result.ok or self._needs_js(result):
            if PLAYWRIGHT_RENDERER.available:
                log.info("JS render kerak -> Playwright: {}", url)
                return self._scrape_playwright(url, infinite_scroll)

        return result

    def close(self) -> None:
        """Resurslarni tozalaydi."""
        self.fetcher.close()
