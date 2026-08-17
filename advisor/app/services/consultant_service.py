"""Biznes-konsultant hujjatlari generatsiyasi."""

from __future__ import annotations

from enum import Enum

from app.ai.base import ChatMessage, CompletionRequest, Role
from app.ai.prompts import build_system_prompt
from app.ai.router import ModelRouter
from app.core.config import BusinessProfile


class Framework(str, Enum):
    BUSINESS_PLAN = "business_plan"
    SWOT = "swot"
    PESTEL = "pestel"
    BMC = "bmc"
    LEAN_CANVAS = "lean_canvas"
    MARKETING_PLAN = "marketing_plan"
    GO_TO_MARKET = "go_to_market"
    PRICING = "pricing"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    RISK_ANALYSIS = "risk_analysis"
    FINANCIAL_FORECAST = "financial_forecast"
    KPI = "kpi"
    OKR = "okr"
    ROADMAP = "roadmap"
    PITCH_DECK = "pitch_deck"
    GRANT_APPLICATION = "grant_application"
    TENDER = "tender"


FRAMEWORK_LABELS: dict[Framework, str] = {
    Framework.BUSINESS_PLAN: "Biznes-reja",
    Framework.SWOT: "SWOT tahlil",
    Framework.PESTEL: "PESTEL tahlil",
    Framework.BMC: "Business Model Canvas",
    Framework.LEAN_CANVAS: "Lean Canvas",
    Framework.MARKETING_PLAN: "Marketing reja",
    Framework.GO_TO_MARKET: "Go-To-Market",
    Framework.PRICING: "Narxlash strategiyasi",
    Framework.COMPETITOR_ANALYSIS: "Raqobatchilar tahlili",
    Framework.RISK_ANALYSIS: "Risklar tahlili",
    Framework.FINANCIAL_FORECAST: "Moliyaviy prognoz",
    Framework.KPI: "KPI tizimi",
    Framework.OKR: "OKR",
    Framework.ROADMAP: "Roadmap (12 oy)",
    Framework.PITCH_DECK: "Pitch Deck",
    Framework.GRANT_APPLICATION: "Grant arizasi",
    Framework.TENDER: "Tender taklifi",
}

_INSTRUCTIONS: dict[Framework, str] = {
    Framework.BUSINESS_PLAN: (
        "To'liq biznes-reja yoz: 1) Rezyume 2) Kompaniya 3) Bozor tahlili 4) Mahsulot "
        "5) Marketing 6) Operatsion reja 7) Jamoa 8) Moliyaviy prognoz (3 yil, jadval) "
        "9) Risklar 10) Ilova."
    ),
    Framework.SWOT: "SWOT tahlil: har kvadrant uchun 5+ punkt; yakunda SO/WO/ST/WT strategiyalari.",
    Framework.PESTEL: "PESTEL tahlil — har omilda O'zbekistonga xos aniq faktlar.",
    Framework.BMC: "Business Model Canvas: 9 blok, har blokda konkret punktlar.",
    Framework.LEAN_CANVAS: "Lean Canvas: 9 blok, startap gipotezalari bilan.",
    Framework.MARKETING_PLAN: (
        "12 oylik marketing reja: maqsadlar, segmentlar, kanallar (Telegram, Instagram, "
        "Google), byudjet taqsimoti (jadval), KPI, oylik taqvim."
    ),
    Framework.GO_TO_MARKET: "Go-To-Market: ICP, positioning, kanallar, 90 kunlik reja.",
    Framework.PRICING: "Narxlash: 3 tarif varianti, raqobat taqqoslash, psixologik narxlash.",
    Framework.COMPETITOR_ANALYSIS: (
        "Raqobatchilar tahlili: taqqoslash jadvali (narx, sifat, kanal, USP), "
        "differensiatsiya tavsiyalari."
    ),
    Framework.RISK_ANALYSIS: (
        "Risklar reestri jadvali: risk, ehtimol (1-5), ta'sir (1-5), ball, mitigatsiya, mas'ul."
    ),
    Framework.FINANCIAL_FORECAST: (
        "3 yillik moliyaviy prognoz: daromad modeli, P&L jadvali (yilma-yil), farazlar, "
        "sezgirlik tahlili."
    ),
    Framework.KPI: "KPI tizimi: bo'limlar bo'yicha 5-7 KPI, formula, chastota, target.",
    Framework.OKR: "Choraklik OKR: 3-4 Objective, har biriga 3-4 o'lchanadigan Key Result.",
    Framework.ROADMAP: "12 oylik roadmap: choraklar bo'yicha milestone'lar, bog'liqliklar.",
    Framework.PITCH_DECK: (
        "12 slaydlik pitch deck strukturasi: har slayd uchun sarlavha, asosiy xabar, vizual tavsiya."
    ),
    Framework.GRANT_APPLICATION: (
        "Grant arizasi: loyiha maqsadi, muammo asoslash, natijalar, byudjet jadvali, "
        "barqarorlik rejasi. Rasmiy uslub."
    ),
    Framework.TENDER: (
        "Tender taklifi: texnik taklif, malaka, narx asoslash, muddat jadvali, kafolatlar."
    ),
}


class ConsultantService:
    def __init__(self, router: ModelRouter, profile: BusinessProfile):
        self._router = router
        self._profile = profile

    def generate(
        self, framework: Framework, business_description: str, extra_context: str = ""
    ) -> str:
        system = build_system_prompt("consultant", self._profile)
        user_prompt = f"{_INSTRUCTIONS[framework]}\n\nBiznes tavsifi:\n{business_description}"
        if extra_context:
            user_prompt += f"\n\nQo'shimcha kontekst:\n{extra_context}"
        result = self._router.complete(
            CompletionRequest(
                messages=(
                    ChatMessage(Role.SYSTEM, system),
                    ChatMessage(Role.USER, user_prompt),
                ),
                temperature=0.5,
                max_tokens=4000,
            ),
            module="consultant",
        )
        return result.content
