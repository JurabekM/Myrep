"""Repository abstractions (ports).

Services depend on these ABCs only; Mongo implementations live in
app/infrastructure/repositories. This keeps business logic testable with
in-memory fakes and swappable storage.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from app.domain.entities.conversation import Conversation, Message
from app.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def update(self, user_id: str, fields: dict[str, Any]) -> User: ...

    @abstractmethod
    async def list_paginated(
        self, *, skip: int, limit: int, filters: dict[str, Any] | None = None
    ) -> tuple[list[User], int]: ...


class ConversationRepository(ABC):
    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation: ...

    @abstractmethod
    async def get(self, conversation_id: str, user_id: str) -> Conversation | None: ...

    @abstractmethod
    async def list_for_user(
        self, user_id: str, *, skip: int, limit: int
    ) -> list[Conversation]: ...

    @abstractmethod
    async def update(self, conversation_id: str, fields: dict[str, Any]) -> None: ...

    @abstractmethod
    async def delete(self, conversation_id: str, user_id: str) -> bool: ...


class MessageRepository(ABC):
    @abstractmethod
    async def add(self, message: Message) -> Message: ...

    @abstractmethod
    async def list_for_conversation(
        self, conversation_id: str, *, limit: int = 50, before_id: str | None = None
    ) -> list[Message]: ...

    @abstractmethod
    async def set_feedback(self, message_id: str, feedback: int) -> None: ...

    @abstractmethod
    async def text_search(self, query: str, *, limit: int) -> list[Message]: ...


class UsageStatsRepository(ABC):
    @abstractmethod
    async def record(
        self, user_id: str, day: date, module: str, *, tokens: int, cost_usd: float
    ) -> None: ...

    @abstractmethod
    async def aggregate_for_user(self, user_id: str, *, days: int) -> list[dict[str, Any]]: ...


class AuditLogRepository(ABC):
    @abstractmethod
    async def record(
        self,
        *,
        actor_id: str,
        action: str,
        resource: str,
        ip: str | None = None,
        user_agent: str | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None: ...
