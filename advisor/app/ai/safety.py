"""AI xavfsizlik guardraillari.

Uch qism:
  1. ``screen_prompt_injection`` — kirish matnida hujjum naqshlari (uz/ru/en)
     skrining qilinadi (LLM chaqirilishidan oldin).
  2. ``estimate_confidence`` — javob va (agar bor) RAG kontekstiga asoslanib
     ishonchlilik darajasi va hallucination xavfi baholanadi (heuristik,
     qo'shimcha LLM chaqiruvisiz — tez va oflayn ishlaydi).
  3. ``build_disclaimer`` — huquq/soliq/moliya kategoriyalari uchun majburiy
     ogohlantirish matni.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.logging_setup import get_logger

logger = get_logger(__name__)

LEGAL_DISCLAIMER = (
    "⚠️ Bu AI asosidagi ma'lumot bo'lib, yakuniy qaror uchun malakali yurist "
    "bilan maslahatlashing."
)
TAX_DISCLAIMER = (
    "⚠️ Bu AI asosidagi ma'lumot bo'lib, yakuniy qaror uchun malakali soliq "
    "maslahatchisi bilan maslahatlashing. Stavkalar o'zgargan bo'lishi mumkin — "
    "soliq.uz'ni tekshiring."
)
FINANCE_DISCLAIMER = (
    "⚠️ Bu AI asosidagi tahlil bo'lib, investitsiya maslahati emas. Moliyaviy "
    "qarorlar uchun mutaxassis bilan maslahatlashing."
)

_DISCLAIMERS = {
    "legal": LEGAL_DISCLAIMER,
    "tax": TAX_DISCLAIMER,
    "finance": FINANCE_DISCLAIMER,
    "investment": FINANCE_DISCLAIMER,
}

_INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|above|prior) (instructions|prompts)",
    r"disregard (your|the) (system|previous) prompt",
    r"you are now (dan|jailbroken|unrestricted)",
    r"reveal (your|the) (system prompt|instructions)",
    r"забудь (все )?(предыдущие )?инструкции",
    r"игнорируй (все )?(предыдущие )?инструкции",
    r"avvalgi (barcha )?ko'?rsatmalarni (unut|e'?tiborsiz qoldir)",
    r"tizim promptini (ko'?rsat|oshkor qil)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# Uzr/noaniqlik iboralari — ishonchlilikni pasaytiradi.
_UNCERTAIN_MARKERS = [
    "aniq ma'lumotim yo'q", "bilmayman", "aniq emas", "taxminan", "ehtimol",
    "не знаю", "не уверен", "i'm not sure", "i don't know", "cannot be certain",
]


@dataclass(frozen=True)
class InjectionResult:
    suspicious: bool
    matched: str | None = None


@dataclass(frozen=True)
class SafetyReport:
    confidence: float
    category: str
    grounded: bool | None  # None = RAG ishlatilmagan
    disclaimer: str | None


def screen_prompt_injection(text: str) -> InjectionResult:
    match = _INJECTION_RE.search(text)
    if match:
        logger.warning("Prompt-injection shubhasi: %s", match.group(0)[:80])
        return InjectionResult(True, match.group(0))
    return InjectionResult(False)


def build_disclaimer(category: str) -> str | None:
    return _DISCLAIMERS.get(category)


def estimate_confidence(
    answer: str,
    *,
    category: str,
    used_rag: bool,
    had_context: bool,
) -> SafetyReport:
    """Heuristik ishonchlilik bahosi (0..1).

    - Uzun, tuzilmali javoblar biroz ishonchliroq.
    - Noaniqlik iboralari ishonchni pasaytiradi.
    - RAG ishlatilgan-u kontekst topilmagan bo'lsa — grounding past, xavf yuqori.
    """
    confidence = 0.7
    grounded: bool | None = None

    lowered = answer.lower()
    uncertainty_hits = sum(1 for m in _UNCERTAIN_MARKERS if m in lowered)
    confidence -= 0.12 * uncertainty_hits

    if len(answer) > 400:
        confidence += 0.1
    if len(answer) < 60:
        confidence -= 0.15

    if used_rag:
        grounded = had_context
        if had_context:
            confidence += 0.15
        else:
            confidence -= 0.25  # RAG kerak edi-yu manba yo'q — hallucination xavfi

    confidence = max(0.05, min(confidence, 0.98))
    return SafetyReport(
        confidence=round(confidence, 2),
        category=category,
        grounded=grounded,
        disclaimer=build_disclaimer(category),
    )
