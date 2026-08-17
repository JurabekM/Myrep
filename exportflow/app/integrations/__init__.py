"""Integration adapters for LLM, email, lead import, CRM and webhooks."""

from app.integrations.base import BaseProvider, ProviderResult
from app.integrations.registry import DEFAULT_PROVIDERS, REGISTRY, provider_class, providers_for

__all__ = [
    "BaseProvider",
    "DEFAULT_PROVIDERS",
    "ProviderResult",
    "REGISTRY",
    "provider_class",
    "providers_for",
]
