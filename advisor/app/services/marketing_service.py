"""Marketing AI generatsiyasi."""

from __future__ import annotations

from enum import Enum

from app.ai.base import ChatMessage, CompletionRequest, Role
from app.ai.prompts import build_system_prompt
from app.ai.router import ModelRouter
from app.core.config import BusinessProfile


class MarketingTask(str, Enum):
    CONTENT_PLAN = "content_plan"
    AD_COPY = "ad_copy"
    SMM_STRATEGY = "smm_strategy"
    TARGET_AUDIENCE = "target_audience"
    SEO_PLAN = "seo_plan"
    LANDING_PAGE = "landing_page"
    EMAIL_CAMPAIGN = "email_campaign"
    FUNNEL = "funnel"
    AB_TEST = "ab_test"


TASK_LABELS: dict[MarketingTask, str] = {
    MarketingTask.CONTENT_PLAN: "Kontent-plan (30 kun)",
    MarketingTask.AD_COPY: "Reklama matnlari",
    MarketingTask.SMM_STRATEGY: "SMM strategiya",
    MarketingTask.TARGET_AUDIENCE: "Target auditoriya",
    MarketingTask.SEO_PLAN: "SEO reja",
    MarketingTask.LANDING_PAGE: "Landing page matni",
    MarketingTask.EMAIL_CAMPAIGN: "Email ketma-ketligi",
    MarketingTask.FUNNEL: "Marketing funnel",
    MarketingTask.AB_TEST: "A/B test rejasi",
}

_INSTRUCTIONS: dict[MarketingTask, str] = {
    MarketingTask.CONTENT_PLAN: (
        "30 kunlik kontent-plan jadval ko'rinishida: sana, kanal, format, mavzu, CTA, hashtag."
    ),
    MarketingTask.AD_COPY: "Reklama matnlari: 5 variant (turli hook), sarlavha + matn + CTA, uz va ru.",
    MarketingTask.SMM_STRATEGY: (
        "SMM strategiya: kanal tanlash asoslash, post turlari, chastota, rubrikator, byudjet."
    ),
    MarketingTask.TARGET_AUDIENCE: (
        "Target auditoriya: 3-4 segment, persona, og'riq nuqtalari, messaging, kanal, CPM/CPC mo'ljal."
    ),
    MarketingTask.SEO_PLAN: (
        "SEO reja: kalit so'zlar klasteri (uz/ru), on-page checklist, 20 kontent mavzusi, 6 oylik taqvim."
    ),
    MarketingTask.LANDING_PAGE: (
        "Landing page to'liq matni: hero, muammo, yechim, ijtimoiy isbot, tariflar, FAQ, CTA."
    ),
    MarketingTask.EMAIL_CAMPAIGN: "Email ketma-ketligi (5 xat): mavzu variantlari, matn, CTA, oraliq.",
    MarketingTask.FUNNEL: (
        "Marketing funnel: TOFU/MOFU/BOFU, har bosqich uchun kontent, kanal, metrika, konversiya mo'ljal."
    ),
    MarketingTask.AB_TEST: "A/B test rejasi: 5 gipoteza (ICE ball), test dizayni, namuna hajmi, metrika.",
}


class MarketingService:
    def __init__(self, router: ModelRouter, profile: BusinessProfile):
        self._router = router
        self._profile = profile

    def generate(
        self,
        task: MarketingTask,
        business_description: str,
        *,
        channels: list[str] | None = None,
        budget_uzs: int | None = None,
    ) -> str:
        system = build_system_prompt("marketing", self._profile)
        parts = [_INSTRUCTIONS[task], f"\nBiznes tavsifi:\n{business_description}"]
        if channels:
            parts.append("Kanallar: " + ", ".join(channels))
        if budget_uzs:
            parts.append(f"Oylik byudjet: {budget_uzs:,} so'm")
        result = self._router.complete(
            CompletionRequest(
                messages=(
                    ChatMessage(Role.SYSTEM, system),
                    ChatMessage(Role.USER, "\n\n".join(parts)),
                ),
                temperature=0.7,
                max_tokens=4000,
            ),
            module="marketing",
        )
        return result.content
