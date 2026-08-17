"""OpenAI-compatible provider.

One implementation covers every vendor exposing the OpenAI Chat Completions
API: OpenAI itself, DeepSeek, Qwen (DashScope compatible-mode), Llama serving
endpoints (vLLM/TGI/Together) and local Ollama (/v1). Only base_url + key
differ, so subclasses are pure configuration.
"""

from collections.abc import AsyncIterator

from openai import APIError, AsyncOpenAI

from app.ai.base import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    ProviderCapabilities,
    StreamChunk,
    Usage,
)
from app.core.exceptions import AIProviderError


def _to_openai_messages(messages: tuple[ChatMessage, ...]) -> list[dict]:
    result: list[dict] = []
    for msg in messages:
        if msg.images:
            content: list[dict] = [{"type": "text", "text": msg.content}]
            content.extend(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{img['mime_type']};base64,{img['data']}"},
                }
                for img in msg.images
            )
            result.append({"role": msg.role.value, "content": content})
        else:
            result.append({"role": msg.role.value, "content": msg.content})
    return result


class OpenAICompatProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        capabilities: ProviderCapabilities | None = None,
    ):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._capabilities = capabilities or ProviderCapabilities(
            vision=True, json_mode=True, max_context=128_000, embeddings=True
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        try:
            response = await self._client.chat.completions.create(
                model=request.model,
                messages=_to_openai_messages(request.messages),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                response_format={"type": "json_object"} if request.json_mode else {"type": "text"},
            )
        except APIError as exc:
            raise AIProviderError(f"{self.name} xatosi: {exc}") from exc
        choice = response.choices[0]
        usage = response.usage
        return CompletionResponse(
            content=choice.message.content or "",
            model=response.model,
            usage=Usage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            ),
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        try:
            stream = await self._client.chat.completions.create(
                model=request.model,
                messages=_to_openai_messages(request.messages),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
            usage: Usage | None = None
            async for chunk in stream:
                if chunk.usage is not None:
                    usage = Usage(
                        input_tokens=chunk.usage.prompt_tokens,
                        output_tokens=chunk.usage.completion_tokens,
                    )
                if chunk.choices and chunk.choices[0].delta.content:
                    yield StreamChunk(delta=chunk.choices[0].delta.content)
            yield StreamChunk(delta="", finished=True, usage=usage)
        except APIError as exc:
            raise AIProviderError(f"{self.name} stream xatosi: {exc}") from exc

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        try:
            response = await self._client.embeddings.create(model=model, input=texts)
        except APIError as exc:
            raise AIProviderError(f"{self.name} embedding xatosi: {exc}") from exc
        return [item.embedding for item in response.data]


class DeepSeekProvider(OpenAICompatProvider):
    name = "deepseek"

    def __init__(self, api_key: str):
        super().__init__(
            api_key,
            base_url="https://api.deepseek.com/v1",
            capabilities=ProviderCapabilities(vision=False, json_mode=True, max_context=64_000),
        )


class QwenProvider(OpenAICompatProvider):
    name = "qwen"

    def __init__(self, api_key: str):
        super().__init__(
            api_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            capabilities=ProviderCapabilities(vision=True, json_mode=True, max_context=128_000),
        )


class LlamaProvider(OpenAICompatProvider):
    """Any OpenAI-compatible Llama serving endpoint (vLLM, TGI, Together...)."""

    name = "llama"

    def __init__(self, api_key: str, base_url: str):
        super().__init__(
            api_key,
            base_url=base_url,
            capabilities=ProviderCapabilities(vision=False, json_mode=False, max_context=128_000),
        )


class OllamaProvider(OpenAICompatProvider):
    """Local models via Ollama's OpenAI-compatible endpoint."""

    name = "local"

    def __init__(self, base_url: str):
        super().__init__(
            api_key="ollama",  # noqa: S106 — Ollama ignores the key
            base_url=f"{base_url.rstrip('/')}/v1",
            capabilities=ProviderCapabilities(
                vision=False, json_mode=False, max_context=32_000, embeddings=True
            ),
        )
