"""RAG qidiruv fasadi — chunklarni topib, kontekst va manbalarni qaytaradi."""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.vector_store import SearchHit, VectorStore

COLLECTION_LEGAL = "legal"
COLLECTION_KNOWLEDGE = "knowledge"
COLLECTION_USER_DOC = "user_doc"


@dataclass
class Source:
    title: str
    url: str | None
    article: str | None
    snippet: str
    score: float

    def to_dict(self) -> dict:
        return {
            "title": self.title, "url": self.url, "article": self.article,
            "snippet": self.snippet, "score": round(self.score, 3),
        }


@dataclass
class RetrievalResult:
    context: str
    sources: list[Source]

    @property
    def has_context(self) -> bool:
        return bool(self.sources)


class Retriever:
    def __init__(self, vector_store: VectorStore):
        self._store = vector_store

    def retrieve(
        self, collection: str, query: str, *, top_k: int = 6, min_score: float = 0.05
    ) -> RetrievalResult:
        hits = self._store.search(collection, query, top_k=top_k, min_score=min_score)
        sources = [_hit_to_source(h) for h in hits]
        return RetrievalResult(context=_format_context(hits), sources=sources)


def _hit_to_source(hit: SearchHit) -> Source:
    chunk = hit.chunk
    return Source(
        title=chunk.title or "Manba",
        url=chunk.url,
        article=chunk.article,
        snippet=chunk.text[:300],
        score=hit.score,
    )


def _format_context(hits: list[SearchHit]) -> str:
    blocks = []
    for i, hit in enumerate(hits, start=1):
        chunk = hit.chunk
        header = f"[{i}] {chunk.title or 'Manba'}"
        if chunk.article:
            header += f", {chunk.article}"
        blocks.append(f"{header}\n{chunk.text}")
    return "\n\n---\n\n".join(blocks)
