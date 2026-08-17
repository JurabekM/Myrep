"""OpenAI-compatible chat-completions provider.

Works with any endpoint that speaks the ``/v1/chat/completions`` protocol.
On any failure the caller falls back to :class:`DemoRuleBasedProvider`, so the
application keeps working without internet access.
"""

from __future__ import annotations

import json
import logging
import time as _time
from typing import Any

import httpx

from app.integrations.base import AdapterCredentials, AdapterResult
from app.integrations.llm import nlu
from app.integrations.llm.base_llm import AgentContext, AgentReply, LLMProvider
from app.models.enums import AIState
from app.utils.dates import now

logger = logging.getLogger(__name__)
TIMEOUT = 45.0

SYSTEM_TEMPLATE = """Sen "{agent}" ismli virtual sotuv operatorisan. Kompaniya: {company}.
Ohang: {tone}. Javob tili: {language} (mijoz qaysi tilda yozsa, o'sha tilda javob ber).
Vazifang: mijozni iliq kutib olish, ehtiyojini aniqlash, tasdiqlangan ma'lumot asosida
javob berish va uni bron/qabul/test-drive bosqichiga olib borish.

QAT'IY QOIDALAR:
1. Faqat quyidagi tasdiqlangan ma'lumotdan foydalan. Narx, chegirma yoki aksiyani o'zingdan to'qima.
2. Tibbiy, huquqiy yoki moliyaviy maslahat berma.
3. Javobni bilmasang yoki mijoz salbiy kayfiyatda bo'lsa — escalate=true qil.
4. "Men sun'iy intellektman" deb keraksiz ta'kidlama.
5. Qisqa, hurmatli va aniq yoz (2-5 gap).

TASDIQLANGAN MA'LUMOT:
Xizmatlar: {services}
Filiallar: {branches}
Aksiyalar: {promos}
Bilimlar bazasi: {knowledge}
Bo'sh vaqtlar: {slots}
Ichki eslatmalar (mijozga ko'rsatma): {notes}
Taqiqlangan mavzular: {forbidden}
Joriy holat: {state}
Mijoz: {lead_name} / {lead_phone} / qiziqish: {interest}

Javobni FAQAT JSON obyekt sifatida qaytar:
{{"reply": "matn", "next_state": "one_of:{states}", "escalate": true|false,
 "escalation_reason": "matn", "wants_booking": true|false,
 "extracted": {{"full_name": "", "phone": "", "datetime": ""}}}}
"""


class OpenAICompatibleProvider(LLMProvider):
    """Chat-completions client for OpenAI and compatible gateways."""

    provider = "openai_compatible"
    title = "OpenAI-compatible LLM"

    def __init__(self, credentials: AdapterCredentials | None = None) -> None:
        super().__init__(credentials)
        self.model = self.credentials.get("model", "gpt-4o-mini") or "gpt-4o-mini"
        self.base_url = (
            self.credentials.get("base_url", "https://api.openai.com/v1")
            or "https://api.openai.com/v1"
        ).rstrip("/")

    def is_configured(self) -> bool:
        """Requires an API key."""
        return self.credentials.has("api_key")

    def _headers(self) -> dict[str, str]:
        """Authorization headers."""
        return {
            "Authorization": f"Bearer {self.credentials.get('api_key')}",
            "Content-Type": "application/json",
        }

    def test_connection(self) -> AdapterResult:
        """List models to validate the key and the base URL."""
        if not self.is_configured():
            return AdapterResult.failure("API key kiritilmagan", "not_configured")
        try:
            response = httpx.get(
                f"{self.base_url}/models", headers=self._headers(), timeout=TIMEOUT
            )
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Ulanib bo'lmadi: {type(exc).__name__}", "network")
        if response.status_code >= 400:
            self.last_error = f"HTTP {response.status_code}"
            return AdapterResult.failure(self.last_error, "api")
        self.last_error = ""
        self.last_sync_at = now()
        return AdapterResult.success(f"{self.model} ulandi")

    # ------------------------------------------------------------------ #
    def _chat(self, messages: list[dict[str, str]], max_tokens: int = 600) -> str:
        """Low level chat call returning the assistant message text."""
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json={
                "model": self.model,
                "messages": messages,
                "temperature": float(self.credentials.settings.get("temperature", 0.3) or 0.3),
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]

    def _build_system(self, context: AgentContext) -> str:
        """Render the system prompt from the approved context."""
        services = (
            "; ".join(f"{s.get('name')} — {s.get('price_label')}" for s in context.services[:12])
            or "—"
        )
        branches = (
            "; ".join(
                f"{b.get('name')} ({b.get('address')}, {b.get('hours')})"
                for b in context.branches[:5]
            )
            or "—"
        )
        return SYSTEM_TEMPLATE.format(
            agent=context.agent_name,
            company=context.company_name,
            tone=context.tone,
            language=context.language,
            services=services,
            branches=branches,
            promos="; ".join(context.promos) or "—",
            knowledge=" | ".join(context.knowledge[:8]) or "—",
            slots=", ".join(context.free_slots[:5]) or "—",
            notes=" | ".join(context.internal_notes[:5]) or "—",
            forbidden=", ".join(context.forbidden_topics) or "—",
            state=context.state,
            lead_name=context.lead_name or "—",
            lead_phone=context.lead_phone or "—",
            interest=context.lead_interest or "—",
            states=",".join(s.value for s in AIState),
        )

    def generate_reply(self, context: AgentContext, customer_message: str) -> AgentReply:
        """Ask the model for the next reply; raises on transport failure."""
        started = _time.perf_counter()
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._build_system(context)}
        ]
        for turn in context.history[-12:]:
            role = "user" if turn.role == "customer" else "assistant"
            messages.append({"role": role, "content": turn.text})
        messages.append({"role": "user", "content": customer_message})

        raw = self._chat(messages)
        try:
            parsed: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"reply": raw.strip(), "next_state": context.state}

        understanding = nlu.understand(customer_message, context.language)
        extracted = {k: str(v) for k, v in (parsed.get("extracted") or {}).items() if v}
        if understanding.phone and "phone" not in extracted:
            extracted["phone"] = understanding.phone
        extracted["language"] = (
            understanding.language if understanding.language != "unknown" else context.language
        )

        next_state = str(parsed.get("next_state") or context.state)
        if next_state not in {s.value for s in AIState}:
            next_state = AIState.QUALIFICATION
        return AgentReply(
            text=str(parsed.get("reply") or "").strip(),
            next_state=next_state,
            escalate=bool(parsed.get("escalate")),
            escalation_reason=str(parsed.get("escalation_reason") or ""),
            wants_booking=bool(parsed.get("wants_booking")),
            extracted=extracted,
            confidence=0.9,
            provider=self.provider,
            model=self.model,
            latency_ms=int((_time.perf_counter() - started) * 1000),
        )

    def analyze_call(self, transcript: str, language: str = "uz") -> dict[str, Any]:
        """Ask the model to analyse a call transcript; returns a plain dict."""
        prompt = (
            "Quyidagi qo'ng'iroq transkriptini tahlil qil va FAQAT JSON qaytar: "
            '{"summary": "", "customer_need": "", "objections": "", "operator_mistakes": "", '
            '"next_best_action": "", "sentiment": "positive|neutral|negative", '
            '"quality_score": 0-100, "got_phone": true|false, "got_purpose": true|false, '
            '"got_booking": true|false}\n\nTranskript:\n' + transcript
        )
        raw = self._chat([{"role": "user", "content": prompt}], max_tokens=700)
        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        data["alert_raised"] = data.get("sentiment") == "negative"
        return data
