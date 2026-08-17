"""LLM provider abstraction (port).

Every provider — OpenAI, Anthropic, Gemini, DeepSeek, Mistral, Llama, Qwen,
local Ollama — implements this interface, so the rest of the app never
imports a vendor SDK directly.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class ChatMessage:
    role: ChatRole
    content: str
    # Optional vision input: list of {"mime_type": ..., "data": base64}
    images: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True)
class CompletionRequest:
    messages: tuple[ChatMessage, ...]
    model: str  # provider-local model name, e.g. "gpt-4o"
    temperature: float = 0.4
    max_tokens: int = 2048
    json_mode: bool = False


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class CompletionResponse:
    content: str
    model: str
    usage: Usage = field(default_factory=Usage)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StreamChunk:
    delta: str
    finished: bool = False
    usage: Usage | None = None  # present on the final chunk when available


@dataclass(frozen=True)
class ProviderCapabilities:
    vision: bool = False
    json_mode: bool = False
    max_context: int = 128_000
    embeddings: bool = False


class LLMProvider(ABC):
    """Vendor adapter. `name` is the registry key used in model ids like
    'openai:gpt-4o' or 'anthropic:claude-sonnet-5'."""

    name: str

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse: ...

    @abstractmethod
    def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]: ...

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        raise NotImplementedError(f"{self.name} embeddinglarni qo'llab-quvvatlamaydi")

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities: ...


def parse_model_id(model_id: str) -> tuple[str, str]:
    """Split 'provider:model' → (provider, model)."""
    provider, sep, model = model_id.partition(":")
    if not provider or not sep or not model:
        raise ValueError(f"Model id 'provider:model' formatida bo'lishi kerak: {model_id!r}")
    return provider, model
