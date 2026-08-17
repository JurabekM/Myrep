"""Offline rule-based content generator.

This provider is always available: it needs no API key and no internet. It
composes text strictly from the facts handed to it, so it can never invent a
certificate, an MOQ, a price or a lead time that is not in the database.
"""

from __future__ import annotations

from app.integrations.base import ProviderResult
from app.integrations.llm.base import GenerationRequest, LLMProvider

_GREETING = {
    "en": "Dear {contact},",
    "ru": "Уважаемый(ая) {contact},",
    "uz": "Hurmatli {contact},",
}

_CLOSING = {
    "en": "Best regards,\n{sender}\n{company}\n{phone} | {email}",
    "ru": "С уважением,\n{sender}\n{company}\n{phone} | {email}",
    "uz": "Hurmat bilan,\n{sender}\n{company}\n{phone} | {email}",
}

_LABELS = {
    "en": {
        "moq": "Minimum order quantity",
        "lead_time": "Production lead time",
        "packaging": "Packaging",
        "hs": "HS code",
        "origin": "Country of origin",
        "unit": "Unit",
        "capacity": "Monthly capacity",
        "certificates": "Certificates",
        "price": "Price",
        "incoterm": "Delivery terms",
        "specs": "Technical specification",
        "days": "days",
        "no_certificates": "Certification documents are available on request.",
    },
    "ru": {
        "moq": "Минимальный объём заказа",
        "lead_time": "Срок производства",
        "packaging": "Упаковка",
        "hs": "Код ТН ВЭД",
        "origin": "Страна происхождения",
        "unit": "Единица измерения",
        "capacity": "Мощность в месяц",
        "certificates": "Сертификаты",
        "price": "Цена",
        "incoterm": "Условия поставки",
        "specs": "Технические характеристики",
        "days": "дней",
        "no_certificates": "Документы о сертификации предоставляются по запросу.",
    },
    "uz": {
        "moq": "Minimal buyurtma hajmi",
        "lead_time": "Ishlab chiqarish muddati",
        "packaging": "Qadoqlash",
        "hs": "HS kodi",
        "origin": "Kelib chiqish mamlakati",
        "unit": "O'lchov birligi",
        "capacity": "Oylik quvvat",
        "certificates": "Sertifikatlar",
        "price": "Narx",
        "incoterm": "Yetkazib berish sharti",
        "specs": "Texnik tavsif",
        "days": "kun",
        "no_certificates": "Sertifikatlash hujjatlari so'rov asosida taqdim etiladi.",
    },
}


def _lang(request: GenerationRequest) -> str:
    return request.language if request.language in _LABELS else "en"


def _product_name(facts: dict, lang: str) -> str:
    product = facts.get("product") or {}
    return (
        product.get(f"name_{lang}")
        or product.get("name_en")
        or product.get("name_uz")
        or product.get("sku")
        or "our product"
    )


def _fact_lines(facts: dict, lang: str) -> list[str]:
    """Bullet lines built only from values that actually exist."""
    labels = _LABELS[lang]
    product = facts.get("product") or {}
    price = facts.get("price") or {}
    lines: list[str] = []

    if product.get("hs_code"):
        lines.append(f"- {labels['hs']}: {product['hs_code']}")
    if product.get("origin_country"):
        lines.append(f"- {labels['origin']}: {product['origin_country']}")
    if product.get("moq"):
        unit = product.get("unit") or ""
        lines.append(f"- {labels['moq']}: {product['moq']:g} {unit}".rstrip())
    if product.get("lead_time_days"):
        lines.append(f"- {labels['lead_time']}: {product['lead_time_days']} {labels['days']}")
    if product.get("capacity_month"):
        lines.append(f"- {labels['capacity']}: {product['capacity_month']:g}")
    if product.get("packaging_type"):
        lines.append(f"- {labels['packaging']}: {product['packaging_type']}")
    if price.get("unit_price"):
        incoterm = price.get("incoterm") or ""
        origin = price.get("origin_point") or ""
        suffix = f" ({incoterm} {origin})".rstrip().rstrip("(") if incoterm else ""
        lines.append(
            f"- {labels['price']}: {price['unit_price']:g} {price.get('currency', '')}{suffix}"
        )
    certificates = facts.get("certificates") or []
    if certificates:
        names = ", ".join(cert["name"] for cert in certificates)
        lines.append(f"- {labels['certificates']}: {names}")
    return lines


def _spec_lines(facts: dict, lang: str) -> list[str]:
    specs = facts.get("specifications") or []
    lines = []
    for spec in specs:
        name = spec.get(f"name_{lang}") or spec.get("name_en") or ""
        value = spec.get(f"value_{lang}") or spec.get("value_en") or ""
        if name and value:
            lines.append(f"- {name}: {value}")
    return lines


class DemoRuleBasedProvider(LLMProvider):
    """Template-driven generator used when no LLM credentials are configured."""

    code = "demo"
    label = "Demo (rule-based, offline)"
    is_demo = True
    fields = ()

    def test_connection(self) -> ProviderResult:
        """Always available."""
        return ProviderResult.success("Demo provider is always available")

    def describe(self) -> str:
        return "Offline template engine - no API key required"

    def generate(self, request: GenerationRequest) -> ProviderResult:
        """Render a template for the requested content type."""
        lang = _lang(request)
        builder = getattr(self, f"_build_{request.content_type}", None)
        if builder is None:
            builder = self._build_generic
        try:
            text = builder(request, lang)
        except Exception as exc:  # pragma: no cover - defensive
            return ProviderResult.failure(f"Demo generation failed: {exc}")
        if request.instruction:
            note = {
                "en": "\n\nAdditional note: ",
                "ru": "\n\nДополнительно: ",
                "uz": "\n\nQo'shimcha: ",
            }[lang]
            text = f"{text}{note}{request.instruction}"
        return ProviderResult.success("Generated by the offline template engine", data=text)

    # ------------------------------------------------------------ templates
    def _header(self, request: GenerationRequest, lang: str) -> str:
        company = (request.facts.get("company") or {}).get("name", "")
        product = _product_name(request.facts, lang)
        return {
            "en": f"{product} - {company}",
            "ru": f"{product} - {company}",
            "uz": f"{product} - {company}",
        }[lang]

    def _build_generic(self, request: GenerationRequest, lang: str) -> str:
        lines = [self._header(request, lang), ""]
        lines.extend(_fact_lines(request.facts, lang))
        specs = _spec_lines(request.facts, lang)
        if specs:
            lines.append("")
            lines.append(_LABELS[lang]["specs"] + ":")
            lines.extend(specs)
        return "\n".join(lines).strip()

    def _build_product_description_short(self, request: GenerationRequest, lang: str) -> str:
        product = request.facts.get("product") or {}
        name = _product_name(request.facts, lang)
        existing = product.get(f"short_desc_{lang}") or ""
        if existing:
            return existing
        base = {
            "en": (
                f"{name} manufactured in {product.get('origin_country', 'Uzbekistan')} for "
                f"international B2B buyers. Consistent quality, export-grade packaging and "
                f"reliable delivery schedules."
            ),
            "ru": (
                f"{name} — продукция производства {product.get('origin_country', 'Узбекистан')} "
                f"для международных оптовых покупателей. Стабильное качество, экспортная "
                f"упаковка и предсказуемые сроки поставки."
            ),
            "uz": (
                f"{name} — {product.get('origin_country', 'O‘zbekiston')}da ishlab chiqarilgan, "
                f"xalqaro ulgurji xaridorlar uchun mo‘ljallangan mahsulot. Barqaror sifat, "
                f"eksport darajasidagi qadoqlash va ishonchli yetkazib berish muddatlari."
            ),
        }[lang]
        return base

    def _build_product_description_full(self, request: GenerationRequest, lang: str) -> str:
        product = request.facts.get("product") or {}
        existing = product.get(f"full_desc_{lang}") or ""
        parts = [self._build_product_description_short(request, lang)]
        if existing:
            parts.append(existing)
        facts = _fact_lines(request.facts, lang)
        if facts:
            parts.append("")
            parts.extend(facts)
        specs = _spec_lines(request.facts, lang)
        if specs:
            parts.append("")
            parts.append(_LABELS[lang]["specs"] + ":")
            parts.extend(specs)
        if not (request.facts.get("certificates") or []):
            parts.append("")
            parts.append(_LABELS[lang]["no_certificates"])
        return "\n".join(parts).strip()

    def _build_b2b_product_description(self, request: GenerationRequest, lang: str) -> str:
        name = _product_name(request.facts, lang)
        intro = {
            "en": (
                f"{name}\n\nWe supply {name} to importers, distributors and retail chains "
                f"worldwide. Every order is produced against an agreed specification and "
                f"inspected before shipment."
            ),
            "ru": (
                f"{name}\n\nМы поставляем {name} импортёрам, дистрибьюторам и розничным сетям "
                f"по всему миру. Каждый заказ производится по согласованной спецификации и "
                f"проверяется перед отгрузкой."
            ),
            "uz": (
                f"{name}\n\nBiz {name} mahsulotini butun dunyo importchilari, distribyutorlari "
                f"va chakana tarmoqlariga yetkazib beramiz. Har bir buyurtma kelishilgan "
                f"spetsifikatsiya asosida ishlab chiqariladi va jo‘natishdan oldin tekshiriladi."
            ),
        }[lang]
        lines = [intro, ""]
        lines.extend(_fact_lines(request.facts, lang))
        return "\n".join(lines).strip()

    def _build_alibaba_listing(self, request: GenerationRequest, lang: str) -> str:
        product = request.facts.get("product") or {}
        name = _product_name(request.facts, lang)
        title = self._build_seo_title(request, lang)
        lines = [
            f"Title: {title}",
            "",
            "Product overview:",
            self._build_product_description_short(request, lang),
            "",
            "Key attributes:",
        ]
        lines.extend(_fact_lines(request.facts, lang) or [f"- {name}"])
        specs = _spec_lines(request.facts, lang)
        if specs:
            lines.append("")
            lines.append("Specification:")
            lines.extend(specs)
        lines.extend(
            [
                "",
                "Supply ability and samples are confirmed per enquiry.",
                f"Reference SKU: {product.get('sku', '-')}",
            ]
        )
        return "\n".join(lines).strip()

    def _build_seo_title(self, request: GenerationRequest, lang: str) -> str:
        product = request.facts.get("product") or {}
        name = _product_name(request.facts, lang)
        chunks = [name]
        if product.get("origin_country"):
            chunks.append(f"Made in {product['origin_country']}")
        if product.get("moq"):
            chunks.append(f"MOQ {product['moq']:g} {product.get('unit', '')}".strip())
        certificates = request.facts.get("certificates") or []
        if certificates:
            chunks.append(certificates[0]["name"])
        return " | ".join(chunks)[:120]

    def _build_buyer_email(self, request: GenerationRequest, lang: str) -> str:
        return self._compose_email(
            request,
            lang,
            body={
                "en": (
                    "We are a manufacturer from {country} and we noticed your interest in "
                    "{product}. Below are the key commercial parameters of this item."
                ),
                "ru": (
                    "Мы — производитель из {country}, и обратили внимание на ваш интерес к "
                    "позиции {product}. Ниже приведены ключевые коммерческие параметры."
                ),
                "uz": (
                    "Biz {country}dagi ishlab chiqaruvchimiz va sizning {product} mahsulotiga "
                    "qiziqishingizni ko‘rdik. Quyida asosiy tijorat parametrlari keltirilgan."
                ),
            }[lang],
        )

    def _build_follow_up_email(self, request: GenerationRequest, lang: str) -> str:
        return self._compose_email(
            request,
            lang,
            body={
                "en": (
                    "I am following up on our offer for {product}. Please let us know whether "
                    "the commercial terms work for you, or which points you would like us to "
                    "revise."
                ),
                "ru": (
                    "Возвращаюсь к нашему предложению по позиции {product}. Сообщите, пожалуйста, "
                    "подходят ли коммерческие условия или какие пункты стоит скорректировать."
                ),
                "uz": (
                    "{product} bo‘yicha taklifimizga qaytmoqdaman. Iltimos, tijorat shartlari "
                    "sizga mos kelishini yoki qaysi bandlarni qayta ko‘rib chiqish kerakligini "
                    "bildiring."
                ),
            }[lang],
            include_facts=False,
        )

    def _build_commercial_offer(self, request: GenerationRequest, lang: str) -> str:
        quotation = request.facts.get("quotation") or {}
        header = {
            "en": "COMMERCIAL OFFER",
            "ru": "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ",
            "uz": "TIJORAT TAKLIFI",
        }[lang]
        lines = [header, ""]
        if quotation.get("number"):
            lines.append(f"No: {quotation['number']}")
        lines.append(self._build_b2b_product_description(request, lang))
        if quotation.get("incoterm"):
            lines.append("")
            lines.append(
                f"{_LABELS[lang]['incoterm']}: {quotation['incoterm']} {quotation.get('destination', '')}".rstrip()
            )
        if quotation.get("payment_terms"):
            lines.append(f"Payment: {quotation['payment_terms']}")
        if quotation.get("valid_until"):
            lines.append(f"Validity: {quotation['valid_until']}")
        return "\n".join(lines).strip()

    def _build_quotation_intro(self, request: GenerationRequest, lang: str) -> str:
        buyer = request.facts.get("buyer") or {}
        company = (request.facts.get("company") or {}).get("name", "")
        return {
            "en": (
                f"Thank you for your interest in {company}. Following your enquiry we are "
                f"pleased to submit our quotation for {buyer.get('company_name', 'your company')}. "
                f"All terms below are valid within the stated validity period."
            ),
            "ru": (
                f"Благодарим за интерес к компании {company}. По итогам вашего запроса "
                f"направляем коммерческое предложение для {buyer.get('company_name', 'вашей компании')}. "
                f"Все условия действительны в течение указанного срока."
            ),
            "uz": (
                f"{company} kompaniyasiga qiziqishingiz uchun rahmat. So‘rovingiz asosida "
                f"{buyer.get('company_name', 'kompaniyangiz')} uchun tijorat taklifimizni "
                f"yubormoqdamiz. Barcha shartlar ko‘rsatilgan muddat ichida amal qiladi."
            ),
        }[lang]

    def _build_objection_response(self, request: GenerationRequest, lang: str) -> str:
        objection = request.instruction or ""
        return {
            "en": (
                "Thank you for the direct feedback. Regarding your point"
                f"{' (' + objection + ')' if objection else ''}, here is how we can address it:\n"
                "1. We can review the order structure so the unit economics improve for you.\n"
                "2. We can adjust packaging or delivery terms instead of the unit price.\n"
                "3. We can propose a trial order first, then scale up on repeat volumes.\n\n"
                "Only the parameters confirmed in writing by our side are binding."
            ),
            "ru": (
                "Спасибо за прямую обратную связь. По вашему замечанию"
                f"{' (' + objection + ')' if objection else ''} предлагаем следующее:\n"
                "1. Пересмотреть структуру заказа для улучшения удельной экономики.\n"
                "2. Скорректировать упаковку или условия поставки вместо цены за единицу.\n"
                "3. Начать с пробной партии и увеличить объём при повторных заказах.\n\n"
                "Обязательными являются только параметры, письменно подтверждённые с нашей стороны."
            ),
            "uz": (
                "Ochiq fikringiz uchun rahmat. E'tirozingiz"
                f"{' (' + objection + ')' if objection else ''} bo‘yicha quyidagilarni taklif qilamiz:\n"
                "1. Buyurtma tuzilmasini qayta ko‘rib chiqish orqali birlik iqtisodini yaxshilash.\n"
                "2. Birlik narxi o‘rniga qadoqlash yoki yetkazib berish shartlarini moslashtirish.\n"
                "3. Avval sinov partiyasi, keyin takroriy hajmlarda kengaytirish.\n\n"
                "Faqat biz tomondan yozma tasdiqlangan parametrlar majburiy hisoblanadi."
            ),
        }[lang]

    def _build_linkedin_outreach(self, request: GenerationRequest, lang: str) -> str:
        buyer = request.facts.get("buyer") or {}
        company = (request.facts.get("company") or {}).get("name", "")
        product = _product_name(request.facts, lang)
        return {
            "en": (
                f"Hello {buyer.get('contact_person', '')}, I am with {company}, a manufacturer "
                f"of {product}. We currently supply importers in several markets and I would be "
                f"glad to share our specification sheet and current terms. Would that be useful?"
            ),
            "ru": (
                f"Здравствуйте, {buyer.get('contact_person', '')}. Я представляю {company} — "
                f"производителя позиции {product}. Мы поставляем импортёрам в нескольких странах "
                f"и готовы поделиться спецификацией и текущими условиями. Будет ли это полезно?"
            ),
            "uz": (
                f"Assalomu alaykum, {buyer.get('contact_person', '')}. Men {company} kompaniyasidanman, "
                f"{product} ishlab chiqaramiz. Hozirda bir necha bozorda importchilar bilan "
                f"ishlaymiz va spetsifikatsiya hamda joriy shartlarni ulashishga tayyormiz. "
                f"Bu siz uchun foydali bo‘ladimi?"
            ),
        }[lang]

    def _build_certificate_explanation(self, request: GenerationRequest, lang: str) -> str:
        certificates = request.facts.get("certificates") or []
        if not certificates:
            return {
                "en": (
                    "At present no certificate is registered for this product in our system. "
                    "Please tell us which certification your market requires and we will confirm "
                    "the feasibility and timeline before making any commitment."
                ),
                "ru": (
                    "В настоящее время в нашей системе нет зарегистрированных сертификатов по "
                    "этой позиции. Сообщите, какая сертификация требуется на вашем рынке, и мы "
                    "подтвердим возможность и сроки до принятия обязательств."
                ),
                "uz": (
                    "Hozircha tizimimizda ushbu mahsulot uchun sertifikat qayd etilmagan. "
                    "Bozoringiz qanday sertifikatlashni talab qilishini bildiring — biz majburiyat "
                    "olishdan oldin imkoniyat va muddatni tasdiqlaymiz."
                ),
            }[lang]
        lines = {
            "en": ["The following certification documents are registered for this product:"],
            "ru": ["По данной позиции зарегистрированы следующие документы:"],
            "uz": ["Ushbu mahsulot bo‘yicha quyidagi hujjatlar qayd etilgan:"],
        }[lang]
        for cert in certificates:
            expiry = cert.get("expiry_date")
            lines.append(f"- {cert['name']}" + (f" (valid until {expiry})" if expiry else ""))
        return "\n".join(lines)

    def _build_negotiation_talking_points(self, request: GenerationRequest, lang: str) -> str:
        facts = _fact_lines(request.facts, lang)
        head = {
            "en": "Negotiation talking points:",
            "ru": "Тезисы для переговоров:",
            "uz": "Muzokara uchun asosiy tezislar:",
        }[lang]
        tail = {
            "en": [
                "- Anchor on total landed cost, not only unit price.",
                "- Offer volume tiers instead of a flat discount.",
                "- Trade payment terms against price concessions.",
                "- Confirm every agreed parameter in writing.",
            ],
            "ru": [
                "- Обсуждайте полную стоимость поставки, а не только цену за единицу.",
                "- Предлагайте объёмные уровни вместо простой скидки.",
                "- Меняйте условия оплаты на ценовые уступки.",
                "- Фиксируйте каждый согласованный параметр письменно.",
            ],
            "uz": [
                "- Faqat birlik narxi emas, umumiy yetkazib berish qiymatini muhokama qiling.",
                "- Oddiy chegirma o‘rniga hajm bo‘yicha darajalarni taklif qiling.",
                "- To‘lov shartlarini narx yon berishlariga almashtiring.",
                "- Kelishilgan har bir parametrni yozma qayd eting.",
            ],
        }[lang]
        return "\n".join([head, *facts, "", *tail]).strip()

    # -------------------------------------------------------------- helpers
    def _compose_email(
        self,
        request: GenerationRequest,
        lang: str,
        body: str,
        include_facts: bool = True,
    ) -> str:
        buyer = request.facts.get("buyer") or {}
        company = request.facts.get("company") or {}
        product = _product_name(request.facts, lang)
        greeting = _GREETING[lang].format(contact=buyer.get("contact_person") or "Sir/Madam")
        text = body.format(
            product=product,
            country=company.get("country", "Uzbekistan"),
            buyer=buyer.get("company_name", ""),
        )
        parts = [greeting, "", text]
        if include_facts:
            facts = _fact_lines(request.facts, lang)
            if facts:
                parts.append("")
                parts.extend(facts)
        parts.append("")
        parts.append(
            _CLOSING[lang].format(
                sender=request.facts.get("sender", ""),
                company=company.get("name", ""),
                phone=company.get("phone", ""),
                email=company.get("email", ""),
            )
        )
        return "\n".join(parts).strip()
