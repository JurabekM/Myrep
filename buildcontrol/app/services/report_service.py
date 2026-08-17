"""Report datasets.

Every report is materialised as a :class:`ReportData` table which the PDF and
Excel renderers consume without knowing anything about the domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.models.enums import CounterpartyKind, ExpenseStatus, PurchaseStatus
from app.services import (
    counterparty_service,
    estimate_service,
    expense_service,
    project_service,
    purchase_service,
    stage_service,
    warehouse_service,
)
from app.utils.formatting import fmt_date
from app.utils.i18n import tr
from app.utils.labels import (
    expense_category_label,
    expense_status_label,
    method_label,
    purchase_status_label,
    stage_status_label,
    tx_kind_label,
    unit_label,
)

#: Column kinds understood by the renderers.
TEXT, MONEY, NUMBER, PERCENT, DATE = "text", "money", "number", "percent", "date"


@dataclass
class Column:
    """A report column definition."""

    key: str
    title: str
    kind: str = TEXT
    width: float = 1.0


@dataclass
class ReportData:
    """A rendered-ready tabular report."""

    key: str
    title: str
    subtitle: str = ""
    columns: list[Column] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    totals: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


#: ``(key, i18n title, needs_project)`` for every available report.
REPORT_TYPES: list[tuple[str, str, bool]] = [
    ("estimate", "rep_estimate", True),
    ("plan_fact", "rep_plan_fact", True),
    ("overrun", "rep_overrun", False),
    ("purchases", "rep_purchases", False),
    ("quotes", "rep_quotes", False),
    ("stock", "rep_stock", False),
    ("movements", "rep_movements", False),
    ("stages", "rep_stages", True),
    ("delays", "rep_delays", False),
    ("contractors", "rep_contractors", False),
    ("payments", "rep_payments", True),
]


@dataclass
class ReportFilters:
    """Filter payload coming from the reports page."""

    project_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    status: str = ""
    category: str = ""


def _period(filters: ReportFilters) -> str:
    if filters.date_from or filters.date_to:
        return f"{fmt_date(filters.date_from)} — {fmt_date(filters.date_to)}"
    return ""


def _project_name(project_id: int | None) -> str:
    if not project_id:
        return ""
    return project_service.get_project(project_id).get("name", "")


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _estimate_report(f: ReportFilters) -> ReportData:
    tree = estimate_service.load_tree(int(f.project_id))
    rows: list[dict] = []

    def walk(node, level: int) -> None:
        rows.append(
            {
                "code": node.code,
                "name": ("    " * level) + node.name,
                "unit": "",
                "quantity": "",
                "plan_unit_price": "",
                "plan_total": node.plan_total,
                "actual_total": node.actual_total,
                "variance": node.variance,
                "_group": True,
            }
        )
        for item in node.items:
            rows.append(
                {
                    "code": item.code,
                    "name": ("    " * (level + 1)) + item.name,
                    "unit": unit_label(item.unit),
                    "quantity": item.quantity,
                    "plan_unit_price": item.plan_unit_price,
                    "plan_total": item.plan_total,
                    "actual_total": item.actual_total,
                    "variance": item.variance,
                    "_group": False,
                }
            )
        for child in node.children:
            walk(child, level + 1)

    for root in tree.roots:
        walk(root, 0)

    return ReportData(
        key="estimate",
        title=tr("rep_estimate"),
        subtitle=f"{_project_name(f.project_id)} · v{tree.version_no}",
        columns=[
            Column("code", tr("code"), TEXT, 0.6),
            Column("name", tr("name"), TEXT, 3.0),
            Column("unit", tr("unit"), TEXT, 0.7),
            Column("quantity", tr("quantity"), NUMBER, 0.8),
            Column("plan_unit_price", tr("plan_unit_price"), MONEY, 1.2),
            Column("plan_total", tr("plan_total"), MONEY, 1.3),
            Column("actual_total", tr("actual_total"), MONEY, 1.3),
            Column("variance", tr("variance"), MONEY, 1.2),
        ],
        rows=rows,
        totals={
            "plan_total": tree.plan_total,
            "actual_total": tree.actual_total,
            "variance": tree.variance,
        },
    )


def _plan_fact_report(f: ReportFilters) -> ReportData:
    tree = estimate_service.load_tree(int(f.project_id))
    rows = [
        {
            "code": item.code,
            "name": item.name,
            "unit": unit_label(item.unit),
            "quantity": item.quantity,
            "plan_total": item.plan_total,
            "actual_total": item.actual_total,
            "variance": item.variance,
            "variance_percent": item.variance_percent,
            "progress_percent": item.progress_percent,
        }
        for item in tree.all_items()
    ]
    return ReportData(
        key="plan_fact",
        title=tr("rep_plan_fact"),
        subtitle=_project_name(f.project_id),
        columns=[
            Column("code", tr("code"), TEXT, 0.6),
            Column("name", tr("name"), TEXT, 2.6),
            Column("unit", tr("unit"), TEXT, 0.7),
            Column("quantity", tr("quantity"), NUMBER, 0.8),
            Column("plan_total", tr("plan_total"), MONEY, 1.3),
            Column("actual_total", tr("actual_total"), MONEY, 1.3),
            Column("variance", tr("variance"), MONEY, 1.2),
            Column("variance_percent", tr("variance_percent"), PERCENT, 0.9),
            Column("progress_percent", tr("percent_done"), PERCENT, 0.9),
        ],
        rows=rows,
        totals={
            "plan_total": sum(r["plan_total"] for r in rows),
            "actual_total": sum(r["actual_total"] for r in rows),
            "variance": sum(r["variance"] for r in rows),
        },
    )


def _overrun_report(f: ReportFilters) -> ReportData:
    rows = []
    projects = (
        [p for p in project_service.list_projects() if p.id == f.project_id]
        if f.project_id
        else project_service.list_projects()
    )
    for project in projects:
        totals = project.extra["totals"]
        rows.append(
            {
                "project": project.name,
                "budget": totals.planned_budget,
                "estimate_total": totals.estimate_total,
                "committed": totals.committed,
                "actual": totals.actual,
                "remaining": totals.remaining,
                "usage": round(totals.usage_ratio * 100, 1),
                "over_items": totals.over_budget_items,
            }
        )
    rows.sort(key=lambda r: r["usage"], reverse=True)
    return ReportData(
        key="overrun",
        title=tr("rep_overrun"),
        columns=[
            Column("project", tr("project"), TEXT, 2.4),
            Column("budget", tr("budget"), MONEY, 1.3),
            Column("estimate_total", tr("estimate_total"), MONEY, 1.3),
            Column("committed", tr("committed_cost"), MONEY, 1.3),
            Column("actual", tr("actual_cost"), MONEY, 1.3),
            Column("remaining", tr("remaining_funds"), MONEY, 1.3),
            Column("usage", tr("budget_usage"), PERCENT, 0.9),
            Column("over_items", tr("over_budget"), NUMBER, 0.8),
        ],
        rows=rows,
        totals={
            "budget": sum(r["budget"] for r in rows),
            "actual": sum(r["actual"] for r in rows),
            "remaining": sum(r["remaining"] for r in rows),
        },
    )


def _purchases_report(f: ReportFilters) -> ReportData:
    rows = []
    for req in purchase_service.list_requests(project_id=f.project_id, status=f.status):
        if f.date_from and req["needed_date"] and req["needed_date"] < f.date_from:
            continue
        if f.date_to and req["needed_date"] and req["needed_date"] > f.date_to:
            continue
        rows.append(
            {
                "number": req["number"],
                "project": req["project"],
                "title": req["title"],
                "quantity": req["quantity"],
                "unit": unit_label(req["unit"]),
                "est_total": req["est_total"],
                "selected_supplier": req["selected_supplier"],
                "selected_total": req["selected_total"],
                "needed_date": req["needed_date"],
                "status": purchase_status_label(req["status"]),
            }
        )
    return ReportData(
        key="purchases",
        title=tr("rep_purchases"),
        subtitle=_period(f),
        columns=[
            Column("number", "№", TEXT, 0.8),
            Column("project", tr("project"), TEXT, 1.6),
            Column("title", tr("product_service"), TEXT, 2.0),
            Column("quantity", tr("quantity"), NUMBER, 0.7),
            Column("unit", tr("unit"), TEXT, 0.7),
            Column("est_total", tr("est_price"), MONEY, 1.2),
            Column("selected_supplier", tr("supplier"), TEXT, 1.4),
            Column("selected_total", tr("total_value"), MONEY, 1.2),
            Column("needed_date", tr("needed_date"), DATE, 0.9),
            Column("status", tr("status"), TEXT, 1.1),
        ],
        rows=rows,
        totals={
            "est_total": sum(r["est_total"] for r in rows),
            "selected_total": sum(r["selected_total"] for r in rows),
        },
    )


def _quotes_report(f: ReportFilters) -> ReportData:
    rows = []
    for req in purchase_service.list_requests(project_id=f.project_id):
        for quote in purchase_service.list_quotes(req["id"]):
            rows.append(
                {
                    "number": req["number"],
                    "title": req["title"],
                    "supplier": quote.supplier_name,
                    "unit_price": quote.unit_price,
                    "delivery_cost": quote.delivery_cost,
                    "total_value": quote.total_value,
                    "delivery_days": quote.delivery_days,
                    "payment_terms": quote.payment_terms,
                    "mark": (
                        tr("best_offer")
                        if quote.is_best
                        else (tr("best_price") if quote.is_cheapest else "")
                    ),
                }
            )
    return ReportData(
        key="quotes",
        title=tr("rep_quotes"),
        columns=[
            Column("number", "№", TEXT, 0.8),
            Column("title", tr("product_service"), TEXT, 2.0),
            Column("supplier", tr("supplier"), TEXT, 1.6),
            Column("unit_price", tr("unit_price"), MONEY, 1.2),
            Column("delivery_cost", tr("delivery_cost"), MONEY, 1.1),
            Column("total_value", tr("total_value"), MONEY, 1.3),
            Column("delivery_days", tr("delivery_days"), NUMBER, 0.8),
            Column("payment_terms", tr("payment_terms"), TEXT, 1.3),
            Column("mark", "", TEXT, 1.0),
        ],
        rows=rows,
    )


def _stock_report(f: ReportFilters) -> ReportData:
    rows = [
        {
            "sku": row.sku,
            "name": row.name,
            "category": row.category,
            "unit": unit_label(row.unit),
            "balance": row.balance,
            "min_stock": row.min_stock,
            "standard_price": row.standard_price,
            "value": row.value,
            "flag": tr("low_stock_warning") if row.is_low else "",
        }
        for row in warehouse_service.list_materials(category=f.category)
    ]
    return ReportData(
        key="stock",
        title=tr("rep_stock"),
        columns=[
            Column("sku", tr("sku"), TEXT, 1.0),
            Column("name", tr("name"), TEXT, 2.4),
            Column("category", tr("category"), TEXT, 1.2),
            Column("unit", tr("unit"), TEXT, 0.7),
            Column("balance", tr("stock"), NUMBER, 0.9),
            Column("min_stock", tr("min_stock"), NUMBER, 0.9),
            Column("standard_price", tr("standard_price"), MONEY, 1.2),
            Column("value", tr("stock_value"), MONEY, 1.2),
            Column("flag", "", TEXT, 1.2),
        ],
        rows=rows,
        totals={"value": sum(r["value"] for r in rows)},
    )


def _movements_report(f: ReportFilters) -> ReportData:
    rows = [
        {
            "tx_date": tx["tx_date"],
            "kind": tx_kind_label(tx["kind"]),
            "sku": tx["sku"],
            "material": tx["material"],
            "quantity": tx["signed_quantity"],
            "unit_price": tx["unit_price"],
            "total": tx["total"],
            "project": tx["project"],
            "user": tx["user"],
        }
        for tx in warehouse_service.list_transactions(
            project_id=f.project_id, date_from=f.date_from, date_to=f.date_to
        )
    ]
    return ReportData(
        key="movements",
        title=tr("rep_movements"),
        subtitle=_period(f),
        columns=[
            Column("tx_date", tr("date"), DATE, 0.9),
            Column("kind", tr("type"), TEXT, 1.1),
            Column("sku", tr("sku"), TEXT, 1.0),
            Column("material", tr("material"), TEXT, 2.0),
            Column("quantity", tr("quantity"), NUMBER, 0.9),
            Column("unit_price", tr("unit_price"), MONEY, 1.1),
            Column("total", tr("total"), MONEY, 1.2),
            Column("project", tr("project"), TEXT, 1.6),
            Column("user", tr("user"), TEXT, 1.1),
        ],
        rows=rows,
        totals={"total": sum(r["total"] for r in rows)},
    )


def _stages_report(f: ReportFilters) -> ReportData:
    rows = [
        {
            "name": row["name"],
            "plan_start": row["plan_start"],
            "plan_end": row["plan_end"],
            "actual_start": row["actual_start"],
            "actual_end": row["actual_end"],
            "progress_percent": row["progress_percent"],
            "responsible": row["responsible"],
            "status": stage_status_label(row["status"]),
        }
        for row in stage_service.list_stages(int(f.project_id), status=f.status)
    ]
    return ReportData(
        key="stages",
        title=tr("rep_stages"),
        subtitle=_project_name(f.project_id),
        columns=[
            Column("name", tr("stage"), TEXT, 2.4),
            Column("plan_start", tr("plan_start"), DATE, 0.9),
            Column("plan_end", tr("plan_end"), DATE, 0.9),
            Column("actual_start", tr("actual_start"), DATE, 0.9),
            Column("actual_end", tr("actual_end"), DATE, 0.9),
            Column("progress_percent", tr("percent_done"), PERCENT, 0.9),
            Column("responsible", tr("responsible"), TEXT, 1.3),
            Column("status", tr("status"), TEXT, 1.2),
        ],
        rows=rows,
    )


def _delays_report(f: ReportFilters) -> ReportData:
    rows = stage_service.delayed_stages(f.project_id)
    return ReportData(
        key="delays",
        title=tr("rep_delays"),
        columns=[
            Column("project", tr("project"), TEXT, 1.8),
            Column("name", tr("stage"), TEXT, 2.2),
            Column("plan_end", tr("plan_end"), DATE, 1.0),
            Column("overdue_days", tr("delay_days"), NUMBER, 0.9),
            Column("progress_percent", tr("percent_done"), PERCENT, 0.9),
            Column("responsible", tr("responsible"), TEXT, 1.3),
        ],
        rows=rows,
    )


def _contractors_report(_f: ReportFilters) -> ReportData:
    rows = counterparty_service.contractor_performance()
    return ReportData(
        key="contractors",
        title=tr("rep_contractors"),
        columns=[
            Column("name", tr("name"), TEXT, 2.2),
            Column("category", tr("category"), TEXT, 1.4),
            Column("contract_amount", tr("contract_amount"), MONEY, 1.3),
            Column("paid_amount", tr("paid_amount"), MONEY, 1.3),
            Column("paid_ratio", tr("percent_done"), PERCENT, 0.9),
            Column("delay_days", tr("delay_days"), NUMBER, 0.9),
            Column("quality_score", tr("quality_score"), NUMBER, 0.9),
            Column("disputes", tr("disputes"), NUMBER, 0.8),
            Column("rating", tr("rating"), NUMBER, 0.8),
        ],
        rows=rows,
        totals={
            "contract_amount": sum(r["contract_amount"] for r in rows),
            "paid_amount": sum(r["paid_amount"] for r in rows),
        },
    )


def _payments_report(f: ReportFilters) -> ReportData:
    expenses = expense_service.list_expenses(
        project_id=f.project_id,
        status=f.status,
        category=f.category,
        date_from=f.date_from,
        date_to=f.date_to,
    )
    rows = [
        {
            "pay_date": e["pay_date"],
            "category": expense_category_label(e["category"]),
            "counterparty": e["counterparty"],
            "estimate_item": e["estimate_item"],
            "amount": e["amount"],
            "paid": e["paid"],
            "method": method_label(e["method"]),
            "invoice_no": e["invoice_no"],
            "status": expense_status_label(e["status"]),
        }
        for e in expenses
    ]
    return ReportData(
        key="payments",
        title=tr("rep_payments"),
        subtitle=f"{_project_name(f.project_id)} {_period(f)}".strip(),
        columns=[
            Column("pay_date", tr("pay_date"), DATE, 0.9),
            Column("category", tr("category"), TEXT, 1.2),
            Column("counterparty", tr("counterparty"), TEXT, 1.8),
            Column("estimate_item", tr("estimate_item"), TEXT, 1.8),
            Column("amount", tr("amount"), MONEY, 1.3),
            Column("paid", tr("paid_amount"), MONEY, 1.3),
            Column("method", tr("method"), TEXT, 1.1),
            Column("invoice_no", tr("invoice_no"), TEXT, 1.0),
            Column("status", tr("status"), TEXT, 1.1),
        ],
        rows=rows,
        totals={
            "amount": sum(r["amount"] for r in rows),
            "paid": sum(r["paid"] for r in rows),
        },
        notes=[
            f"{tr('enum.expense_status.pending')}: "
            f"{sum(1 for e in expenses if e['status'] == ExpenseStatus.PENDING.value)}"
        ],
    )


_BUILDERS = {
    "estimate": _estimate_report,
    "plan_fact": _plan_fact_report,
    "overrun": _overrun_report,
    "purchases": _purchases_report,
    "quotes": _quotes_report,
    "stock": _stock_report,
    "movements": _movements_report,
    "stages": _stages_report,
    "delays": _delays_report,
    "contractors": _contractors_report,
    "payments": _payments_report,
}


def build(report_key: str, filters: ReportFilters) -> ReportData:
    """Build the dataset of ``report_key`` using ``filters``."""
    builder = _BUILDERS.get(report_key)
    if builder is None:
        raise KeyError(report_key)
    return builder(filters)


def status_options(report_key: str) -> list[tuple[str, str]]:
    """Return the status filter options relevant for a report."""
    if report_key in ("purchases", "quotes"):
        return [("", tr("all"))] + [
            (s.value, purchase_status_label(s.value)) for s in PurchaseStatus
        ]
    if report_key in ("payments",):
        return [("", tr("all"))] + [(s.value, expense_status_label(s.value)) for s in ExpenseStatus]
    if report_key in ("stages",):
        from app.models.enums import StageStatus

        return [("", tr("all"))] + [(s.value, stage_status_label(s.value)) for s in StageStatus]
    if report_key == "contractors":
        return [(CounterpartyKind.CONTRACTOR.value, tr("contractors"))]
    return [("", tr("all"))]
