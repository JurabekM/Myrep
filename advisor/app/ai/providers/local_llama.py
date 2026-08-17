"""Lokal GGUF model provayderi (llama-cpp-python).

Mutlaqo oflayn, kalitsiz fallback. ``llama-cpp-python`` og'ir bog'liqlik, shu
sabab lazy import qilinadi — o'rnatilmagan bo'lsa provayder ``is_available()``
False qaytaradi va router uni o'tkazib yuboradi.

Model fayli (``.gguf``) ``models_dir`` ichida bo'lishi kerak. Tavsiya
etiladigan yengil modellar: Qwen2.5-3B/7B-Instruct yoki Llama-3.2-3B-Instruct
(Q4_K_M kvantlangan). Model bir marta xotiraga yuklanadi va qayta ishlatiladi.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path

from app.ai.base import (
    ChatMessage,
    CompletionRequest,
    CompletionResult,
    LLMProvider,
    messages_to_dicts,
)
from app.core.exceptions import AIProviderError
from app.core.logging_setup import get_logger

logger = get_logger(__name__)


def _find_model(models_dir: Path, filename: str) -> Path | None:
    if filename:
        candidate = models_dir / filename
        return candidate if candidate.exists() else None
    ggufs = sorted(models_dir.glob("*.gguf"))
    return ggufs[0] if ggufs else None


class LocalLlamaProvider(LLMProvider):
    name = "local"

    def __init__(self, models_dir: Path, filename: str = "", context_size: int = 4096):
        self._models_dir = models_dir
        self._filename = filename
        self._context_size = context_size
        self._llm = None  # lazy
        self._load_lock = threading.Lock()

    def is_available(self) -> bool:
        try:
            import llama_cpp  # noqa: F401
        except ImportError:
            return False
        return _find_model(self._models_dir, self._filename) is not None

    def _ensure_loaded(self):  # type: ignore[no-untyped-def]
        if self._llm is not None:
            return self._llm
        with self._load_lock:
            if self._llm is not None:
                return self._llm
            try:
                from llama_cpp import Llama
            except ImportError as exc:
                raise AIProviderError(
                    "llama-cpp-python o'rnatilmagan (oflayn model uchun)"
                ) from exc
            model_path = _find_model(self._models_dir, self._filename)
            if model_path is None:
                raise AIProviderError(
                    f"GGUF model topilmadi: {self._models_dir}"
                )
            logger.info("Lokal model yuklanmoqda: %s", model_path.name)
            self._llm = Llama(
                model_path=str(model_path),
                n_ctx=self._context_size,
                n_threads=None,  # avtomatik (CPU yadrolari soni)
                verbose=False,
            )
            self._model_name = model_path.stem
            return self._llm

    def complete(self, request: CompletionRequest) -> CompletionResult:
        llm = self._ensure_loaded()
        try:
            response = llm.create_chat_completion(
                messages=messages_to_dicts(request.messages),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        except Exception as exc:  # llama_cpp turli xatolar chiqaradi
            raise AIProviderError(f"lokal model xatosi: {exc}") from exc
        content = response["choices"][0]["message"]["content"]
        usage = response.get("usage", {})
        return CompletionResult(
            content=content or "",
            provider=self.name,
            model=getattr(self, "_model_name", "local"),
            tokens=usage.get("total_tokens", 0),
        )

    def stream(self, request: CompletionRequest) -> Iterator[str]:
        llm = self._ensure_loaded()
        try:
            for chunk in llm.create_chat_completion(
                messages=messages_to_dicts(request.messages),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            ):
                delta = chunk["choices"][0].get("delta", {})
                if delta.get("content"):
                    yield delta["content"]
        except Exception as exc:
            raise AIProviderError(f"lokal model stream xatosi: {exc}") from exc
