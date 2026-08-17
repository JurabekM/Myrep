"""Google Gemini provider (OpenAI-compatible endpoint).

Google ships an OpenAI-compatible surface for the Gemini API, which lets us
reuse the battle-tested OpenAICompatProvider instead of a second SDK code
path. Embeddings are supported through the same endpoint.
"""

from app.ai.base import ProviderCapabilities
from app.ai.providers.openai_compat import OpenAICompatProvider


class GeminiProvider(OpenAICompatProvider):
    name = "gemini"

    def __init__(self, api_key: str):
        super().__init__(
            api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            capabilities=ProviderCapabilities(
                vision=True, json_mode=True, max_context=1_000_000, embeddings=True
            ),
        )
