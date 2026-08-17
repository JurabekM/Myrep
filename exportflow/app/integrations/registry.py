"""Provider registry: maps ``(kind, provider code)`` to adapter classes."""

from __future__ import annotations

from app.integrations.base import BaseProvider
from app.integrations.crm.providers import AmoCRMAdapter, Bitrix24Adapter, WebhookAdapter
from app.integrations.email.providers import DemoOutboxProvider, SMTPProvider
from app.integrations.llm.demo_provider import DemoRuleBasedProvider
from app.integrations.llm.openai_compatible import OpenAICompatibleProvider
from app.integrations.marketplace.providers import (
    AlibabaImportAdapter,
    CSVImportAdapter,
    DemoLeadProvider,
    LinkedInImportAdapter,
)

#: ``kind -> {provider code -> adapter class}``
REGISTRY: dict[str, dict[str, type[BaseProvider]]] = {
    "llm": {
        DemoRuleBasedProvider.code: DemoRuleBasedProvider,
        OpenAICompatibleProvider.code: OpenAICompatibleProvider,
    },
    "email": {
        DemoOutboxProvider.code: DemoOutboxProvider,
        SMTPProvider.code: SMTPProvider,
    },
    "lead_import": {
        DemoLeadProvider.code: DemoLeadProvider,
        CSVImportAdapter.code: CSVImportAdapter,
        AlibabaImportAdapter.code: AlibabaImportAdapter,
        LinkedInImportAdapter.code: LinkedInImportAdapter,
    },
    "crm": {
        WebhookAdapter.code: WebhookAdapter,
        Bitrix24Adapter.code: Bitrix24Adapter,
        AmoCRMAdapter.code: AmoCRMAdapter,
    },
    "webhook": {
        WebhookAdapter.code: WebhookAdapter,
    },
}

#: Fallback provider used whenever nothing is configured for a kind.
DEFAULT_PROVIDERS = {
    "llm": DemoRuleBasedProvider.code,
    "email": DemoOutboxProvider.code,
    "lead_import": DemoLeadProvider.code,
    "crm": WebhookAdapter.code,
    "webhook": WebhookAdapter.code,
}


def provider_class(kind: str, code: str) -> type[BaseProvider] | None:
    """Look up an adapter class, or ``None`` when it is unknown."""
    return REGISTRY.get(kind, {}).get(code)


def providers_for(kind: str) -> dict[str, type[BaseProvider]]:
    """All adapters registered for a given integration kind."""
    return REGISTRY.get(kind, {})
