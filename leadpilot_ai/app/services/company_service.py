"""Company profile, branches, services, marketing catalogue and backup/restore."""

from __future__ import annotations

import logging
import shutil
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.config import load_config
from app.database.engine import get_engine, session_scope
from app.models.crm import MarketingCampaign, MarketingSource
from app.models.enums import Permission as Perm
from app.models.operations import ScheduleSlot
from app.models.organization import Branch, Company, Service
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.utils.dates import now

logger = logging.getLogger(__name__)


class CompanyError(Exception):
    """Company/catalogue rule violation (``code`` is an i18n key)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


# --------------------------------------------------------------------------- #
# Company profile
# --------------------------------------------------------------------------- #
def get_company(company_id: int = 1) -> Company | None:
    """Load the company profile."""
    with session_scope() as session:
        return (
            session.get(Company, company_id) or session.execute(select(Company)).scalars().first()
        )


def save_company(*, actor: CurrentUser, company_id: int = 1, **values: Any) -> Company:
    """Update the company profile."""
    actor.require(Perm.SETTINGS_MANAGE)
    with session_scope() as session:
        company = session.get(Company, company_id)
        if company is None:
            raise CompanyError("company_not_found")
        changes = []
        for field, value in values.items():
            if not hasattr(company, field):
                continue
            old = getattr(company, field)
            if old == value:
                continue
            setattr(company, field, value)
            changes.append(f"{field}: {old} → {value}")
        session.flush()
        if changes:
            audit_service.record(
                session,
                action="company_updated",
                entity_type="company",
                entity_id=company.id,
                entity_label=company.name,
                detail="; ".join(changes)[:2000],
                user_id=actor.id,
                username=actor.username,
            )
        return company


# --------------------------------------------------------------------------- #
# Branches
# --------------------------------------------------------------------------- #
def list_branches(include_archived: bool = False) -> list[Branch]:
    """All branches."""
    with session_scope() as session:
        stmt = select(Branch).order_by(Branch.name)
        if not include_archived:
            stmt = stmt.where(Branch.is_archived.is_(False))
        return list(session.execute(stmt).scalars().all())


def save_branch(
    *,
    actor: CurrentUser,
    branch_id: int | None = None,
    name: str,
    address: str = "",
    phone: str = "",
    work_start: str = "09:00",
    work_end: str = "19:00",
    is_active: bool = True,
    company_id: int = 1,
) -> Branch:
    """Create or update a branch."""
    actor.require(Perm.SETTINGS_MANAGE)
    if not name.strip():
        raise CompanyError("branch_name_required")
    with session_scope() as session:
        if branch_id:
            branch = session.get(Branch, branch_id)
            if branch is None:
                raise CompanyError("branch_not_found")
        else:
            branch = Branch(company_id=company_id, name=name)
            session.add(branch)
        branch.name = name.strip()
        branch.address = address.strip()
        branch.phone = phone.strip()
        branch.work_start = work_start
        branch.work_end = work_end
        branch.is_active = is_active
        session.flush()
        audit_service.record(
            session,
            action="branch_saved",
            entity_type="branch",
            entity_id=branch.id,
            entity_label=branch.name,
            user_id=actor.id,
            username=actor.username,
        )
        return branch


def archive_branch(branch_id: int, *, actor: CurrentUser) -> None:
    """Archive a branch."""
    actor.require(Perm.SETTINGS_MANAGE)
    with session_scope() as session:
        branch = session.get(Branch, branch_id)
        if branch is None:
            raise CompanyError("branch_not_found")
        branch.is_archived = True
        branch.archived_at = now()
        branch.is_active = False


# --------------------------------------------------------------------------- #
# Services
# --------------------------------------------------------------------------- #
def list_services(include_archived: bool = False, only_active: bool = False) -> list[Service]:
    """All services."""
    with session_scope() as session:
        stmt = select(Service).order_by(Service.category, Service.name)
        if not include_archived:
            stmt = stmt.where(Service.is_archived.is_(False))
        if only_active:
            stmt = stmt.where(Service.is_active.is_(True))
        return list(session.execute(stmt).scalars().unique().all())


def save_service(
    *,
    actor: CurrentUser,
    service_id: int | None = None,
    name: str,
    name_ru: str = "",
    category: str = "",
    description: str = "",
    price: float = 0.0,
    price_max: float | None = None,
    duration_minutes: int = 30,
    branch_id: int | None = None,
    is_active: bool = True,
    company_id: int = 1,
) -> Service:
    """Create or update a service."""
    actor.require(Perm.SETTINGS_MANAGE)
    if not name.strip():
        raise CompanyError("service_name_required")
    if price < 0:
        raise CompanyError("service_price_negative")
    with session_scope() as session:
        if service_id:
            service = session.get(Service, service_id)
            if service is None:
                raise CompanyError("service_not_found")
        else:
            service = Service(company_id=company_id, name=name)
            session.add(service)
        service.name = name.strip()
        service.name_ru = name_ru.strip()
        service.category = category.strip()
        service.description = description
        service.price = float(price)
        service.price_max = price_max
        service.duration_minutes = int(duration_minutes)
        service.branch_id = branch_id
        service.is_active = is_active
        session.flush()
        audit_service.record(
            session,
            action="service_saved",
            entity_type="service",
            entity_id=service.id,
            entity_label=service.name,
            new_value=str(price),
            user_id=actor.id,
            username=actor.username,
        )
        return service


def archive_service(service_id: int, *, actor: CurrentUser) -> None:
    """Archive a service."""
    actor.require(Perm.SETTINGS_MANAGE)
    with session_scope() as session:
        service = session.get(Service, service_id)
        if service is None:
            raise CompanyError("service_not_found")
        service.is_archived = True
        service.archived_at = now()
        service.is_active = False


# --------------------------------------------------------------------------- #
# Marketing catalogue
# --------------------------------------------------------------------------- #
def list_sources() -> list[MarketingSource]:
    """All marketing sources."""
    with session_scope() as session:
        return list(
            session.execute(select(MarketingSource).order_by(MarketingSource.name)).scalars().all()
        )


def save_source(
    *,
    actor: CurrentUser,
    source_id: int | None = None,
    name: str,
    source_type: str = "other",
    utm_source: str = "",
    is_active: bool = True,
) -> MarketingSource:
    """Create or update a marketing source."""
    actor.require(Perm.MARKETING_EDIT)
    if not name.strip():
        raise CompanyError("source_name_required")
    with session_scope() as session:
        if source_id:
            source = session.get(MarketingSource, source_id)
            if source is None:
                raise CompanyError("source_not_found")
        else:
            source = MarketingSource(name=name)
            session.add(source)
        source.name = name.strip()
        source.source_type = source_type
        source.utm_source = utm_source.strip().lower()
        source.is_active = is_active
        session.flush()
        return source


def list_campaigns(include_archived: bool = False) -> list[MarketingCampaign]:
    """All marketing campaigns."""
    with session_scope() as session:
        stmt = select(MarketingCampaign).order_by(MarketingCampaign.name)
        if not include_archived:
            stmt = stmt.where(MarketingCampaign.is_archived.is_(False))
        return list(session.execute(stmt).scalars().unique().all())


def save_campaign(
    *,
    actor: CurrentUser,
    campaign_id: int | None = None,
    source_id: int,
    name: str,
    utm_campaign: str = "",
    utm_medium: str = "",
    utm_content: str = "",
    cost: float = 0.0,
    start_date: date | None = None,
    end_date: date | None = None,
    branch_id: int | None = None,
    service_id: int | None = None,
    is_active: bool = True,
) -> MarketingCampaign:
    """Create or update a campaign with its budget."""
    actor.require(Perm.MARKETING_EDIT)
    if not name.strip():
        raise CompanyError("campaign_name_required")
    if cost < 0:
        raise CompanyError("campaign_cost_negative")
    if start_date and end_date and end_date < start_date:
        raise CompanyError("campaign_invalid_dates")
    with session_scope() as session:
        if campaign_id:
            campaign = session.get(MarketingCampaign, campaign_id)
            if campaign is None:
                raise CompanyError("campaign_not_found")
        else:
            campaign = MarketingCampaign(source_id=source_id, name=name)
            session.add(campaign)
        campaign.source_id = source_id
        campaign.name = name.strip()
        campaign.utm_campaign = utm_campaign.strip().lower()
        campaign.utm_medium = utm_medium.strip().lower()
        campaign.utm_content = utm_content.strip()
        campaign.cost = float(cost)
        campaign.start_date = start_date
        campaign.end_date = end_date
        campaign.branch_id = branch_id
        campaign.service_id = service_id
        campaign.is_active = is_active
        session.flush()
        audit_service.record(
            session,
            action="campaign_saved",
            entity_type="campaign",
            entity_id=campaign.id,
            entity_label=campaign.name,
            new_value=f"cost={cost}",
            user_id=actor.id,
            username=actor.username,
        )
        return campaign


# --------------------------------------------------------------------------- #
# Schedule templates
# --------------------------------------------------------------------------- #
def list_schedule_slots() -> list[ScheduleSlot]:
    """Working-hours templates."""
    with session_scope() as session:
        return list(
            session.execute(select(ScheduleSlot).order_by(ScheduleSlot.weekday)).scalars().all()
        )


def save_schedule_slot(
    *,
    actor: CurrentUser,
    slot_id: int | None = None,
    weekday: int,
    start_time: str,
    end_time: str,
    slot_minutes: int = 30,
    branch_id: int | None = None,
    specialist_id: int | None = None,
    is_active: bool = True,
) -> ScheduleSlot:
    """Create or update a working-hours template."""
    actor.require(Perm.SETTINGS_MANAGE)
    with session_scope() as session:
        if slot_id:
            slot = session.get(ScheduleSlot, slot_id)
            if slot is None:
                raise CompanyError("slot_not_found")
        else:
            slot = ScheduleSlot(weekday=weekday)
            session.add(slot)
        slot.weekday = weekday
        slot.start_time = start_time
        slot.end_time = end_time
        slot.slot_minutes = slot_minutes
        slot.branch_id = branch_id
        slot.specialist_id = specialist_id
        slot.is_active = is_active
        session.flush()
        return slot


# --------------------------------------------------------------------------- #
# Backup / restore
# --------------------------------------------------------------------------- #
def backup_database(target_path: str, *, actor: CurrentUser) -> str:
    """Copy the SQLite database to ``target_path``."""
    actor.require(Perm.SETTINGS_MANAGE)
    source = load_config().database_path
    destination = Path(target_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA wal_checkpoint(FULL)")
    shutil.copy2(source, destination)
    with session_scope() as session:
        audit_service.record(
            session,
            action="backup_created",
            entity_type="database",
            entity_label=destination.name,
            user_id=actor.id,
            username=actor.username,
        )
    return str(destination)


def restore_database(source_path: str, *, actor: CurrentUser) -> str:
    """Replace the working database with a backup file.

    The current database is kept as ``*.before-restore`` so the operation can be
    undone manually. The application must be restarted afterwards.
    """
    actor.require(Perm.SETTINGS_MANAGE)
    source = Path(source_path)
    if not source.exists():
        raise CompanyError("backup_not_found")
    target = load_config().database_path
    engine = get_engine()
    engine.dispose()
    safety_copy = target.with_suffix(target.suffix + ".before-restore")
    if target.exists():
        shutil.copy2(target, safety_copy)
    shutil.copy2(source, target)
    return str(safety_copy)
