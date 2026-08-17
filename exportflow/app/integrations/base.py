"""Common contracts shared by every integration adapter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResult:
    """Uniform result returned by adapter operations."""

    ok: bool
    message: str = ""
    data: Any = None
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, message: str = "", data: Any = None, **details: Any) -> ProviderResult:
        """Build a successful result."""
        return cls(True, message, data, details)

    @classmethod
    def failure(cls, message: str, **details: Any) -> ProviderResult:
        """Build a failed result."""
        return cls(False, message, None, details)


class BaseProvider(ABC):
    """Base class for all providers.

    ``settings`` holds non-secret configuration; ``secrets`` holds credentials
    loaded from the OS keyring and is never persisted or logged.
    """

    #: Stable identifier stored in ``IntegrationConfig.provider``.
    code: str = "base"
    #: Human readable name shown in the settings page.
    label: str = "Base provider"
    #: Adapter family: llm / email / lead_import / crm / webhook.
    kind: str = "generic"
    #: True for providers that work fully offline.
    is_demo: bool = False
    #: Field definitions rendered by the settings dialog:
    #: ``(name, label, is_secret)``.
    fields: tuple[tuple[str, str, bool], ...] = ()

    def __init__(self, settings: dict | None = None, secrets: dict | None = None) -> None:
        self.settings = dict(settings or {})
        self.secrets = dict(secrets or {})

    @abstractmethod
    def test_connection(self) -> ProviderResult:
        """Verify that the provider is reachable and configured correctly."""

    def describe(self) -> str:
        """Short status text for the integrations page."""
        return self.label
