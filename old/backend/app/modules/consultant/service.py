"""Business-consultant artifact generation.

Each framework has a structured brief → the service assembles a rich prompt
with the user's business profile and returns Markdown ready for display or
DOCX/PDF export.
"""

from enum import StrEnum

from app.ai.base import ChatMessage, ChatRole, CompletionRequest
from app.ai.prompts.loader import PromptRepository
from app.ai.router import ModelRouter
from app.domain.entities.user import User


class Framework(StrEnum):
    BUSINESS_PLAN = "business_plan"
    SWOT = "swot"
    PESTEL = "pestel"
    BUSINESS_MODEL_CANVAS = "bmc"
    LEAN_CANVAS = "lean_canvas"
    MARKETING_PLAN = "marketing_plan"
    GO_TO_MARKET = "go_to_market"
    SALES_STRATEGY = "sales_strategy"
    PRICING = "pricing"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    RISK_ANALYSIS = "risk_analysis"
    FINANCIAL_FORECAST = "financial_forecast"
    KPI = "kpi"
    OKR = "okr"
    ROADMAP = "roadmap"
    INVESTMENT_PITCH = "investment_pitch"
    INVESTOR_DECK = "investor_deck"
    GRANT_APPLICATION = "grant_application"
    TENDER_DOCUMENT = "tender_document"


_FRAMEWORK_INSTRUCTIONS: dict[Framework, str] = {
    Framework.BUSINESS_PLAN: (
        "To'liq biznes-reja yoz: 1) Rezyume 2) Kompaniya tavsifi 3) Bozor tahlili "
        "4) Mahsulot/xizmat 5) Marketing strategiyasi 6) Operatsion reja 7) Jamoa "
        "8) Moliyaviy prognoz (3 yil, jadval) 9) Risklar 10) Ilova. "
        "Grant/kredit arizalariga mos rasmiyroq uslubda."
    ),
    Framework.SWOT: (
        "SWOT tahlil yoz: har kvadrant uchun kamida 5 punkt, har punktga qisqa izoh; "
        "yakunida SO/WO/ST/WT strategiyalari."
    ),
    Framework.PESTEL: (
        "PESTEL tahlil yoz (Siyosiy, Iqtisodiy, Ijtimoiy, Texnologik, Ekologik, "
        "Huquqiy) — har omilda O'zbekistonga xos aniq faktlar."
    ),
    Framework.BUSINESS_MODEL_CANVAS: (
        "Business Model Canvas yoz: 9 blok, har blokda konkret punktlar."
    ),
    Framework.LEAN_CANVAS: "Lean Canvas yoz: 9 blok, startap uchun gipotezalar bilan.",
    Framework.MARKETING_PLAN: (
        "12 oylik marketing reja: maqsadlar, segmentlar, kanallar (Telegram, Instagram, "
        "Google), byudjet taqsimoti (jadval), KPI, oylik taqvim."
    ),
    Framework.GO_TO_MARKET: "Go-to-Market strategiya: ICP, positioning, kanallar, 90 kunlik reja.",
    Framework.SALES_STRATEGY: "Savdo strategiyasi: funnel bosqichlari, skriptlar, CRM jarayoni, kvotalar.",
    Framework.PRICING: "Narxlash strategiyasi: 3 tarif varianti, raqobat taqqoslash, psixologik narxlash.",
    Framework.COMPETITOR_ANALYSIS: (
        "Raqobatchilar tahlili: taqqoslash jadvali (narx, sifat, kanal, USP), "
        "positioning xaritasi tavsifi, differensiatsiya tavsiyalari."
    ),
    Framework.RISK_ANALYSIS: (
        "Risklar tahlili: risk reestri jadvali (risk, ehtimol 1-5, ta'sir 1-5, ball, "
        "mitigatsiya, mas'ul)."
    ),
    Framework.FINANCIAL_FORECAST: (
        "3 yillik moliyaviy prognoz: daromad modeli, P&L jadvali (yilma-yil), "
        "asosiy farazlar ro'yxati, sezgirlik tahlili."
    ),
    Framework.KPI: "KPI tizimi: bo'limlar bo'yicha 5-7 KPI, formula, chastota, target.",
    Framework.OKR: "Choraklik OKR: 3-4 Objective, har biriga 3-4 o'lchanadigan Key Result.",
    Framework.ROADMAP: "12 oylik roadmap: choraklar bo'yicha milestone'lar, bog'liqliklar.",
    Framework.INVESTMENT_PITCH: (
        "Investor pitch matni (5 daqiqalik nutq): hook, muammo, yechim, bozor, "
        "traction, jamoa, so'rov (raise), foydalanish rejasi."
    ),
    Framework.INVESTOR_DECK: (
        "12 slaydlik investor deck strukturasi: har slayd uchun sarlavha, asosiy "
        "xabar va vizual tavsiya."
    ),
    Framework.GRANT_APPLICATION: (
        "Grant arizasi matni: loyiha maqsadi, muammo asoslash, natijalar, byudjet "
        "jadvali, barqarorlik rejasi. Rasmiy uslub."
    ),
    Framework.TENDER_DOCUMENT: (
        "Tender taklifi strukturasi: texnik taklif, malaka, narx asoslash, muddat "
        "jadvali, kafolatlar."
    ),
}


class ConsultantService:
    def __init__(self, ai_router: ModelRouter, prompts: PromptRepository):
        self._ai = ai_router
        self._prompts = prompts

    def frameworks(self) -> list[str]:
        return [f.value for f in Framework]

    async def generate(
        self,
        user: User,
        framework: Framework,
        business_description: str,
        *,
        extra_context: str | None = None,
        model: str | None = None,
    ) -> str:
        system = await self._prompts.get("module.consultant")
        profile = user.profile
        profile_block = (
            f"Biznes profili: soha={profile.industry or '-'}, "
            f"turi={profile.business_type.value if profile.business_type else '-'}, "
            f"hudud={profile.location or '-'}, xodimlar={profile.employees or '-'}, "
            f"yillik aylanma={profile.annual_revenue_uzs or '-'} so'm."
        )
        user_prompt = (
            f"{_FRAMEWORK_INSTRUCTIONS[framework]}\n\n"
            f"Biznes tavsifi:\n{business_description}\n\n{profile_block}"
        )
        if extra_context:
            user_prompt += f"\n\nQo'shimcha kontekst:\n{extra_context}"

        response = await self._ai.complete(
            CompletionRequest(
                messages=(
                    ChatMessage(role=ChatRole.SYSTEM, content=system),
                    ChatMessage(role=ChatRole.USER, content=user_prompt),
                ),
                model="consultant",
                temperature=0.5,
                max_tokens=8000,
            ),
            model_id=model,
            user_id=user.id,
            module="consultant",
        )
        return response.content
