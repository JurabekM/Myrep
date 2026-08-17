"""AI provayder abstraksiyasi (port).

Har bir provayder — Groq, Gemini, OpenRouter (bepul tariflar) va lokal
llama-cpp — shu interfeysni amalga oshiradi. Router faqat shu abstraksiyaga
tayanadi, konkret provayderni bilmaydi (SOLID: DIP).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


@dataclass(frozen=True)
class CompletionRequest:
    messages: tuple[ChatMessage, ...]
    temperature: float = 0.4
    max_tokens: int = 2048


@dataclass(frozen=True)
class CompletionResult:
    content: str
    provider: str
    model: str
    tokens: int = 0


class LLMProvider(ABC):
    """Vendor adapteri. ``name`` — router va statistikada ishlatiladigan kalit."""

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Provayder sozlangan va ishlatishga tayyormi (kalit bor / model mavjud)."""

    @abstractmethod
    def complete(self, request: CompletionRequest) -> CompletionResult:
        """To'liq javob (bloklovchi)."""

    def stream(self, request: CompletionRequest) -> Iterator[str]:
        """Oqim (token-token). Standart: to'liq javobni bir bo'lak qilib qaytaradi.

        Streamni qo'llab-quvvatlaydigan provayderlar buni qayta yozadi.
        """
        yield self.complete(request).content


def messages_to_dicts(messages: tuple[ChatMessage, ...]) -> list[dict]:
    """OpenAI-mos formatdagi ro'yxat (Groq/OpenRouter uchun)."""
    return [{"role": m.role.value, "content": m.content} for m in messages]
