# -*- coding: utf-8 -*-
"""
browser/renderer.py
===================
Brauzer asosidagi renderlash (JavaScript, SPA, AJAX, Infinite Scroll).

Playwright (sync API) ishlatiladi. Cloudflare himoyasi kuchli bo'lgan
saytlar uchun `undetected-chromedriver` (Selenium) zaxira sifatida
mavjud.

Barcha brauzer bog'liqliklari "lazy import" qilinadi — ya'ni kutubxona
o'rnatilmagan bo'lsa ham platformaning qolgan qismi ishlashda davom
etadi.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import CONFIG
from proxy.proxy_manager import PROXY_MANAGER
from proxy.user_agent import UA_MANAGER
from logs.logger import get_logger

log = get_logger(__name__)


@dataclass
class RenderResult:
    """Renderlash natijasi."""
    html: str
    status_code: int
    final_url: str
    xhr_requests: list[str]  # aniqlangan AJAX/XHR endpointlar


class PlaywrightRenderer:
    """Playwright orqali sahifani to'liq (JS bilan) renderlaydi."""

    def __init__(self) -> None:
        self._available = self._check()

    @staticmethod
    def _check() -> bool:
        try:
            import playwright  # noqa: F401
            return True
        except ImportError:
            log.warning("Playwright o'rnatilmagan. 'playwright install' ni bajaring.")
            return False

    @property
    def available(self) -> bool:
        return self._available

    def render(self, url: str, wait: float | None = None,
               infinite_scroll: bool = False, timeout: int | None = None) -> RenderResult:
        """
        URL'ni Playwright bilan yuklaydi va yakuniy HTML'ni qaytaradi.

        Args:
            url: yuklanadigan manzil.
            wait: JS render tugashini kutish vaqti (sekund).
            infinite_scroll: True bo'lsa sahifani oxirigacha scroll qiladi.
            timeout: sahifa yuklanish timeout (sekund).
        """
        from playwright.sync_api import sync_playwright

        wait = wait if wait is not None else CONFIG.scraper.render_wait
        timeout_ms = int((timeout or CONFIG.scraper.timeout) * 1000)
        xhr_requests: list[str] = []

        launch_args: dict = {"headless": True}
        proxy_raw = PROXY_MANAGER.get_raw()
        if proxy_raw:
            launch_args["proxy"] = {"server": proxy_raw}

        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_args)
            context = browser.new_context(
                user_agent=UA_MANAGER.random(),
                ignore_https_errors=not CONFIG.scraper.verify_ssl,
            )
            page = context.new_page()

            # AJAX/XHR so'rovlarni kuzatib boramiz (API endpointlarni aniqlash)
            def _on_request(request):
                if request.resource_type in ("xhr", "fetch"):
                    xhr_requests.append(request.url)

            page.on("request", _on_request)

            status_code = 0
            try:
                response = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                status_code = response.status if response else 0
                page.wait_for_timeout(int(wait * 1000))

                if infinite_scroll:
                    self._do_infinite_scroll(page)

                html = page.content()
                final_url = page.url
            finally:
                context.close()
                browser.close()

        return RenderResult(
            html=html,
            status_code=status_code,
            final_url=final_url,
            xhr_requests=sorted(set(xhr_requests)),
        )

    @staticmethod
    def _do_infinite_scroll(page) -> None:
        """Sahifani balandligi o'zgarmaguncha pastga scroll qiladi."""
        max_scroll = CONFIG.scraper.max_scroll
        pause_ms = int(CONFIG.scraper.scroll_pause * 1000)
        last_height = page.evaluate("document.body.scrollHeight")
        for i in range(max_scroll):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(pause_ms)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                log.debug("Infinite scroll tugadi ({} marta)", i + 1)
                break
            last_height = new_height


class UndetectedRenderer:
    """
    undetected-chromedriver orqali kuchli Cloudflare himoyasini aylanib
    o'tish uchun zaxira renderer.
    """

    def __init__(self) -> None:
        self._available = self._check()

    @staticmethod
    def _check() -> bool:
        try:
            import undetected_chromedriver  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def available(self) -> bool:
        return self._available

    def render(self, url: str, wait: float | None = None) -> RenderResult:
        """URL'ni undetected-chromedriver bilan yuklaydi."""
        import undetected_chromedriver as uc

        wait = wait if wait is not None else CONFIG.scraper.render_wait
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument(f"--user-agent={UA_MANAGER.random()}")

        driver = uc.Chrome(options=options)
        try:
            driver.set_page_load_timeout(CONFIG.scraper.timeout)
            driver.get(url)
            import time
            time.sleep(wait)
            html = driver.page_source
            final_url = driver.current_url
        finally:
            driver.quit()

        return RenderResult(html=html, status_code=200, final_url=final_url, xhr_requests=[])


# Global singletonlar
PLAYWRIGHT_RENDERER = PlaywrightRenderer()
UNDETECTED_RENDERER = UndetectedRenderer()
