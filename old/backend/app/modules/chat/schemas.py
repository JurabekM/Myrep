"""Chat request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities.conversation import (
    Attachment,
    MessageRole,
    Module,
    SafetyReport,
    SourceReference,
)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32_000)
    conversation_id: str | None = None  # None → yangi suhbat
    module: Module = Module.CHAT
    model: str | None = None  # "provider:model" yoki None (default)
    attachment_ids: list[str] = Field(default_factory=list, max_length=5)


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    attachments: list[Attachment]
    sources: list[SourceReference]
    safety: SafetyReport | None
    model: str | None
    feedback: int | None
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    title: str
    module: Module
    model: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime


class FeedbackRequest(BaseModel):
    feedback: int = Field(ge=-1, le=1)
