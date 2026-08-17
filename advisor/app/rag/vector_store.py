"""Lokal vektor qidiruv — TF-IDF + kosinus o'xshashligi.

Docker/tashqi vektor bazasi (Qdrant, Chroma serveri) TALAB ETILMAYDI. Chunklar
SQLite'da (``kb_chunks``) saqlanadi; qidiruv paytida ular xotiraga o'qilib,
scikit-learn TF-IDF matritsasi quriladi va kosinus o'xshashligi hisoblanadi.

O'zbek/rus matni uchun so'z-darajali n-gram (1,2) + belgi-darajali fallback
ishlatiladi, bu morfologik boy tillarda qisman moslikni yaxshilaydi. Matritsa
kolleksiya bo'yicha keshlanadi va chunklar soni o'zgarganda qayta quriladi.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.logging_setup import get_logger
from app.data.repositories.kb_repo import KBChunk, KBRepository

logger = get_logger(__name__)


@dataclass
class SearchHit:
    chunk: KBChunk
    score: float


class _CollectionIndex:
    """Bitta kolleksiya uchun keshlangan TF-IDF matritsasi."""

    def __init__(self, chunks: list[KBChunk]):
        self.chunks = chunks
        # Belgi-darajali n-gram (char_wb) — o'zbek/rus morfologiyasida o'zak
        # o'zgarishlarini qamrab oladi ("ulush" ↔ "ulushni", "sotish" ↔ "sotishi").
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=1,
            sublinear_tf=True,
        )
        self._matrix = None
        corpus = [c.text for c in chunks]
        if corpus:
            try:
                self._matrix = self._vectorizer.fit_transform(corpus)
            except ValueError:
                # "empty vocabulary" — korpus faqat stop-so'zlardan iborat;
                # qidiruv baribir bo'sh natija qaytaradi.
                self._matrix = None

    def search(self, query: str, top_k: int, min_score: float) -> list[SearchHit]:
        if not self.chunks or self._matrix is None:
            return []
        try:
            query_vec = self._vectorizer.transform([query])
        except ValueError:
            return []
        scores = cosine_similarity(query_vec, self._matrix)[0]
        top_indices = np.argsort(scores)[::-1][:top_k]
        hits = [
            SearchHit(chunk=self.chunks[i], score=float(scores[i]))
            for i in top_indices
            if scores[i] >= min_score
        ]
        return hits


class VectorStore:
    """Kolleksiya bo'yicha indekslarni boshqaradi (lazy + kesh)."""

    def __init__(self, kb_repo: KBRepository):
        self._kb = kb_repo
        self._indexes: dict[str, _CollectionIndex] = {}
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()

    def invalidate(self, collection: str) -> None:
        with self._lock:
            self._indexes.pop(collection, None)
            self._counts.pop(collection, None)

    def _get_index(self, collection: str) -> _CollectionIndex:
        current_count = self._kb.count(collection)
        with self._lock:
            cached = self._indexes.get(collection)
            if cached is not None and self._counts.get(collection) == current_count:
                return cached
            logger.info(
                "Vektor indeks qurilmoqda: %s (%d chunk)", collection, current_count
            )
            chunks = self._kb.get_collection(collection)
            index = _CollectionIndex(chunks)
            self._indexes[collection] = index
            self._counts[collection] = current_count
            return index

    def search(
        self,
        collection: str,
        query: str,
        *,
        top_k: int = 6,
        min_score: float = 0.05,
    ) -> list[SearchHit]:
        if not query.strip():
            return []
        return self._get_index(collection).search(query, top_k, min_score)
