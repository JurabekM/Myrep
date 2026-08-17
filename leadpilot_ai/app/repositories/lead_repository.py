"""Lead queries: filtering, search, pagination and duplicate detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.crm import Lead, Tag, lead_tags
from app.models.enums import CLOSED_STATUSES, IntentLevel
from app.repositories.base import BaseRepository
from app.utils.formatting import normalize_phone


@dataclass
class LeadFilter:
    """Declarative filter used by the leads table and by reports."""

    search: str = ""
    statuses: list[str] = field(default_factory=list)
    channels: list[str] = field(default_factory=list)
    owner_ids: list[int] = field(default_factory=list)
    source_ids: list[int] = field(default_factory=list)
    campaign_ids: list[int] = field(default_factory=list)
    service_ids: list[int] = field(default_factory=list)
    branch_ids: list[int] = field(default_factory=list)
    tag_ids: list[int] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None
    only_open: bool = False
    only_unassigned: bool = False
    include_archived: bool = False
    min_score: int | None = None


class LeadRepository(BaseRepository[Lead]):
    """Repository for :class:`~app.models.crm.Lead`."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Lead)

    # ------------------------------------------------------------------ #
    # Query building
    # ------------------------------------------------------------------ #
    def _apply(self, stmt: Select, flt: LeadFilter) -> Select:
        """Apply a :class:`LeadFilter` to a select statement."""
        if not flt.include_archived:
            stmt = stmt.where(Lead.is_archived.is_(False))
        if flt.search:
            pattern = f"%{flt.search.strip().lower()}%"
            digits = normalize_phone(flt.search) or ""
            stmt = stmt.where(
                or_(
                    func.lower(Lead.full_name).like(pattern),
                    func.lower(Lead.telegram_username).like(pattern),
                    func.lower(Lead.email).like(pattern),
                    func.lower(Lead.interest).like(pattern),
                    func.lower(Lead.notes).like(pattern),
                    Lead.phone.like(f"%{flt.search.strip()}%"),
                    Lead.phone == digits if digits else Lead.id == -1,
                )
            )
        if flt.statuses:
            stmt = stmt.where(Lead.status.in_(flt.statuses))
        if flt.channels:
            stmt = stmt.where(Lead.channel.in_(flt.channels))
        if flt.owner_ids:
            stmt = stmt.where(Lead.owner_id.in_(flt.owner_ids))
        if flt.source_ids:
            stmt = stmt.where(Lead.source_id.in_(flt.source_ids))
        if flt.campaign_ids:
            stmt = stmt.where(Lead.campaign_id.in_(flt.campaign_ids))
        if flt.service_ids:
            stmt = stmt.where(Lead.service_id.in_(flt.service_ids))
        if flt.branch_ids:
            stmt = stmt.where(Lead.branch_id.in_(flt.branch_ids))
        if flt.intents:
            stmt = stmt.where(Lead.intent.in_(flt.intents))
        if flt.tag_ids:
            stmt = stmt.where(
                Lead.id.in_(select(lead_tags.c.lead_id).where(lead_tags.c.tag_id.in_(flt.tag_ids)))
            )
        if flt.date_from:
            stmt = stmt.where(Lead.created_at >= flt.date_from)
        if flt.date_to:
            stmt = stmt.where(Lead.created_at <= flt.date_to)
        if flt.only_open:
            stmt = stmt.where(Lead.status.notin_(list(CLOSED_STATUSES)))
        if flt.only_unassigned:
            stmt = stmt.where(Lead.owner_id.is_(None))
        if flt.min_score is not None:
            stmt = stmt.where(Lead.score >= flt.min_score)
        return stmt

    def search(
        self,
        flt: LeadFilter,
        *,
        sort_field: str = "created_at",
        descending: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Lead]:
        """Return a page of leads matching ``flt``."""
        stmt = self._apply(select(Lead), flt)
        column = getattr(Lead, sort_field, Lead.created_at)
        stmt = stmt.order_by(column.desc() if descending else column.asc(), Lead.id.desc())
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.execute(stmt).scalars().unique().all())

    def count_filtered(self, flt: LeadFilter) -> int:
        """Total number of leads matching ``flt`` (for pagination)."""
        stmt = self._apply(select(func.count(Lead.id)), flt)
        return int(self.session.execute(stmt).scalar_one())

    # ------------------------------------------------------------------ #
    # Duplicate detection
    # ------------------------------------------------------------------ #
    def find_duplicates(
        self,
        *,
        phone: str | None = None,
        telegram_username: str | None = None,
        email: str | None = None,
        external_id: str | None = None,
        exclude_id: int | None = None,
    ) -> list[Lead]:
        """Find existing leads that look like the same person."""
        clauses = []
        normalized = normalize_phone(phone)
        if normalized:
            clauses.append(Lead.phone == normalized)
        if telegram_username:
            clauses.append(
                func.lower(Lead.telegram_username) == telegram_username.lower().lstrip("@")
            )
        if email:
            clauses.append(func.lower(Lead.email) == email.lower())
        if external_id:
            clauses.append(Lead.external_id == external_id)
        if not clauses:
            return []
        stmt = select(Lead).where(or_(*clauses), Lead.is_archived.is_(False))
        if exclude_id:
            stmt = stmt.where(Lead.id != exclude_id)
        return list(self.session.execute(stmt).scalars().unique().all())

    # ------------------------------------------------------------------ #
    # Aggregates
    # ------------------------------------------------------------------ #
    def status_counts(self, flt: LeadFilter | None = None) -> dict[str, int]:
        """Number of leads per status."""
        stmt = select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
        stmt = self._apply(stmt, flt or LeadFilter())
        return {row[0]: row[1] for row in self.session.execute(stmt).all()}

    def hot_leads(self, threshold: int = 70, limit: int = 50) -> list[Lead]:
        """Leads whose score marks them as hot and that are still open."""
        stmt = (
            select(Lead)
            .where(
                Lead.is_archived.is_(False),
                Lead.status.notin_(list(CLOSED_STATUSES)),
                or_(Lead.score >= threshold, Lead.intent == IntentLevel.HOT),
            )
            .order_by(Lead.score.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().unique().all())

    def tags(self) -> list[Tag]:
        """All available tags ordered by name."""
        return list(self.session.execute(select(Tag).order_by(Tag.name)).scalars().all())
