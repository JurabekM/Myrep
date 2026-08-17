"""ModelRouter fallback testlari — soxta (fake) provayderlar bilan."""

import pytest

from app.ai.base import ChatMessage, CompletionRequest, CompletionResult, LLMProvider, Role
from app.ai.router import ModelRouter
from app.core.exceptions import AIProviderError, AllProvidersFailedError


class _FakeProvider(LLMProvider):
    def __init__(self, name, *, available=True, fails=False, text="javob"):
        self.name = name
        self._available = available
        self._fails = fails
        self._text = text
        self.called = False

    def is_available(self):
        return self._available

    def complete(self, request):
        self.called = True
        if self._fails:
            raise AIProviderError(f"{self.name} ataylab xato")
        return CompletionResult(self._text, self.name, self.name)


def _request():
    return CompletionRequest(messages=(ChatMessage(Role.USER, "test"),))


def test_uses_first_available():
    providers = {"a": _FakeProvider("a"), "b": _FakeProvider("b")}
    router = ModelRouter(providers, ["a", "b"])
    result = router.complete(_request())
    assert result.provider == "a"
    assert providers["b"].called is False


def test_falls_back_on_failure():
    providers = {
        "a": _FakeProvider("a", fails=True),
        "b": _FakeProvider("b", text="B javobi"),
    }
    router = ModelRouter(providers, ["a", "b"])
    result = router.complete(_request())
    assert result.provider == "b"
    assert result.content == "B javobi"


def test_skips_unavailable():
    providers = {
        "a": _FakeProvider("a", available=False),
        "b": _FakeProvider("b"),
    }
    router = ModelRouter(providers, ["a", "b"])
    assert router.available_providers() == ["b"]
    assert router.complete(_request()).provider == "b"


def test_all_fail_raises():
    providers = {
        "a": _FakeProvider("a", fails=True),
        "b": _FakeProvider("b", fails=True),
    }
    router = ModelRouter(providers, ["a", "b"])
    with pytest.raises(AllProvidersFailedError):
        router.complete(_request())


def test_none_available_raises():
    providers = {"a": _FakeProvider("a", available=False)}
    router = ModelRouter(providers, ["a"])
    with pytest.raises(AllProvidersFailedError):
        router.complete(_request())
