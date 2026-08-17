"""LLM and speech-to-text providers."""

from app.integrations.llm.base_llm import AgentContext, AgentReply, ChatTurn, LLMProvider
from app.integrations.llm.demo_provider import DemoRuleBasedProvider
from app.integrations.llm.openai_provider import OpenAICompatibleProvider
from app.integrations.llm.speech import (
    MockTranscriber,
    OpenAICompatibleTranscriber,
    TranscriberAdapter,
)

__all__ = [
    "LLMProvider",
    "AgentContext",
    "AgentReply",
    "ChatTurn",
    "DemoRuleBasedProvider",
    "OpenAICompatibleProvider",
    "TranscriberAdapter",
    "MockTranscriber",
    "OpenAICompatibleTranscriber",
]
