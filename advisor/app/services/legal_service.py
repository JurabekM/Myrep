"""Huquqiy servis — lex.uz RAG savol-javob va shartnoma tahlili."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.base import ChatMessage, CompletionRequest, Role
from app.ai.prompts import build_system_prompt
from app.ai.router import ModelRouter
from app.ai.safety import LEGAL_DISCLAIMER, estimate_confidence
from app.core.config import BusinessProfile
from app.rag.retriever import COLLECTION_LEGAL, Retriever


@dataclass
class LegalAnswer:
    answer: str
    sources: list[dict]
    confidence: float
    disclaimer: str = LEGAL_DISCLAIMER


class LegalService:
    def __init__(self, router: ModelRouter, retriever: Retriever, profile: BusinessProfile):
        self._router = router
        self._retriever = retriever
        self._profile = profile

    def ask(self, question: str) -> LegalAnswer:
        result = self._retriever.retrieve(COLLECTION_LEGAL, question)
        system = build_system_prompt("legal", self._profile)
        if result.has_context:
            user_prompt = (
                f"Manbalar:\n{result.context}\n\nSavol: {question}\n\n"
                "Faqat yuqoridagi manbalarga tayanib javob ber; har fikrga [raqam] havola qo'y."
            )
        else:
            user_prompt = (
                f"Savol: {question}\n\nDIQQAT: mos qonun manbasi topilmadi. Umumiy "
                "yo'nalish ber, ammo aniq modda keltirma va manba yo'qligini ochiq ayt."
            )
        completion = self._router.complete(
            CompletionRequest(
                messages=(
                    ChatMessage(Role.SYSTEM, system),
                    ChatMessage(Role.USER, user_prompt),
                ),
                temperature=0.2,
                max_tokens=2500,
            ),
            module="legal",
        )
        report = estimate_confidence(
            completion.content, category="legal", used_rag=True,
            had_context=result.has_context,
        )
        return LegalAnswer(
            answer=completion.content,
            sources=[s.to_dict() for s in result.sources],
            confidence=report.confidence,
        )

    def analyze_contract(self, contract_text: str, focus: str = "") -> str:
        system = build_system_prompt("legal", self._profile)
        focus_line = f"Alohida e'tibor: {focus}\n" if focus else ""
        user_prompt = (
            "Quyidagi shartnomani tahlil qil. Struktura:\n"
            "1. Qisqacha xulosa\n2. Tomonlar majburiyatlari\n3. Risklar (daraja: "
            "yuqori/o'rta/past)\n4. Xavfli/noaniq bandlar\n5. O'zgartirish takliflari\n\n"
            f"{focus_line}\nShartnoma matni:\n{contract_text}"
        )
        completion = self._router.complete(
            CompletionRequest(
                messages=(
                    ChatMessage(Role.SYSTEM, system),
                    ChatMessage(Role.USER, user_prompt),
                ),
                temperature=0.2,
                max_tokens=3500,
            ),
            module="legal",
        )
        return f"{completion.content}\n\n{LEGAL_DISCLAIMER}"
