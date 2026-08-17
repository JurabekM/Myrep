"""Gibrid ModelRouter — provayderlarni ustuvorlik bo'yicha sinaydi.

Bitta provayder ishlamasa (limit tugadi, internet yo'q, xato), keyingisiga
o'tadi. Shu sabab bitta bepul tarif limiti tugasa ham tizim to'xtamaydi va
oxirida har doim oflayn lokal model (agar mavjud) fallback bo'lib qoladi.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import date

from app.ai.base import CompletionRequest, CompletionResult, LLMProvider
from app.ai.providers.gemini_free import GeminiProvider
from app.ai.providers.groq_free import GroqProvider
from app.ai.providers.local_llama import LocalLlamaProvider
from app.ai.providers.openrouter_free import OpenRouterProvider
from app.core.config import AppConfig
from app.core.exceptions import AIProviderError, AllProvidersFailedError
from app.core.logging_setup import get_logger
from app.data.repositories.kb_repo import UsageRepository

logger = get_logger(__name__)


def build_providers(config: AppConfig) -> dict[str, LLMProvider]:
    """Barcha ma'lum provayderlarni yaratadi (sozlanmagan bo'lsa ham obyekt
    yaratiladi; ``is_available()`` filtrlaydi)."""
    ai = config.ai
    return {
        "groq": GroqProvider(ai.groq_api_key, ai.groq_model),
        "gemini": GeminiProvider(ai.gemini_api_key, ai.gemini_model),
        "openrouter": OpenRouterProvider(ai.openrouter_api_key, ai.openrouter_model),
        "local": LocalLlamaProvider(
            config.paths.models_dir, ai.local_model_filename, ai.local_context_size
        ),
    }


class ModelRouter:
    def __init__(
        self,
        providers: dict[str, LLMProvider],
        order: list[str],
        usage_repo: UsageRepository | None = None,
    ):
        self._providers = providers
        self._order = order
        self._usage = usage_repo

    def available_providers(self) -> list[str]:
        return [name for name in self._order if self._is_available(name)]

    def _is_available(self, name: str) -> bool:
        provider = self._providers.get(name)
        return provider is not None and provider.is_available()

    def _candidates(self) -> list[LLMProvider]:
        candidates = [
            self._providers[name] for name in self._order if self._is_available(name)
        ]
        if not candidates:
            raise AllProvidersFailedError(
                "Hech qanday AI provayder sozlanmagan. Sozlamalar sahifasida bepul "
                "API kalit kiriting yoki models/ papkasiga GGUF model joylashtiring."
            )
        return candidates

    def _record(self, provider: str, module: str, tokens: int) -> None:
        if self._usage is not None:
            try:
                self._usage.record(date.today().isoformat(), module, provider, tokens)
            except Exception:  # statistika xatosi asosiy oqimni to'xtatmasin
                logger.debug("Usage yozishda xato", exc_info=True)

    def complete(self, request: CompletionRequest, *, module: str = "chat") -> CompletionResult:
        errors: list[str] = []
        for provider in self._candidates():
            try:
                result = provider.complete(request)
                self._record(provider.name, module, result.tokens)
                return result
            except AIProviderError as exc:
                logger.warning("Provayder ishlamadi (%s): %s", provider.name, exc)
                errors.append(f"{provider.name}: {exc}")
        raise AllProvidersFailedError(
            "Barcha AI provayderlar ishlamadi:\n" + "\n".join(errors)
        )

    def stream(
        self,
        request: CompletionRequest,
        *,
        module: str = "chat",
        on_provider: Callable[[str], None] | None = None,
    ) -> Iterator[str]:
        """Oqim; birinchi ishlagan provayderdan token yetkazadi.

        Agar provayder hech narsa chiqarmasdan xato bersa, keyingisiga o'tiladi.
        Token chiqa boshlagach xato bo'lsa — qayta urinilmaydi (dublikat bo'lmasin).
        """
        errors: list[str] = []
        for provider in self._candidates():
            emitted = False
            try:
                if on_provider is not None:
                    on_provider(provider.name)
                for piece in provider.stream(request):
                    emitted = True
                    yield piece
                self._record(provider.name, module, 0)
                return
            except AIProviderError as exc:
                logger.warning("Stream ishlamadi (%s): %s", provider.name, exc)
                errors.append(f"{provider.name}: {exc}")
                if emitted:
                    raise
        raise AllProvidersFailedError(
            "Barcha AI provayderlar ishlamadi:\n" + "\n".join(errors)
        )
