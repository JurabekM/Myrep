"""Integration configuration, audit log and key/value settings."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class IntegrationConfig(IdMixin, TimestampMixin, Base):
    """Non-secret configuration of an external provider.

    Credentials themselves are never stored here; they live in the OS keyring
    and are referenced through :attr:`secret_key`.
    """

    __tablename__ = "integration_configs"

    kind: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settings_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    secret_key: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="not_configured", nullable=False)
    last_sync_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(Text)
    sync_log: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<IntegrationConfig {self.kind}/{self.provider}>"


class AuditLog(IdMixin, Base):
    """Immutable record of every meaningful change."""

    __tablename__ = "audit_logs"

    at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    username: Mapped[str | None] = mapped_column(String(60))
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    summary: Mapped[str] = mapped_column(String(400), default="", nullable=False)
    details: Mapped[str | None] = mapped_column(Text)


class AppSetting(IdMixin, TimestampMixin, Base):
    """Simple key/value store for application preferences."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, default="", nullable=False)
    group: Mapped[str] = mapped_column(String(40), default="general", nullable=False)
