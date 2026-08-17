"""LLM provider contract."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field

from app.integrations.base import BaseProvider, ProviderResult


@dataclass
class GenerationRequest:
    """Everything an LLM adapter needs to produce export sales copy.

    ``facts`` is the authoritative product/buyer data. Providers must not add
    claims that are not present in it.
    """

    content_type: str
    language: str = "en"
    tone: str = "professional"
    instruction: str = ""
    facts: dict = field(default_factory=dict)
    max_words: int = 350


class LLMProvider(BaseProvider):
    """Generates multilingual B2B export content."""

    kind = "llm"

    @abstractmethod
    def generate(self, request: GenerationRequest) -> ProviderResult:
        """Return generated text in ``ProviderResult.data``."""
