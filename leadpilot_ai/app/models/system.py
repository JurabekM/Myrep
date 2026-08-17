"""Integration configuration, audit log and generic key/value settings."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin
from app.models.enums import IntegrationKind, IntegrationStatus


class IntegrationConfig(Base, IdMixin, TimestampMixin):
    """Stored settings for one external provider.

    Secret values are **never** written to this table in clear text: they go to
    the OS keyring under ``keyring_ref`` and only fall back to an obfuscated
    blob in ``secret_blob`` when no keyring backend exists.
    """

    __tablename__ = "integration_configs"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), default=IntegrationKind.CHANNEL, index=True)
    provider: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), default="")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    use_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(24), default=IntegrationStatus.DEMO)
    settings_json: Mapped[str] = mapped_column(Text, default="{}")
    keyring_ref: Mapped[str] = mapped_column(String(120), default="")
    secret_blob: Mapped[str] = mapped_column(Text, default="")
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")


class AuditLog(Base, IdMixin):
    """Immutable record of every important action."""

    __tablename__ = "audit_logs"

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), default="", index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entity_label: Mapped[str] = mapped_column(String(200), default="")
    old_value: Mapped[str] = mapped_column(Text, default="")
    new_value: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class AppSetting(Base, IdMixin, TimestampMixin):
    """Generic key/value store for runtime settings."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(96), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(String(255), default="")


class SchemaVersion(Base, IdMixin):
    """Applied migration revisions (lightweight migration mechanism)."""

    __tablename__ = "schema_versions"

    revision: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
