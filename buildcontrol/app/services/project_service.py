"""Project CRUD plus the aggregated figures shown on the project overview.

Cost conventions used across the whole application:

``committed``
    Sum of expenses whose status is *approved* or *paid* — money the company
    has formally agreed to spend.
``actual``
    ``committed`` plus the valuation of materials issued from the warehouse to
    the project that are not already covered by an expense document.
``remaining``
    ``planned_budget - actual`` (may be negative, which is surfaced in red).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import session_scope
from app.models.entities import (
    AuditLog,
    EstimateItem,
    EstimateSection,
    EstimateVersion,
    Expense,
    Project,
    PurchaseRequest,
    User,
    WarehouseTransaction,
    WorkStage,
)
from app.models.enums import (
    ACTUAL_EXPENSE_STATUSES,
    ExpenseStatus,
    ProjectStatus,
    PurchaseStatus,
    StageStatus,
    TxKind,
)
from app.repositories import Repositories
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.services.permissions import Perm, require


@dataclass
class ProjectTotals:
    """Aggregated money / progress figures for one project."""

    project_id: int
    planned_budget: float = 0.0
    estimate_total: float = 0.0
    committed: float = 0.0
    actual: float = 0.0
    material_issued: float = 0.0
    pending_expenses: float = 0.0
    delayed_stages: int = 0
    total_stages: int = 0
    done_stages: int = 0
    pending_purchases: int = 0
    avg_progress: float = 0.0
    over_budget_items: int = 0

    @property
    def remaining(self) -> float:
        return round(self.planned_budget - self.actual, 2)

    @property
    def usage_ratio(self) -> float:
        """Actual cost as a share of the planned budget (0..n)."""
        return (self.actual / self.planned_budget) if self.planned_budget else 0.0

    @property
    def is_over_budget(self) -> bool:
        return self.planned_budget > 0 and self.actual > self.planned_budget


@dataclass
class ProjectRow:
    """Row rendered in the projects table."""

    id: int
    code: str
    name: str
    client: str
    address: str
    project_type: str
    status: str
    start_date: date | None
    end_date: date | None
    manager: str
    planned_budget: float
    actual: float
    is_archived: bool
    notes: str = ""
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #


def _sum(session: Session, stmt) -> float:
    return float(session.scalar(stmt) or 0.0)


def compute_totals(session: Session, project_id: int) -> ProjectTotals:
    """Compute every headline figure for a project in a handful of queries."""
    project = session.get(Project, project_id)
    if project is None:
        raise LookupError(f"Project #{project_id} not found")

    totals = ProjectTotals(project_id=project_id, planned_budget=project.planned_budget or 0.0)

    totals.committed = _sum(
        session,
        select(func.sum(Expense.amount)).where(
            Expense.project_id == project_id,
            Expense.is_archived.is_(False),
            Expense.status.in_(ACTUAL_EXPENSE_STATUSES),
        ),
    )
    totals.pending_expenses = _sum(
        session,
        select(func.sum(Expense.amount)).where(
            Expense.project_id == project_id,
            Expense.is_archived.is_(False),
            Expense.status == ExpenseStatus.PENDING.value,
        ),
    )
    totals.material_issued = _sum(
        session,
        select(func.sum(WarehouseTransaction.quantity * WarehouseTransaction.unit_price)).where(
            WarehouseTransaction.project_id == project_id,
            WarehouseTransaction.kind == TxKind.OUT.value,
        ),
    )
    totals.actual = round(totals.committed + totals.material_issued, 2)

    version = Repositories(session).versions.current(project_id)
    if version is not None:
        totals.estimate_total = _sum(
            session,
            select(func.sum(EstimateItem.quantity * EstimateItem.plan_unit_price))
            .join(EstimateSection, EstimateItem.section_id == EstimateSection.id)
            .where(EstimateSection.version_id == version.id),
        )
        totals.over_budget_items = int(
            session.scalar(
                select(func.count())
                .select_from(EstimateItem)
                .join(EstimateSection, EstimateItem.section_id == EstimateSection.id)
                .where(
                    EstimateSection.version_id == version.id,
                    EstimateItem.actual_cost > EstimateItem.quantity * EstimateItem.plan_unit_price,
                    EstimateItem.actual_cost > 0,
                )
            )
            or 0
        )

    stages = list(
        session.scalars(select(WorkStage).where(WorkStage.project_id == project_id)).all()
    )
    totals.total_stages = len(stages)
    totals.delayed_stages = sum(1 for s in stages if s.status == StageStatus.DELAYED.value)
    totals.done_stages = sum(1 for s in stages if s.status == StageStatus.DONE.value)
    totals.avg_progress = (
        round(sum(s.progress_percent or 0.0 for s in stages) / len(stages), 1) if stages else 0.0
    )

    totals.pending_purchases = int(
        session.scalar(
            select(func.count())
            .select_from(PurchaseRequest)
            .where(
                PurchaseRequest.project_id == project_id,
                PurchaseRequest.is_archived.is_(False),
                PurchaseRequest.status == PurchaseStatus.SUBMITTED.value,
            )
        )
        or 0
    )
    return totals


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def list_projects(
    text: str = "",
    status: str = "",
    include_archived: bool = False,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[ProjectRow]:
    """Return project rows matching the given filters."""
    with session_scope() as session:
        repos = Repositories(session)
        rows: list[ProjectRow] = []
        for project in repos.projects.search(text, status, include_archived):
            if date_from and project.start_date and project.start_date < date_from:
                continue
            if date_to and project.start_date and project.start_date > date_to:
                continue
            totals = compute_totals(session, project.id)
            rows.append(
                ProjectRow(
                    id=project.id,
                    code=project.code,
                    name=project.name,
                    client=project.client or "",
                    address=project.address or "",
                    project_type=project.project_type,
                    status=project.status,
                    start_date=project.start_date,
                    end_date=project.end_date,
                    manager=project.manager.label if project.manager else "—",
                    planned_budget=project.planned_budget or 0.0,
                    actual=totals.actual,
                    is_archived=project.is_archived,
                    notes=project.notes or "",
                    extra={"totals": totals},
                )
            )
        return rows


def get_project(project_id: int) -> dict:
    """Return one project as a plain dictionary."""
    with session_scope() as session:
        project = Repositories(session).projects.get_or_raise(project_id)
        data = project.as_dict()
        data["manager_name"] = project.manager.label if project.manager else ""
        return data


def get_totals(project_id: int) -> ProjectTotals:
    """Return aggregated figures for the project overview tab."""
    with session_scope() as session:
        return compute_totals(session, project_id)


def save_project(data: dict, actor: CurrentUser, project_id: int | None = None) -> int:
    """Create or update a project. Returns the project id."""
    require(actor.role_code, Perm.PROJECT_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        db_actor = session.get(User, actor.id)
        if project_id:
            project = repos.projects.get_or_raise(project_id)
            before = project.as_dict()
            repos.projects.update(project, **data)
            audit_service.log(
                session,
                user=db_actor,
                action=audit_service.Action.UPDATE,
                entity_type="Project",
                entity_id=project.id,
                project_id=project.id,
                description=project.name,
                old_value=f"budget={before.get('planned_budget')}, status={before.get('status')}",
                new_value=f"budget={project.planned_budget}, status={project.status}",
            )
        else:
            data.setdefault("code", repos.projects.next_code())
            project = repos.projects.create(**data)
            repos.versions.create(
                project_id=project.id,
                version_no=1,
                is_current=True,
                created_by_id=actor.id,
            )
            audit_service.log(
                session,
                user=db_actor,
                action=audit_service.Action.CREATE,
                entity_type="Project",
                entity_id=project.id,
                project_id=project.id,
                description=project.name,
            )
        return project.id


def archive_project(project_id: int, actor: CurrentUser, archived: bool = True) -> None:
    """Soft-delete or restore a project."""
    require(actor.role_code, Perm.PROJECT_ARCHIVE)
    with session_scope() as session:
        repos = Repositories(session)
        project = repos.projects.get_or_raise(project_id)
        repos.projects.archive(project, archived)
        project.status = ProjectStatus.ARCHIVED.value if archived else ProjectStatus.ACTIVE.value
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.ARCHIVE,
            entity_type="Project",
            entity_id=project_id,
            project_id=project_id,
            description=project.name,
            new_value=str(archived),
        )


def project_activity(project_id: int, limit: int = 200) -> list[dict]:
    """Return the audit trail rows belonging to a project."""
    with session_scope() as session:
        rows = []
        for entry in Repositories(session).audit.recent(limit=limit, project_id=project_id):
            rows.append(
                {
                    "id": entry.id,
                    "ts": entry.ts,
                    "username": entry.username,
                    "action": entry.action,
                    "entity_type": entry.entity_type,
                    "entity_id": entry.entity_id,
                    "description": entry.description,
                    "old_value": entry.old_value,
                    "new_value": entry.new_value,
                }
            )
        return rows


def global_activity(limit: int = 500, action: str = "", text: str = "") -> list[dict]:
    """Return audit entries across all projects, optionally filtered."""
    with session_scope() as session:
        stmt = select(AuditLog).order_by(AuditLog.ts.desc()).limit(limit)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if text:
            pattern = f"%{text}%"
            stmt = stmt.where(AuditLog.description.ilike(pattern))
        return [
            {
                "id": e.id,
                "ts": e.ts,
                "username": e.username,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "description": e.description,
                "old_value": e.old_value,
                "new_value": e.new_value,
            }
            for e in session.scalars(stmt).all()
        ]


def portfolio_summary() -> dict:
    """Return counts and totals across every non-archived project."""
    with session_scope() as session:
        projects = Repositories(session).projects.list()
        budget = sum(p.planned_budget or 0.0 for p in projects)
        actual = 0.0
        over = 0
        for project in projects:
            totals = compute_totals(session, project.id)
            actual += totals.actual
            if totals.is_over_budget:
                over += 1
        return {
            "count": len(projects),
            "active": sum(1 for p in projects if p.status == ProjectStatus.ACTIVE.value),
            "budget": budget,
            "actual": round(actual, 2),
            "over_budget": over,
        }


def project_choices(include_all: bool = True) -> list[tuple[int | str, str]]:
    """Return ``[(id, name)]`` pairs for project pickers."""
    with session_scope() as session:
        rows = [(p.id, f"{p.code} — {p.name}") for p in Repositories(session).projects.list()]
    if include_all:
        rows.insert(0, ("", "—"))
    return rows


def user_choices(include_empty: bool = True) -> list[tuple[int | str, str]]:
    """Return ``[(id, name)]`` pairs for responsible-person pickers."""
    with session_scope() as session:
        rows = [(u.id, u.label) for u in Repositories(session).users.active()]
    if include_empty:
        rows.insert(0, ("", "—"))
    return rows


def estimate_versions_exist(project_id: int) -> bool:
    """True when the project already has an estimate version."""
    with session_scope() as session:
        return Repositories(session).versions.current(project_id) is not None


def ensure_current_version(
    session: Session, project_id: int, user_id: int | None
) -> EstimateVersion:
    """Return the project's current estimate version, creating it when absent."""
    repos = Repositories(session)
    version = repos.versions.current(project_id)
    if version is None:
        version = repos.versions.create(
            project_id=project_id, version_no=1, is_current=True, created_by_id=user_id
        )
    return version
