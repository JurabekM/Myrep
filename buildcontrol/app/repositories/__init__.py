"""Typed repositories for the ORM entities."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.entities import (
    Attachment,
    AuditLog,
    CompanySettings,
    Counterparty,
    DailySiteLog,
    EstimateItem,
    EstimateSection,
    EstimateVersion,
    Expense,
    Material,
    Payment,
    Project,
    ProjectMember,
    PurchaseOrder,
    PurchaseRequest,
    RefItem,
    Role,
    SupplierQuote,
    User,
    WarehouseTransaction,
    WorkStage,
)
from app.models.enums import CounterpartyKind
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    model = Role

    def by_code(self, code: str) -> Role | None:
        return self.session.scalar(select(Role).where(Role.code == code))


class UserRepository(BaseRepository[User]):
    model = User

    def by_username(self, username: str) -> User | None:
        """Case-insensitive username lookup."""
        return self.session.scalar(
            select(User).where(User.username == (username or "").strip().lower())
        )

    def active(self) -> list[User]:
        return self.list(filters=[User.is_active.is_(True)], order_by=User.full_name)


class ProjectRepository(BaseRepository[Project]):
    model = Project

    def search(
        self,
        text: str = "",
        status: str = "",
        include_archived: bool = False,
    ) -> list[Project]:
        """Filter projects by free text and status."""
        filters = []
        if text:
            pattern = f"%{text.strip()}%"
            filters.append(
                or_(
                    Project.name.ilike(pattern),
                    Project.client.ilike(pattern),
                    Project.address.ilike(pattern),
                    Project.code.ilike(pattern),
                )
            )
        if status:
            filters.append(Project.status == status)
        return self.list(
            filters=filters,
            order_by=Project.created_at.desc(),
            include_archived=include_archived,
        )

    def next_code(self) -> str:
        """Generate the next sequential project code (``PRJ-0007``)."""
        count = self.session.scalar(select(Project.id).order_by(Project.id.desc()).limit(1)) or 0
        return f"PRJ-{count + 1:04d}"


class ProjectMemberRepository(BaseRepository[ProjectMember]):
    model = ProjectMember


class EstimateVersionRepository(BaseRepository[EstimateVersion]):
    model = EstimateVersion

    def for_project(self, project_id: int) -> list[EstimateVersion]:
        return self.list(
            filters=[EstimateVersion.project_id == project_id],
            order_by=EstimateVersion.version_no.desc(),
        )

    def current(self, project_id: int) -> EstimateVersion | None:
        """Return the version currently shown/edited for a project."""
        return self.session.scalar(
            select(EstimateVersion)
            .where(
                EstimateVersion.project_id == project_id,
                EstimateVersion.is_current.is_(True),
            )
            .order_by(EstimateVersion.version_no.desc())
        )


class EstimateSectionRepository(BaseRepository[EstimateSection]):
    model = EstimateSection

    def for_version(self, version_id: int) -> list[EstimateSection]:
        return self.list(
            filters=[EstimateSection.version_id == version_id],
            order_by=EstimateSection.order_index,
        )


class EstimateItemRepository(BaseRepository[EstimateItem]):
    model = EstimateItem

    def for_version(self, version_id: int) -> list[EstimateItem]:
        stmt = (
            select(EstimateItem)
            .join(EstimateSection, EstimateItem.section_id == EstimateSection.id)
            .where(EstimateSection.version_id == version_id)
            .order_by(EstimateItem.order_index)
        )
        return list(self.session.scalars(stmt).all())

    def for_project(self, project_id: int) -> list[EstimateItem]:
        stmt = (
            select(EstimateItem)
            .join(EstimateSection, EstimateItem.section_id == EstimateSection.id)
            .join(EstimateVersion, EstimateSection.version_id == EstimateVersion.id)
            .where(
                EstimateVersion.project_id == project_id,
                EstimateVersion.is_current.is_(True),
            )
            .order_by(EstimateItem.order_index)
        )
        return list(self.session.scalars(stmt).all())


class CounterpartyRepository(BaseRepository[Counterparty]):
    model = Counterparty

    def suppliers(self) -> list[Counterparty]:
        return self.list(
            filters=[Counterparty.kind == CounterpartyKind.SUPPLIER.value],
            order_by=Counterparty.name,
        )

    def contractors(self) -> list[Counterparty]:
        return self.list(
            filters=[Counterparty.kind == CounterpartyKind.CONTRACTOR.value],
            order_by=Counterparty.name,
        )


class PurchaseRequestRepository(BaseRepository[PurchaseRequest]):
    model = PurchaseRequest

    def for_project(self, project_id: int) -> list[PurchaseRequest]:
        return self.list(
            filters=[PurchaseRequest.project_id == project_id],
            order_by=PurchaseRequest.created_at.desc(),
        )

    def next_number(self) -> str:
        last = self.session.scalar(
            select(PurchaseRequest.id).order_by(PurchaseRequest.id.desc()).limit(1)
        )
        return f"XT-{(last or 0) + 1:05d}"


class SupplierQuoteRepository(BaseRepository[SupplierQuote]):
    model = SupplierQuote

    def for_request(self, request_id: int) -> list[SupplierQuote]:
        return self.list(
            filters=[SupplierQuote.request_id == request_id],
            order_by=SupplierQuote.unit_price,
        )


class PurchaseOrderRepository(BaseRepository[PurchaseOrder]):
    model = PurchaseOrder

    def next_number(self) -> str:
        last = self.session.scalar(
            select(PurchaseOrder.id).order_by(PurchaseOrder.id.desc()).limit(1)
        )
        return f"PO-{(last or 0) + 1:05d}"


class MaterialRepository(BaseRepository[Material]):
    model = Material

    def by_sku(self, sku: str) -> Material | None:
        return self.session.scalar(select(Material).where(Material.sku == sku))


class WarehouseTransactionRepository(BaseRepository[WarehouseTransaction]):
    model = WarehouseTransaction

    def for_material(self, material_id: int) -> list[WarehouseTransaction]:
        return self.list(
            filters=[WarehouseTransaction.material_id == material_id],
            order_by=WarehouseTransaction.tx_date.desc(),
        )

    def for_project(self, project_id: int) -> list[WarehouseTransaction]:
        return self.list(
            filters=[WarehouseTransaction.project_id == project_id],
            order_by=WarehouseTransaction.tx_date.desc(),
        )


class WorkStageRepository(BaseRepository[WorkStage]):
    model = WorkStage

    def for_project(self, project_id: int) -> list[WorkStage]:
        return self.list(
            filters=[WorkStage.project_id == project_id],
            order_by=WorkStage.order_index,
        )


class DailySiteLogRepository(BaseRepository[DailySiteLog]):
    model = DailySiteLog

    def for_project(self, project_id: int) -> list[DailySiteLog]:
        return self.list(
            filters=[DailySiteLog.project_id == project_id],
            order_by=DailySiteLog.log_date.desc(),
        )


class ExpenseRepository(BaseRepository[Expense]):
    model = Expense

    def for_project(self, project_id: int) -> list[Expense]:
        return self.list(
            filters=[Expense.project_id == project_id],
            order_by=Expense.pay_date.desc(),
        )


class PaymentRepository(BaseRepository[Payment]):
    model = Payment


class AttachmentRepository(BaseRepository[Attachment]):
    model = Attachment

    def for_entity(self, entity_type: str, entity_id: int) -> list[Attachment]:
        return self.list(
            filters=[
                Attachment.entity_type == entity_type,
                Attachment.entity_id == entity_id,
            ],
            order_by=Attachment.created_at.desc(),
        )


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def recent(self, limit: int = 100, project_id: int | None = None) -> list[AuditLog]:
        filters = [AuditLog.project_id == project_id] if project_id else []
        return self.list(filters=filters, order_by=AuditLog.ts.desc(), limit=limit)


class RefItemRepository(BaseRepository[RefItem]):
    model = RefItem

    def of_kind(self, kind: str) -> list[RefItem]:
        return self.list(filters=[RefItem.kind == kind], order_by=RefItem.order_index)


class CompanySettingsRepository(BaseRepository[CompanySettings]):
    model = CompanySettings

    def get_or_create(self) -> CompanySettings:
        """Return the singleton settings row, creating it on first access."""
        row = self.session.scalar(select(CompanySettings).limit(1))
        if row is None:
            row = self.create(name="BuildControl")
        return row


class Repositories:
    """Bundle giving services one entry point per session."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.roles = RoleRepository(session)
        self.users = UserRepository(session)
        self.projects = ProjectRepository(session)
        self.members = ProjectMemberRepository(session)
        self.versions = EstimateVersionRepository(session)
        self.sections = EstimateSectionRepository(session)
        self.items = EstimateItemRepository(session)
        self.counterparties = CounterpartyRepository(session)
        self.requests = PurchaseRequestRepository(session)
        self.quotes = SupplierQuoteRepository(session)
        self.orders = PurchaseOrderRepository(session)
        self.materials = MaterialRepository(session)
        self.stock = WarehouseTransactionRepository(session)
        self.stages = WorkStageRepository(session)
        self.logs = DailySiteLogRepository(session)
        self.expenses = ExpenseRepository(session)
        self.payments = PaymentRepository(session)
        self.attachments = AttachmentRepository(session)
        self.audit = AuditLogRepository(session)
        self.refs = RefItemRepository(session)
        self.company = CompanySettingsRepository(session)
