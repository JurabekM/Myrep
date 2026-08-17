"""Qdrant vector store client.

Three collections, all multi-tenant safe:
  - legal_uz         : lex.uz law corpus (shared, read-only for users)
  - knowledge_base   : admin-curated KB (shared)
  - user_documents   : per-user uploads — every point carries user_id payload
                       and every search MUST filter by it.
"""

from dataclasses import dataclass, field
from typing import Any

from qdrant_client import AsyncQdrantClient, models

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorCollections:
    LEGAL_UZ = "legal_uz"
    KNOWLEDGE_BASE = "knowledge_base"
    USER_DOCUMENTS = "user_documents"

    ALL = (LEGAL_UZ, KNOWLEDGE_BASE, USER_DOCUMENTS)


@dataclass(frozen=True)
class VectorHit:
    id: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


class QdrantManager:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: AsyncQdrantClient | None = None

    async def connect(self) -> None:
        api_key = self._settings.qdrant_api_key
        self._client = AsyncQdrantClient(
            url=self._settings.qdrant_url,
            api_key=api_key.get_secret_value() if api_key else None,
        )
        await self._ensure_collections()
        logger.info("qdrant_connected", url=self._settings.qdrant_url)

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> AsyncQdrantClient:
        if self._client is None:
            raise RuntimeError("QdrantManager.connect() has not been called")
        return self._client

    async def _ensure_collections(self) -> None:
        dim = self._settings.embedding_dimensions
        for name in VectorCollections.ALL:
            if not await self.client.collection_exists(name):
                await self.client.create_collection(
                    collection_name=name,
                    vectors_config=models.VectorParams(
                        size=dim, distance=models.Distance.COSINE
                    ),
                )
                await self.client.create_payload_index(
                    collection_name=name,
                    field_name="user_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                await self.client.create_payload_index(
                    collection_name=name,
                    field_name="source_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )

    async def upsert(
        self,
        collection: str,
        points: list[tuple[str, list[float], dict[str, Any]]],
    ) -> None:
        await self.client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(id=pid, vector=vector, payload=payload)
                for pid, vector, payload in points
            ],
        )

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        *,
        limit: int = 8,
        user_id: str | None = None,
        extra_filter: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[VectorHit]:
        must: list[models.Condition] = []
        if user_id is not None:
            must.append(
                models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))
            )
        if extra_filter:
            must.extend(
                models.FieldCondition(key=k, match=models.MatchValue(value=v))
                for k, v in extra_filter.items()
            )
        result = await self.client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=limit,
            query_filter=models.Filter(must=must) if must else None,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [
            VectorHit(id=str(p.id), score=p.score, payload=dict(p.payload or {}))
            for p in result.points
        ]

    async def delete_by_source(self, collection: str, source_id: str) -> None:
        await self.client.delete(
            collection_name=collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="source_id", match=models.MatchValue(value=source_id)
                        )
                    ]
                )
            ),
        )
