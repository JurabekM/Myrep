# -*- coding: utf-8 -*-
"""
scraper/fetcher.py
==================
Past darajali HTTP fetcher. Bitta URL'ni yuklaydi va retry, proxy,
user-agent, timeout mexanizmlarini qo'llaydi.

`tenacity` orqali quyidagi xatoliklarda avtomatik qayta urinadi:
    - Timeout
    - Connection error
    - DNS error
    - HTTP 429 (Too Many Requests)
    - HTTP 5xx (server xatoliklari)
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

from config.settings import CONFIG
from proxy.proxy_manager import PROXY_MANAGER
from proxy.user_agent import UA_MANAGER
from logs.logger import get_logger

log = get_logger(__name__)


class RetryableError(Exception):
    """Qayta urinishga arziydigan xatolik (429, 5xx)."""


@dataclass
class FetchResult:
    """HTTP so'rov natijasi."""
    url: str
    final_url: str
    status_code: int
    html: str
    content_type: str
    response_time: float
    ok: bool
    error: str = ""
    raw_content: bytes = b""


class Fetcher:
    """requests asosidagi HTTP klient (retry + proxy + UA bilan)."""

    def __init__(self) -> None:
        self.session = requests.Session()

    def _fetch_once(self, url: str) -> requests.Response:
        """Bitta so'rov yuboradi (retry dekoratori tashqarida qo'llanadi)."""
        headers = UA_MANAGER.headers()
        proxies = PROXY_MANAGER.get_proxy()
        resp = self.session.get(
            url,
            headers=headers,
            proxies=proxies,
            timeout=CONFIG.scraper.timeout,
            verify=CONFIG.scraper.verify_ssl,
            allow_redirects=CONFIG.scraper.follow_redirects,
        )
        # 429 va 5xx larni qayta urinish uchun exception ko'taramiz
        if resp.status_code == 429 or resp.status_code >= 500:
            raise RetryableError(f"HTTP {resp.status_code}")
        return resp

    def fetch(self, url: str) -> FetchResult:
        """
        URL'ni yuklaydi, kerak bo'lsa qayta urinadi.

        Returns:
            FetchResult obyekti (muvaffaqiyat yoki xatolik bilan).
        """
        start = time.perf_counter()

        # tenacity retry mexanizmini dinamik konfiguratsiya bilan quramiz
        retryer = retry(
            stop=stop_after_attempt(CONFIG.scraper.max_retries),
            wait=wait_exponential(multiplier=CONFIG.scraper.retry_backoff, min=1, max=30),
            retry=retry_if_exception_type(
                (RetryableError, requests.Timeout, requests.ConnectionError)
            ),
            reraise=True,
        )

        try:
            if CONFIG.scraper.request_delay > 0:
                time.sleep(CONFIG.scraper.request_delay)
            resp = retryer(self._fetch_once)(url)
            elapsed = time.perf_counter() - start
            content_type = resp.headers.get("Content-Type", "")
            # Matnli kontent bo'lsagina html sifatida o'qiymiz
            text = resp.text if "text" in content_type or "html" in content_type \
                or "json" in content_type or "xml" in content_type else ""
            return FetchResult(
                url=url,
                final_url=resp.url,
                status_code=resp.status_code,
                html=text,
                content_type=content_type,
                response_time=round(elapsed, 3),
                ok=resp.status_code < 400,
                raw_content=resp.content,
            )
        except (RetryError, requests.RequestException, RetryableError) as exc:
            elapsed = time.perf_counter() - start
            log.error("Fetch xatoligi {}: {}", url, exc)
            return FetchResult(
                url=url, final_url=url, status_code=0, html="",
                content_type="", response_time=round(elapsed, 3),
                ok=False, error=str(exc),
            )

    def close(self) -> None:
        """Sessiyani yopadi."""
        self.session.close()
