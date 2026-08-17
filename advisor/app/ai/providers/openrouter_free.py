"""OpenRouter bepul model provayderi.

OpenRouter ``:free`` bilan tugaydigan modellarni bepul taqdim etadi (masalan
``meta-llama/llama-3.3-70b-instruct:free``). Kalit https://openrouter.ai dan
bepul olinadi. Reyting uchun ixtiyoriy sarlavhalar qo'shiladi.
"""

from __future__ import annotations

from app.ai.providers.openai_compat import OpenAICompatProvider


class OpenRouterProvider(OpenAICompatProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "meta-llama/llama-3.3-70b-instruct:free",
    ):
        super().__init__(
            "openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            model=model,
            extra_headers={
                "HTTP-Referer": "https://localhost/ai-business-advisor",
                "X-Title": "AI Business Advisor Uzbekistan",
            },
        )
