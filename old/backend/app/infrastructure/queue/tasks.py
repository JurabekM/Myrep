"""Celery tasks. Workers are separate processes, so each task builds its own
async container via a private event loop (asyncio.run)."""

import asyncio

from bson import ObjectId
from celery import shared_task

from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3)
def process_document(self, document_id: str) -> dict:  # type: ignore[no-untyped-def]
    """Extract text from an uploaded document, then index it for RAG."""
    try:
        return asyncio.run(_process_document(document_id))
    except Exception as exc:
        logger.error("process_document_failed", document_id=document_id, error=str(exc))
        raise self.retry(exc=exc)


async def _process_document(document_id: str) -> dict:
    from app.core.dependencies import build_container, shutdown_container
    from app.infrastructure.database.mongo import Collections
    from app.modules.documents.extraction import extract_text
    from app.rag.ingestion import KnowledgeIngestionService

    container = await build_container()
    try:
        coll = container.mongo.collection(Collections.DOCUMENTS)
        doc = await coll.find_one({"_id": ObjectId(document_id)})
        if doc is None:
            return {"status": "missing", "document_id": document_id}
        try:
            data = await container.storage.download(doc["gridfs_id"])
            text = extract_text(doc["filename"], data)
            ingestion = KnowledgeIngestionService(
                container.mongo, container.qdrant, container.ai_router
            )
            chunks = await ingestion.ingest_user_document(
                doc["user_id"], document_id, text, doc["filename"]
            )
            await coll.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"status": "ready", "ocr_text": text, "chunks": chunks}},
            )
            return {"status": "ready", "document_id": document_id, "chunks": chunks}
        except Exception as exc:
            await coll.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"status": "failed", "error": str(exc)[:500]}},
            )
            raise
    finally:
        await shutdown_container(container)


@shared_task
def ingest_lex_url(url: str) -> dict:
    return asyncio.run(_ingest_lex_url(url))


async def _ingest_lex_url(url: str) -> dict:
    from app.core.dependencies import build_container, shutdown_container
    from app.rag.ingestion import KnowledgeIngestionService

    container = await build_container()
    try:
        service = KnowledgeIngestionService(
            container.mongo, container.qdrant, container.ai_router
        )
        return await service.ingest_lex_url(url)
    finally:
        await shutdown_container(container)


@shared_task
def refresh_lex_corpus() -> dict:
    """Re-check every known lex.uz source; unchanged checksums are skipped."""
    return asyncio.run(_refresh_lex_corpus())


async def _refresh_lex_corpus() -> dict:
    from app.core.dependencies import build_container, shutdown_container
    from app.infrastructure.database.mongo import Collections
    from app.rag.ingestion import KnowledgeIngestionService

    container = await build_container()
    try:
        service = KnowledgeIngestionService(
            container.mongo, container.qdrant, container.ai_router
        )
        sources = container.mongo.collection(Collections.KB_SOURCES)
        refreshed = failed = 0
        async for source in sources.find({"type": "lex.uz"}):
            try:
                await service.ingest_lex_url(source["url"])
                refreshed += 1
            except Exception as exc:
                failed += 1
                logger.warning("lex_refresh_failed", url=source["url"], error=str(exc))
        return {"refreshed": refreshed, "failed": failed}
    finally:
        await shutdown_container(container)
