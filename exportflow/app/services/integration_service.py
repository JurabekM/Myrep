"""Integration configuration, credential handling and provider instantiation.

Credentials never touch the database: only a keyring reference is stored in
``IntegrationConfig.secret_key``.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.base import BaseProvider, ProviderResult
from app.integrations.registry import DEFAULT_PROVIDERS, provider_class, providers_for
from app.models import IntegrationConfig
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.utils.errors import IntegrationError
from app.utils.formatting import fmt_datetime, now
from app.utils.logging_setup import get_logger
from app.utils.security import delete_secret, load_secret, mask, save_secret

log = get_logger(__name__)


def _secret_key(kind: str, provider: str, field: str) -> str:
    return f"{kind}:{provider}:{field}"


def ensure_defaults(session: Session) -> None:
    """Create a demo configuration row for every integration kind."""
    for kind, provider in DEFAULT_PROVIDERS.items():
        existing = session.scalar(select(IntegrationConfig).where(IntegrationConfig.kind == kind))
        if existing is not None:
            continue
        adapter = provider_class(kind, provider)
        session.add(
            IntegrationConfig(
                kind=kind,
                provider=provider,
                name=adapter.label if adapter else provider,
                is_enabled=True,
                is_default=True,
                settings_json="{}",
                status="demo",
            )
        )
    session.flush()


def list_configs(session: Session, kind: str | None = None) -> list[dict]:
    """Integration configurations for the settings page."""
    stmt = select(IntegrationConfig).order_by(IntegrationConfig.kind, IntegrationConfig.id)
    if kind:
        stmt = stmt.where(IntegrationConfig.kind == kind)
    rows = session.scalars(stmt).unique().all()
    result = []
    for row in rows:
        adapter = provider_class(row.kind, row.provider)
        secrets_present = {}
        if adapter:
            for name, _label, is_secret in adapter.fields:
                if is_secret:
                    value = load_secret(_secret_key(row.kind, row.provider, name))
                    secrets_present[name] = mask(value) if value else ""
        result.append(
            {
                "id": row.id,
                "kind": row.kind,
                "provider": row.provider,
                "name": row.name or (adapter.label if adapter else row.provider),
                "is_enabled": row.is_enabled,
                "is_default": row.is_default,
                "settings": json.loads(row.settings_json or "{}"),
                "secrets": secrets_present,
                "status": row.status,
                "last_sync_at": row.last_sync_at,
                "last_sync_text": fmt_datetime(row.last_sync_at),
                "last_error": row.last_error or "",
                "sync_log": row.sync_log or "",
                "is_demo": bool(adapter and adapter.is_demo),
                "fields": list(adapter.fields) if adapter else [],
            }
        )
    return result


def active_config(session: Session, kind: str) -> IntegrationConfig | None:
    """Return the enabled configuration for one kind."""
    return session.scalar(
        select(IntegrationConfig)
        .where(IntegrationConfig.kind == kind, IntegrationConfig.is_enabled.is_(True))
        .order_by(IntegrationConfig.is_default.desc(), IntegrationConfig.id)
    )


def build_provider(session: Session, kind: str) -> BaseProvider:
    """Instantiate the active adapter for a kind, falling back to demo.

    The application never breaks when credentials are missing: the demo
    provider is always constructible.
    """
    config = active_config(session, kind)
    provider_code = config.provider if config else DEFAULT_PROVIDERS.get(kind, "")
    adapter_cls = provider_class(kind, provider_code)
    if adapter_cls is None:
        adapter_cls = provider_class(kind, DEFAULT_PROVIDERS.get(kind, ""))
    if adapter_cls is None:
        raise IntegrationError(f"No provider available for '{kind}'", key="error.no_provider")

    settings = json.loads(config.settings_json or "{}") if config else {}
    secrets: dict[str, str] = {}
    missing_secret = False
    for name, _label, is_secret in adapter_cls.fields:
        if not is_secret:
            continue
        value = load_secret(_secret_key(kind, provider_code, name))
        if value:
            secrets[name] = value
        else:
            missing_secret = True

    if missing_secret and not adapter_cls.is_demo:
        fallback_cls = provider_class(kind, DEFAULT_PROVIDERS.get(kind, ""))
        if fallback_cls is not None:
            log.info("Credentials missing for %s/%s, using demo provider", kind, provider_code)
            return fallback_cls({}, {})
    return adapter_cls(settings, secrets)


def provider_status(session: Session, kind: str) -> dict:
    """Short status used by the title bar integration indicator."""
    config = active_config(session, kind)
    provider = build_provider(session, kind)
    return {
        "kind": kind,
        "provider": provider.code,
        "label": provider.label,
        "is_demo": provider.is_demo,
        "status": config.status if config else "demo",
        "last_error": config.last_error if config else "",
    }


def save_config(
    session: Session,
    actor: CurrentUser,
    *,
    kind: str,
    provider: str,
    settings: dict,
    secrets: dict[str, str],
    is_enabled: bool = True,
) -> IntegrationConfig:
    """Persist non-secret settings and push credentials into the keyring."""
    actor.require("integration.manage")
    adapter_cls = provider_class(kind, provider)
    if adapter_cls is None:
        raise IntegrationError(f"Unknown provider '{provider}'", key="error.no_provider")

    config = session.scalar(
        select(IntegrationConfig).where(
            IntegrationConfig.kind == kind, IntegrationConfig.provider == provider
        )
    )
    if config is None:
        config = IntegrationConfig(kind=kind, provider=provider)
        session.add(config)
    config.name = adapter_cls.label
    config.settings_json = json.dumps(settings or {}, ensure_ascii=False)
    config.is_enabled = is_enabled
    config.status = "demo" if adapter_cls.is_demo else "configured"

    for name, value in (secrets or {}).items():
        key = _secret_key(kind, provider, name)
        if value:
            save_secret(key, value)
        else:
            delete_secret(key)
    config.secret_key = _secret_key(kind, provider, "*")

    # Only one configuration per kind may be enabled at a time.
    if is_enabled:
        others = session.scalars(
            select(IntegrationConfig).where(
                IntegrationConfig.kind == kind, IntegrationConfig.id != (config.id or 0)
            )
        ).all()
        for other in others:
            other.is_enabled = False
    session.flush()

    audit_service.record(
        session,
        action="update",
        entity_type="integration",
        entity_id=config.id,
        summary=f"Integration {kind}/{provider} configured",
        user_id=actor.id,
        username=actor.username,
    )
    return config


def switch_to_demo(session: Session, actor: CurrentUser, kind: str) -> IntegrationConfig:
    """Fall back to the offline demo provider for a kind."""
    actor.require("integration.manage")
    provider = DEFAULT_PROVIDERS.get(kind, "")
    return save_config(session, actor, kind=kind, provider=provider, settings={}, secrets={})


def test_connection(
    session: Session, actor: CurrentUser, kind: str, provider: str
) -> ProviderResult:
    """Run the adapter's connection test and store the outcome."""
    actor.require("integration.manage")
    adapter_cls = provider_class(kind, provider)
    if adapter_cls is None:
        return ProviderResult.failure("Unknown provider")
    config = session.scalar(
        select(IntegrationConfig).where(
            IntegrationConfig.kind == kind, IntegrationConfig.provider == provider
        )
    )
    settings = json.loads(config.settings_json or "{}") if config else {}
    secrets = {
        name: (load_secret(_secret_key(kind, provider, name)) or "")
        for name, _label, is_secret in adapter_cls.fields
        if is_secret
    }
    adapter = adapter_cls(settings, secrets)
    result = adapter.test_connection()
    if config is not None:
        config.status = "connected" if result.ok else "error"
        config.last_error = None if result.ok else result.message
        config.last_sync_at = now()
        session.flush()
    return result


def append_sync_log(session: Session, kind: str, provider: str, text: str) -> None:
    """Append a line to the adapter's rolling sync log (last 50 lines)."""
    config = session.scalar(
        select(IntegrationConfig).where(
            IntegrationConfig.kind == kind, IntegrationConfig.provider == provider
        )
    )
    if config is None:
        return
    lines = (config.sync_log or "").splitlines()
    lines.append(f"{fmt_datetime(now())} | {text}")
    config.sync_log = "\n".join(lines[-50:])
    config.last_sync_at = now()
    session.flush()


def available_providers(kind: str) -> list[dict]:
    """Adapters registered for a kind, used to populate combo boxes."""
    return [
        {
            "code": code,
            "label": cls.label,
            "is_demo": cls.is_demo,
            "fields": list(cls.fields),
        }
        for code, cls in providers_for(kind).items()
    ]
