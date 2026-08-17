"""Mistral provider via its OpenAI-compatible API."""

from app.ai.base import ProviderCapabilities
from app.ai.providers.openai_compat import OpenAICompatProvider


class MistralProvider(OpenAICompatProvider):
    name = "mistral"

    def __init__(self, api_key: str):
        super().__init__(
            api_key,
            base_url="https://api.mistral.ai/v1",
            capabilities=ProviderCapabilities(
                vision=False, json_mode=True, max_context=128_000, embeddings=True
            ),
        )
