"""Document upload + AI analysis endpoints.

Upload stores the file in GridFS and dispatches extraction/indexing to
Celery; analysis endpoints operate on the extracted text.
"""

from datetime import datetime, timezone
from enum import StrEnum

from bson import ObjectId
from fastapi import APIRouter, UploadFile, status
from pydantic import BaseModel, Field

from app.ai.base import ChatMessage, ChatRole, CompletionRequest
from app.core.dependencies import Container, CurrentUser
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.database.mongo import Collections

router = APIRouter(prefix="/documents", tags=["documents"])


class AnalysisTask(StrEnum):
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    EXPLAIN = "explain"
    RISKS = "risks"
    SUGGESTIONS = "suggestions"
    EXTRACT = "extract"
    CLASSIFY = "classify"


_TASK_PROMPTS: dict[AnalysisTask, str] = {
    AnalysisTask.SUMMARIZE: "Hujjatning tuzilmali xulosasini yoz (asosiy punktlar, raqamlar).",
    AnalysisTask.TRANSLATE: "Hujjatni {target_lang} tiliga professional tarjima qil.",
    AnalysisTask.EXPLAIN: "Hujjatni oddiy tilda, band-band tushuntir.",
    AnalysisTask.RISKS: "Hujjatdagi risklarni aniqla: risk, darajasi (yuqori/o'rta/past), izoh.",
    AnalysisTask.SUGGESTIONS: "Hujjatni yaxshilash bo'yicha aniq takliflar ber.",
    AnalysisTask.EXTRACT: "Hujjatdan tuzilmali ma'lumot ajrat: tomonlar, sanalar, summalar, muddatlar, majburiyatlar — JSON.",
    AnalysisTask.CLASSIFY: "Hujjat turini aniqla (shartnoma/hisobot/ariza/...) va qisqa asosla.",
}


class AnalyzeRequest(BaseModel):
    document_id: str
    task: AnalysisTask
    target_lang: str = Field(default="uz", max_length=10)
    model: str | None = None


class CompareRequest(BaseModel):
    document_id_a: str
    document_id_b: str
    model: str | None = None


class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    size: int
    created_at: datetime


async def _get_document(container, document_id: str, user_id: str) -> dict:  # type: ignore[no-untyped-def]
    doc = await container.mongo.collection(Collections.DOCUMENTS).find_one(
        {"_id": ObjectId(document_id), "user_id": user_id}
    )
    if doc is None:
        raise NotFoundError("Hujjat topilmadi")
    return doc


def _require_text(doc: dict) -> str:
    if doc.get("status") != "ready" or not doc.get("ocr_text"):
        raise ValidationError(
            "Hujjat hali qayta ishlanmoqda yoki matn ajratilmagan",
            details={"status": doc.get("status")},
        )
    return str(doc["ocr_text"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload(file: UploadFile, user: CurrentUser, container: Container) -> DocumentResponse:
    data = await file.read()
    stored = await container.storage.upload(
        file.filename or "document", data, file.content_type or "application/octet-stream",
        user_id=user.id,
    )
    now = datetime.now(timezone.utc)
    result = await container.mongo.collection(Collections.DOCUMENTS).insert_one(
        {
            "user_id": user.id,
            "gridfs_id": stored.file_id,
            "filename": stored.filename,
            "content_type": stored.content_type,
            "size": stored.size,
            "status": "processing",
            "ocr_text": None,
            "created_at": now,
        }
    )
    document_id = str(result.inserted_id)
    from app.infrastructure.queue.tasks import process_document

    process_document.delay(document_id)
    return DocumentResponse(
        id=document_id, filename=stored.filename, status="processing",
        size=stored.size, created_at=now,
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(user: CurrentUser, container: Container) -> list[DocumentResponse]:
    cursor = (
        container.mongo.collection(Collections.DOCUMENTS)
        .find({"user_id": user.id})
        .sort("created_at", -1)
        .limit(100)
    )
    return [
        DocumentResponse(
            id=str(d["_id"]), filename=d["filename"], status=d["status"],
            size=d["size"], created_at=d["created_at"],
        )
        async for d in cursor
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, user: CurrentUser, container: Container) -> DocumentResponse:
    doc = await _get_document(container, document_id, user.id)
    return DocumentResponse(
        id=str(doc["_id"]), filename=doc["filename"], status=doc["status"],
        size=doc["size"], created_at=doc["created_at"],
    )


@router.post("/analyze")
async def analyze(req: AnalyzeRequest, user: CurrentUser, container: Container) -> dict:
    doc = await _get_document(container, req.document_id, user.id)
    text = _require_text(doc)
    system = await container.prompts.get("module.documents")
    instruction = _TASK_PROMPTS[req.task].format(target_lang=req.target_lang)
    response = await container.ai_router.complete(
        CompletionRequest(
            messages=(
                ChatMessage(role=ChatRole.SYSTEM, content=system),
                ChatMessage(
                    role=ChatRole.USER,
                    content=f"{instruction}\n\nHujjat ({doc['filename']}):\n{text[:100_000]}",
                ),
            ),
            model="documents",
            temperature=0.2,
            max_tokens=6000,
            json_mode=req.task is AnalysisTask.EXTRACT,
        ),
        model_id=req.model,
        user_id=user.id,
        module="documents",
    )
    return {"task": req.task, "document_id": req.document_id, "result": response.content}


@router.post("/compare")
async def compare(req: CompareRequest, user: CurrentUser, container: Container) -> dict:
    doc_a = await _get_document(container, req.document_id_a, user.id)
    doc_b = await _get_document(container, req.document_id_b, user.id)
    text_a, text_b = _require_text(doc_a), _require_text(doc_b)
    system = await container.prompts.get("module.documents")
    response = await container.ai_router.complete(
        CompletionRequest(
            messages=(
                ChatMessage(role=ChatRole.SYSTEM, content=system),
                ChatMessage(
                    role=ChatRole.USER,
                    content=(
                        "Ikki hujjatni taqqosla: umumiy jihatlar, farqlar (jadval), "
                        "qaysi biri qulayroq va nima uchun.\n\n"
                        f"HUJJAT A ({doc_a['filename']}):\n{text_a[:50_000]}\n\n"
                        f"HUJJAT B ({doc_b['filename']}):\n{text_b[:50_000]}"
                    ),
                ),
            ),
            model="documents",
            temperature=0.2,
            max_tokens=5000,
        ),
        model_id=req.model,
        user_id=user.id,
        module="documents",
    )
    return {"result": response.content}
