"""LLM provider contract and the data structures exchanged with it."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.integrations.base import AdapterResult, BaseAdapter
from app.models.enums import AIState


@dataclass
class ChatTurn:
    """One turn of the dialogue passed to the provider."""

    role: str  # "customer" | "agent" | "note"
    text: str


@dataclass
class AgentContext:
    """Everything the AI is allowed to know when writing a reply."""

    agent_name: str = "AI"
    company_name: str = ""
    tone: str = "friendly"
    language: str = "uz"
    state: str = AIState.NEW_LEAD
    lead_name: str = ""
    lead_phone: str = ""
    lead_interest: str = ""
    lead_score: int = 0
    history: list[ChatTurn] = field(default_factory=list)
    knowledge: list[str] = field(default_factory=list)
    services: list[dict[str, Any]] = field(default_factory=list)
    branches: list[dict[str, Any]] = field(default_factory=list)
    promos: list[str] = field(default_factory=list)
    internal_notes: list[str] = field(default_factory=list)
    free_slots: list[str] = field(default_factory=list)
    channel: str = "demo"
    forbidden_topics: list[str] = field(default_factory=list)
    signature: str = ""
    within_working_hours: bool = True


@dataclass
class AgentReply:
    """Structured answer produced by an LLM provider."""

    text: str
    next_state: str = AIState.GREETING
    escalate: bool = False
    escalation_reason: str = ""
    wants_booking: bool = False
    extracted: dict[str, str] = field(default_factory=dict)
    kb_refs: list[str] = field(default_factory=list)
    confidence: float = 1.0
    provider: str = "demo"
    model: str = "rule-based"
    latency_ms: int = 0


class LLMProvider(BaseAdapter):
    """Generates sales replies and analyses call transcripts."""

    @abstractmethod
    def generate_reply(self, context: AgentContext, customer_message: str) -> AgentReply:
        """Produce the next agent reply for ``customer_message``."""

    @abstractmethod
    def analyze_call(self, transcript: str, language: str = "uz") -> dict[str, Any]:
        """Return summary / objections / next action for a call transcript."""

    def test_connection(self) -> AdapterResult:  # pragma: no cover - overridden
        """Default: report unconfigured."""
        return AdapterResult.failure("Sozlanmagan", "not_configured")
