"""Marketing AI endpoints — content generation for UZ market."""

from enum import StrEnum

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ai.base import ChatMessage, ChatRole, CompletionRequest
from app.core.dependencies import Container, CurrentUser

router = APIRouter(prefix="/marketing", tags=["marketing"])


class MarketingTask(StrEnum):
    SEO_AUDIT_PLAN = "seo_audit_plan"
    SMM_STRATEGY = "smm_strategy"
    CONTENT_PLAN = "content_plan"
    AD_COPY = "ad_copy"
    TARGET_AUDIENCE = "target_audience"
    LANDING_PAGE = "landing_page"
    EMAIL_CAMPAIGN = "email_campaign"
    FUNNEL = "funnel"
    AB_TEST_PLAN = "ab_test_plan"


class Channel(StrEnum):
    INSTAGRAM = "instagram"
    TELEGRAM = "telegram"
    FACEBOOK = "facebook"
    GOOGLE_ADS = "google_ads"
    EMAIL = "email"
    WEBSITE = "website"


_TASK_INSTRUCTIONS: dict[MarketingTask, str] = {
    MarketingTask.SEO_AUDIT_PLAN: (
        "SEO reja tuz: kalit so'zlar klasteri (uz/ru), on-page checklist, kontent "
        "mavzulari (20 ta), texnik SEO bosqichlari, 6 oylik taqvim."
    ),
    MarketingTask.SMM_STRATEGY: (
        "SMM strategiya: kanal tanlash asoslash, post turlari, chastota, "
        "rubrikator, engagement taktikalari, byudjet."
    ),
    MarketingTask.CONTENT_PLAN: (
        "30 kunlik kontent-plan jadval ko'rinishida: sana, kanal, format, mavzu, "
        "CTA, hashtag. Post g'oyalari konkret bo'lsin."
    ),
    MarketingTask.AD_COPY: (
        "Reklama matnlari yoz: 5 variant (turli hook), har biri sarlavha + matn + "
        "CTA. Uz va ru tillarida."
    ),
    MarketingTask.TARGET_AUDIENCE: (
        "Target auditoriya tahlili: 3-4 segment, har biri uchun persona, og'riq "
        "nuqtalari, xabar (messaging), kanal va taxminiy CPM/CPC mo'ljali."
    ),
    MarketingTask.LANDING_PAGE: (
        "Landing page strukturasi va to'liq matni: hero, muammo, yechim, "
        "ijtimoiy isbot, tariflar, FAQ, CTA. Konversiyaga yo'naltirilgan."
    ),
    MarketingTask.EMAIL_CAMPAIGN: (
        "Email ketma-ketligi (5 xat): mavzu qatori variantlari, matn, CTA, "
        "yuborish oralig'i."
    ),
    MarketingTask.FUNNEL: (
        "Marketing funnel loyihasi: TOFU/MOFU/BOFU bosqichlari, har bosqich uchun "
        "kontent, kanal, metrika va konversiya mo'ljali."
    ),
    MarketingTask.AB_TEST_PLAN: (
        "A/B test rejasi: 5 ta gipoteza (ICE ball bilan), test dizayni, namuna "
        "hajmi mo'ljali, muvaffaqiyat metrikasi."
    ),
}


class MarketingRequest(BaseModel):
    task: MarketingTask
    business_description: str = Field(min_length=10, max_length=8_000)
    channels: list[Channel] = Field(default_factory=list, max_length=6)
    budget_uzs: int | None = Field(default=None, ge=0)
    extra_context: str | None = Field(default=None, max_length=8_000)
    model: str | None = None


@router.get("/tasks")
async def tasks(user: CurrentUser) -> dict:
    return {"tasks": [t.value for t in MarketingTask], "channels": [c.value for c in Channel]}


@router.post("/generate")
async def generate(req: MarketingRequest, user: CurrentUser, container: Container) -> dict:
    system = await container.prompts.get("module.marketing")
    parts = [
        _TASK_INSTRUCTIONS[req.task],
        f"\nBiznes tavsifi:\n{req.business_description}",
    ]
    if req.channels:
        parts.append("Kanallar: " + ", ".join(c.value for c in req.channels))
    if req.budget_uzs:
        parts.append(f"Oylik byudjet: {req.budget_uzs:,} so'm")
    if req.extra_context:
        parts.append(f"Qo'shimcha kontekst:\n{req.extra_context}")

    response = await container.ai_router.complete(
        CompletionRequest(
            messages=(
                ChatMessage(role=ChatRole.SYSTEM, content=system),
                ChatMessage(role=ChatRole.USER, content="\n\n".join(parts)),
            ),
            model="marketing",
            temperature=0.7,
            max_tokens=6000,
        ),
        model_id=req.model,
        user_id=user.id,
        module="marketing",
    )
    return {"task": req.task, "content": response.content}
