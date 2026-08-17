"""Groq bepul tarif provayderi.

Groq OpenAI-mos API taqdim etadi va bepul tarifda kunlik cheklov bilan juda
tez inferens beradi. Kalit https://console.groq.com dan bepul (karta shart
emas) olinadi.
"""

from __future__ import annotations

from app.ai.providers.openai_compat import OpenAICompatProvider


class GroqProvider(OpenAICompatProvider):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        super().__init__(
            "groq",
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
            model=model,
        )
