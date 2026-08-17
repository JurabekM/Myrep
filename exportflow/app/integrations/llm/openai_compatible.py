"""OpenAI-compatible chat completion adapter (works with any compatible host)."""

from __future__ import annotations

import json

from app.integrations.base import ProviderResult
from app.integrations.llm.base import GenerationRequest, LLMProvider
from app.utils.logging_setup import get_logger

log = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are an export sales copywriter for an Uzbek manufacturer. "
    "Write professional B2B export content. Follow these hard rules:\n"
    "1. Use ONLY the facts provided in the FACTS block. Never invent MOQ, price, "
    "lead time, Incoterms, capacity or certificates.\n"
    "2. If no certificate is listed, never write 'certified' or name any certificate.\n"
    "3. English must follow international B2B trade style; Russian must read as natural "
    "post-Soviet business correspondence; Uzbek must be formal and clear.\n"
    "4. Return plain text without markdown fences."
)


class OpenAICompatibleProvider(LLMProvider):
    """Calls a ``/v1/chat/completions`` endpoint using httpx."""

    code = "openai_compatible"
    label = "OpenAI-compatible API"
    fields = (
        ("base_url", "Base URL", False),
        ("model", "Model", False),
        ("api_key", "API key", True),
        ("timeout", "Timeout (s)", False),
    )

    @property
    def base_url(self) -> str:
        """Endpoint root, defaulting to the public OpenAI API."""
        return (self.settings.get("base_url") or "https://api.openai.com/v1").rstrip("/")

    @property
    def model(self) -> str:
        """Configured model name."""
        return self.settings.get("model") or "gpt-4o-mini"

    def _headers(self) -> dict[str, str]:
        api_key = self.secrets.get("api_key") or ""
        if not api_key:
            raise ValueError("API key is not configured")
        return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def test_connection(self) -> ProviderResult:
        """Send a minimal completion request to verify the credentials."""
        try:
            import httpx

            with httpx.Client(timeout=float(self.settings.get("timeout") or 20)) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 5,
                    },
                )
            if response.status_code >= 400:
                return ProviderResult.failure(f"HTTP {response.status_code}")
            return ProviderResult.success("Connection successful")
        except Exception as exc:
            log.warning("LLM connection test failed: %s", type(exc).__name__)
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")

    def generate(self, request: GenerationRequest) -> ProviderResult:
        """Generate content through the remote model."""
        user_prompt = (
            f"CONTENT TYPE: {request.content_type}\n"
            f"LANGUAGE: {request.language}\n"
            f"TONE: {request.tone}\n"
            f"MAX WORDS: {request.max_words}\n"
            f"EXTRA INSTRUCTION: {request.instruction or '-'}\n\n"
            f"FACTS (JSON):\n{json.dumps(request.facts, ensure_ascii=False, default=str)}"
        )
        try:
            import httpx

            with httpx.Client(timeout=float(self.settings.get("timeout") or 60)) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": _SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.4,
                    },
                )
            if response.status_code >= 400:
                return ProviderResult.failure(f"HTTP {response.status_code}")
            payload = response.json()
            text = payload["choices"][0]["message"]["content"].strip()
            return ProviderResult.success("Generated", data=text)
        except Exception as exc:
            log.warning("LLM generation failed: %s", type(exc).__name__)
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")
