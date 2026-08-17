"""Estimate tree, versioning and plan/actual recalculation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import session_scope
from app.models.entities import (
    EstimateItem,
    EstimateSection,
    EstimateVersion,
    Expense,
    User,
    WarehouseTransaction,
)
from app.models.enums import (
    ACTUAL_EXPENSE_STATUSES,
    EstimateItemStatus,
    EstimateStatus,
    TxKind,
)
from app.repositories import Repositories
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.services.permissions import Perm, PermissionDenied, require

#: Statuses in which the estimate tree may be edited.
EDITABLE_STATUSES = (EstimateStatus.DRAFT.value, EstimateStatus.REVISION.value)


class EstimateLocked(Exception):
    """Raised when an approved / submitted estimate is edited."""


@dataclass
class ItemRow:
    """Flat representation of one estimate line for the tree view."""

    id: int
    section_id: int
    code: str
    name: str
    category: str
    unit: str
    quantity: float
    plan_unit_price: float
    plan_total: float
    actual_unit_price: float
    actual_total: float
    variance: float
    variance_percent: float
    progress_percent: float
    responsible: str
    status: str
    note: str
    order_index: int


@dataclass
class SectionNode:
    """A node of the estimate tree."""

    id: int
    parent_id: int | None
    code: str
    name: str
    order_index: int
    children: list[SectionNode] = field(default_factory=list)
    items: list[ItemRow] = field(default_factory=list)

    @property
    def plan_total(self) -> float:
        return round(
            sum(i.plan_total for i in self.items) + sum(c.plan_total for c in self.children), 2
        )

    @property
    def actual_total(self) -> float:
        return round(
            sum(i.actual_total for i in self.items) + sum(c.actual_total for c in self.children), 2
        )

    @property
    def variance(self) -> float:
        return round(self.actual_total - self.plan_total, 2)


@dataclass
class EstimateTree:
    """The whole estimate of one version."""

    version_id: int
    version_no: int
    status: str
    is_current: bool
    created_at: datetime | None
    approved_by: str
    note: str
    roots: list[SectionNode] = field(default_factory=list)

    @property
    def plan_total(self) -> float:
        return round(sum(r.plan_total for r in self.roots), 2)

    @property
    def actual_total(self) -> float:
        return round(sum(r.actual_total for r in self.roots), 2)

    @property
    def variance(self) -> float:
        return round(self.actual_total - self.plan_total, 2)

    @property
    def editable(self) -> bool:
        return self.status in EDITABLE_STATUSES

    def all_items(self) -> list[ItemRow]:
        """Depth-first list of every item in the tree."""
        result: list[ItemRow] = []

        def walk(node: SectionNode) -> None:
            result.extend(node.items)
            for child in node.children:
                walk(child)

        for root in self.roots:
            walk(root)
        return result


# --------------------------------------------------------------------------- #
# Recalculation
# --------------------------------------------------------------------------- #


def recalc_item_actuals(session: Session, project_id: int) -> None:
    """Refresh ``EstimateItem.actual_cost`` from expenses and material issues.

    Actual cost of a line = approved/paid expenses booked on it
    + value of warehouse issues booked on it.
    """
    repos = Repositories(session)
    version = repos.versions.current(project_id)
    if version is None:
        return
    items = repos.items.for_version(version.id)
    if not items:
        return
    ids = [i.id for i in items]

    expense_rows = session.execute(
        select(Expense.estimate_item_id, func.sum(Expense.amount))
        .where(
            Expense.estimate_item_id.in_(ids),
            Expense.is_archived.is_(False),
            Expense.status.in_(ACTUAL_EXPENSE_STATUSES),
        )
        .group_by(Expense.estimate_item_id)
    ).all()
    stock_rows = session.execute(
        select(
            WarehouseTransaction.estimate_item_id,
            func.sum(WarehouseTransaction.quantity * WarehouseTransaction.unit_price),
        )
        .where(
            WarehouseTransaction.estimate_item_id.in_(ids),
            WarehouseTransaction.kind == TxKind.OUT.value,
        )
        .group_by(WarehouseTransaction.estimate_item_id)
    ).all()

    totals: dict[int, float] = {}
    for item_id, value in list(expense_rows) + list(stock_rows):
        if item_id is None:
            continue
        totals[item_id] = totals.get(item_id, 0.0) + float(value or 0.0)

    for item in items:
        item.actual_cost = round(totals.get(item.id, 0.0), 2)
    session.flush()


def recalculate(project_id: int) -> None:
    """Public wrapper around :func:`recalc_item_actuals` with its own transaction."""
    with session_scope() as session:
        recalc_item_actuals(session, project_id)


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #


def _item_row(item: EstimateItem) -> ItemRow:
    return ItemRow(
        id=item.id,
        section_id=item.section_id,
        code=item.code or "",
        name=item.name,
        category=item.category or "",
        unit=item.unit,
        quantity=item.quantity or 0.0,
        plan_unit_price=item.plan_unit_price or 0.0,
        plan_total=item.plan_total,
        actual_unit_price=item.actual_unit_price,
        actual_total=item.actual_cost or 0.0,
        variance=item.variance,
        variance_percent=item.variance_percent,
        progress_percent=item.progress_percent or 0.0,
        responsible=item.responsible.label if item.responsible else "",
        status=item.status or EstimateItemStatus.PLANNED.value,
        note=item.note or "",
        order_index=item.order_index or 0,
    )


def _build_tree(session: Session, version: EstimateVersion) -> EstimateTree:
    repos = Repositories(session)
    sections = repos.sections.for_version(version.id)
    items = repos.items.for_version(version.id)

    nodes: dict[int, SectionNode] = {
        s.id: SectionNode(
            id=s.id,
            parent_id=s.parent_id,
            code=s.code or "",
            name=s.name,
            order_index=s.order_index or 0,
        )
        for s in sections
    }
    for item in items:
        node = nodes.get(item.section_id)
        if node is not None:
            node.items.append(_item_row(item))
    roots: list[SectionNode] = []
    for section in sections:
        node = nodes[section.id]
        if section.parent_id and section.parent_id in nodes:
            nodes[section.parent_id].children.append(node)
        else:
            roots.append(node)

    def sort(node: SectionNode) -> None:
        node.children.sort(key=lambda n: (n.order_index, n.id))
        node.items.sort(key=lambda i: (i.order_index, i.id))
        for child in node.children:
            sort(child)

    roots.sort(key=lambda n: (n.order_index, n.id))
    for root in roots:
        sort(root)

    return EstimateTree(
        version_id=version.id,
        version_no=version.version_no,
        status=version.status,
        is_current=version.is_current,
        created_at=version.created_at,
        approved_by=version.approved_by.label if version.approved_by else "",
        note=version.note or "",
        roots=roots,
    )


def load_tree(project_id: int, version_id: int | None = None) -> EstimateTree:
    """Load the estimate tree of a project (current version by default)."""
    with session_scope() as session:
        repos = Repositories(session)
        version = (
            repos.versions.get_or_raise(version_id)
            if version_id
            else repos.versions.current(project_id)
        )
        if version is None:
            version = repos.versions.create(project_id=project_id, version_no=1, is_current=True)
        recalc_item_actuals(session, project_id)
        return _build_tree(session, version)


def list_versions(project_id: int) -> list[dict]:
    """Return the version history of a project."""
    with session_scope() as session:
        rows = []
        for version in Repositories(session).versions.for_project(project_id):
            plan = float(
                session.scalar(
                    select(func.sum(EstimateItem.quantity * EstimateItem.plan_unit_price))
                    .join(EstimateSection, EstimateItem.section_id == EstimateSection.id)
                    .where(EstimateSection.version_id == version.id)
                )
                or 0.0
            )
            rows.append(
                {
                    "id": version.id,
                    "version_no": version.version_no,
                    "status": version.status,
                    "is_current": version.is_current,
                    "created_at": version.created_at,
                    "created_by": version.created_by.label if version.created_by else "",
                    "approved_by": version.approved_by.label if version.approved_by else "",
                    "approved_at": version.approved_at,
                    "note": version.note or "",
                    "plan_total": round(plan, 2),
                }
            )
        return rows


def item_choices(project_id: int) -> list[tuple[int | str, str]]:
    """Return ``[(item_id, label)]`` for estimate-item pickers."""
    with session_scope() as session:
        repos = Repositories(session)
        version = repos.versions.current(project_id)
        if version is None:
            return [("", "—")]
        rows: list[tuple[int | str, str]] = [("", "—")]
        for item in repos.items.for_version(version.id):
            prefix = f"{item.code} " if item.code else ""
            rows.append((item.id, f"{prefix}{item.name}"))
        return rows


def section_choices(project_id: int) -> list[tuple[int | str, str]]:
    """Return ``[(section_id, label)]`` for section pickers."""
    with session_scope() as session:
        repos = Repositories(session)
        version = repos.versions.current(project_id)
        if version is None:
            return [("", "—")]
        rows: list[tuple[int | str, str]] = [("", "—")]
        for section in repos.sections.for_version(version.id):
            prefix = f"{section.code} " if section.code else ""
            rows.append((section.id, f"{prefix}{section.name}"))
        return rows


# --------------------------------------------------------------------------- #
# Editing
# --------------------------------------------------------------------------- #


def _assert_editable(session: Session, version_id: int) -> EstimateVersion:
    version = Repositories(session).versions.get_or_raise(version_id)
    if version.status not in EDITABLE_STATUSES:
        raise EstimateLocked(version.status)
    return version


def add_section(
    version_id: int,
    name: str,
    actor: CurrentUser,
    parent_id: int | None = None,
    code: str = "",
) -> int:
    """Create a section (or sub-section) inside a version."""
    require(actor.role_code, Perm.ESTIMATE_EDIT)
    with session_scope() as session:
        version = _assert_editable(session, version_id)
        repos = Repositories(session)
        siblings = repos.sections.list(
            filters=[
                EstimateSection.version_id == version_id,
                (
                    EstimateSection.parent_id.is_(None)
                    if parent_id is None
                    else EstimateSection.parent_id == parent_id
                ),
            ]
        )
        order = len(siblings)
        section = repos.sections.create(
            version_id=version_id,
            parent_id=parent_id,
            name=name.strip(),
            code=code.strip() or _auto_code(session, version_id, parent_id, order),
            order_index=order,
        )
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.CREATE,
            entity_type="EstimateSection",
            entity_id=section.id,
            project_id=version.project_id,
            description=section.name,
        )
        return section.id


def _auto_code(session: Session, version_id: int, parent_id: int | None, order: int) -> str:
    """Generate a hierarchical code such as ``2.3``."""
    if parent_id is None:
        return str(order + 1)
    parent = session.get(EstimateSection, parent_id)
    base = parent.code if parent and parent.code else "1"
    return f"{base}.{order + 1}"


def update_section(section_id: int, name: str, code: str, actor: CurrentUser) -> None:
    """Rename a section."""
    require(actor.role_code, Perm.ESTIMATE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        section = repos.sections.get_or_raise(section_id)
        _assert_editable(session, section.version_id)
        section.name = name.strip()
        section.code = code.strip()
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.UPDATE,
            entity_type="EstimateSection",
            entity_id=section_id,
            description=section.name,
        )


def delete_section(section_id: int, actor: CurrentUser) -> None:
    """Delete a section together with its children and items."""
    require(actor.role_code, Perm.ESTIMATE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        section = repos.sections.get_or_raise(section_id)
        version = _assert_editable(session, section.version_id)
        name = section.name
        repos.sections.delete(section)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.DELETE,
            entity_type="EstimateSection",
            entity_id=section_id,
            project_id=version.project_id,
            description=name,
        )


def save_item(data: dict, actor: CurrentUser, item_id: int | None = None) -> int:
    """Create or update an estimate item."""
    require(actor.role_code, Perm.ESTIMATE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        if item_id:
            item = repos.items.get_or_raise(item_id)
            section = repos.sections.get_or_raise(item.section_id)
            version = _assert_editable(session, section.version_id)
            before = f"qty={item.quantity}, price={item.plan_unit_price}"
            repos.items.update(item, **data)
            audit_service.log(
                session,
                user=session.get(User, actor.id),
                action=audit_service.Action.UPDATE,
                entity_type="EstimateItem",
                entity_id=item.id,
                project_id=version.project_id,
                description=item.name,
                old_value=before,
                new_value=f"qty={item.quantity}, price={item.plan_unit_price}",
            )
        else:
            section = repos.sections.get_or_raise(int(data["section_id"]))
            version = _assert_editable(session, section.version_id)
            data.setdefault(
                "order_index",
                repos.items.count(filters=[EstimateItem.section_id == section.id]),
            )
            item = repos.items.create(**data)
            audit_service.log(
                session,
                user=session.get(User, actor.id),
                action=audit_service.Action.CREATE,
                entity_type="EstimateItem",
                entity_id=item.id,
                project_id=version.project_id,
                description=item.name,
            )
        return item.id


def delete_item(item_id: int, actor: CurrentUser) -> None:
    """Delete an estimate item."""
    require(actor.role_code, Perm.ESTIMATE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        item = repos.items.get_or_raise(item_id)
        section = repos.sections.get_or_raise(item.section_id)
        version = _assert_editable(session, section.version_id)
        name = item.name
        repos.items.delete(item)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.DELETE,
            entity_type="EstimateItem",
            entity_id=item_id,
            project_id=version.project_id,
            description=name,
        )


def move_item(item_id: int, target_section_id: int, position: int, actor: CurrentUser) -> None:
    """Move an item to ``target_section_id`` at ``position`` (drag & drop)."""
    require(actor.role_code, Perm.ESTIMATE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        item = repos.items.get_or_raise(item_id)
        section = repos.sections.get_or_raise(item.section_id)
        _assert_editable(session, section.version_id)
        item.section_id = target_section_id
        siblings = [
            i
            for i in repos.items.list(
                filters=[EstimateItem.section_id == target_section_id],
                order_by=EstimateItem.order_index,
            )
            if i.id != item_id
        ]
        position = max(0, min(position, len(siblings)))
        siblings.insert(position, item)
        for index, sibling in enumerate(siblings):
            sibling.order_index = index
        session.flush()


def move_section(section_id: int, direction: int, actor: CurrentUser) -> None:
    """Move a section up (-1) or down (+1) among its siblings."""
    require(actor.role_code, Perm.ESTIMATE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        section = repos.sections.get_or_raise(section_id)
        _assert_editable(session, section.version_id)
        siblings = repos.sections.list(
            filters=[
                EstimateSection.version_id == section.version_id,
                (
                    EstimateSection.parent_id.is_(None)
                    if section.parent_id is None
                    else EstimateSection.parent_id == section.parent_id
                ),
            ],
            order_by=EstimateSection.order_index,
        )
        index = next((i for i, s in enumerate(siblings) if s.id == section_id), None)
        if index is None:
            return
        new_index = max(0, min(index + direction, len(siblings) - 1))
        siblings.insert(new_index, siblings.pop(index))
        for position, sibling in enumerate(siblings):
            sibling.order_index = position
        session.flush()


# --------------------------------------------------------------------------- #
# Workflow
# --------------------------------------------------------------------------- #


def set_status(version_id: int, status: str, actor: CurrentUser, note: str = "") -> None:
    """Move an estimate version through its approval workflow."""
    if status == EstimateStatus.APPROVED.value:
        require(actor.role_code, Perm.ESTIMATE_APPROVE)
    else:
        require(actor.role_code, Perm.ESTIMATE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        version = repos.versions.get_or_raise(version_id)
        old = version.status
        version.status = status
        version.note = note or version.note
        if status == EstimateStatus.APPROVED.value:
            version.approved_by_id = actor.id
            version.approved_at = datetime.now()
        action = (
            audit_service.Action.APPROVE
            if status == EstimateStatus.APPROVED.value
            else audit_service.Action.UPDATE
        )
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=action,
            entity_type="EstimateVersion",
            entity_id=version_id,
            project_id=version.project_id,
            description=f"estimate v{version.version_no}",
            old_value=old,
            new_value=status,
        )


def create_new_version(project_id: int, actor: CurrentUser, note: str = "") -> int:
    """Clone the current version into a new editable draft."""
    require(actor.role_code, Perm.ESTIMATE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        source = repos.versions.current(project_id)
        if source is None:
            raise LookupError("no current estimate version")
        highest = max(v.version_no for v in repos.versions.for_project(project_id))
        source.is_current = False
        clone = repos.versions.create(
            project_id=project_id,
            version_no=highest + 1,
            status=EstimateStatus.DRAFT.value,
            is_current=True,
            created_by_id=actor.id,
            note=note,
        )
        mapping: dict[int, int] = {}
        for section in repos.sections.for_version(source.id):
            new_section = repos.sections.create(
                version_id=clone.id,
                parent_id=mapping.get(section.parent_id) if section.parent_id else None,
                code=section.code,
                name=section.name,
                order_index=section.order_index,
            )
            mapping[section.id] = new_section.id
        for item in repos.items.for_version(source.id):
            repos.items.create(
                section_id=mapping[item.section_id],
                code=item.code,
                name=item.name,
                category=item.category,
                unit=item.unit,
                quantity=item.quantity,
                plan_unit_price=item.plan_unit_price,
                actual_cost=0.0,
                progress_percent=item.progress_percent,
                responsible_id=item.responsible_id,
                status=item.status,
                note=item.note,
                order_index=item.order_index,
            )
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.CREATE,
            entity_type="EstimateVersion",
            entity_id=clone.id,
            project_id=project_id,
            description=f"estimate v{clone.version_no}",
            old_value=f"v{source.version_no}",
            new_value=f"v{clone.version_no}",
        )
        return clone.id


def set_current_version(version_id: int, actor: CurrentUser) -> None:
    """Make ``version_id`` the version used for cost calculations."""
    require(actor.role_code, Perm.ESTIMATE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        version = repos.versions.get_or_raise(version_id)
        for other in repos.versions.for_project(version.project_id):
            other.is_current = other.id == version_id
        session.flush()


def compare_versions(left_id: int, right_id: int) -> list[dict]:
    """Return per-item differences between two estimate versions."""
    with session_scope() as session:
        repos = Repositories(session)
        left = {(_key(i)): i for i in repos.items.for_version(left_id)}
        right = {(_key(i)): i for i in repos.items.for_version(right_id)}
        rows: list[dict] = []
        for key in sorted(set(left) | set(right)):
            old, new = left.get(key), right.get(key)
            row = {
                "name": (new or old).name,
                "code": (new or old).code or "",
                "old_qty": old.quantity if old else None,
                "new_qty": new.quantity if new else None,
                "old_price": old.plan_unit_price if old else None,
                "new_price": new.plan_unit_price if new else None,
                "old_total": old.plan_total if old else 0.0,
                "new_total": new.plan_total if new else 0.0,
            }
            row["delta"] = round(row["new_total"] - row["old_total"], 2)
            if old is None:
                row["change"] = "added"
            elif new is None:
                row["change"] = "removed"
            elif abs(row["delta"]) > 0.005 or old.quantity != new.quantity:
                row["change"] = "changed"
            else:
                row["change"] = "same"
            rows.append(row)
        return rows


def _key(item: EstimateItem) -> str:
    return f"{item.code}|{item.name}".lower()


def bulk_import(version_id: int, rows: list[dict], actor: CurrentUser) -> int:
    """Import ``rows`` (from Excel) into a version. Returns imported item count."""
    require(actor.role_code, Perm.ESTIMATE_EDIT)
    with session_scope() as session:
        version = _assert_editable(session, version_id)
        repos = Repositories(session)
        sections: dict[str, int] = {
            s.name.strip().lower(): s.id for s in repos.sections.for_version(version_id)
        }
        imported = 0
        for row in rows:
            section_name = (row.get("section") or "Import").strip()
            key = section_name.lower()
            if key not in sections:
                order = len(sections)
                created = repos.sections.create(
                    version_id=version_id,
                    name=section_name,
                    code=str(order + 1),
                    order_index=order,
                )
                sections[key] = created.id
            repos.items.create(
                section_id=sections[key],
                code=str(row.get("code") or ""),
                name=str(row.get("name") or "").strip() or "—",
                category=str(row.get("category") or ""),
                unit=str(row.get("unit") or "piece"),
                quantity=float(row.get("quantity") or 0.0),
                plan_unit_price=float(row.get("price") or 0.0),
                note=str(row.get("note") or ""),
                order_index=imported,
            )
            imported += 1
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.CREATE,
            entity_type="EstimateVersion",
            entity_id=version_id,
            project_id=version.project_id,
            description=f"Excel import: {imported} items",
        )
        return imported


def guard_edit(actor: CurrentUser, tree: EstimateTree) -> None:
    """Raise when ``actor`` may not edit ``tree`` (used by the UI before dialogs)."""
    if not actor.can(Perm.ESTIMATE_EDIT):
        raise PermissionDenied(Perm.ESTIMATE_EDIT)
    if not tree.editable:
        raise EstimateLocked(tree.status)
