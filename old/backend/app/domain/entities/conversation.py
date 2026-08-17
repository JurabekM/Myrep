"""Conversation & message entities (chat domain)."""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class Module(StrEnum):
    CHAT = "chat"
    CONSULTANT = "consultant"
    LEGAL = "legal"
    TAX = "tax"
    MARKETING = "marketing"
    DOCUMENTS = "documents"
    FINANCE = "finance"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Attachment(BaseModel):
    file_id: str
    filename: str
    content_type: str
    size: int


class SourceReference(BaseModel):
    """Citation attached to an AI answer (RAG grounding)."""

    title: str
    url: str | None = None
    snippet: str | None = None
    article: str | None = None  # qonun moddasi, masalan "58-modda"
    score: float | None = None


class SafetyReport(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    category: str
    grounded: bool | None = None  # None = RAG ishlatilmagan
    hallucination_risk: float | None = Field(default=None, ge=0.0, le=1.0)
    disclaimer: str | None = None


class Message(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    attachments: list[Attachment] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    safety: SafetyReport | None = None
    model: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    feedback: int | None = None  # 1 = up, -1 = down
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Conversation(BaseModel):
    id: str
    user_id: str
    title: str
    module: Module = Module.CHAT
    model: str | None = None  # None = router default
    summary: str | None = None  # rolling memory of older messages
    message_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
