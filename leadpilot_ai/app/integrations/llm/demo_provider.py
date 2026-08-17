"""Deterministic rule-based sales agent used when no LLM is configured.

It implements the full state machine required by the product spec and never
invents facts: every concrete statement (price, address, promo, slot) comes from
the :class:`~app.integrations.llm.base_llm.AgentContext` that the service layer
fills from the approved knowledge base.
"""

from __future__ import annotations

import time as _time
from typing import Any

from app.integrations.base import AdapterResult
from app.integrations.llm import nlu
from app.integrations.llm.base_llm import AgentContext, AgentReply, LLMProvider
from app.models.enums import AIState, LanguageCode, Sentiment
from app.utils.dates import fmt_datetime

# --------------------------------------------------------------------------- #
# Phrase book. Every user-facing string exists in both languages.
# --------------------------------------------------------------------------- #
PHRASES: dict[str, dict[str, str]] = {
    "greeting": {
        "uz": "Assalomu alaykum! {company} ga xush kelibsiz. Men {agent}man. Sizga qanday yordam bera olaman?",
        "ru": "Здравствуйте! Вас приветствует {company}. Меня зовут {agent}. Чем могу помочь?",
    },
    "greeting_after_hours": {
        "uz": "Assalomu alaykum! {company}. Hozir ish vaqtimiz tugagan, ammo men savolingizni qabul qilaman va ertaga operatorimiz siz bilan bog'lanadi.",
        "ru": "Здравствуйте! {company}. Сейчас нерабочее время, но я приму ваш вопрос — завтра оператор свяжется с вами.",
    },
    "ask_need": {
        "uz": "Qaysi xizmat sizni qiziqtiryapti? Quyidagilardan tanlashingiz mumkin:\n{services}",
        "ru": "Какая услуга вас интересует? Можно выбрать из списка:\n{services}",
    },
    "price_answer": {
        "uz": "{service} — {price} so'm.{promo}\nSizga qulay vaqtni belgilaymizmi?",
        "ru": "{service} — {price} сум.{promo}\nПодберём удобное для вас время?",
    },
    "price_unknown": {
        "uz": "Aniq narxni operatorimiz tasdiqlaydi — men noto'g'ri ma'lumot bermaslikni afzal ko'raman. Hoziroq operatorga ulayman.",
        "ru": "Точную цену подтвердит оператор — я не хочу дать неверную информацию. Сейчас передам оператору.",
    },
    "schedule_answer": {
        "uz": "Ish vaqtimiz: {hours}. Eng yaqin bo'sh vaqtlar:\n{slots}\nQaysi biri sizga mos?",
        "ru": "Мы работаем: {hours}. Ближайшее свободное время:\n{slots}\nКакое вам подходит?",
    },
    "address_answer": {
        "uz": "Manzilimiz: {branches}",
        "ru": "Наш адрес: {branches}",
    },
    "ask_name_phone": {
        "uz": "Yaxshi! Bron qilish uchun ismingiz va telefon raqamingizni qoldirsangiz bo'ldi.",
        "ru": "Отлично! Для записи оставьте, пожалуйста, ваше имя и номер телефона.",
    },
    "ask_phone": {
        "uz": "Rahmat! Telefon raqamingizni ham qoldirasizmi? Operatorimiz tasdiqlash uchun bog'lanadi.",
        "ru": "Спасибо! Оставьте, пожалуйста, номер телефона — оператор перезвонит для подтверждения.",
    },
    "booking_offer": {
        "uz": "Sizga {slot} vaqti mos keladimi?",
        "ru": "Вам подходит {slot}?",
    },
    "booking_ready": {
        "uz": "Ajoyib! {slot} ga bron qilaman. Tasdiqlash xabarini yuboraman.",
        "ru": "Отлично! Записываю вас на {slot}. Отправлю подтверждение.",
    },
    "objection_price": {
        "uz": "Sizni tushunaman. Bizda amaldagi takliflar bor:{promo}\nOperatorimiz siz uchun eng qulay variantni aytib beradi — hoziroq ulayman.",
        "ru": "Понимаю вас. У нас есть действующие предложения:{promo}\nОператор подберёт оптимальный вариант — сейчас передам ему диалог.",
    },
    "handoff": {
        "uz": "Albatta, hoziroq operatorimizga ulayman. Bir necha daqiqada javob berishadi.",
        "ru": "Конечно, сейчас передам оператору. Ответят в течение нескольких минут.",
    },
    "negative_handoff": {
        "uz": "Uzr so'rayman. Bu holatni mas'ul xodimimizga darhol yetkazdim, u siz bilan bog'lanadi.",
        "ru": "Приношу извинения. Я сразу передал(а) ситуацию ответственному сотруднику, он свяжется с вами.",
    },
    "opt_out": {
        "uz": "Tushundim, boshqa xabar yubormaymiz. Murojaatingiz uchun rahmat.",
        "ru": "Поняла, больше писать не будем. Спасибо за обращение.",
    },
    "unknown": {
        "uz": "Bu savolga aniq javob berish uchun operatorimizga ulayman — noto'g'ri ma'lumot bermayman.",
        "ru": "Чтобы ответить точно, передам вопрос оператору — не хочу дать неверную информацию.",
    },
    "forbidden": {
        "uz": "Bu savol bo'yicha maslahatni faqat mutaxassisimiz bera oladi. Sizni operatorga ulayman.",
        "ru": "По этому вопросу консультацию даст только наш специалист. Соединяю с оператором.",
    },
    "followup": {
        "uz": "Savolingiz qoldimi? Yordam berishga tayyorman.",
        "ru": "Остались вопросы? Готова помочь.",
    },
    "thanks": {
        "uz": "Sizga rahmat! Yana savol tug'ilsa, yozing.",
        "ru": "Спасибо вам! Если появятся вопросы — пишите.",
    },
}

ESCALATION_REASONS = {
    "human_request": "Mijoz operator so'radi",
    "negative": "Salbiy kayfiyat / shikoyat",
    "price_negotiation": "Narx bo'yicha kelishuv",
    "unknown_question": "AI aniq javob topa olmadi",
    "forbidden_topic": "Taqiqlangan mavzu",
    "hot_lead": "Yuqori niyatli lead",
    "max_messages": "Avtomatik xabarlar limiti",
}


class DemoRuleBasedProvider(LLMProvider):
    """Rule-based sales agent. Always available, no credentials needed."""

    provider = "demo_llm"
    title = "Demo AI (rule-based)"
    is_demo = True

    def test_connection(self) -> AdapterResult:
        """The demo agent is always ready."""
        return AdapterResult.success("Demo AI faol")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _lang(context: AgentContext, understanding: nlu.Understanding) -> str:
        """Pick the answer language: the customer's language wins."""
        if understanding.language in (LanguageCode.UZ, LanguageCode.RU):
            return understanding.language
        if context.language in ("uz", "ru"):
            return context.language
        return "uz"

    @staticmethod
    def _phrase(key: str, lang: str, **kwargs: Any) -> str:
        """Render a phrase from the phrase book."""
        template = PHRASES[key][lang if lang in ("uz", "ru") else "uz"]
        return template.format(**kwargs)

    @staticmethod
    def _service_list(context: AgentContext, lang: str) -> str:
        """Bullet list of active services with prices."""
        currency = "сум" if lang == "ru" else "so'm"
        lines = []
        for service in context.services[:8]:
            use_ru = lang == "ru" and service.get("name_ru")
            name = service.get("name_ru") if use_ru else service.get("name")
            price = service.get("price_label", "")
            lines.append(f"• {name} — {price} {currency}")
        return "\n".join(lines) if lines else "• —"

    @staticmethod
    def _match_service(context: AgentContext, text: str) -> dict[str, Any] | None:
        """Find the service the customer is talking about."""
        lowered = (text or "").lower()
        best: dict[str, Any] | None = None
        best_hits = 0
        for service in context.services:
            names = [str(service.get("name", "")), str(service.get("name_ru", ""))]
            for name in names:
                if not name:
                    continue
                tokens = [t for t in name.lower().split() if len(t) > 3]
                hits = sum(1 for t in tokens if t[:6] in lowered)
                if name.lower() in lowered:
                    hits += 3
                if hits > best_hits:
                    best_hits, best = hits, service
        return best if best_hits > 0 else None

    @staticmethod
    def _promo_text(context: AgentContext, lang: str) -> str:
        """Return promo lines, or an empty string when there are none."""
        if not context.promos:
            return ""
        return "\n" + "\n".join(f"• {p}" for p in context.promos[:3])

    @staticmethod
    def _slots_text(context: AgentContext) -> str:
        """Bullet list of free slots offered to the customer."""
        if not context.free_slots:
            return "• —"
        return "\n".join(f"• {slot}" for slot in context.free_slots[:4])

    def _knowledge_answer(self, context: AgentContext, understanding: nlu.Understanding) -> str:
        """Find an approved knowledge base snippet matching the question."""
        if not context.knowledge:
            return ""
        words = set(understanding.keywords)
        best_text, best_hits = "", 0
        for snippet in context.knowledge:
            lowered = snippet.lower()
            hits = sum(1 for w in words if w in lowered)
            if hits > best_hits:
                best_hits, best_text = hits, snippet
        return best_text if best_hits >= 2 else ""

    def _is_forbidden(self, context: AgentContext, text: str) -> bool:
        """Whether the message touches a topic the AI must not answer."""
        lowered = (text or "").lower()
        for topic in context.forbidden_topics:
            token = topic.strip().lower()
            if token and token.split()[0] in lowered:
                return True
        return False

    # ------------------------------------------------------------------ #
    # Main entry point
    # ------------------------------------------------------------------ #
    def generate_reply(self, context: AgentContext, customer_message: str) -> AgentReply:
        """Run the sales state machine and produce the next reply."""
        started = _time.perf_counter()
        understanding = nlu.understand(customer_message, context.language)
        lang = self._lang(context, understanding)
        extracted: dict[str, str] = {}
        if understanding.phone:
            extracted["phone"] = understanding.phone
        if understanding.name:
            extracted["full_name"] = understanding.name
        if understanding.requested_datetime:
            extracted["datetime"] = understanding.requested_datetime.isoformat()
        extracted["language"] = lang

        def finish(
            text: str,
            state: str,
            *,
            escalate: bool = False,
            reason: str = "",
            wants_booking: bool = False,
            kb_refs: list[str] | None = None,
            confidence: float = 1.0,
        ) -> AgentReply:
            """Build the reply object with timing and signature."""
            body = text
            if context.signature and not escalate:
                body = f"{body}\n\n{context.signature}"
            return AgentReply(
                text=body,
                next_state=state,
                escalate=escalate,
                escalation_reason=reason,
                wants_booking=wants_booking,
                extracted=extracted,
                kb_refs=kb_refs or [],
                confidence=confidence,
                provider=self.provider,
                model="rule-based-v1",
                latency_ms=int((_time.perf_counter() - started) * 1000),
            )

        # 1. Hard stops -------------------------------------------------- #
        if understanding.has("opt_out"):
            extracted["opt_out"] = "1"
            return finish(self._phrase("opt_out", lang), AIState.LOST)

        if understanding.sentiment == Sentiment.NEGATIVE and understanding.has("negative"):
            return finish(
                self._phrase("negative_handoff", lang),
                AIState.HUMAN_HANDOFF,
                escalate=True,
                reason=ESCALATION_REASONS["negative"],
            )

        if understanding.has("human"):
            return finish(
                self._phrase("handoff", lang),
                AIState.HUMAN_HANDOFF,
                escalate=True,
                reason=ESCALATION_REASONS["human_request"],
            )

        if self._is_forbidden(context, customer_message):
            return finish(
                self._phrase("forbidden", lang),
                AIState.HUMAN_HANDOFF,
                escalate=True,
                reason=ESCALATION_REASONS["forbidden_topic"],
            )

        # 2. Price objection --------------------------------------------- #
        if understanding.has("objection_price"):
            return finish(
                self._phrase("objection_price", lang, promo=self._promo_text(context, lang)),
                AIState.OBJECTION_HANDLING,
                escalate=True,
                reason=ESCALATION_REASONS["price_negotiation"],
            )

        # 3. Booking intent ---------------------------------------------- #
        if understanding.has("booking") or context.state == AIState.BOOKING_ATTEMPT:
            missing_name = not (context.lead_name or understanding.name)
            missing_phone = not (context.lead_phone or understanding.phone)
            if understanding.requested_datetime and not (missing_name or missing_phone):
                return finish(
                    self._phrase(
                        "booking_ready", lang, slot=fmt_datetime(understanding.requested_datetime)
                    ),
                    AIState.BOOKING_ATTEMPT,
                    wants_booking=True,
                )
            if missing_name and missing_phone:
                return finish(self._phrase("ask_name_phone", lang), AIState.BOOKING_ATTEMPT)
            if missing_phone:
                return finish(self._phrase("ask_phone", lang), AIState.BOOKING_ATTEMPT)
            slot = context.free_slots[0] if context.free_slots else ""
            if slot:
                return finish(
                    self._phrase("booking_offer", lang, slot=slot), AIState.BOOKING_ATTEMPT
                )
            return finish(self._phrase("ask_name_phone", lang), AIState.BOOKING_ATTEMPT)

        # 4. Price question ---------------------------------------------- #
        if understanding.has("price"):
            service = self._match_service(context, customer_message) or (
                context.services[0] if len(context.services) == 1 else None
            )
            if service:
                name = (
                    service.get("name_ru")
                    if lang == "ru" and service.get("name_ru")
                    else service.get("name")
                )
                return finish(
                    self._phrase(
                        "price_answer",
                        lang,
                        service=name,
                        price=service.get("price_label", ""),
                        promo=self._promo_text(context, lang),
                    ),
                    AIState.OFFER_PRESENTATION,
                    kb_refs=[f"service:{service.get('id')}"],
                )
            if context.services:
                return finish(
                    self._phrase("ask_need", lang, services=self._service_list(context, lang)),
                    AIState.NEED_DISCOVERY,
                )
            return finish(
                self._phrase("price_unknown", lang),
                AIState.HUMAN_HANDOFF,
                escalate=True,
                reason=ESCALATION_REASONS["unknown_question"],
                confidence=0.3,
            )

        # 5. Schedule / free slots ---------------------------------------- #
        if understanding.has("schedule"):
            hours = (
                context.branches[0].get("hours", "09:00–19:00")
                if context.branches
                else "09:00–19:00"
            )
            return finish(
                self._phrase("schedule_answer", lang, hours=hours, slots=self._slots_text(context)),
                AIState.BOOKING_ATTEMPT,
            )

        # 6. Address ------------------------------------------------------ #
        if understanding.has("address"):
            if context.branches:
                text = "; ".join(
                    f"{b.get('name')} — {b.get('address')}" for b in context.branches[:3]
                )
                return finish(
                    self._phrase("address_answer", lang, branches=text),
                    AIState.NEED_DISCOVERY,
                    kb_refs=["branch"],
                )
            return finish(
                self._phrase("unknown", lang),
                AIState.HUMAN_HANDOFF,
                escalate=True,
                reason=ESCALATION_REASONS["unknown_question"],
                confidence=0.2,
            )

        # 7. Greeting ----------------------------------------------------- #
        if understanding.has("greeting") or context.state in (
            AIState.NEW_LEAD,
            AIState.GREETING,
        ):
            key = "greeting" if context.within_working_hours else "greeting_after_hours"
            greeting = self._phrase(
                key, lang, company=context.company_name or "—", agent=context.agent_name
            )
            if context.services and context.within_working_hours:
                greeting += "\n\n" + self._phrase(
                    "ask_need", lang, services=self._service_list(context, lang)
                )
            return finish(greeting, AIState.NEED_DISCOVERY)

        # 8. Confirmation / thanks ---------------------------------------- #
        if understanding.has("thanks") and not understanding.has("price", "booking"):
            return finish(self._phrase("thanks", lang), AIState.FOLLOW_UP)

        if understanding.has("confirm") and context.state in (
            AIState.OFFER_PRESENTATION,
            AIState.QUALIFICATION,
        ):
            return finish(self._phrase("ask_name_phone", lang), AIState.BOOKING_ATTEMPT)

        # 9. Knowledge base lookup ---------------------------------------- #
        snippet = self._knowledge_answer(context, understanding)
        if snippet:
            return finish(snippet, AIState.QUALIFICATION, kb_refs=["kb"], confidence=0.8)

        # 10. Nothing matched: never invent an answer --------------------- #
        return finish(
            self._phrase("unknown", lang),
            AIState.HUMAN_HANDOFF,
            escalate=True,
            reason=ESCALATION_REASONS["unknown_question"],
            confidence=0.1,
        )

    # ------------------------------------------------------------------ #
    def analyze_call(self, transcript: str, language: str = "uz") -> dict[str, Any]:
        """Rule-based call analysis (summary, objections, next step, quality)."""
        text = transcript or ""
        understanding = nlu.understand(text, language)
        lang = understanding.language if understanding.language in ("uz", "ru") else language
        got_phone = bool(understanding.phone) or "raqam" in text.lower() or "номер" in text.lower()
        got_booking = (
            understanding.has("booking") or "yozdim" in text.lower() or "записыва" in text.lower()
        )
        got_purpose = understanding.has("price", "booking", "schedule", "address")

        objections: list[str] = []
        if understanding.has("objection_price"):
            objections.append("Narx qimmat" if lang == "uz" else "Дорого")
        if understanding.has("decline"):
            objections.append("Hozircha qiziqmaydi" if lang == "uz" else "Пока не интересно")

        mistakes: list[str] = []
        if not got_phone:
            mistakes.append(
                "Operator telefon raqamini olmadi" if lang == "uz" else "Оператор не взял номер"
            )
        if not got_booking and understanding.sentiment != Sentiment.NEGATIVE:
            mistakes.append("Bron taklif qilinmadi" if lang == "uz" else "Не предложена запись")

        if got_booking:
            next_step = "Bronni tasdiqlash" if lang == "uz" else "Подтвердить запись"
        elif understanding.sentiment == Sentiment.NEGATIVE:
            next_step = "Rahbar aralashuvi" if lang == "uz" else "Вмешательство руководителя"
        else:
            next_step = "Qayta qo'ng'iroq qilish" if lang == "uz" else "Перезвонить"

        quality = 40
        quality += 20 if got_phone else 0
        quality += 20 if got_booking else 0
        quality += 10 if got_purpose else 0
        quality += 10 if understanding.sentiment == Sentiment.POSITIVE else 0
        quality -= 20 if understanding.sentiment == Sentiment.NEGATIVE else 0
        quality = max(0, min(100, quality))

        summary_words = " ".join(text.split()[:35])
        return {
            "summary": summary_words + ("…" if len(text.split()) > 35 else ""),
            "customer_need": ", ".join(sorted(understanding.intents)) or "—",
            "objections": "; ".join(objections) or "—",
            "operator_mistakes": "; ".join(mistakes) or "—",
            "next_best_action": next_step,
            "sentiment": understanding.sentiment,
            "quality_score": quality,
            "got_phone": got_phone,
            "got_purpose": got_purpose,
            "got_booking": got_booking,
            "alert_raised": understanding.sentiment == Sentiment.NEGATIVE,
        }
