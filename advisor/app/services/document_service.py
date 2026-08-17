"""Hujjat servisi — yuklash, matn ajratish, AI tahlil."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from app.ai.base import ChatMessage, CompletionRequest, Role
from app.ai.prompts import build_system_prompt
from app.ai.router import ModelRouter
from app.core.config import BusinessProfile
from app.core.exceptions import NotFoundError, ValidationError
from app.data.repositories.document_repo import Document, DocumentRepository
from app.services.document_extractor import extract_text


class AnalysisTask(str, Enum):
    SUMMARIZE = "summarize"
    EXPLAIN = "explain"
    RISKS = "risks"
    SUGGESTIONS = "suggestions"
    TRANSLATE = "translate"
    EXTRACT = "extract"
    CLASSIFY = "classify"


TASK_LABELS: dict[AnalysisTask, str] = {
    AnalysisTask.SUMMARIZE: "Xulosa",
    AnalysisTask.EXPLAIN: "Tushuntirish",
    AnalysisTask.RISKS: "Risklar",
    AnalysisTask.SUGGESTIONS: "Takliflar",
    AnalysisTask.TRANSLATE: "Tarjima",
    AnalysisTask.EXTRACT: "Ma'lumot ajratish",
    AnalysisTask.CLASSIFY: "Turini aniqlash",
}

_TASK_PROMPTS: dict[AnalysisTask, str] = {
    AnalysisTask.SUMMARIZE: "Hujjatning tuzilmali xulosasini yoz (asosiy punktlar, raqamlar).",
    AnalysisTask.EXPLAIN: "Hujjatni oddiy tilda, band-band tushuntir.",
    AnalysisTask.RISKS: "Hujjatdagi risklarni aniqla: risk, darajasi, izoh.",
    AnalysisTask.SUGGESTIONS: "Hujjatni yaxshilash bo'yicha aniq takliflar ber.",
    AnalysisTask.TRANSLATE: "Hujjatni {target_lang} tiliga professional tarjima qil.",
    AnalysisTask.EXTRACT: "Hujjatdan tuzilmali ma'lumot ajrat: tomonlar, sanalar, summalar, majburiyatlar.",
    AnalysisTask.CLASSIFY: "Hujjat turini aniqla va qisqa asosla.",
}


class DocumentService:
    def __init__(
        self, documents: DocumentRepository, router: ModelRouter, profile: BusinessProfile
    ):
        self._documents = documents
        self._router = router
        self._profile = profile

    def upload(self, file_path: str) -> Document:
        path = Path(file_path)
        if not path.exists():
            raise ValidationError(f"Fayl topilmadi: {file_path}")
        size = path.stat().st_size
        return self._documents.create(
            path.name, str(path), _guess_type(path.suffix), size
        )

    def process(self, document_id: int) -> Document:
        """Matn ajratadi va holatni yangilaydi (fon workerida chaqiriladi)."""
        document = self._documents.get(document_id)
        if document is None:
            raise NotFoundError("Hujjat topilmadi")
        try:
            data = Path(document.path).read_bytes()
            text = extract_text(document.filename, data)
            self._documents.mark_ready(document_id, text)
        except Exception as exc:
            self._documents.mark_failed(document_id, str(exc))
            raise
        return self._documents.get(document_id)  # type: ignore[return-value]

    def list_documents(self) -> list[Document]:
        return self._documents.list_all()

    def analyze(self, document_id: int, task: AnalysisTask, target_lang: str = "uz") -> str:
        document = self._documents.get(document_id)
        if document is None:
            raise NotFoundError("Hujjat topilmadi")
        if document.status != "ready" or not document.extracted_text:
            raise ValidationError("Hujjat hali qayta ishlanmagan yoki matn ajratilmagan")

        system = build_system_prompt("documents", self._profile)
        instruction = _TASK_PROMPTS[task].format(target_lang=target_lang)
        result = self._router.complete(
            CompletionRequest(
                messages=(
                    ChatMessage(Role.SYSTEM, system),
                    ChatMessage(
                        Role.USER,
                        f"{instruction}\n\nHujjat ({document.filename}):\n"
                        f"{document.extracted_text[:80_000]}",
                    ),
                ),
                temperature=0.2,
                max_tokens=4000,
            ),
            module="documents",
        )
        return result.content


def _guess_type(suffix: str) -> str:
    mapping = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    return mapping.get(suffix.lower(), "application/octet-stream")
