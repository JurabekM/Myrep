"""Legal assistant: RAG-grounded answers over lex.uz corpus + contract analysis."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ai.base import ChatMessage, ChatRole, CompletionRequest
from app.ai.safety.pipeline import LEGAL_TAX_DISCLAIMER
from app.core.dependencies import Container, CurrentUser
from app.infrastructure.vector.qdrant import VectorCollections
from app.rag.retrieval import HybridRetriever, format_context

router = APIRouter(prefix="/legal", tags=["legal"])


class LegalQuestionRequest(BaseModel):
    question: str = Field(min_length=5, max_length=8_000)
    model: str | None = None


class ContractAnalysisRequest(BaseModel):
    contract_text: str = Field(min_length=100, max_length=120_000)
    focus: str | None = Field(default=None, max_length=500)  # masalan: "ijara shartlari"
    model: str | None = None


@router.post("/ask")
async def ask(req: LegalQuestionRequest, user: CurrentUser, container: Container) -> dict:
    retriever = HybridRetriever(container.qdrant, container.ai_router)
    chunks = await retriever.search(VectorCollections.LEGAL_UZ, req.question, limit=6)

    system = await container.prompts.get("module.legal")
    if chunks:
        user_prompt = (
            f"Manbalar:\n{format_context(chunks)}\n\n"
            f"Savol: {req.question}\n\n"
            "Faqat yuqoridagi manbalarga tayanib javob ber; har fikrga [raqam] "
            "ko'rinishida havola qo'y."
        )
    else:
        user_prompt = (
            f"Savol: {req.question}\n\n"
            "DIQQAT: mos qonun manbasi topilmadi. Umumiy yo'nalish bergin, ammo aniq "
            "modda keltirma va manba yo'qligini ochiq ayt."
        )

    response = await container.ai_router.complete(
        CompletionRequest(
            messages=(
                ChatMessage(role=ChatRole.SYSTEM, content=system),
                ChatMessage(role=ChatRole.USER, content=user_prompt),
            ),
            model="legal",
            temperature=0.2,
            max_tokens=3000,
        ),
        model_id=req.model,
        user_id=user.id,
        module="legal",
    )
    safety = await container.safety.evaluate(
        req.question, response.content, sources=[c.source for c in chunks] or None
    )
    return {
        "answer": response.content,
        "sources": [c.source.model_dump() for c in chunks],
        "safety": safety.model_dump(),
        "disclaimer": LEGAL_TAX_DISCLAIMER,
    }


@router.post("/analyze-contract")
async def analyze_contract(
    req: ContractAnalysisRequest, user: CurrentUser, container: Container
) -> dict:
    system = await container.prompts.get("module.legal")
    focus_line = f"Alohida e'tibor: {req.focus}\n" if req.focus else ""
    user_prompt = (
        "Quyidagi shartnomani tahlil qil. Natija strukturasi:\n"
        "1. Qisqacha xulosa\n2. Tomonlar majburiyatlari\n3. Aniqlangan risklar "
        "(darajasi bilan: yuqori/o'rta/past)\n4. Noaniq yoki xavfli bandlar\n"
        "5. O'zgartirish takliflari\n\n"
        f"{focus_line}\nShartnoma matni:\n{req.contract_text}"
    )
    response = await container.ai_router.complete(
        CompletionRequest(
            messages=(
                ChatMessage(role=ChatRole.SYSTEM, content=system),
                ChatMessage(role=ChatRole.USER, content=user_prompt),
            ),
            model="legal",
            temperature=0.2,
            max_tokens=4000,
        ),
        model_id=req.model,
        user_id=user.id,
        module="legal",
    )
    return {"analysis": response.content, "disclaimer": LEGAL_TAX_DISCLAIMER}
