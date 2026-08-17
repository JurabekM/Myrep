"""Google Gemini bepul tarif provayderi.

Gemini API bepul tarifda kunlik so'rovlar limiti bilan ishlaydi; kalit
https://aistudio.google.com/app/apikey dan bepul (karta shart emas) olinadi.
Gemini o'zining ``generativelanguage`` REST endpointini ishlatadi (OpenAI
formatidan farq qiladi), shuning uchun alohida implementatsiya.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx

from app.ai.base import (
    ChatMessage,
    CompletionRequest,
    CompletionResult,
    LLMProvider,
    Role,
)
from app.core.exceptions import AIProviderError
from app.core.logging_setup import get_logger

logger = get_logger(__name__)

_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _to_gemini_contents(messages: tuple[ChatMessage, ...]) -> tuple[str | None, list[dict]]:
    """Gemini system'ni alohida oladi; user/assistant -> user/model."""
    system_parts = [m.content for m in messages if m.role is Role.SYSTEM]
    contents = [
        {
            "role": "user" if m.role is Role.USER else "model",
            "parts": [{"text": m.content}],
        }
        for m in messages
        if m.role is not Role.SYSTEM
    ]
    system = "\n\n".join(system_parts) if system_parts else None
    return system, contents


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", timeout: float = 60.0):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _body(self, request: CompletionRequest) -> dict:
        system, contents = _to_gemini_contents(request.messages)
        body: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        return body

    def complete(self, request: CompletionRequest) -> CompletionResult:
        url = f"{_BASE}/models/{self._model}:generateContent?key={self._api_key}"
        try:
            response = httpx.post(url, json=self._body(request), timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise AIProviderError(
                f"gemini HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise AIProviderError(f"gemini xatosi: {exc}") from exc

        candidates = data.get("candidates", [])
        if not candidates:
            raise AIProviderError("gemini bo'sh javob qaytardi (kontent filtri bo'lishi mumkin)")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        usage = data.get("usageMetadata", {})
        return CompletionResult(
            content=text,
            provider=self.name,
            model=self._model,
            tokens=usage.get("totalTokenCount", 0),
        )

    def stream(self, request: CompletionRequest) -> Iterator[str]:
        url = (
            f"{_BASE}/models/{self._model}:streamGenerateContent"
            f"?alt=sse&key={self._api_key}"
        )
        try:
            with httpx.stream(
                "POST", url, json=self._body(request), timeout=self._timeout
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        chunk = json.loads(line[6:])
                        parts = chunk["candidates"][0]["content"]["parts"]
                        for part in parts:
                            if part.get("text"):
                                yield part["text"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        except httpx.HTTPStatusError as exc:
            raise AIProviderError(f"gemini HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(f"gemini stream xatosi: {exc}") from exc
