"""Lex.uz hujjatlarini yuklab olish (scraping).

Lex.uz — O'zbekiston qonunchiligining ochiq davlat portali. Faqat lex.uz
xostlariga ruxsat beriladi (SSRF himoyasi). Yuklangan matn chunklarга ajratilib,
lokal RAG bazasiga (``kb_chunks``, ``legal`` kolleksiyasi) joylashtiriladi.
"""

from __future__ import annotations

import hashlib

import httpx
from bs4 import BeautifulSoup

from app.core.exceptions import ScraperError
from app.core.logging_setup import get_logger
from app.data.repositories.kb_repo import KBRepository
from app.rag.chunking import chunk_legal_text
from app.rag.retriever import COLLECTION_LEGAL
from app.rag.vector_store import VectorStore

logger = get_logger(__name__)

_ALLOWED_HOSTS = {"lex.uz", "www.lex.uz"}
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "AIBusinessAdvisor/2.0"
    )
}


class LexScraper:
    def __init__(self, kb_repo: KBRepository, vector_store: VectorStore):
        self._kb = kb_repo
        self._store = vector_store

    def fetch(self, url: str) -> tuple[str, str]:
        """(sarlavha, toza matn) qaytaradi. Faqat lex.uz'ga ruxsat."""
        host = httpx.URL(url).host or ""
        if host not in _ALLOWED_HOSTS:
            raise ScraperError(f"Faqat lex.uz hujjatlariga ruxsat berilgan: {url}")
        try:
            with httpx.Client(
                timeout=30, follow_redirects=True, headers=_HEADERS
            ) as client:
                response = client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ScraperError(f"Lex.uz yuklab bo'lmadi: {exc}") from exc

        soup = BeautifulSoup(response.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        title = (soup.title.get_text(strip=True) if soup.title else url)[:300]
        text = soup.get_text(separator="\n", strip=True)
        if len(text) < 200:
            raise ScraperError(
                "Hujjat matni juda qisqa — sahifa to'liq yuklanmadi yoki bo'sh"
            )
        return title, text

    def ingest_url(self, url: str) -> dict:
        """Lex.uz hujjatini yuklab, chunklab, RAG bazasiga qo'shadi."""
        title, text = self.fetch(url)
        source_id = hashlib.sha256(url.encode()).hexdigest()[:16]
        chunks = chunk_legal_text(text, law_title=title, url=url)
        payload = [
            {"text": c.text, "article": c.metadata.get("article"), "chunk_index": c.index}
            for c in chunks
        ]
        count = self._kb.add_chunks(
            COLLECTION_LEGAL, source_id, payload, title=title, url=url
        )
        self._store.invalidate(COLLECTION_LEGAL)
        logger.info("Lex.uz hujjat indekslandi: %s (%d chunk)", title, count)
        return {"title": title, "url": url, "chunks": count}

    def ingest_manual_text(self, title: str, text: str, url: str | None = None) -> dict:
        """Qo'lda kiritilgan qonun/hujjat matnini indekslaydi (internetsiz)."""
        source_id = hashlib.sha256((url or title).encode()).hexdigest()[:16]
        chunks = chunk_legal_text(text, law_title=title, url=url)
        payload = [
            {"text": c.text, "article": c.metadata.get("article"), "chunk_index": c.index}
            for c in chunks
        ]
        count = self._kb.add_chunks(
            COLLECTION_LEGAL, source_id, payload, title=title, url=url
        )
        self._store.invalidate(COLLECTION_LEGAL)
        return {"title": title, "url": url, "chunks": count}
