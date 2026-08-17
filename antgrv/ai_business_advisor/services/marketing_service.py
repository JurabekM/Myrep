class MarketingService:
    """
    Marketing templates and strategies generator.
    These can be used as prompts for the AI or generated locally.
    """

    @staticmethod
    def generate_content_plan_template(business_type: str, platforms: list[str]) -> str:
        """Generates a basic content plan structure."""
        platforms_str = ", ".join(platforms)
        template = f"""
# Content Plan for {business_type}
**Platforms:** {platforms_str}

## Homa (Week 1)
- **Dushanba:** Ta'limiy post (Mijozlarga foydali maslahat)
- **Chorshanba:** Mahsulot/Xizmat namoyishi (Orqa fon sirlari)
- **Juma:** Ijtimoiy isbot (Mijoz fikri, Review)

## Homa (Week 2)
- **Seshanba:** Interaktiv (So'rovnoma yoki Q&A)
- **Payshanba:** Aksiya/Taklif (Call to Action)
- **Shanba:** Jamoa bilan tanishuv

*(Iltimos, ushbu strukturani to'ldirish uchun AI ga murojaat qiling)*
"""
        return template

    @staticmethod
    def get_funnel_strategy(funnel_type: str) -> str:
        strategies = {
            "webinar": "1. Traffic (Ads) -> 2. Landing Page (Email capture) -> 3. Value Video/Webinar -> 4. Sales Offer -> 5. Retargeting",
            "lead_magnet": "1. Traffic -> 2. Lead Magnet Download -> 3. Email Sequence (3-5 days) -> 4. Core Offer",
            "direct_sale": "1. Traffic -> 2. VSL (Video Sales Letter) / Landing Page -> 3. Checkout -> 4. Upsell 1 -> 5. Thank You"
        }
        return strategies.get(funnel_type, "Noma'lum voronka turi. (lead_magnet, webinar, direct_sale lardan birini tanlang)")

marketing_service = MarketingService()
