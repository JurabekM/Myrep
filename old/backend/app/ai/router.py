"""ModelRouter: provider registry, fallback chain, cost tracking.

Providers are registered only when their API key is configured. Every call
goes through the fallback chain so a single vendor outage degrades quality,
not availability.
"""

from collections.abc import AsyncIterator
from datetime import date

from app.ai.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    StreamChunk,
    parse_model_id,
)
from app.ai.providers.anthropic_provider import AnthropicProvider
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.mistral_provider import MistralProvider
from app.ai.providers.openai_compat import (
    DeepSeekProvider,
    LlamaProvider,
    OllamaProvider,
    OpenAICompatProvider,
    QwenProvider,
)
from app.core.config import Settings
from app.core.exceptions import AIProviderError, AllProvidersFailedError
from app.core.logging import get_logger
from app.domain.interfaces.repositories import UsageStatsRepository

logger = get_logger(__name__)

# USD per 1M tokens (input, output) — used for cost accounting; admin can
# refine via model configuration. Unknown models fall back to (1.0, 3.0).
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "deepseek-chat": (0.27, 1.1),
    "gemini-2.0-flash": (0.1, 0.4),
    "mistral-large-latest": (2.0, 6.0),
}
_DEFAULT_PRICING = (1.0, 3.0)


def _cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = _PRICING.get(model, _DEFAULT_PRICING)
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


def build_provider_registry(settings: Settings) -> dict[str, LLMProvider]:
    registry: dict[str, LLMProvider] = {}
    if settings.openai_api_key:
        registry["openai"] = OpenAICompatProvider(settings.openai_api_key.get_secret_value())
    if settings.anthropic_api_key:
        registry["anthropic"] = AnthropicProvider(settings.anthropic_api_key.get_secret_value())
    if settings.google_api_key:
        registry["gemini"] = GeminiProvider(settings.google_api_key.get_secret_value())
    if settings.deepseek_api_key:
        registry["deepseek"] = DeepSeekProvider(settings.deepseek_api_key.get_secret_value())
    if settings.mistral_api_key:
        registry["mistral"] = MistralProvider(settings.mistral_api_key.get_secret_value())
    if settings.qwen_api_key:
        registry["qwen"] = QwenProvider(settings.qwen_api_key.get_secret_value())
    if settings.llama_api_base:
        key = settings.llama_api_key.get_secret_value() if settings.llama_api_key else "none"
        registry["llama"] = LlamaProvider(key, settings.llama_api_base)
    # Local Ollama is always registered; calls fail fast if the daemon is down.
    registry["local"] = OllamaProvider(settings.ollama_base_url)
    return registry


class ModelRouter:
    def __init__(
        self,
        registry: dict[str, LLMProvider],
        settings: Settings,
        usage_stats: UsageStatsRepository | None = None,
        fallback_chain: list[str] | None = None,
    ):
        self._registry = registry
        self._settings = settings
        self._usage = usage_stats
        self._fallback_chain = fallback_chain or self._default_fallbacks()

    def _default_fallbacks(self) -> list[str]:
        preferred = ["openai:gpt-4o", "anthropic:claude-sonnet-5", "deepseek:deepseek-chat"]
        return [m for m in preferred if parse_model_id(m)[0] in self._registry]

    def _provider(self, provider_name: str) -> LLMProvider:
        provider = self._registry.get(provider_name)
        if provider is None:
            raise AIProviderError(
                f"'{provider_name}' provider sozlanmagan",
                details={"available": sorted(self._registry)},
            )
        return provider

    def available_models(self) -> list[str]:
        return sorted(self._registry)

    def _candidates(self, model_id: str | None) -> list[str]:
        primary = model_id or self._settings.default_chat_model
        chain = [primary, *[m for m in self._fallback_chain if m != primary]]
        return [m for m in chain if parse_model_id(m)[0] in self._registry] or [primary]

    async def _record_usage(
        self, user_id: str | None, module: str, model: str, input_tokens: int, output_tokens: int
    ) -> None:
        if self._usage is None or user_id is None:
            return
        await self._usage.record(
            user_id,
            date.today(),
            module,
            tokens=input_tokens + output_tokens,
            cost_usd=_cost_usd(model, input_tokens, output_tokens),
        )

    async def complete(
        self,
        request: CompletionRequest,
        *,
        model_id: str | None = None,
        user_id: str | None = None,
        module: str = "chat",
    ) -> CompletionResponse:
        errors: list[str] = []
        for candidate in self._candidates(model_id):
            provider_name, model = parse_model_id(candidate)
            try:
                response = await self._provider(provider_name).complete(
                    CompletionRequest(
                        messages=request.messages,
                        model=model,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        json_mode=request.json_mode,
                    )
                )
                await self._record_usage(
                    user_id, module, model, response.usage.input_tokens,
                    response.usage.output_tokens,
                )
                return response
            except AIProviderError as exc:
                errors.append(f"{candidate}: {exc.message}")
                logger.warning("provider_failed", model=candidate, error=exc.message)
        raise AllProvidersFailedError(
            "Hech bir AI provider javob bermadi", details={"errors": errors}
        )

    async def stream(
        self,
        request: CompletionRequest,
        *,
        model_id: str | None = None,
        user_id: str | None = None,
        module: str = "chat",
    ) -> AsyncIterator[StreamChunk]:
        errors: list[str] = []
        for candidate in self._candidates(model_id):
            provider_name, model = parse_model_id(candidate)
            provider = self._provider(provider_name)
            emitted = False
            try:
                async for chunk in provider.stream(
                    CompletionRequest(
                        messages=request.messages,
                        model=model,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                    )
                ):
                    emitted = emitted or bool(chunk.delta)
                    if chunk.finished and chunk.usage:
                        await self._record_usage(
                            user_id, module, model,
                            chunk.usage.input_tokens, chunk.usage.output_tokens,
                        )
                    yield chunk
                return
            except AIProviderError as exc:
                errors.append(f"{candidate}: {exc.message}")
                logger.warning("provider_stream_failed", model=candidate, error=exc.message)
                if emitted:
                    # Mid-stream failure: cannot switch models without
                    # duplicating output — surface the error instead.
                    raise
        raise AllProvidersFailedError(
            "Hech bir AI provider javob bermadi", details={"errors": errors}
        )

    async def embed(self, texts: list[str], *, model_id: str | None = None) -> list[list[float]]:
        provider_name, model = parse_model_id(model_id or self._settings.default_embedding_model)
        return await self._provider(provider_name).embed(texts, model)
