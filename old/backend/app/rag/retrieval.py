"""Hybrid retrieval: dense (Qdrant) + lexical (BM25) fused with RRF."""

from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.ai.router import ModelRouter
from app.domain.entities.conversation import SourceReference
from app.infrastructure.vector.qdrant import QdrantManager, VectorHit

_RRF_K = 60
_DENSE_CANDIDATES = 24
_MIN_DENSE_SCORE = 0.25


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    text: str
    score: float
    source: SourceReference


def _hit_to_chunk(hit: VectorHit, score: float) -> RetrievedChunk:
    payload = hit.payload
    return RetrievedChunk(
        id=hit.id,
        text=str(payload.get("text", "")),
        score=score,
        source=SourceReference(
            title=str(payload.get("law_title") or payload.get("title") or "Manba"),
            url=payload.get("url"),
            article=payload.get("article"),
            snippet=str(payload.get("text", ""))[:300],
            score=score,
        ),
    )


class HybridRetriever:
    def __init__(self, qdrant: QdrantManager, ai_router: ModelRouter):
        self._qdrant = qdrant
        self._ai = ai_router

    async def search(
        self,
        collection: str,
        query: str,
        *,
        limit: int = 6,
        user_id: str | None = None,
    ) -> list[RetrievedChunk]:
        """Dense search first; BM25 re-ranks the dense candidate pool, then
        both rankings are fused with Reciprocal Rank Fusion."""
        query_vector = (await self._ai.embed([query]))[0]
        hits = await self._qdrant.search(
            collection,
            query_vector,
            limit=_DENSE_CANDIDATES,
            user_id=user_id,
            score_threshold=_MIN_DENSE_SCORE,
        )
        if not hits:
            return []

        # Lexical ranking over the candidate pool.
        corpus = [str(h.payload.get("text", "")) for h in hits]
        bm25 = BM25Okapi([doc.lower().split() for doc in corpus])
        lexical_scores = bm25.get_scores(query.lower().split())
        lexical_order = sorted(
            range(len(hits)), key=lambda i: lexical_scores[i], reverse=True
        )

        # RRF fusion of dense rank (hits are already dense-sorted) + lexical rank.
        rrf: dict[int, float] = {}
        for rank, idx in enumerate(range(len(hits))):
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (_RRF_K + rank + 1)
        for rank, idx in enumerate(lexical_order):
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (_RRF_K + rank + 1)

        fused = sorted(rrf.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return [_hit_to_chunk(hits[idx], score) for idx, score in fused]


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Render retrieved chunks as a numbered context block for the LLM."""
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        source = chunk.source
        header = f"[{i}] {source.title}"
        if source.article:
            header += f", {source.article}"
        blocks.append(f"{header}\n{chunk.text}")
    return "\n\n---\n\n".join(blocks)
