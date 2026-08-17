"""Marketing ROI attribution and operator performance analytics."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.models.crm import Lead, MarketingCampaign, MarketingSource, RevenueRecord
from app.models.enums import BookingStatus, LeadStatus, TaskStatus
from app.models.messaging import Conversation, Message
from app.models.operations import Booking, Call, CallAnalysis, Task
from app.models.organization import Service, User
from app.utils.dates import end_of_day, start_of_day

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Formulas (pure functions — unit tested)
# --------------------------------------------------------------------------- #
def conversion_rate(sales: int, leads: int) -> float:
    """``Sotuvlar / Leadlar × 100``."""
    return (sales / leads * 100) if leads else 0.0


def cost_per_lead(cost: float, leads: int) -> float:
    """``Reklama xarajati / Leadlar``."""
    return (cost / leads) if leads else 0.0


def cost_per_booking(cost: float, bookings: int) -> float:
    """``Reklama xarajati / Bronlar``."""
    return (cost / bookings) if bookings else 0.0


def cost_per_sale(cost: float, sales: int) -> float:
    """``Reklama xarajati / Sotuvlar``."""
    return (cost / sales) if sales else 0.0


def roas(revenue: float, cost: float) -> float:
    """``Daromad / Reklama xarajati``."""
    return (revenue / cost) if cost else 0.0


@dataclass
class MarketingRow:
    """One row of the Marketing Source Analysis worksheet."""

    key: str
    source_id: int | None
    campaign_id: int | None
    source_name: str
    campaign_name: str
    leads: int = 0
    answered: int = 0
    bookings: int = 0
    arrivals: int = 0
    sales: int = 0
    revenue: float = 0.0
    cost: float = 0.0

    @property
    def conversion(self) -> float:
        """Lead → sale conversion in percent."""
        return conversion_rate(self.sales, self.leads)

    @property
    def cpl(self) -> float:
        """Cost per lead."""
        return cost_per_lead(self.cost, self.leads)

    @property
    def cpb(self) -> float:
        """Cost per booking."""
        return cost_per_booking(self.cost, self.bookings)

    @property
    def cps(self) -> float:
        """Cost per sale."""
        return cost_per_sale(self.cost, self.sales)

    @property
    def roas(self) -> float:
        """Return on ad spend."""
        return roas(self.revenue, self.cost)


@dataclass
class OperatorRow:
    """One row of the operator quality worksheet."""

    user_id: int
    full_name: str
    leads: int = 0
    first_response_avg_sec: int = 0
    response_avg_sec: int = 0
    closed: int = 0
    bookings: int = 0
    arrivals: int = 0
    sales: int = 0
    revenue: float = 0.0
    missed_followups: int = 0
    call_quality: float = 0.0
    ai_usage: float = 0.0
    positive_sentiment: float = 0.0

    @property
    def conversion(self) -> float:
        """Lead → sale conversion in percent."""
        return conversion_rate(self.sales, self.leads)


@dataclass
class PeriodFilter:
    """Common filter for every analytical query."""

    date_from: date | None = None
    date_to: date | None = None
    channels: list[str] = field(default_factory=list)
    branch_ids: list[int] = field(default_factory=list)
    service_ids: list[int] = field(default_factory=list)
    owner_ids: list[int] = field(default_factory=list)
    source_ids: list[int] = field(default_factory=list)
    campaign_ids: list[int] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)

    def start(self) -> datetime | None:
        """Inclusive lower bound as a datetime."""
        return start_of_day(self.date_from) if self.date_from else None

    def end(self) -> datetime | None:
        """Inclusive upper bound as a datetime."""
        return end_of_day(self.date_to) if self.date_to else None


def _apply_lead_period(stmt, flt: PeriodFilter):  # type: ignore[no-untyped-def]
    """Apply the shared period filter to a lead query."""
    if flt.start():
        stmt = stmt.where(Lead.created_at >= flt.start())
    if flt.end():
        stmt = stmt.where(Lead.created_at <= flt.end())
    if flt.channels:
        stmt = stmt.where(Lead.channel.in_(flt.channels))
    if flt.branch_ids:
        stmt = stmt.where(Lead.branch_id.in_(flt.branch_ids))
    if flt.service_ids:
        stmt = stmt.where(Lead.service_id.in_(flt.service_ids))
    if flt.owner_ids:
        stmt = stmt.where(Lead.owner_id.in_(flt.owner_ids))
    if flt.source_ids:
        stmt = stmt.where(Lead.source_id.in_(flt.source_ids))
    if flt.campaign_ids:
        stmt = stmt.where(Lead.campaign_id.in_(flt.campaign_ids))
    if flt.statuses:
        stmt = stmt.where(Lead.status.in_(flt.statuses))
    return stmt.where(Lead.is_archived.is_(False))


# --------------------------------------------------------------------------- #
# Marketing attribution
# --------------------------------------------------------------------------- #
def marketing_rows(flt: PeriodFilter, *, group_by_campaign: bool = True) -> list[MarketingRow]:
    """Build the Marketing Source Analysis rows with every ROI metric."""
    with session_scope() as session:
        leads = list(
            session.execute(_apply_lead_period(select(Lead), flt)).scalars().unique().all()
        )
        sources = {s.id: s for s in session.execute(select(MarketingSource)).scalars().all()}
        campaigns = {c.id: c for c in session.execute(select(MarketingCampaign)).scalars().all()}

        booking_counts = _counts_by_lead(session, Booking, "lead_id")
        arrival_ids = {
            row[0]
            for row in session.execute(
                select(Booking.lead_id).where(
                    Booking.status.in_([BookingStatus.ARRIVED, BookingStatus.COMPLETED])
                )
            ).all()
        }
        answered_ids = {
            row[0]
            for row in session.execute(
                select(Message.lead_id).where(Message.direction == "outbound").distinct()
            ).all()
        }

        rows: dict[str, MarketingRow] = {}
        for lead in leads:
            source = sources.get(lead.source_id) if lead.source_id else None
            campaign = campaigns.get(lead.campaign_id) if lead.campaign_id else None
            if group_by_campaign:
                key = f"{lead.source_id or 0}:{lead.campaign_id or 0}"
            else:
                key = str(lead.source_id or 0)
            row = rows.get(key)
            if row is None:
                row = MarketingRow(
                    key=key,
                    source_id=lead.source_id,
                    campaign_id=lead.campaign_id if group_by_campaign else None,
                    source_name=source.name if source else (lead.utm_source or "—"),
                    campaign_name=(
                        (campaign.name if campaign else lead.utm_campaign or "—")
                        if group_by_campaign
                        else ""
                    ),
                )
                rows[key] = row
            row.leads += 1
            if lead.id in answered_ids:
                row.answered += 1
            row.bookings += booking_counts.get(lead.id, 0)
            if lead.id in arrival_ids:
                row.arrivals += 1
            if lead.status == LeadStatus.WON:
                row.sales += 1
                row.revenue += float(lead.revenue or 0)

        # Campaign costs
        for row in rows.values():
            if row.campaign_id and row.campaign_id in campaigns:
                row.cost = float(campaigns[row.campaign_id].cost or 0)
            elif not group_by_campaign and row.source_id:
                row.cost = float(
                    sum(c.cost or 0 for c in campaigns.values() if c.source_id == row.source_id)
                )
        return sorted(rows.values(), key=lambda r: r.leads, reverse=True)


def _counts_by_lead(session: Session, model, field_name: str) -> dict[int, int]:
    """Count rows of ``model`` grouped by lead id."""
    column = getattr(model, field_name)
    rows = session.execute(select(column, func.count(model.id)).group_by(column)).all()
    return {int(lead_id): int(count) for lead_id, count in rows if lead_id is not None}


def leads_of_source(
    flt: PeriodFilter, *, source_id: int | None, campaign_id: int | None = None
) -> list[Lead]:
    """Drill-down: leads that came from one marketing row."""
    with session_scope() as session:
        stmt = _apply_lead_period(select(Lead), flt)
        stmt = (
            stmt.where(Lead.source_id == source_id)
            if source_id
            else stmt.where(Lead.source_id.is_(None))
        )
        if campaign_id:
            stmt = stmt.where(Lead.campaign_id == campaign_id)
        return list(session.execute(stmt.order_by(Lead.created_at.desc())).scalars().unique().all())


# --------------------------------------------------------------------------- #
# Operator performance
# --------------------------------------------------------------------------- #
def operator_rows(flt: PeriodFilter) -> list[OperatorRow]:
    """Aggregate the operator quality worksheet."""
    with session_scope() as session:
        users = list(
            session.execute(
                select(User).where(User.is_archived.is_(False), User.is_active.is_(True))
            )
            .scalars()
            .unique()
            .all()
        )
        rows: dict[int, OperatorRow] = {
            user.id: OperatorRow(user_id=user.id, full_name=user.full_name) for user in users
        }

        leads = list(
            session.execute(_apply_lead_period(select(Lead), flt)).scalars().unique().all()
        )
        response_totals: dict[int, list[int]] = {}
        for lead in leads:
            if lead.owner_id not in rows:
                continue
            row = rows[lead.owner_id]
            row.leads += 1
            if lead.status in (LeadStatus.WON, LeadStatus.LOST):
                row.closed += 1
            if lead.status == LeadStatus.WON:
                row.sales += 1
                row.revenue += float(lead.revenue or 0)
            if lead.first_response_seconds is not None:
                response_totals.setdefault(lead.owner_id, []).append(lead.first_response_seconds)

        for user_id, values in response_totals.items():
            rows[user_id].first_response_avg_sec = int(sum(values) / len(values))
            rows[user_id].response_avg_sec = rows[user_id].first_response_avg_sec

        booking_stmt = select(Booking.specialist_id, Booking.status, func.count(Booking.id))
        if flt.start():
            booking_stmt = booking_stmt.where(Booking.starts_at >= flt.start())
        if flt.end():
            booking_stmt = booking_stmt.where(Booking.starts_at <= flt.end())
        for specialist_id, status, count in session.execute(
            booking_stmt.group_by(Booking.specialist_id, Booking.status)
        ).all():
            if specialist_id in rows:
                rows[specialist_id].bookings += int(count)
                if status in (BookingStatus.ARRIVED, BookingStatus.COMPLETED):
                    rows[specialist_id].arrivals += int(count)

        overdue_stmt = select(Task.assignee_id, func.count(Task.id)).where(
            Task.status == TaskStatus.OVERDUE
        )
        for assignee_id, count in session.execute(overdue_stmt.group_by(Task.assignee_id)).all():
            if assignee_id in rows:
                rows[assignee_id].missed_followups = int(count)

        quality_stmt = select(Call.operator_id, func.avg(CallAnalysis.quality_score)).join(
            CallAnalysis, CallAnalysis.call_id == Call.id
        )
        if flt.start():
            quality_stmt = quality_stmt.where(Call.started_at >= flt.start())
        if flt.end():
            quality_stmt = quality_stmt.where(Call.started_at <= flt.end())
        for operator_id, avg_quality in session.execute(
            quality_stmt.group_by(Call.operator_id)
        ).all():
            if operator_id in rows:
                rows[operator_id].call_quality = float(avg_quality or 0)

        sentiment_stmt = select(
            Call.operator_id,
            func.sum(func.iif(CallAnalysis.sentiment == "positive", 1, 0)),
            func.count(CallAnalysis.id),
        ).join(CallAnalysis, CallAnalysis.call_id == Call.id)
        for operator_id, positive, total in session.execute(
            sentiment_stmt.group_by(Call.operator_id)
        ).all():
            if operator_id in rows and total:
                rows[operator_id].positive_sentiment = float(positive or 0) / float(total) * 100

        ai_usage = _ai_usage_by_operator(session)
        for operator_id, ratio in ai_usage.items():
            if operator_id in rows:
                rows[operator_id].ai_usage = ratio

        return [row for row in rows.values() if row.leads or row.bookings or row.call_quality]


def _ai_usage_by_operator(session: Session) -> dict[int, float]:
    """Share of operator messages that came from an AI suggestion."""
    rows = session.execute(
        select(
            Message.sender_user_id,
            func.count(Message.id),
            func.sum(func.iif(Message.ai_interaction_id.isnot(None), 1, 0)),
        )
        .where(Message.direction == "outbound", Message.sender_user_id.isnot(None))
        .group_by(Message.sender_user_id)
    ).all()
    return {
        int(user_id): (float(used or 0) / float(total) * 100) if total else 0.0
        for user_id, total, used in rows
        if user_id is not None
    }


# --------------------------------------------------------------------------- #
# Headline numbers for the workspace overview strip
# --------------------------------------------------------------------------- #
def workspace_summary(flt: PeriodFilter) -> dict[str, float]:
    """Compact KPI set displayed above the leads worksheet."""
    with session_scope() as session:
        leads = list(
            session.execute(_apply_lead_period(select(Lead), flt)).scalars().unique().all()
        )
        total = len(leads)
        won = sum(1 for lead in leads if lead.status == LeadStatus.WON)
        lost = sum(1 for lead in leads if lead.status == LeadStatus.LOST)
        hot = sum(1 for lead in leads if lead.intent == "hot")
        revenue = sum(float(lead.revenue or 0) for lead in leads)
        responses = [
            lead.first_response_seconds for lead in leads if lead.first_response_seconds is not None
        ]
        booking_stmt = select(func.count(Booking.id)).where(Booking.is_archived.is_(False))
        if flt.start():
            booking_stmt = booking_stmt.where(Booking.starts_at >= flt.start())
        if flt.end():
            booking_stmt = booking_stmt.where(Booking.starts_at <= flt.end())
        bookings = int(session.execute(booking_stmt).scalar_one())
        return {
            "leads": float(total),
            "won": float(won),
            "lost": float(lost),
            "hot": float(hot),
            "bookings": float(bookings),
            "revenue": revenue,
            "conversion": conversion_rate(won, total),
            "avg_first_response_sec": float(sum(responses) / len(responses)) if responses else 0.0,
        }


def channel_conversion(flt: PeriodFilter) -> list[dict[str, float | str]]:
    """Conversion per channel used by the reports page."""
    with session_scope() as session:
        leads = list(
            session.execute(_apply_lead_period(select(Lead), flt)).scalars().unique().all()
        )
        buckets: dict[str, dict[str, float]] = {}
        for lead in leads:
            bucket = buckets.setdefault(
                lead.channel, {"leads": 0, "won": 0, "revenue": 0.0, "bookings": 0}
            )
            bucket["leads"] += 1
            if lead.status == LeadStatus.WON:
                bucket["won"] += 1
                bucket["revenue"] += float(lead.revenue or 0)
            if lead.status in (LeadStatus.BOOKED, LeadStatus.ARRIVED, LeadStatus.WON):
                bucket["bookings"] += 1
        return [
            {
                "channel": channel,
                "leads": values["leads"],
                "bookings": values["bookings"],
                "won": values["won"],
                "revenue": values["revenue"],
                "conversion": conversion_rate(int(values["won"]), int(values["leads"])),
            }
            for channel, values in sorted(
                buckets.items(), key=lambda kv: kv[1]["leads"], reverse=True
            )
        ]


def loss_reasons(flt: PeriodFilter) -> list[dict[str, float | str]]:
    """Breakdown of why leads were lost."""
    with session_scope() as session:
        stmt = _apply_lead_period(select(Lead), flt).where(Lead.status == LeadStatus.LOST)
        leads = list(session.execute(stmt).scalars().unique().all())
        buckets: dict[str, int] = {}
        for lead in leads:
            buckets[lead.loss_reason or "other"] = buckets.get(lead.loss_reason or "other", 0) + 1
        total = sum(buckets.values()) or 1
        return [
            {"reason": reason, "count": count, "share": count / total * 100}
            for reason, count in sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)
        ]


def service_sales(flt: PeriodFilter) -> list[dict[str, float | str]]:
    """Revenue grouped by service and branch."""
    with session_scope() as session:
        services = {s.id: s.name for s in session.execute(select(Service)).scalars().all()}
        stmt = select(
            RevenueRecord.service_id, func.count(RevenueRecord.id), func.sum(RevenueRecord.amount)
        )
        if flt.date_from:
            stmt = stmt.where(RevenueRecord.sale_date >= flt.date_from)
        if flt.date_to:
            stmt = stmt.where(RevenueRecord.sale_date <= flt.date_to)
        rows = session.execute(stmt.group_by(RevenueRecord.service_id)).all()
        return [
            {
                "service": services.get(service_id, "—"),
                "sales": float(count or 0),
                "revenue": float(total or 0),
            }
            for service_id, count, total in rows
        ]


def followup_compliance(flt: PeriodFilter) -> dict[str, float]:
    """How well the team executes its follow-up tasks."""
    with session_scope() as session:
        stmt = select(Task.status, func.count(Task.id)).where(Task.is_archived.is_(False))
        if flt.start():
            stmt = stmt.where(Task.created_at >= flt.start())
        if flt.end():
            stmt = stmt.where(Task.created_at <= flt.end())
        counts = {
            status: int(count)
            for status, count in session.execute(stmt.group_by(Task.status)).all()
        }
        total = sum(counts.values()) or 1
        done = counts.get(TaskStatus.DONE, 0)
        return {
            "total": float(sum(counts.values())),
            "done": float(done),
            "open": float(counts.get(TaskStatus.OPEN, 0)),
            "overdue": float(counts.get(TaskStatus.OVERDUE, 0)),
            "compliance": done / total * 100,
        }


def unanswered_leads(minutes: int = 15) -> list[Lead]:
    """Leads waiting longer than ``minutes`` for a first answer."""
    from app.utils.dates import now

    with session_scope() as session:
        threshold = now()
        stmt = (
            select(Lead)
            .join(Conversation, Conversation.lead_id == Lead.id)
            .where(
                Lead.is_archived.is_(False),
                Conversation.unread_count > 0,
                Conversation.last_message_at.isnot(None),
            )
            .distinct()
        )
        result = []
        for lead, conversation in session.execute(stmt.add_columns(Conversation)).unique().all():
            waited = (threshold - conversation.last_message_at).total_seconds() / 60
            if waited >= minutes:
                result.append(lead)
        return result
