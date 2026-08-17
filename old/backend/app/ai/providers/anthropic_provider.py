"""Anthropic Claude provider."""

from collections.abc import AsyncIterator

from anthropic import APIError, AsyncAnthropic

from app.ai.base import (
    ChatMessage,
    ChatRole,
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    ProviderCapabilities,
    StreamChunk,
    Usage,
)
from app.core.exceptions import AIProviderError


def _split_messages(messages: tuple[ChatMessage, ...]) -> tuple[str, list[dict]]:
    """Anthropic takes the system prompt separately from the message list."""
    system_parts: list[str] = []
    converted: list[dict] = []
    for msg in messages:
        if msg.role is ChatRole.SYSTEM:
            system_parts.append(msg.content)
            continue
        if msg.images:
            content: list[dict] = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img["mime_type"],
                        "data": img["data"],
                    },
                }
                for img in msg.images
            ]
            content.append({"type": "text", "text": msg.content})
            converted.append({"role": msg.role.value, "content": content})
        else:
            converted.append({"role": msg.role.value, "content": msg.content})
    return "\n\n".join(system_parts), converted


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str):
        self._client = AsyncAnthropic(api_key=api_key)

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(vision=True, json_mode=False, max_context=200_000)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        system, messages = _split_messages(request.messages)
        try:
            response = await self._client.messages.create(
                model=request.model,
                system=system or None,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        except APIError as exc:
            raise AIProviderError(f"anthropic xatosi: {exc}") from exc
        text = "".join(block.text for block in response.content if block.type == "text")
        return CompletionResponse(
            content=text,
            model=response.model,
            usage=Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        system, messages = _split_messages(request.messages)
        try:
            async with self._client.messages.stream(
                model=request.model,
                system=system or None,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(delta=text)
                final = await stream.get_final_message()
                yield StreamChunk(
                    delta="",
                    finished=True,
                    usage=Usage(
                        input_tokens=final.usage.input_tokens,
                        output_tokens=final.usage.output_tokens,
                    ),
                )
        except APIError as exc:
            raise AIProviderError(f"anthropic stream xatosi: {exc}") from exc
