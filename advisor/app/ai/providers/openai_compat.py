"""OpenAI-mos HTTP provayderlar uchun umumiy asos (Groq, OpenRouter).

Groq va OpenRouter ikkalasi ham OpenAI Chat Completions API'sini taqdim etadi
va bepul tariflarga ega. Farqi faqat base_url, model va kalitda — shu sabab
bitta implementatsiya ikkalasiga xizmat qiladi (DRY).
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx

from app.ai.base import (
    CompletionRequest,
    CompletionResult,
    LLMProvider,
    messages_to_dicts,
)
from app.core.exceptions import AIProviderError
from app.core.logging_setup import get_logger

logger = get_logger(__name__)


class OpenAICompatProvider(LLMProvider):
    def __init__(
        self,
        name: str,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        extra_headers: dict[str, str] | None = None,
    ):
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._extra_headers = extra_headers or {}

    @property
    def model(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            **self._extra_headers,
        }

    def _payload(self, request: CompletionRequest, stream: bool) -> dict:
        return {
            "model": self._model,
            "messages": messages_to_dicts(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": stream,
        }

    def complete(self, request: CompletionRequest) -> CompletionResult:
        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(request, stream=False),
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise AIProviderError(
                f"{self.name} HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise AIProviderError(f"{self.name} xatosi: {exc}") from exc

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return CompletionResult(
            content=choice or "",
            provider=self.name,
            model=self._model,
            tokens=usage.get("total_tokens", 0),
        )

    def stream(self, request: CompletionRequest) -> Iterator[str]:
        try:
            with httpx.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(request, stream=True),
                timeout=self._timeout,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        delta = json.loads(payload)["choices"][0]["delta"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                    piece = delta.get("content")
                    if piece:
                        yield piece
        except httpx.HTTPStatusError as exc:
            raise AIProviderError(
                f"{self.name} HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(f"{self.name} stream xatosi: {exc}") from exc
