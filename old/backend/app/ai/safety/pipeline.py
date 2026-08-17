"""AI safety pipeline.

Order per answer:
  1. prompt-injection screening on user input (pre-LLM)
  2. LLM answer
  3. grounding / hallucination scoring (when RAG context exists)
  4. category classification + confidence score
  5. disclaimer injection for regulated categories (legal / tax)
"""

import re
from dataclasses import dataclass

from app.ai.base import ChatMessage, ChatRole, CompletionRequest
from app.ai.router import ModelRouter
from app.core.logging import get_logger
from app.domain.entities.conversation import SafetyReport, SourceReference

logger = get_logger(__name__)

LEGAL_TAX_DISCLAIMER = (
    "⚠️ Bu AI asosidagi ma'lumot bo'lib, yakuniy qaror uchun malakali "
    "yurist yoki soliq maslahatchisi bilan maslahatlashing."
)

FINANCE_DISCLAIMER = (
    "⚠️ Bu AI asosidagi tahlil bo'lib, investitsiya maslahati emas. "
    "Moliyaviy qarorlar uchun mutaxassis bilan maslahatlashing."
)

_REGULATED_CATEGORIES = {"legal": LEGAL_TAX_DISCLAIMER, "tax": LEGAL_TAX_DISCLAIMER,
                         "finance": FINANCE_DISCLAIMER, "investment": FINANCE_DISCLAIMER}

# Common injection phrasings (uz / ru / en). A heuristic pre-filter; the
# system prompt additionally instructs the model to ignore embedded orders.
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

_CATEGORIES = (
    "strategy", "marketing", "tax", "legal", "accounting", "investment",
    "grants", "credit", "startup", "it", "hr", "finance", "export", "import",
    "market_analysis", "general",
)


@dataclass(frozen=True)
class InjectionScreenResult:
    suspicious: bool
    matched: str | None = None


def screen_prompt_injection(text: str) -> InjectionScreenResult:
    match = _INJECTION_RE.search(text)
    if match:
        logger.warning("prompt_injection_suspected", snippet=match.group(0)[:80])
        return InjectionScreenResult(suspicious=True, matched=match.group(0))
    return InjectionScreenResult(suspicious=False)


class SafetyEvaluator:
    """Post-answer evaluation via a cheap judge model call."""

    def __init__(self, router: ModelRouter, judge_model: str | None = None):
        self._router = router
        self._judge_model = judge_model  # None → router default

    async def evaluate(
        self,
        question: str,
        answer: str,
        sources: list[SourceReference] | None = None,
    ) -> SafetyReport:
        grounded: bool | None = None
        hallucination_risk: float | None = None

        judge_prompt = (
            "You are a strict evaluator for a business-advisory AI in Uzbekistan.\n"
            f"Question:\n{question[:2000]}\n\nAnswer:\n{answer[:4000]}\n\n"
        )
        if sources:
            context = "\n---\n".join(
                f"[{s.title}] {s.snippet or ''}"[:800] for s in sources[:6]
            )
            judge_prompt += f"Retrieved sources:\n{context}\n\n"
        judge_prompt += (
            "Return STRICT JSON with keys: "
            '"category" (one of: ' + ", ".join(_CATEGORIES) + "), "
            '"confidence" (0..1 — how reliable the answer is), '
            + (
                '"grounded" (true if the answer is supported by the sources), '
                '"hallucination_risk" (0..1)'
                if sources
                else '"grounded" (null), "hallucination_risk" (null)'
            )
        )

        try:
            response = await self._router.complete(
                CompletionRequest(
                    messages=(ChatMessage(role=ChatRole.USER, content=judge_prompt),),
                    model="judge",  # replaced by model_id below
                    temperature=0.0,
                    max_tokens=200,
                    json_mode=True,
                ),
                model_id=self._judge_model,
                module="safety",
            )
            report = _parse_judge_json(response.content)
        except Exception as exc:  # judge failure must never block the answer
            logger.warning("safety_judge_failed", error=str(exc))
            report = SafetyReport(confidence=0.5, category="general")

        if sources is not None and report.grounded is None:
            grounded = None  # keep explicit
        disclaimer = _REGULATED_CATEGORIES.get(report.category)
        return SafetyReport(
            confidence=report.confidence,
            category=report.category,
            grounded=report.grounded if sources else None,
            hallucination_risk=report.hallucination_risk if sources else None,
            disclaimer=disclaimer,
        )


def _parse_judge_json(raw: str) -> SafetyReport:
    import json

    # Models sometimes wrap JSON in code fences.
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    data = json.loads(cleaned)
    category = data.get("category", "general")
    if category not in _CATEGORIES:
        category = "general"
    confidence = min(max(float(data.get("confidence", 0.5)), 0.0), 1.0)
    grounded = data.get("grounded")
    risk = data.get("hallucination_risk")
    return SafetyReport(
        confidence=confidence,
        category=category,
        grounded=bool(grounded) if isinstance(grounded, bool) else None,
        hallucination_risk=min(max(float(risk), 0.0), 1.0) if isinstance(risk, (int, float)) else None,
    )
