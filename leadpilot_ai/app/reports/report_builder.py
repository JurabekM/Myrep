"""Builds the data of every report; the page decides PDF or Excel."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from app.models.enums import BookingStatus
from app.repositories.lead_repository import LeadFilter
from app.services import (
    ai_agent_service,
    analytics_service,
    booking_service,
    call_service,
    lead_service,
    task_service,
)
from app.services.analytics_service import PeriodFilter
from app.ui.i18n import tr
from app.ui.widgets.labels import (
    booking_status_label,
    channel_label,
    intent_label,
    loss_label,
    outcome_label,
    status_label,
)
from app.utils.dates import fmt_date, fmt_datetime
from app.utils.formatting import fmt_duration, fmt_money, fmt_number, fmt_percent, pretty_phone


@dataclass
class ReportSection:
    """One table inside a report."""

    title: str
    headers: Sequence[str]
    rows: list[Sequence[Any]]


@dataclass
class ReportSpec:
    """Definition of a report offered on the reports page."""

    key: str
    title_key: str
    builder: Callable[[PeriodFilter], list[ReportSection]]


# --------------------------------------------------------------------------- #
# Individual builders
# --------------------------------------------------------------------------- #
def _leads_registry(flt: PeriodFilter) -> list[ReportSection]:
    """Full lead registry for the period."""
    leads, _ = lead_service.search_leads(
        LeadFilter(
            date_from=flt.start(),
            date_to=flt.end(),
            channels=flt.channels,
            owner_ids=flt.owner_ids,
            source_ids=flt.source_ids,
            campaign_ids=flt.campaign_ids,
            service_ids=flt.service_ids,
            statuses=flt.statuses,
        ),
        limit=5000,
    )
    headers = [
        "ID",
        tr("common.name"),
        tr("common.phone"),
        tr("common.channel"),
        tr("common.status"),
        tr("leads.intent"),
        tr("common.score"),
        tr("leads.owner"),
        tr("common.source"),
        tr("common.revenue"),
        tr("common.created"),
    ]
    rows = [
        [
            lead.id,
            lead.display_name,
            pretty_phone(lead.phone),
            channel_label(lead.channel),
            status_label(lead.status),
            intent_label(lead.intent),
            lead.score,
            lead.owner.full_name if lead.owner else "—",
            lead.source.name if lead.source else (lead.utm_source or "—"),
            fmt_money(lead.revenue) if lead.revenue else "—",
            fmt_date(lead.created_at),
        ]
        for lead in leads
    ]
    return [ReportSection(tr("rep.leads_registry"), headers, rows)]


def _period_results(flt: PeriodFilter) -> list[ReportSection]:
    """Headline KPIs of the period."""
    summary = analytics_service.workspace_summary(flt)
    headers = [tr("common.name"), tr("common.count")]
    rows = [
        [tr("mkt.leads"), fmt_number(summary["leads"])],
        [tr("intent.hot"), fmt_number(summary["hot"])],
        [tr("mkt.bookings"), fmt_number(summary["bookings"])],
        [tr("status.won"), fmt_number(summary["won"])],
        [tr("status.lost"), fmt_number(summary["lost"])],
        [tr("common.revenue"), fmt_money(summary["revenue"])],
        [tr("mkt.conversion"), fmt_percent(summary["conversion"])],
        [tr("ops.first_response"), fmt_duration(int(summary["avg_first_response_sec"]))],
    ]
    return [ReportSection(tr("rep.period_results"), headers, rows)]


def _channel_conversion(flt: PeriodFilter) -> list[ReportSection]:
    """Conversion per channel."""
    headers = [
        tr("common.channel"),
        tr("mkt.leads"),
        tr("mkt.bookings"),
        tr("status.won"),
        tr("common.revenue"),
        tr("mkt.conversion"),
    ]
    rows = [
        [
            channel_label(str(row["channel"])),
            fmt_number(row["leads"]),
            fmt_number(row["bookings"]),
            fmt_number(row["won"]),
            fmt_money(row["revenue"]),
            fmt_percent(float(row["conversion"])),
        ]
        for row in analytics_service.channel_conversion(flt)
    ]
    return [ReportSection(tr("rep.channel_conversion"), headers, rows)]


def _campaign_roi(flt: PeriodFilter) -> list[ReportSection]:
    """ROI per marketing campaign."""
    headers = [
        tr("common.source"),
        tr("common.campaign"),
        tr("mkt.leads"),
        tr("mkt.bookings"),
        tr("mkt.sales"),
        tr("common.revenue"),
        tr("mkt.cost"),
        tr("mkt.cpl"),
        tr("mkt.cpb"),
        tr("mkt.cps"),
        tr("mkt.roas"),
        tr("mkt.conversion"),
    ]
    rows = [
        [
            row.source_name,
            row.campaign_name,
            fmt_number(row.leads),
            fmt_number(row.bookings),
            fmt_number(row.sales),
            fmt_money(row.revenue),
            fmt_money(row.cost),
            fmt_money(row.cpl),
            fmt_money(row.cpb),
            fmt_money(row.cps),
            f"{row.roas:.2f}",
            fmt_percent(row.conversion),
        ]
        for row in analytics_service.marketing_rows(flt)
    ]
    return [ReportSection(tr("rep.campaign_roi"), headers, rows)]


def _bookings(flt: PeriodFilter) -> list[ReportSection]:
    """Booking register."""
    bookings = booking_service.list_bookings(day_from=flt.date_from, day_to=flt.date_to, limit=5000)
    headers = [
        tr("common.date"),
        tr("common.name"),
        tr("common.service"),
        tr("common.branch"),
        tr("booking.specialist"),
        tr("common.status"),
        tr("booking.created_by_ai"),
    ]
    rows = [
        [
            fmt_datetime(booking.starts_at),
            booking.lead.display_name if booking.lead else "—",
            booking.service.name if booking.service else "—",
            booking.branch.name if booking.branch else "—",
            booking.specialist.full_name if booking.specialist else "—",
            booking_status_label(booking.status),
            tr("common.yes") if booking.created_by_ai else tr("common.no"),
        ]
        for booking in bookings
    ]
    return [ReportSection(tr("rep.bookings"), headers, rows)]


def _no_shows(flt: PeriodFilter) -> list[ReportSection]:
    """Customers who did not arrive."""
    bookings = booking_service.list_bookings(
        day_from=flt.date_from,
        day_to=flt.date_to,
        statuses=[BookingStatus.NO_SHOW, BookingStatus.NOT_CONFIRMED],
        limit=5000,
    )
    headers = [
        tr("common.date"),
        tr("common.name"),
        tr("common.phone"),
        tr("common.service"),
        tr("common.status"),
        tr("leads.owner"),
    ]
    rows = [
        [
            fmt_datetime(booking.starts_at),
            booking.lead.display_name if booking.lead else "—",
            pretty_phone(booking.lead.phone) if booking.lead else "—",
            booking.service.name if booking.service else "—",
            booking_status_label(booking.status),
            booking.lead.owner.full_name if booking.lead and booking.lead.owner else "—",
        ]
        for booking in bookings
    ]
    return [ReportSection(tr("rep.no_shows"), headers, rows)]


def _operators(flt: PeriodFilter) -> list[ReportSection]:
    """Operator performance."""
    headers = [
        tr("common.operator"),
        tr("mkt.leads"),
        tr("ops.first_response"),
        tr("ops.closed"),
        tr("mkt.bookings"),
        tr("mkt.arrivals"),
        tr("mkt.sales"),
        tr("common.revenue"),
        tr("mkt.conversion"),
        tr("ops.missed"),
        tr("ops.call_quality"),
        tr("ops.ai_usage"),
    ]
    rows = [
        [
            row.full_name,
            fmt_number(row.leads),
            fmt_duration(row.first_response_avg_sec),
            fmt_number(row.closed),
            fmt_number(row.bookings),
            fmt_number(row.arrivals),
            fmt_number(row.sales),
            fmt_money(row.revenue),
            fmt_percent(row.conversion),
            fmt_number(row.missed_followups),
            f"{row.call_quality:.0f}",
            fmt_percent(row.ai_usage),
        ]
        for row in analytics_service.operator_rows(flt)
    ]
    return [ReportSection(tr("rep.operators"), headers, rows)]


def _ai_quality(flt: PeriodFilter) -> list[ReportSection]:
    """AI answer quality."""
    summary = ai_agent_service.quality_summary(flt.start(), flt.end())
    headers = [tr("common.name"), tr("common.count")]
    rows = [
        [tr("common.total"), fmt_number(summary["total"])],
        [tr("ai.sent"), fmt_number(summary["sent"])],
        [tr("ai.edited"), fmt_number(summary["edited"])],
        [tr("ai.rejected"), fmt_number(summary["rejected"])],
        [tr("ai.escalated"), fmt_number(summary["escalated"])],
        [tr("ai.review_useful"), fmt_percent(summary["useful_ratio"])],
    ]
    interactions = ai_agent_service.list_interactions(
        date_from=flt.start(), date_to=flt.end(), limit=300
    )
    detail_headers = [
        tr("common.date"),
        tr("ai.provider"),
        tr("common.status"),
        tr("ai.state"),
        tr("inbox.ai_suggestion"),
    ]
    detail_rows = [
        [
            fmt_datetime(item.created_at),
            f"{item.provider}/{item.model}",
            item.status,
            item.state_after,
            (item.suggested_reply or "")[:180],
        ]
        for item in interactions
    ]
    return [
        ReportSection(tr("rep.ai_quality"), headers, rows),
        ReportSection(tr("ai.quality"), detail_headers, detail_rows),
    ]


def _calls(flt: PeriodFilter) -> list[ReportSection]:
    """Call register with analysis."""
    calls = call_service.list_calls(date_from=flt.date_from, date_to=flt.date_to, limit=3000)
    headers = [
        tr("common.date"),
        tr("common.name"),
        tr("common.phone"),
        tr("calls.direction"),
        tr("common.duration"),
        tr("common.result"),
        tr("common.operator"),
    ]
    rows = [
        [
            fmt_datetime(call.started_at),
            call.lead.display_name if call.lead else "—",
            pretty_phone(call.phone),
            tr(f"calls.{call.direction}"),
            fmt_duration(call.duration_seconds),
            outcome_label(call.outcome),
            call.operator.full_name if call.operator else "—",
        ]
        for call in calls
    ]
    return [ReportSection(tr("rep.calls"), headers, rows)]


def _lost_reasons(flt: PeriodFilter) -> list[ReportSection]:
    """Why leads were lost."""
    headers = [tr("common.reason"), tr("common.count"), tr("common.share")]
    rows = [
        [loss_label(str(row["reason"])), fmt_number(row["count"]), fmt_percent(float(row["share"]))]
        for row in analytics_service.loss_reasons(flt)
    ]
    return [ReportSection(tr("rep.lost_reasons"), headers, rows)]


def _followups(flt: PeriodFilter) -> list[ReportSection]:
    """Follow-up execution."""
    summary = analytics_service.followup_compliance(flt)
    headers = [tr("common.name"), tr("common.count")]
    rows = [
        [tr("common.total"), fmt_number(summary["total"])],
        [tr("tstatus.done"), fmt_number(summary["done"])],
        [tr("tstatus.open"), fmt_number(summary["open"])],
        [tr("tstatus.overdue"), fmt_number(summary["overdue"])],
        [tr("rep.followups"), fmt_percent(summary["compliance"])],
    ]
    tasks = task_service.list_tasks(limit=1000)
    detail_headers = [
        tr("common.title"),
        tr("common.type"),
        tr("tasks.assignee"),
        tr("tasks.due"),
        tr("common.status"),
    ]
    detail_rows = [
        [
            task.title,
            task.task_type,
            task.assignee.full_name if task.assignee else "—",
            fmt_datetime(task.due_at),
            task.status,
        ]
        for task in tasks
    ]
    return [
        ReportSection(tr("rep.followups"), headers, rows),
        ReportSection(tr("tasks.title"), detail_headers, detail_rows),
    ]


def _service_sales(flt: PeriodFilter) -> list[ReportSection]:
    """Revenue by service."""
    headers = [tr("common.service"), tr("mkt.sales"), tr("common.revenue")]
    rows = [
        [str(row["service"]), fmt_number(row["sales"]), fmt_money(row["revenue"])]
        for row in analytics_service.service_sales(flt)
    ]
    return [ReportSection(tr("rep.service_sales"), headers, rows)]


REPORTS: list[ReportSpec] = [
    ReportSpec("leads_registry", "rep.leads_registry", _leads_registry),
    ReportSpec("period_results", "rep.period_results", _period_results),
    ReportSpec("channel_conversion", "rep.channel_conversion", _channel_conversion),
    ReportSpec("campaign_roi", "rep.campaign_roi", _campaign_roi),
    ReportSpec("bookings", "rep.bookings", _bookings),
    ReportSpec("no_shows", "rep.no_shows", _no_shows),
    ReportSpec("operators", "rep.operators", _operators),
    ReportSpec("ai_quality", "rep.ai_quality", _ai_quality),
    ReportSpec("calls", "rep.calls", _calls),
    ReportSpec("lost_reasons", "rep.lost_reasons", _lost_reasons),
    ReportSpec("followups", "rep.followups", _followups),
    ReportSpec("service_sales", "rep.service_sales", _service_sales),
]


def build(report_key: str, flt: PeriodFilter) -> list[ReportSection]:
    """Build the sections of one report."""
    for spec in REPORTS:
        if spec.key == report_key:
            return spec.builder(flt)
    raise KeyError(report_key)


def report_title(report_key: str) -> str:
    """Localized title of a report."""
    for spec in REPORTS:
        if spec.key == report_key:
            return tr(spec.title_key)
    return report_key
