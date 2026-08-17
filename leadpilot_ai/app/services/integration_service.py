"""Adapter registry: resolves the right adapter for each provider and channel.

Credentials are read from the OS keyring first and only fall back to an
obfuscated blob inside the database.  Nothing secret is ever logged or shown in
the interface — the settings page displays masked values only.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.integrations.base import AdapterCredentials, AdapterResult
from app.integrations.channels import (
    ChannelAdapter,
    DemoChannelAdapter,
    InstagramAdapter,
    TelegramAdapter,
    WebsiteChatAdapter,
    WhatsAppAdapter,
)
from app.integrations.crm import (
    AmoCRMAdapter,
    Bitrix24Adapter,
    CRMExporter,
    InternalCRMExporter,
    WebhookAdapter,
)
from app.integrations.llm import (
    DemoRuleBasedProvider,
    LLMProvider,
    MockTranscriber,
    OpenAICompatibleProvider,
    OpenAICompatibleTranscriber,
    TranscriberAdapter,
)
from app.integrations.telephony import (
    DemoTelephonyAdapter,
    SIPProviderAdapter,
    TelephonyAdapter,
    TwilioAdapter,
)
from app.models.enums import Channel, IntegrationKind, IntegrationStatus
from app.models.enums import Permission as Perm
from app.models.system import IntegrationConfig
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.utils.dates import now
from app.utils.security import deobfuscate, keyring_available, obfuscate, read_secret, store_secret

logger = logging.getLogger(__name__)

#: Which secret fields each provider expects.
SECRET_FIELDS: dict[str, list[str]] = {
    "telegram": ["bot_token"],
    "whatsapp": ["access_token", "phone_number_id", "relay_url", "relay_token"],
    "instagram": ["access_token", "ig_account_id", "relay_url", "relay_token"],
    "website": ["relay_url", "send_url", "relay_token"],
    "twilio": ["account_sid", "auth_token", "from_number", "twiml_url"],
    "sip": ["base_url", "api_key", "extension"],
    "openai_compatible": ["api_key", "base_url", "model"],
    "openai_stt": ["api_key", "base_url", "model"],
    "bitrix24": ["webhook_base"],
    "amocrm": ["base_url", "access_token"],
    "webhook": ["webhook_url", "webhook_token"],
}

CHANNEL_PROVIDERS: dict[str, str] = {
    Channel.TELEGRAM: "telegram",
    Channel.WHATSAPP: "whatsapp",
    Channel.INSTAGRAM: "instagram",
    Channel.WEBSITE: "website",
}

_ADAPTER_CLASSES: dict[str, type] = {
    "telegram": TelegramAdapter,
    "whatsapp": WhatsAppAdapter,
    "instagram": InstagramAdapter,
    "website": WebsiteChatAdapter,
    "twilio": TwilioAdapter,
    "sip": SIPProviderAdapter,
    "openai_compatible": OpenAICompatibleProvider,
    "openai_stt": OpenAICompatibleTranscriber,
    "bitrix24": Bitrix24Adapter,
    "amocrm": AmoCRMAdapter,
    "webhook": WebhookAdapter,
    "internal": InternalCRMExporter,
}

#: Shared demo singletons so simulated traffic survives between polls.
_demo_channels: dict[str, DemoChannelAdapter] = {}
_demo_telephony = DemoTelephonyAdapter()
_demo_llm = DemoRuleBasedProvider()
_demo_stt = MockTranscriber()


def demo_channel(channel: str) -> DemoChannelAdapter:
    """Return (and cache) the demo adapter for one channel."""
    if channel not in _demo_channels:
        _demo_channels[channel] = DemoChannelAdapter(channel)
    return _demo_channels[channel]


def demo_telephony() -> DemoTelephonyAdapter:
    """Shared demo telephony adapter."""
    return _demo_telephony


def demo_llm() -> DemoRuleBasedProvider:
    """Shared demo AI provider."""
    return _demo_llm


def demo_transcriber() -> MockTranscriber:
    """Shared demo transcriber."""
    return _demo_stt


# --------------------------------------------------------------------------- #
# Configuration storage
# --------------------------------------------------------------------------- #
def _keyring_key(provider: str, field: str) -> str:
    """Name under which a secret is stored in the OS keyring."""
    return f"{provider}:{field}"


def get_config(provider: str, *, session: Session | None = None) -> IntegrationConfig | None:
    """Load the stored configuration row of a provider."""

    def _get(db: Session) -> IntegrationConfig | None:
        return db.execute(
            select(IntegrationConfig).where(IntegrationConfig.provider == provider)
        ).scalar_one_or_none()

    if session is not None:
        return _get(session)
    with session_scope() as db:
        return _get(db)


def list_configs() -> list[IntegrationConfig]:
    """All integration configuration rows."""
    with session_scope() as session:
        return list(
            session.execute(select(IntegrationConfig).order_by(IntegrationConfig.kind))
            .scalars()
            .all()
        )


def load_credentials(provider: str) -> AdapterCredentials:
    """Assemble the credentials of a provider from keyring + database."""
    config = get_config(provider)
    secrets: dict[str, str] = {}
    settings: dict[str, Any] = {}
    if config is not None:
        try:
            settings = json.loads(config.settings_json or "{}")
        except json.JSONDecodeError:
            settings = {}
        blob: dict[str, str] = {}
        if config.secret_blob:
            try:
                blob = json.loads(deobfuscate(config.secret_blob) or "{}")
            except json.JSONDecodeError:
                blob = {}
        for field in SECRET_FIELDS.get(provider, []):
            value = read_secret(_keyring_key(provider, field)) or blob.get(field, "")
            if value:
                secrets[field] = value
    return AdapterCredentials(provider=provider, secrets=secrets, settings=settings)


def save_credentials(
    provider: str,
    *,
    kind: str,
    secrets: dict[str, str],
    settings: dict[str, Any] | None = None,
    is_enabled: bool = True,
    use_demo: bool = False,
    title: str = "",
    actor: CurrentUser | None = None,
) -> IntegrationConfig:
    """Persist credentials, preferring the OS keyring for secret values."""
    if actor is not None:
        actor.require(Perm.INTEGRATION_MANAGE)
    fallback: dict[str, str] = {}
    for field, value in secrets.items():
        if not value:
            continue
        if not store_secret(_keyring_key(provider, field), value):
            fallback[field] = value
    with session_scope() as session:
        config = get_config(provider, session=session)
        if config is None:
            config = IntegrationConfig(company_id=1, provider=provider, kind=kind)
            session.add(config)
        config.kind = kind
        config.title = title or config.title or provider
        config.is_enabled = is_enabled
        config.use_demo = use_demo
        config.settings_json = json.dumps(settings or {}, ensure_ascii=False)
        config.keyring_ref = provider if keyring_available() else ""
        if fallback:
            existing: dict[str, str] = {}
            if config.secret_blob:
                try:
                    existing = json.loads(deobfuscate(config.secret_blob) or "{}")
                except json.JSONDecodeError:
                    existing = {}
            existing.update(fallback)
            config.secret_blob = obfuscate(json.dumps(existing, ensure_ascii=False))
        config.status = IntegrationStatus.DEMO if use_demo else IntegrationStatus.NOT_CONFIGURED
        session.flush()
        audit_service.record(
            session,
            action="integration_saved",
            entity_type="integration",
            entity_id=config.id,
            entity_label=provider,
            new_value=f"enabled={is_enabled}, demo={use_demo}",
            detail="Credential qiymatlari logga yozilmaydi",
            user_id=actor.id if actor else None,
            username=actor.username if actor else "system",
        )
        return config


def update_status(provider: str, status: str, error: str = "") -> None:
    """Update the connection status shown in the top bar."""
    with session_scope() as session:
        config = get_config(provider, session=session)
        if config is None:
            return
        config.status = status
        config.last_error = error[:2000]
        if status == IntegrationStatus.CONNECTED:
            config.last_sync_at = now()
        config.last_test_at = now()


# --------------------------------------------------------------------------- #
# Adapter resolution
# --------------------------------------------------------------------------- #
def _is_demo(provider: str) -> bool:
    """Whether the provider should fall back to its demo implementation."""
    config = get_config(provider)
    if config is None:
        return True
    if config.use_demo or not config.is_enabled:
        return True
    return False


def channel_adapter(channel: str) -> ChannelAdapter:
    """Return the adapter that serves ``channel``, falling back to demo."""
    provider = CHANNEL_PROVIDERS.get(channel)
    if provider is None:
        return demo_channel(channel)
    if _is_demo(provider):
        return demo_channel(channel)
    adapter_class = _ADAPTER_CLASSES[provider]
    adapter = adapter_class(load_credentials(provider))
    if not adapter.is_configured():
        return demo_channel(channel)
    return adapter


def active_channels() -> list[str]:
    """Channels that currently have a working adapter (real or demo)."""
    return [Channel.TELEGRAM, Channel.WHATSAPP, Channel.INSTAGRAM, Channel.WEBSITE, Channel.DEMO]


def llm_provider() -> LLMProvider:
    """Return the configured LLM provider or the deterministic demo agent."""
    if _is_demo("openai_compatible"):
        return demo_llm()
    provider = OpenAICompatibleProvider(load_credentials("openai_compatible"))
    if not provider.is_configured():
        return demo_llm()
    return provider


def transcriber() -> TranscriberAdapter:
    """Return the configured speech-to-text adapter or the mock one."""
    if _is_demo("openai_stt"):
        return demo_transcriber()
    adapter = OpenAICompatibleTranscriber(load_credentials("openai_stt"))
    if not adapter.is_configured():
        return demo_transcriber()
    return adapter


def telephony_adapter() -> TelephonyAdapter:
    """Return the configured telephony adapter or the demo one."""
    for provider in ("twilio", "sip"):
        if _is_demo(provider):
            continue
        adapter = _ADAPTER_CLASSES[provider](load_credentials(provider))
        if adapter.is_configured():
            return adapter
    return demo_telephony()


def crm_exporter() -> CRMExporter:
    """Return the configured CRM exporter or the internal no-op one."""
    for provider in ("bitrix24", "amocrm", "webhook"):
        if _is_demo(provider):
            continue
        adapter = _ADAPTER_CLASSES[provider](load_credentials(provider))
        if adapter.is_configured():
            return adapter
    return InternalCRMExporter()


# --------------------------------------------------------------------------- #
# Connection testing / status overview
# --------------------------------------------------------------------------- #
def test_connection(provider: str, *, actor: CurrentUser | None = None) -> AdapterResult:
    """Run the provider's connection test and store the resulting status."""
    if actor is not None:
        actor.require(Perm.INTEGRATION_MANAGE)
    adapter_class = _ADAPTER_CLASSES.get(provider)
    if adapter_class is None:
        return AdapterResult.failure("Noma'lum provider", "unknown_provider")
    adapter = adapter_class(load_credentials(provider))
    try:
        result = adapter.test_connection()
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Connection test crashed for %s", provider)
        result = AdapterResult.failure(f"Xatolik: {type(exc).__name__}", "exception")
    update_status(
        provider,
        IntegrationStatus.CONNECTED if result.ok else IntegrationStatus.ERROR,
        "" if result.ok else result.message,
    )
    return result


def status_overview() -> list[dict[str, Any]]:
    """Compact status list for the custom top bar."""
    overview: list[dict[str, Any]] = []
    configs = {c.provider: c for c in list_configs()}
    for provider, kind in (
        ("telegram", IntegrationKind.CHANNEL),
        ("whatsapp", IntegrationKind.CHANNEL),
        ("instagram", IntegrationKind.CHANNEL),
        ("website", IntegrationKind.CHANNEL),
        ("twilio", IntegrationKind.TELEPHONY),
        ("openai_compatible", IntegrationKind.LLM),
        ("openai_stt", IntegrationKind.STT),
        ("bitrix24", IntegrationKind.CRM),
    ):
        config = configs.get(provider)
        if config is None:
            status = IntegrationStatus.DEMO
            last_sync = None
            error = ""
        elif config.use_demo or not config.is_enabled:
            status = IntegrationStatus.DEMO
            last_sync = config.last_sync_at
            error = ""
        else:
            status = config.status
            last_sync = config.last_sync_at
            error = config.last_error
        overview.append(
            {
                "provider": provider,
                "kind": kind,
                "status": status,
                "last_sync_at": last_sync,
                "error": error,
            }
        )
    return overview


def ensure_default_configs() -> None:
    """Create demo-mode rows for every provider on first run."""
    kinds = {
        "telegram": IntegrationKind.CHANNEL,
        "whatsapp": IntegrationKind.CHANNEL,
        "instagram": IntegrationKind.CHANNEL,
        "website": IntegrationKind.CHANNEL,
        "twilio": IntegrationKind.TELEPHONY,
        "sip": IntegrationKind.TELEPHONY,
        "openai_compatible": IntegrationKind.LLM,
        "openai_stt": IntegrationKind.STT,
        "bitrix24": IntegrationKind.CRM,
        "amocrm": IntegrationKind.CRM,
        "webhook": IntegrationKind.CRM,
    }
    with session_scope() as session:
        existing = {
            provider for (provider,) in session.execute(select(IntegrationConfig.provider)).all()
        }
        for provider, kind in kinds.items():
            if provider in existing:
                continue
            session.add(
                IntegrationConfig(
                    company_id=1,
                    provider=provider,
                    kind=kind,
                    title=provider,
                    is_enabled=False,
                    use_demo=True,
                    status=IntegrationStatus.DEMO,
                    settings_json="{}",
                )
            )


def poll_channels() -> list[dict[str, int]]:
    """Poll every enabled channel and ingest the messages that arrived."""
    from app.services import conversation_service

    ingested: list[dict[str, int]] = []
    for channel in (
        Channel.TELEGRAM,
        Channel.WHATSAPP,
        Channel.INSTAGRAM,
        Channel.WEBSITE,
        Channel.DEMO,
    ):
        adapter = channel_adapter(channel)
        try:
            incoming = adapter.poll()
        except Exception as exc:  # pragma: no cover - network defensive
            logger.warning("Polling %s failed: %s", channel, type(exc).__name__)
            continue
        for message in incoming:
            try:
                ingested.append(conversation_service.ingest_incoming(message))
            except Exception:
                logger.exception("Failed to ingest message from %s", channel)
    return ingested
