"""Knowledge-base ingestion: lex.uz documents and manual admin uploads.

Fetching respects an allowlist (SSRF guard) and versioning: a document is
re-embedded only when its checksum changes. Heavy work runs in Celery.
"""

import hashlib
import uuid
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.ai.router import ModelRouter
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.infrastructure.database.mongo import Collections, MongoManager
from app.infrastructure.vector.qdrant import QdrantManager, VectorCollections
from app.rag.chunking import Chunk, chunk_legal_text, chunk_recursive

logger = get_logger(__name__)

_ALLOWED_HOSTS = {"lex.uz", "www.lex.uz"}
_EMBED_BATCH = 64


async def fetch_lex_document(url: str) -> tuple[str, str]:
    """Fetch a lex.uz page → (title, plain_text). Only lex.uz hosts allowed."""
    host = httpx.URL(url).host or ""
    if host not in _ALLOWED_HOSTS:
        raise ValidationError("Faqat lex.uz hujjatlariga ruxsat berilgan", details={"url": url})
    async with httpx.AsyncClient(
        timeout=30, follow_redirects=True, headers={"User-Agent": "AIBusinessAdvisorBot/1.0"}
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    title = (soup.title.get_text(strip=True) if soup.title else url)[:300]
    text = soup.get_text(separator="\n", strip=True)
    if len(text) < 200:
        raise ValidationError("Hujjat matni juda qisqa — sahifa yuklanmadi", details={"url": url})
    return title, text


class KnowledgeIngestionService:
    def __init__(self, mongo: MongoManager, qdrant: QdrantManager, ai_router: ModelRouter):
        self._sources = mongo.collection(Collections.KB_SOURCES)
        self._qdrant = qdrant
        self._ai = ai_router

    async def ingest_lex_url(self, url: str) -> dict:
        title, text = await fetch_lex_document(url)
        checksum = hashlib.sha256(text.encode()).hexdigest()

        existing = await self._sources.find_one({"url": url})
        if existing and existing.get("checksum") == checksum:
            return {"status": "unchanged", "url": url, "chunks": existing.get("chunks_count", 0)}

        chunks = chunk_legal_text(text, law_title=title, url=url)
        source_id = str(existing["_id"]) if existing else str(uuid.uuid4())
        await self._replace_vectors(VectorCollections.LEGAL_UZ, source_id, chunks)

        doc = {
            "type": "lex.uz",
            "url": url,
            "title": title,
            "checksum": checksum,
            "chunks_count": len(chunks),
            "updated_at": datetime.now(timezone.utc),
        }
        await self._sources.update_one({"url": url}, {"$set": doc}, upsert=True)
        logger.info("kb_ingested", url=url, chunks=len(chunks))
        return {"status": "ingested", "url": url, "title": title, "chunks": len(chunks)}

    async def ingest_manual_text(self, title: str, text: str) -> dict:
        chunks = chunk_recursive(text, base_metadata={"title": title})
        source_id = str(uuid.uuid4())
        await self._replace_vectors(VectorCollections.KNOWLEDGE_BASE, source_id, chunks)
        await self._sources.insert_one(
            {
                "type": "manual",
                "url": None,
                "title": title,
                "checksum": hashlib.sha256(text.encode()).hexdigest(),
                "chunks_count": len(chunks),
                "source_id": source_id,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        return {"status": "ingested", "title": title, "chunks": len(chunks)}

    async def ingest_user_document(self, user_id: str, document_id: str, text: str, title: str) -> int:
        chunks = chunk_recursive(text, base_metadata={"title": title})
        await self._replace_vectors(
            VectorCollections.USER_DOCUMENTS, document_id, chunks, user_id=user_id
        )
        return len(chunks)

    async def _replace_vectors(
        self,
        collection: str,
        source_id: str,
        chunks: list[Chunk],
        *,
        user_id: str | None = None,
    ) -> None:
        await self._qdrant.delete_by_source(collection, source_id)
        for start in range(0, len(chunks), _EMBED_BATCH):
            batch = chunks[start : start + _EMBED_BATCH]
            vectors = await self._ai.embed([c.text for c in batch])
            points = [
                (
                    str(uuid.uuid4()),
                    vector,
                    {
                        "text": chunk.text,
                        "chunk_index": chunk.index,
                        "source_id": source_id,
                        **({"user_id": user_id} if user_id else {}),
                        **{k: v for k, v in chunk.metadata.items() if v is not None},
                    },
                )
                for chunk, vector in zip(batch, vectors)
            ]
            await self._qdrant.upsert(collection, points)
