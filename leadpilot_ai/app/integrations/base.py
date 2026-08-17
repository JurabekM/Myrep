"""Common contracts shared by every external-service adapter.

The UI never talks to an external service directly: it goes through a service,
which in turn resolves an adapter from :mod:`app.services.integration_service`.
Every adapter fails soft — a missing credential produces a descriptive
:class:`AdapterResult`, never an exception that reaches the interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.models.enums import IntegrationStatus
from app.utils.dates import now


@dataclass
class AdapterResult:
    """Uniform result object returned by every adapter call."""

    ok: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error_code: str = ""

    @classmethod
    def success(cls, message: str = "", **data: Any) -> AdapterResult:
        """Build a successful result."""
        return cls(ok=True, message=message, data=data)

    @classmethod
    def failure(cls, message: str, error_code: str = "error", **data: Any) -> AdapterResult:
        """Build a failed result."""
        return cls(ok=False, message=message, data=data, error_code=error_code)


@dataclass
class IncomingMessage:
    """Normalised inbound message produced by a channel adapter."""

    channel: str
    external_chat_id: str
    text: str
    sender_name: str = ""
    sender_username: str = ""
    phone: str | None = None
    external_message_id: str = ""
    received_at: datetime = field(default_factory=now)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    utm: dict[str, str] = field(default_factory=dict)


@dataclass
class AdapterCredentials:
    """Credentials + non-secret settings handed to an adapter."""

    provider: str
    secrets: dict[str, str] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: str = "") -> str:
        """Read a secret value."""
        return self.secrets.get(key) or str(self.settings.get(key, default) or default)

    def has(self, *keys: str) -> bool:
        """Whether all requested secrets are present and non-empty."""
        return all(bool(self.get(key)) for key in keys)


class BaseAdapter(ABC):
    """Root class of every adapter."""

    #: Machine name shown in the settings page.
    provider: str = "base"
    #: Human readable title.
    title: str = "Base adapter"
    #: True when the adapter works without any credentials.
    is_demo: bool = False

    def __init__(self, credentials: AdapterCredentials | None = None) -> None:
        self.credentials = credentials or AdapterCredentials(provider=self.provider)
        self.last_error: str = ""
        self.last_sync_at: datetime | None = None

    @abstractmethod
    def test_connection(self) -> AdapterResult:
        """Verify credentials / reachability without side effects."""

    def status(self) -> str:
        """Current :class:`~app.models.enums.IntegrationStatus` value."""
        if self.is_demo:
            return IntegrationStatus.DEMO
        if self.last_error:
            return IntegrationStatus.ERROR
        if not self.is_configured():
            return IntegrationStatus.NOT_CONFIGURED
        return IntegrationStatus.CONNECTED

    def is_configured(self) -> bool:
        """Whether the adapter has everything it needs to run."""
        return True

    def describe(self) -> dict[str, Any]:
        """Small dict used by the settings UI."""
        return {
            "provider": self.provider,
            "title": self.title,
            "is_demo": self.is_demo,
            "status": self.status(),
            "last_error": self.last_error,
            "last_sync_at": self.last_sync_at,
        }
