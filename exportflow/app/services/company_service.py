"""Company profile and application settings."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppSetting, Company
from app.services import audit_service
from app.services.auth_service import CurrentUser


def get_company(session: Session) -> Company:
    """Return the (single) company profile, creating a blank one if needed."""
    company = session.scalars(select(Company).order_by(Company.id)).first()
    if company is None:
        company = Company(name="My Export Company")
        session.add(company)
        session.flush()
    return company


def company_dict(session: Session) -> dict:
    """Company profile as a plain dictionary for the UI and templates."""
    company = get_company(session)
    return {column.name: getattr(company, column.name) for column in Company.__table__.columns}


def save_company(session: Session, actor: CurrentUser, values: dict) -> Company:
    """Persist the company profile (requires ``settings.edit``)."""
    actor.require("settings.edit")
    company = get_company(session)
    for key, value in values.items():
        if hasattr(company, key) and key not in {"id", "created_at", "updated_at"}:
            setattr(company, key, value)
    session.flush()
    audit_service.record(
        session,
        action="update",
        entity_type="company",
        entity_id=company.id,
        summary=f"Company profile updated ({company.name})",
        user_id=actor.id,
        username=actor.username,
    )
    return company


# ------------------------------------------------------------------ settings


def get_setting(session: Session, key: str, default: str = "") -> str:
    """Read an application setting."""
    row = session.scalar(select(AppSetting).where(AppSetting.key == key))
    return row.value if row else default


def set_setting(session: Session, key: str, value: str, group: str = "general") -> None:
    """Create or update an application setting."""
    row = session.scalar(select(AppSetting).where(AppSetting.key == key))
    if row is None:
        row = AppSetting(key=key, value=value, group=group)
        session.add(row)
    else:
        row.value = value
        row.group = group
    session.flush()


def all_settings(session: Session, group: str | None = None) -> dict[str, str]:
    """Return settings as a ``key -> value`` mapping."""
    stmt = select(AppSetting)
    if group:
        stmt = stmt.where(AppSetting.group == group)
    return {row.key: row.value for row in session.scalars(stmt).all()}
